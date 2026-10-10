import unreal
import toolset_registry
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.material_instance import MaterialInstanceTools
from editor_toolset.toolsets.static_mesh import StaticMeshTools
from ..common.runtime import guarded, asset, class_ref, object_info, mutation, vector
from ..common.validation import asset_path, finite, ToolError


@unreal.uclass()
class AmineMaterialTools(unreal.ToolsetDefinition):
    """Materials, instances, supported material graph edits and mesh metadata."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_material(destination_path: str) -> str:
        """Create an empty Material at an unused /Game path. Prefer instances when possible to reduce shader compilation."""
        path = asset_path(destination_path, True)
        folder, name = path.rsplit("/", 1)
        with mutation("Create material"):
            obj = MaterialTools.create_material(folder, name)
        return object_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_material_instance(destination_path: str, parent_material_path: str) -> str:
        """Create an unsaved MaterialInstanceConstant at an unused /Game path with a verified parent."""
        path = asset_path(destination_path, True)
        parent = asset(parent_material_path, unreal.MaterialInterface)
        folder, name = path.rsplit("/", 1)
        with mutation("Create material instance"):
            obj = MaterialInstanceTools.create(folder, name, parent)
        return object_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_material_info(material_path: str) -> str:
        """Inspect material/instance identity and exposed parameter names/types."""
        obj = asset(material_path, unreal.MaterialInterface)
        return {"material": object_info(obj), "parameters": [{"name": p.name, "type": str(p.type)} for p in MaterialInstanceTools.list_parameters(obj)]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_material_instance_scalar(instance_path: str, parameter_name: str, value: float) -> str:
        """Set a scalar parameter that exists on the instance's parent. Return the effective value."""
        obj = asset(instance_path, unreal.MaterialInstanceConstant, True)
        finite([value])
        with mutation("Set material scalar", obj):
            MaterialInstanceTools.set_scalar_parameter(obj, parameter_name, value)
        return {"value": MaterialInstanceTools.get_scalar_parameter(obj, parameter_name)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_material_instance_vector(instance_path: str, parameter_name: str, value: unreal.LinearColor) -> str:
        """Set an existing vector parameter using linear RGBA values; HDR values are allowed."""
        obj = asset(instance_path, unreal.MaterialInstanceConstant, True)
        finite([value.r, value.g, value.b, value.a])
        with mutation("Set material vector", obj):
            MaterialInstanceTools.set_vector_parameter(obj, parameter_name, value)
        return {"parameter": parameter_name}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_material_instance_texture(instance_path: str, parameter_name: str, texture_path: str) -> str:
        """Set an existing texture parameter to a verified Texture asset."""
        obj = asset(instance_path, unreal.MaterialInstanceConstant, True)
        texture = asset(texture_path, unreal.Texture)
        with mutation("Set material texture", obj):
            MaterialInstanceTools.set_texture_parameter(obj, parameter_name, texture)
        return {"parameter": parameter_name, "texture": texture.get_path_name()}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def add_material_node(material_path: str, expression_class_path: str, x: int = 0, y: int = 0) -> str:
        """Add a MaterialExpression subclass to a /Game Material using MaterialEditingLibrary."""
        obj = asset(material_path, unreal.Material, True)
        cls = class_ref(expression_class_path, unreal.MaterialExpression)
        with mutation("Add material node", obj):
            node = MaterialTools.add_expression(obj, cls, x, y)
        return object_info(node)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def connect_material_nodes(output_node: str, output_name: str, input_node: str, input_name: str) -> str:
        """Connect exact expression paths belonging to the same Material. Names must match discovered expression pins."""
        left, right = unreal.find_object(None, output_node), unreal.find_object(None, input_node)
        if not isinstance(left, unreal.MaterialExpression) or not isinstance(right, unreal.MaterialExpression) or left.get_outer() != right.get_outer():
            raise ToolError("invalid_expression", "Use exact expression paths from the same material.")
        with mutation("Connect material nodes", left, right, left.get_outer()):
            MaterialTools.connect_expressions(left, output_name, right, input_name)
        return {"connected": True}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def connect_material_output(node_identifier: str, output_name: str, material_property: unreal.MaterialProperty) -> str:
        """Connect an expression output to a material property, e.g. MCP enum MP_BaseColor; use describe_toolset for enum values."""
        node = unreal.find_object(None, node_identifier)
        if not isinstance(node, unreal.MaterialExpression):
            raise ToolError("expression_not_found", "Use an exact MaterialExpression path.")
        with mutation("Connect material output", node, node.get_outer()):
            MaterialTools.connect_to_output(node, output_name, material_property)
        return {"connected": True}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def compile_material(material_path: str) -> str:
        """Request a material recompile. Shader compilation may continue asynchronously; consult logs before claiming readiness."""
        obj = asset(material_path, unreal.Material, True)
        MaterialTools.recompile(obj)
        return {"requested": True, "material": obj.get_path_name(), "completion": "shader_compilation_may_be_pending"}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_static_mesh_info(mesh_path: str) -> str:
        """Return mesh bounds, material slots, LOD count and native Nanite state."""
        mesh = asset(mesh_path, unreal.StaticMesh)
        bounds = StaticMeshTools.get_bounds(mesh)
        return {"mesh": object_info(mesh), "bounds": {"min": vector(bounds.min), "max": vector(bounds.max)},
                "material_slots": list(StaticMeshTools.get_material_slots(mesh)), "lod_count": StaticMeshTools.get_lod_count(mesh), "nanite_enabled": StaticMeshTools.is_nanite_enabled(mesh)}
