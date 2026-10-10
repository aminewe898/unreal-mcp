import unreal
import toolset_registry
from editor_toolset.toolsets.actor import ActorTools
from ..common.runtime import guarded, actor, asset, class_ref, object_info, mutation, set_property
from ..common.validation import name, ToolError


def component(identifier: str):
    obj = unreal.find_object(None, identifier)
    if not isinstance(obj, unreal.ActorComponent) or obj.get_path_name() != identifier:
        raise ToolError("component_not_found", "Use an exact live component path from list_actor_components or list_blueprint_components.")
    return obj


@unreal.uclass()
class AmineComponentTools(unreal.ToolsetDefinition):
    """Inspect, add and modify instance components and assign mesh/material assets."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_actor_components(identifier: str) -> str:
        """Return exact component paths, names and class paths for an editor actor."""
        return [object_info(c) for c in ActorTools.get_components(actor(identifier))]

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_component(identifier: str, properties: list[str] = []) -> str:
        """Inspect a component, optionally reading explicitly requested reflected properties."""
        import json
        obj = component(identifier)
        info = object_info(obj)
        info["properties"] = json.loads(unreal.ToolsetLibrary.get_object_properties(obj, properties)) if properties else {}
        return info

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def add_component(actor_identifier: str, class_path: str, component_name: str) -> str:
        """Add an instance component using Epic's SubobjectDataSubsystem integration. Return its exact path."""
        obj = actor(actor_identifier)
        cls = class_ref(class_path, unreal.ActorComponent)
        name(component_name)
        if any(c.get_name() == component_name for c in ActorTools.get_components(obj)):
            raise ToolError("component_exists", "A component with this name already exists.")
        with mutation("Add component", obj):
            result = ActorTools.add_component(obj, cls, component_name)
        return object_info(result)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def remove_component(identifier: str) -> str:
        """Remove one exact component using Epic's supported subsystem. Native/inherited removal may be rejected."""
        obj = component(identifier)
        before = object_info(obj)
        with mutation("Remove component", obj):
            if not ActorTools.remove_component(obj):
                raise ToolError("component_remove_failed", "Component could not be removed.")
        return {"deleted": before}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_component_property(identifier: str, property_name: str, value_json: str) -> str:
        """Set one exposed component property with a JSON value and return before/after."""
        return set_property(component(identifier), property_name, value_json)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_component_transform(identifier: str, transform: unreal.Transform) -> str:
        """Set a SceneComponent's relative transform. Non-scene components are rejected."""
        obj = component(identifier)
        if not isinstance(obj, unreal.SceneComponent):
            raise ToolError("not_scene_component", "This component has no transform.")
        with mutation("Transform component", obj):
            obj.set_relative_transform(transform, False, True)
        return object_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def assign_static_mesh(component_identifier: str, mesh_path: str) -> str:
        """Assign an existing StaticMesh asset to an exact StaticMeshComponent."""
        obj = component(component_identifier)
        if not isinstance(obj, unreal.StaticMeshComponent):
            raise ToolError("wrong_component_type", "Requires a StaticMeshComponent.")
        mesh = asset(mesh_path, unreal.StaticMesh)
        with mutation("Assign static mesh", obj):
            if not obj.set_static_mesh(mesh):
                raise ToolError("mesh_assignment_failed", "Unreal rejected mesh assignment.")
        return {"component": object_info(obj), "mesh": mesh.get_path_name()}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def assign_material(component_identifier: str, material_path: str, slot_index: int = 0) -> str:
        """Assign an existing material to a PrimitiveComponent slot; validate slot index."""
        obj = component(component_identifier)
        if not isinstance(obj, unreal.PrimitiveComponent) or not 0 <= slot_index < obj.get_num_materials():
            raise ToolError("invalid_material_slot", "Requires a PrimitiveComponent and an existing material slot.")
        material = asset(material_path, unreal.MaterialInterface)
        with mutation("Assign material", obj):
            obj.set_material(slot_index, material)
        return {"component": obj.get_path_name(), "slot": slot_index, "material": material.get_path_name()}
