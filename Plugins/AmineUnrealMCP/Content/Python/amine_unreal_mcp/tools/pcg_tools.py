import json
import unreal
import toolset_registry
from ..common.runtime import guarded, asset, object_info, actor
from ..common.validation import ToolError


@unreal.uclass()
class AminePCGTools(unreal.ToolsetDefinition):
    """PCG graph/component inspection; graph authoring delegates to installed Epic PCGToolset."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_pcg_graph_info(graph_path: str) -> str:
        """Inspect an exact PCGGraph asset and exposed property schemas; no generation is triggered."""
        cls = getattr(unreal, "PCGGraph", None)
        if not cls:
            raise ToolError("plugin_unavailable", "Enable PCG and restart the editor.")
        obj = asset(graph_path, cls)
        return {"graph": object_info(obj), "properties": json.loads(unreal.ToolsetLibrary.list_struct_properties(obj.get_class()))}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_pcg_components(actor_identifier: str) -> str:
        """List exact PCG component paths on one actor. Use component property/reflection tools for safe editing."""
        cls = getattr(unreal, "PCGComponent", None)
        if not cls:
            raise ToolError("plugin_unavailable", "Enable PCG and restart the editor.")
        return [object_info(c) for c in actor(actor_identifier).get_components_by_class(cls)]
