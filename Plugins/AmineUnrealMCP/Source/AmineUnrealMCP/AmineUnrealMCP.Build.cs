using UnrealBuildTool;

public class AmineUnrealMCP : ModuleRules
{
    public AmineUnrealMCP(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "ToolsetRegistry" });
        PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "Json", "JsonUtilities", "ImageWrapper", "RenderCore", "ModelContextProtocol" });
    }
}
