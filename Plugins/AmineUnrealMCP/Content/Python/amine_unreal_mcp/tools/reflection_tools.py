import json
import unreal
import toolset_registry
from ..common.runtime import guarded, class_ref, asset, object_info
from ..common.validation import limit, ToolError


def object_ref(identifier):
    if not identifier.startswith(("/Game/", "/Temp/", "/Engine/")) or identifier.startswith("/Engine/Transient"):
        raise ToolError("unsupported_object", "Inspect project/engine assets or live editor actors; configuration and subsystem objects are excluded.")
    obj = unreal.find_object(None, identifier)
    if obj is None and identifier.startswith("/Game/") and ":" not in identifier:
        obj = asset(identifier)
    if obj is None:
        raise ToolError("object_not_found", "Supply a canonical live object path or exact asset path.")
    if isinstance(obj, unreal.Blueprint):
        obj = unreal.get_default_object(obj.generated_class())
    return obj


@unreal.uclass()
class AmineReflectionTools(unreal.ToolsetDefinition):
    """Discover supported properties and classes instead of guessing Unreal APIs."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_object_properties(identifier: str, name_substring: str | None = None, max_results: int = 100) -> str:
        """Return exposed reflected property schemas for an object or Blueprint CDO, bounded and filterable."""
        limit(max_results)
        obj = object_ref(identifier)
        props = json.loads(unreal.ToolsetLibrary.list_struct_properties(obj.get_class()))
        matches = {k: v for k, v in props.items() if (name_substring or "").lower() in k.lower()}
        return {"object": object_info(obj), "properties": dict(list(matches.items())[:max_results]), "total": len(matches)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_object_properties(identifier: str, property_names: list[str]) -> str:
        """Read only the explicit list of up to 100 reflected properties."""
        if not 1 <= len(property_names) <= 100:
            raise ToolError("invalid_property_count", "Supply 1..100 names.")
        return json.loads(unreal.ToolsetLibrary.get_object_properties(object_ref(identifier), property_names))

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def describe_class(class_path: str, max_results: int = 100) -> str:
        """Return exposed class property schemas and Blueprint-callable function names, bounded to 500 each."""
        limit(max_results)
        cls = class_ref(class_path)
        schema = json.loads(unreal.ToolsetLibrary.list_struct_properties(cls))
        properties = schema
        return {"class_path": cls.get_path_name(), "properties": dict(list(properties.items())[:max_results]), "total_properties": len(properties),
                "functions": list(unreal.AmineMCPBridge.list_class_functions(cls, max_results))}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_subclasses(base_class_path: str, name_substring: str | None = None, max_results: int = 100) -> str:
        """Find derived native/Blueprint classes through Epic's Asset Registry helper without loading every asset."""
        limit(max_results)
        paths = [c.export_text() for c in unreal.ToolsetLibrary.get_derived_classes(class_ref(base_class_path))]
        values = sorted(p for p in paths if (name_substring or "").lower() in p.lower())
        return {"classes": values[:max_results], "total": len(values)}
