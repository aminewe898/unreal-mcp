import unreal
import toolset_registry
from ..common.runtime import guarded, actor, vector, rotation as rotation_info, eas
from ..common.validation import ToolError


@unreal.uclass()
class AmineViewportTools(unreal.ToolsetDefinition):
    """Actual level viewport images with camera/map context for visual iteration."""

    @toolset_registry.tool_call
    @staticmethod
    def capture_viewport(width: int = 1280, height: int = 720) -> unreal.AmineViewportCapture:
        """Return a real MCP PNG image plus camera/map metadata from the active level framebuffer. Letterboxed; 64..2560 x 64..1440. Requires a rendered editor viewport."""
        if not 64 <= width <= 2560 or not 64 <= height <= 1440:
            raise ValueError("invalid_resolution: use 64..2560 width and 64..1440 height")
        result = unreal.AmineMCPBridge.capture_viewport(width, height)
        if not result.image.data:
            raise RuntimeError("viewport_capture_failed: no rendered active level viewport, or framebuffer/PNG encoding failed")
        return result

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_viewport_camera() -> str:
        """Return level viewport camera position in cm and rotation in degrees."""
        location, camera_rotation = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
        return {"location": vector(location), "rotation": rotation_info(camera_rotation)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_viewport_camera(location: unreal.Vector, rotation: unreal.Rotator) -> str:
        """Move the editor camera; actor transforms and assets remain unchanged."""
        from ..common.validation import finite
        finite([location.x, location.y, location.z, rotation.pitch, rotation.yaw, rotation.roll])
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(location, rotation)
        return {"location": vector(location), "rotation": rotation_info(rotation)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def focus_actor(identifier: str) -> str:
        """Frame one resolved actor in the level viewport. Requires PIE to be stopped."""
        obj = actor(identifier)
        if unreal.AmineMCPBridge.is_pie_running():
            raise ToolError("pie_active", "Stop PIE before framing editor actors.")
        unreal.AmineMCPBridge.focus_actors([obj])
        return {"focused": obj.get_path_name()}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def frame_selection() -> str:
        """Frame the current actor selection; fail if no actors are selected."""
        objects = list(eas().get_selected_level_actors())
        if not objects:
            raise ToolError("empty_selection", "Select actors before framing them.")
        if unreal.AmineMCPBridge.is_pie_running():
            raise ToolError("pie_active", "Stop PIE before framing editor actors.")
        unreal.AmineMCPBridge.focus_actors(objects)
        return {"focused": [a.get_path_name() for a in objects]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def pilot_camera(identifier: str) -> str:
        """Pilot the viewport through a camera actor."""
        if unreal.AmineMCPBridge.is_pie_running():
            raise ToolError('pie_active', 'Stop PIE before piloting a camera.')
        obj = actor(identifier)
        if not isinstance(obj, unreal.CameraActor):
            raise ToolError('not_camera', 'Requires a CameraActor or CineCameraActor.')
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        subsystem.pilot_level_actor(obj)
        subsystem.set_exact_camera_view(True)
        if subsystem.get_pilot_level_actor() != obj:
            raise ToolError('pilot_failed', 'Camera pilot was not applied.')
        return {
            'piloted': obj.get_path_name(),
            'exact_camera_view': subsystem.get_exact_camera_view(),
        }

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def eject_camera() -> str:
        """Eject the viewport from any piloted camera."""
        if unreal.AmineMCPBridge.is_pie_running():
            raise ToolError('pie_active', 'Stop PIE before piloting a camera.')
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        subsystem.eject_pilot_level_actor()
        return {'piloted': None}
