import unreal
import toolset_registry
from ..common.runtime import guarded, asset, object_info, actor, mutation, eas, actor_info
from ..common.validation import ToolError


@unreal.uclass()
class AmineNiagaraTools(unreal.ToolsetDefinition):
    """Niagara system inspection and placement; optional plugin capability checks."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_niagara_system_info(system_path: str) -> str:
        """Inspect an existing NiagaraSystem. Discover Epic Niagara toolsets for deeper emitter/module graph operations."""
        cls = getattr(unreal, "NiagaraSystem", None)
        if not cls:
            raise ToolError("plugin_unavailable", "Enable Niagara and restart the editor.")
        return object_info(asset(system_path, cls))

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def place_niagara_system(system_path: str, location: unreal.Vector = unreal.Vector(), label: str = "MCP_Niagara") -> str:
        """Place one existing NiagaraSystem as a NiagaraActor, without changing the system asset."""
        cls = getattr(unreal, "NiagaraActor", None)
        system_cls = getattr(unreal, "NiagaraSystem", None)
        if not cls or not system_cls:
            raise ToolError("plugin_unavailable", "Enable Niagara and restart the editor.")
        system = asset(system_path, system_cls)
        with mutation("Place Niagara system"):
            obj = eas().spawn_actor_from_class(cls, location)
            if not obj:
                raise ToolError("spawn_failed", "Could not create NiagaraActor.")
            obj.set_actor_label(label)
            components = obj.get_components_by_class(unreal.NiagaraComponent)
            if not components:
                raise ToolError("component_missing", "NiagaraActor has no NiagaraComponent.")
            components[0].modify()
            components[0].set_asset(system)
        return actor_info(obj, True)
