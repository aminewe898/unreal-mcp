#include "AmineMCPBridge.h"
#include "Editor.h"
#include "EditorViewportClient.h"
#include "LevelEditorViewport.h"
#include "FileHelpers.h"
#include "ImageUtils.h"
#include "Misc/OutputDevice.h"
#include "Misc/OutputDeviceRedirector.h"
#include "Misc/ScopeLock.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"
#include "UObject/UnrealType.h"
#include "UObject/StrongObjectPtr.h"
#include "ToolsetRegistry/ToolsetRegistrySubsystem.h"
#include "IModelContextProtocolModule.h"
#include "IModelContextProtocolTool.h"
#include "Async/Async.h"
#include "Containers/Ticker.h"

namespace
{
struct FLogEntry { FString Category; FString Severity; FString Message; };
class FAmineLogSink final : public FOutputDevice
{
public:
    FCriticalSection Mutex;
    TArray<FLogEntry> Entries;
    virtual bool CanBeUsedOnAnyThread() const override { return true; }
    virtual void Serialize(const TCHAR* Message, ELogVerbosity::Type Verbosity, const FName& Category) override
    {
        const auto V = Verbosity & ELogVerbosity::VerbosityMask;
        FString Severity = V <= ELogVerbosity::Error ? TEXT("error") : V == ELogVerbosity::Warning ? TEXT("warning") : TEXT("info");
        FScopeLock Lock(&Mutex);
        if (Entries.Num() >= 2000) Entries.RemoveAt(0, 100, EAllowShrinking::No);
        Entries.Add({Category.ToString(), Severity, FString(Message).Left(4096)});
    }
};
FAmineLogSink Sink;
TMap<FString, TSharedPtr<UE::ToolsetRegistry::FToolset>> EpicToolsets;
TArray<FTSTicker::FDelegateHandle> TimeoutHandles;
}

// Epic's registry adapter serializes every result as text. Register the image
// tool through its public MCP interface so clients receive image content.
class FAmineCaptureTool final : public IModelContextProtocolTool
{
public:
    FString GetName() const override { return TEXT("amine_capture_viewport"); }
    FString GetDescription() const override { return TEXT("Capture the actual active level viewport as a PNG image content block with map, camera and dimensions. Prefer this native tool for visual inspection; registry capture_viewport returns JSON text."); }
    TSharedPtr<FJsonObject> GetInputJsonSchema() const override
    {
        auto Schema = MakeShared<FJsonObject>();
        Schema->SetStringField(TEXT("type"), TEXT("object"));
        Schema->SetBoolField(TEXT("additionalProperties"), false);
        auto Props = MakeShared<FJsonObject>();
        for (const auto& Spec : {TPair<FString, int32>(TEXT("width"), 2560), TPair<FString, int32>(TEXT("height"), 1440)})
        {
            auto Value = MakeShared<FJsonObject>();
            Value->SetStringField(TEXT("type"), TEXT("integer"));
            Value->SetNumberField(TEXT("minimum"), 64);
            Value->SetNumberField(TEXT("maximum"), Spec.Value);
            Value->SetNumberField(TEXT("default"), Spec.Key == TEXT("width") ? 1280 : 720);
            Props->SetObjectField(Spec.Key, Value);
        }
        Schema->SetObjectField(TEXT("properties"), Props);
        return Schema;
    }
    void RunAsync(const FModelContextProtocolToolRequestId&, const TSharedPtr<FJsonObject>& Params, const FResultCallback& Complete) override
    {
        int32 Width = 1280, Height = 720;
        if (Params)
        {
            for (const auto& Pair : Params->Values)
            {
                double Value;
                const int32 Max = Pair.Key == TEXT("width") ? 2560 : 1440;
                if ((Pair.Key != TEXT("width") && Pair.Key != TEXT("height")) || !Pair.Value->TryGetNumber(Value) || !FMath::IsFinite(Value) || Value < 64 || Value > Max || Value != FMath::FloorToDouble(Value))
                {
                    Complete(UE::ModelContextProtocol::MakeErrorResult(TEXT("invalid_resolution: integer width 64..2560, height 64..1440 only")));
                    return;
                }
                (Pair.Key == TEXT("width") ? Width : Height) = int32(Value);
            }
        }
        auto Capture = [Width, Height, Complete]()
        {
            FAmineViewportCapture Frame = UAmineMCPBridge::CaptureViewport(Width, Height);
            if (Frame.Image.Data.IsEmpty())
            {
                Complete(UE::ModelContextProtocol::MakeErrorResult(TEXT("viewport_capture_failed: no rendered active level viewport")));
                return;
            }
            auto Result = UE::ModelContextProtocol::MakeImageResult(Frame.Image.MimeType, MoveTemp(Frame.Image.Data));
            auto Metadata = MakeShared<FJsonObject>();
            Metadata->SetStringField(TEXT("map"), Frame.Map);
            Metadata->SetNumberField(TEXT("width"), Frame.Width);
            Metadata->SetNumberField(TEXT("height"), Frame.Height);
            auto Location = MakeShared<FJsonObject>();
            Location->SetNumberField(TEXT("x"), Frame.CameraLocation.X);
            Location->SetNumberField(TEXT("y"), Frame.CameraLocation.Y);
            Location->SetNumberField(TEXT("z"), Frame.CameraLocation.Z);
            Metadata->SetObjectField(TEXT("camera_location"), Location);
            auto Rotation = MakeShared<FJsonObject>();
            Rotation->SetNumberField(TEXT("pitch"), Frame.CameraRotation.Pitch);
            Rotation->SetNumberField(TEXT("yaw"), Frame.CameraRotation.Yaw);
            Rotation->SetNumberField(TEXT("roll"), Frame.CameraRotation.Roll);
            Metadata->SetObjectField(TEXT("camera_rotation"), Rotation);
            FString Text;
            FJsonSerializer::Serialize(Metadata, TJsonWriterFactory<>::Create(&Text));
            auto Content = Result.JsonObject->GetArrayField(TEXT("content"));
            Content.Add(MakeShared<FJsonValueObject>(UE::ModelContextProtocol::MakeTextContentObject(Text)));
            Result.JsonObject->SetArrayField(TEXT("content"), Content);
            Result.JsonObject->SetObjectField(TEXT("structuredContent"), Metadata);
            Complete(Result);
        };
        if (IsInGameThread()) Capture();
        else AsyncTask(ENamedThreads::GameThread, MoveTemp(Capture));
    }
};

class FAmineUnrealMCPModule final : public IModuleInterface
{
public:
    TSharedPtr<FAmineCaptureTool> CaptureTool;
    FDelegateHandle RefreshHandle;
    void StartupModule() override
    {
        GLog->AddOutputDevice(&Sink);
        CaptureTool = MakeShared<FAmineCaptureTool>();
        auto& MCP = IModelContextProtocolModule::GetChecked();
        MCP.AddTool(CaptureTool.ToSharedRef());
        RefreshHandle = MCP.OnRefreshTools().AddLambda([this]() { IModelContextProtocolModule::GetChecked().AddTool(CaptureTool.ToSharedRef()); });
        UE_LOG(LogTemp, Display, TEXT("[AmineUnrealMCP] Native bridge loaded"));
    }
    void ShutdownModule() override
    {
        if (auto* MCP = IModelContextProtocolModule::Get())
        {
            MCP->OnRefreshTools().Remove(RefreshHandle);
            if (CaptureTool) MCP->RemoveTool(CaptureTool.ToSharedRef());
        }
        CaptureTool.Reset();
        for (auto Handle : TimeoutHandles) FTSTicker::GetCoreTicker().RemoveTicker(Handle);
        TimeoutHandles.Reset();
        EpicToolsets.Reset();
        if (GLog) GLog->RemoveOutputDevice(&Sink);
    }
};
IMPLEMENT_MODULE(FAmineUnrealMCPModule, AmineUnrealMCP)

FAmineViewportCapture UAmineMCPBridge::CaptureViewport(int32 Width, int32 Height)
{
    FAmineViewportCapture Out;
    if (!IsInGameThread() || Width < 64 || Height < 64 || Width > 2560 || Height > 1440) return Out;
    FEditorViewportClient* Client = GCurrentLevelEditingViewportClient;
    if (!Client || !Client->Viewport) return Out;
    const FIntPoint Size = Client->Viewport->GetSizeXY();
    if (Size.X <= 0 || Size.Y <= 0 || int64(Size.X) * Size.Y > 16777216) return Out;
    // The active framebuffer is rendered/read synchronously; no polling or filesystem callbacks.
    Client->Viewport->Draw();
    TArray<FColor> Source;
    if (!GetViewportScreenShot(Client->Viewport, Source)) return Out;
    for (auto& Pixel : Source) Pixel.A = 255;
    // Letterbox to preserve the viewport's aspect ratio rather than stretching the scene.
    const double Factor = FMath::Min(double(Width) / Size.X, double(Height) / Size.Y);
    const int32 RW = FMath::Max(1, FMath::RoundToInt(Size.X * Factor));
    const int32 RH = FMath::Max(1, FMath::RoundToInt(Size.Y * Factor));
    TArray<FColor> Resized;
    FImageUtils::ImageResize(Size.X, Size.Y, Source, RW, RH, Resized, true);
    TArray<FColor> Bitmap;
    Bitmap.Init(FColor::Black, Width * Height);
    const int32 X = (Width - RW) / 2, Y = (Height - RH) / 2;
    for (int32 Row = 0; Row < RH; ++Row)
        FMemory::Memcpy(Bitmap.GetData() + (Y + Row) * Width + X, Resized.GetData() + Row * RW, RW * sizeof(FColor));
    if (!Out.Image.SetFromBitmap(Bitmap, FIntPoint(Width, Height))) return Out;
    Out.Width = Width; Out.Height = Height;
    Out.CameraLocation = Client->GetViewLocation(); Out.CameraRotation = Client->GetViewRotation();
    if (Client->GetWorld()) Out.Map = Client->GetWorld()->GetPathName();
    return Out;
}

FString UAmineMCPBridge::GetRecentLogs(const FString& Severity, const FString& Substring, int32 MaxLines)
{
    TArray<TSharedPtr<FJsonValue>> Rows;
    {
        FScopeLock Lock(&Sink.Mutex);
        for (int32 I = Sink.Entries.Num() - 1; I >= 0 && Rows.Num() < FMath::Clamp(MaxLines, 1, 500); --I)
        {
            const auto& E = Sink.Entries[I];
            if ((!Severity.IsEmpty() && E.Severity != Severity) || (!Substring.IsEmpty() && !E.Message.Contains(Substring))) continue;
            auto Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("category"), E.Category); Row->SetStringField(TEXT("severity"), E.Severity);
            Row->SetStringField(TEXT("message"), E.Message); Rows.Insert(MakeShared<FJsonValueObject>(Row), 0);
        }
    }
    FString Output;
    FJsonSerializer::Serialize(Rows, TJsonWriterFactory<>::Create(&Output));
    return Output;
}
void UAmineMCPBridge::ClearLogBuffer() { FScopeLock Lock(&Sink.Mutex); Sink.Entries.Reset(); }
TArray<FString> UAmineMCPBridge::GetDirtyPackages()
{
    TArray<UPackage*> Packages;
    FEditorFileUtils::GetDirtyPackages(Packages);
    TArray<FString> Names;
    for (auto* Package : Packages) Names.AddUnique(Package->GetName());
    Names.Sort(); return Names;
}
TArray<FString> UAmineMCPBridge::ListClassFunctions(UClass* Class, int32 MaxResults)
{
    TArray<FString> Names;
    if (Class) for (TFieldIterator<UFunction> It(Class); It && Names.Num() < FMath::Clamp(MaxResults, 1, 500); ++It)
        if (It->HasAnyFunctionFlags(FUNC_BlueprintCallable)) Names.Add(It->GetName());
    Names.Sort(); return Names;
}
bool UAmineMCPBridge::SetPIEPaused(bool bPaused)
{
    if (!IsInGameThread() || !GEditor || !GEditor->PlayWorld) return false;
    GEditor->PlayWorld->bDebugPauseExecution = bPaused; return true;
}

bool UAmineMCPBridge::IsPIERunning() { return GEditor && GEditor->PlayWorld; }
void UAmineMCPBridge::FocusActors(const TArray<AActor*>& Actors)
{
    if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || Actors.IsEmpty() || !GCurrentLevelEditingViewportClient) return;
    FBox Bounds(ForceInit);
    for (AActor* Actor : Actors)
    {
        if (!IsValid(Actor)) continue;
        FBox ActorBounds = Actor->GetComponentsBoundingBox(true);
        if (!ActorBounds.IsValid || ActorBounds.GetExtent().IsNearlyZero())
            ActorBounds = FBox::BuildAABB(Actor->GetActorLocation(), FVector(50.0));
        Bounds += ActorBounds;
    }
    if (Bounds.IsValid) GCurrentLevelEditingViewportClient->FocusViewportOnBox(Bounds, true);
}
bool UAmineMCPBridge::CacheEpicToolsets()
{
    auto Subsystem = UToolsetRegistrySubsystem::Get();
    if (Subsystem.HasError()) return false;
    for (const FString& Name : {FString(TEXT("EditorToolset.EditorAppToolset")), FString(TEXT("AutomationTestToolset.AutomationTestToolset"))})
    {
        auto Handler = Subsystem.GetValue()->ToolsetRegistry.Find(Name);
        if (Handler) EpicToolsets.Add(Name, Handler);
    }
    return EpicToolsets.Contains(TEXT("EditorToolset.EditorAppToolset"));
}
UToolCallAsyncResultString* UAmineMCPBridge::ExecuteEpicTool(const FString& ToolsetName, const FString& ToolName, const FString& ArgumentsJson)
{
    TStrongObjectPtr<UToolCallAsyncResultString> Result(NewObject<UToolCallAsyncResultString>());
    const TMap<FString, TSet<FString>> Allowed = {
        {TEXT("EditorToolset.EditorAppToolset"), {TEXT("StartPIE"), TEXT("StopPIE"), TEXT("SelectAssets")}},
        {TEXT("AutomationTestToolset.AutomationTestToolset"), {TEXT("DiscoverTests"), TEXT("ListTests"), TEXT("RunTests"), TEXT("GetTestStatus"), TEXT("GetTestResults"), TEXT("StopTests")}}
    };
    auto Names = Allowed.Find(ToolsetName);
    auto Handler = EpicToolsets.Find(ToolsetName);
    if (!IsInGameThread() || !Names || !Names->Contains(ToolName) || !Handler || ArgumentsJson.Len() > 65536)
    {
        Result->SetError(TEXT("unsupported_builtin_tool: internal bridge accepts only a fixed list of verified Epic operations on the editor thread"));
        return Result.Get();
    }
    (*Handler)->ExecuteTool(ToolName, ArgumentsJson).Next([Result](TValueOrError<FString, FString>&& Value)
    {
        if (Value.HasError()) Result->SetError(Value.StealError());
        else
        {
            FString Payload = Value.StealValue();
            TSharedPtr<FJsonObject> Envelope;
            FString Text;
            if (FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Payload), Envelope) && Envelope)
            {
                if (Envelope->TryGetStringField(TEXT("returnValue"), Text)) Payload = MoveTemp(Text);
                else if (auto Field = Envelope->TryGetField(TEXT("returnValue")); Field && Field->IsNull()) Payload = TEXT("null");
            }
            Result->SetValue(Payload);
        }
    });
    if (ToolsetName == TEXT("AutomationTestToolset.AutomationTestToolset") && ToolName == TEXT("RunTests") && !Result->bIsComplete)
    {
        const double Started = FPlatformTime::Seconds();
        auto Handle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Result, Started](float)
        {
            if (Result->bIsComplete) return false;
            if (FPlatformTime::Seconds() - Started < 45.0) return true;
            Result->SetError(TEXT("automation_timeout: requested run exceeded 45 seconds and was stopped"));
            if (auto Handler = EpicToolsets.Find(TEXT("AutomationTestToolset.AutomationTestToolset")))
                (*Handler)->ExecuteTool(TEXT("StopTests"), TEXT("{}"));
            return false;
        }), 0.1f);
        // Only one automation run is permitted. Old completed ticker handles
        // can be removed safely, keeping shutdown bookkeeping bounded.
        if (TimeoutHandles.Num() >= 64)
        {
            FTSTicker::GetCoreTicker().RemoveTicker(TimeoutHandles[0]);
            TimeoutHandles.RemoveAt(0);
        }
        TimeoutHandles.Add(Handle);
    }
    return Result.Get();
}
