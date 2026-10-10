import json
from pathlib import Path
import unreal
import toolset_registry
from ..common.runtime import guarded, actor_info, eas, world, class_ref
from ..version import VERSION


@unreal.uclass()
class AmineProjectTools(unreal.ToolsetDefinition):
    """Inspect the active project and editor without dumping private configuration."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_project_info() -> str:
        """Return project paths, engine version, enabled plugins, modules and active map."""
        path = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path()))
        descriptor = json.loads(path.read_text(encoding="utf-8-sig"))
        return {"plugin_version": VERSION, "project_name": path.stem, "project_file": str(path), "project_path": str(path.parent),
                "engine_version": unreal.SystemLibrary.get_engine_version(), "engine_path": unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_dir()),
                "active_map": world().get_path_name(), "plugins": descriptor.get("Plugins", []), "modules": descriptor.get("Modules", []),
                "content_directories": [unreal.Paths.project_content_dir()]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_editor_state() -> str:
        """Return map, current level, selection, actor count, PIE and dirty packages."""
        level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).get_current_level()
        return {"map": world().get_path_name(), "world_name": world().get_name(), "current_level": level.get_path_name() if level else None,
                "selected_actors": [actor_info(a) for a in eas().get_selected_level_actors()], "actor_count": len(eas().get_all_level_actors()),
                "pie_running": unreal.AmineMCPBridge.is_pie_running(), "dirty_packages": list(unreal.AmineMCPBridge.get_dirty_packages())}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_project_settings() -> str:
        """Read only renderer settings relevant to lighting; omit arbitrary config and credentials."""
        settings = unreal.get_default_object(class_ref("/Script/Engine.RendererSettings"))
        return json.loads(unreal.ToolsetLibrary.get_object_properties(settings, ["DynamicGlobalIllumination", "Reflections", "bAllowStaticLighting"]))
