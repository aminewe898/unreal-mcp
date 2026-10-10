import unreal
import toolset_registry
from ..common.runtime import guarded, actor, object_info, mutation, eas, actor_info
from ..common.validation import finite, ToolError


def light_component(identifier):
    components = actor(identifier).get_components_by_class(unreal.LightComponent)
    if len(components) != 1:
        raise ToolError("light_not_found", "Actor must contain exactly one LightComponent.")
    return components[0]


@unreal.uclass()
class AmineLightingTools(unreal.ToolsetDefinition):
    """Create and adjust supported editor light actors."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_light(kind: str = "point", label: str = "MCP_Light", location: unreal.Vector = unreal.Vector(), rotation: unreal.Rotator = unreal.Rotator()) -> str:
        """Create one light: directional, point, spot, rect or sky. Position in cm, rotation in degrees. Does not save."""
        classes = {"directional": unreal.DirectionalLight, "point": unreal.PointLight, "spot": unreal.SpotLight, "rect": unreal.RectLight, "sky": unreal.SkyLight}
        if kind not in classes:
            raise ToolError("invalid_light_kind", "Use directional, point, spot, rect or sky.")
        finite([location.x, location.y, location.z, rotation.pitch, rotation.yaw, rotation.roll])
        with mutation("Create light"):
            obj = eas().spawn_actor_from_class(classes[kind], location, rotation)
            if not obj:
                raise ToolError("spawn_failed", "Unreal refused light creation.")
            obj.set_actor_label(label)
        return actor_info(obj, True)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_light_intensity(identifier: str, intensity: float) -> str:
        """Set a light's nonnegative intensity in its currently configured Unreal units."""
        finite([intensity])
        if intensity < 0:
            raise ToolError("invalid_intensity", "Intensity cannot be negative.")
        obj = light_component(identifier)
        with mutation("Set light intensity", obj):
            obj.set_intensity(intensity)
        return {"component": obj.get_path_name(), "intensity": intensity}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_light_color(identifier: str, color: unreal.LinearColor) -> str:
        """Set a light color from linear RGBA. Unreal's sRGB conversion is disabled for this linear input."""
        finite([color.r, color.g, color.b, color.a])
        obj = light_component(identifier)
        with mutation("Set light color", obj):
            obj.set_light_color(color, False)
        return object_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_light_temperature(identifier: str, kelvin: float, enabled: bool = True) -> str:
        """Set color temperature to 1000..15000 K and toggle temperature use."""
        if not 1000 <= kelvin <= 15000:
            raise ToolError("invalid_temperature", "Temperature must be 1000..15000 K.")
        obj = light_component(identifier)
        with mutation("Set light temperature", obj):
            obj.set_use_temperature(enabled)
            obj.set_temperature(kelvin)
        return {"kelvin": kelvin, "enabled": enabled}
