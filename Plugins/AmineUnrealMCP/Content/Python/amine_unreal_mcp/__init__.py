"""AmineUnrealMCP 0.1.0 registration and development reload entry point."""
import importlib
import unreal
import toolset_registry
from toolset_registry.registration import Registration

MODULES = ("project_tools", "actor_tools", "component_tools", "asset_tools", "blueprint_tools", "viewport_tools", "editor_tools", "gameplay_tools", "debug_tools", "reflection_tools", "material_tools", "lighting_tools", "sequencer_tools", "testing_tools", "niagara_tools", "pcg_tools")
_registration = None


def register():
    global _registration
    classes = []
    for module_name in MODULES:
        module = importlib.import_module(f"{__name__}.tools.{module_name}")
        classes.extend(value for value in vars(module).values() if isinstance(value, type) and value.__name__.startswith("Amine") and issubclass(value, unreal.ToolsetDefinition))
    _registration = Registration(classes)
    if not _registration.register():
        raise RuntimeError("[AmineUnrealMCP] ToolsetRegistry is unavailable")
    # Epic's tools remain usable by our implementation but the general scripting
    # and filesystem entry points are excluded from the agent-facing registry.
    registry = unreal.ToolsetRegistry
    if not unreal.AmineMCPBridge.cache_epic_toolsets():
        raise RuntimeError("[AmineUnrealMCP] Required Epic editor toolset is unavailable")
    from editor_toolset import toolsets as epic_toolsets
    epic_toolsets._registration.unregister()
    for class_name in ("EditorAppToolset", "LogsToolset", "AgentSkillToolset"):
        cls = getattr(unreal, class_name, None)
        if cls:
            registry.unregister_toolset_class(cls)
    unreal.log(f"[AmineUnrealMCP] Registered {len(classes)} toolsets")


def reload_tools():
    """Editor Python console: amine_unreal_mcp.reload_tools(); then refresh MCP tools."""
    import sys
    toolset_registry.reload_module(sys.modules[__name__])
    register()
    unreal.SystemLibrary.execute_console_command(None, "ModelContextProtocol.RefreshTools")
