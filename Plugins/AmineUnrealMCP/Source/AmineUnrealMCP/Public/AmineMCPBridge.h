#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "ToolsetRegistry/ToolsetImage.h"
#include "ToolsetRegistry/ToolCallAsyncResultString.h"
#include "AmineMCPBridge.generated.h"

USTRUCT(BlueprintType)
struct FAmineViewportCapture
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Amine MCP") FToolsetImage Image;
    UPROPERTY(BlueprintReadOnly, Category="Amine MCP") FString Map;
    UPROPERTY(BlueprintReadOnly, Category="Amine MCP") FVector CameraLocation = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly, Category="Amine MCP") FRotator CameraRotation = FRotator::ZeroRotator;
    UPROPERTY(BlueprintReadOnly, Category="Amine MCP") int32 Width = 0;
    UPROPERTY(BlueprintReadOnly, Category="Amine MCP") int32 Height = 0;
};

UCLASS()
class AMINEUNREALMCP_API UAmineMCPBridge : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static FAmineViewportCapture CaptureViewport(int32 Width = 1280, int32 Height = 720);
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static FString GetRecentLogs(const FString& Severity, const FString& Substring, int32 MaxLines = 100);
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static void ClearLogBuffer();
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static TArray<FString> GetDirtyPackages();
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static TArray<FString> ListClassFunctions(UClass* Class, int32 MaxResults = 100);
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static bool SetPIEPaused(bool bPaused);
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static bool IsPIERunning();
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static void FocusActors(const TArray<AActor*>& Actors);
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static bool CacheEpicToolsets();
    UFUNCTION(BlueprintCallable, Category="Amine MCP") static UToolCallAsyncResultString* ExecuteEpicTool(const FString& ToolsetName, const FString& ToolName, const FString& ArgumentsJson);
};

