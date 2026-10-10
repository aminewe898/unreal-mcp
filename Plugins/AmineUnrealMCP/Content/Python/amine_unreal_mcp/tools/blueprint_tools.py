import json
import unreal
import toolset_registry
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint_node import PinID
from ..common.runtime import guarded, asset, class_ref, object_info, mutation, set_property
from ..common.validation import asset_path, name, limit, ToolError


def blueprint(path):
    return asset(path, unreal.Blueprint)


def compile_info(bp):
    errors = []
    for graph in unreal.BlueprintEditorLibrary.list_graphs(bp):
        editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        for node in editor.list_nodes_with_errors():
            errors.append({"node": node.get_path_name(), "message": str(node.get_editor_property("ErrorMsg"))})
    status = bp.get_editor_property("Status")
    return {"blueprint": bp.get_path_name(), "status": str(status), "compiled": status in (unreal.BlueprintStatus.BS_UP_TO_DATE, unreal.BlueprintStatus.BS_UP_TO_DATE_WITH_WARNINGS), "messages": errors}


def node_ref(path):
    obj = unreal.find_object(None, path)
    if not isinstance(obj, unreal.EdGraphNode) or obj.get_path_name() != path:
        raise ToolError("node_not_found", "Use an exact node path from list_blueprint_nodes.")
    return obj


def pin_ref(node_path, pin_name, output):
    node = node_ref(node_path)
    info = BlueprintTools.get_node_infos([node])[0]
    matches = [pin.pin_id for pin in (info.output_pins if output else info.input_pins) if pin.name == pin_name]
    if len(matches) != 1:
        raise ToolError("pin_not_found", "Pin name is missing or ambiguous. Inspect list_blueprint_nodes.")
    return matches[0]


@unreal.uclass()
class AmineBlueprintTools(unreal.ToolsetDefinition):
    """Supported Blueprint assets, components, defaults, compilation and typed graph editing."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_blueprint(destination_path: str, parent_class_path: str = "/Script/Engine.Actor") -> str:
        """Create a Blueprint at a new /Game path with a verified parent class. Does not save automatically."""
        path = asset_path(destination_path, True)
        parent = class_ref(parent_class_path)
        folder, asset_name = path.rsplit("/", 1)
        with mutation("Create Blueprint"):
            bp = BlueprintTools.create(folder, asset_name, parent)
        return object_info(bp)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_blueprint_info(blueprint_path: str) -> str:
        """Return parent, generated class, member variables, graph identifiers and actual compile status/messages."""
        bp = blueprint(blueprint_path)
        cls = bp.generated_class()
        info = object_info(bp)
        info.update(parent_class=BlueprintTools.get_parent(bp).get_path_name(), generated_class=cls.get_path_name() if cls else None,
                    variables=list(BlueprintTools.list_variables(bp)), graphs=[object_info(g) for g in BlueprintTools.list_graphs(bp)], compile=compile_info(bp))
        return info

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_blueprint_parent_class(blueprint_path: str) -> str:
        """Return the parent class's canonical path."""
        return {"parent_class": BlueprintTools.get_parent(blueprint(blueprint_path)).get_path_name()}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_blueprint_components(blueprint_path: str) -> str:
        """Enumerate Blueprint component templates through Epic's SubobjectDataSubsystem helper."""
        bp = blueprint(blueprint_path)
        return [object_info(c) for c in ActorTools.get_components(BlueprintTools.get_default_object(bp))]

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def add_blueprint_component(blueprint_path: str, class_path: str, component_name: str) -> str:
        """Add a named Blueprint component with supported subsystem APIs; compile and return its template path."""
        bp = blueprint(blueprint_path)
        cls = class_ref(class_path, unreal.ActorComponent)
        name(component_name)
        components = ActorTools.get_components(BlueprintTools.get_default_object(bp))
        if any(c.get_name() == component_name or c.get_name() == component_name + "_GEN_VARIABLE" for c in components):
            raise ToolError("component_exists", "Blueprint component name already exists.")
        with mutation("Add Blueprint component", bp):
            result = ActorTools.add_component(bp, cls, component_name)
        return object_info(result)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def remove_blueprint_component(blueprint_path: str, component_identifier: str) -> str:
        """Remove one exact component template belonging to this Blueprint; inherited/native components may be rejected."""
        bp = blueprint(blueprint_path)
        objects = [c for c in ActorTools.get_components(BlueprintTools.get_default_object(bp)) if c.get_path_name() == component_identifier]
        if len(objects) != 1:
            raise ToolError("component_not_found", "No exact component template belongs to this Blueprint.")
        with mutation("Remove Blueprint component", bp, objects[0]):
            if not ActorTools.remove_component(objects[0]):
                raise ToolError("remove_failed", "Unreal rejected component removal.")
        return {"deleted": component_identifier}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_blueprint_variables(blueprint_path: str) -> str:
        """Return declared member variable names and their current class default values."""
        bp = blueprint(blueprint_path)
        names = list(BlueprintTools.list_variables(bp))
        return {"variables": names, "defaults": json.loads(unreal.ToolsetLibrary.get_object_properties(BlueprintTools.get_default_object(bp), names)) if names else {}}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def add_blueprint_variable(blueprint_path: str, variable_name: str, type_name: str = "float") -> str:
        """Add a member variable: bool, int, float, byte, string, name, text, Vector, Rotator, Transform, Vector2D or LinearColor. Compile afterward."""
        bp = blueprint(blueprint_path)
        name(variable_name)
        if variable_name in BlueprintTools.list_variables(bp):
            raise ToolError("variable_exists", "Variable already exists.")
        with mutation("Add Blueprint variable", bp):
            BlueprintTools.add_variable(bp, variable_name, type_name)
            BlueprintTools.compile_blueprint(bp)
        return {"variables": list(BlueprintTools.list_variables(bp)), "compile": compile_info(bp)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_blueprint_variable_default(blueprint_path: str, variable_name: str, value_json: str) -> str:
        """Set an existing member's class default with one JSON value; compile before editing newly added variables."""
        bp = blueprint(blueprint_path)
        if variable_name not in BlueprintTools.list_variables(bp):
            raise ToolError("variable_not_found", "No declared member variable with this name.")
        with mutation("Set Blueprint variable default", bp):
            return set_property(BlueprintTools.get_default_object(bp), variable_name, value_json)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_blueprint_class_default(blueprint_path: str, property_name: str, value_json: str) -> str:
        """Set one reflected class default property, including inherited properties. Does not save."""
        bp = blueprint(blueprint_path)
        with mutation("Set Blueprint class default", bp):
            return set_property(BlueprintTools.get_default_object(bp), property_name, value_json)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def compile_blueprint(blueprint_path: str) -> str:
        """Compile now and return real compiler status and graph-node diagnostic messages. Compilation errors remain inspectable."""
        bp = asset(blueprint_path, unreal.Blueprint, True)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        return compile_info(bp)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_blueprint_compile_status(blueprint_path: str) -> str:
        """Read compile status and node messages without triggering compilation."""
        return compile_info(blueprint(blueprint_path))

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_blueprint_compile_errors(blueprint_path: str) -> str:
        """Read stored node compiler diagnostics; consult get_errors for broader compiler output."""
        return compile_info(blueprint(blueprint_path))

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_blueprint_nodes(blueprint_path: str, graph_name: str = "EventGraph", max_results: int = 100) -> str:
        """Return bounded graph node paths, discovered type IDs, input/output pin names and literal values."""
        limit(max_results)
        graph = BlueprintTools.get_graph(blueprint(blueprint_path), graph_name)
        infos = BlueprintTools.get_node_infos(BlueprintTools.find_nodes(graph))
        return {"nodes": [{"identifier": info.node.get_path_name(), "type_id": info.type_id,
                           "inputs": [{"name": p.name, "type": p.type_id, "value": p.value} for p in info.input_pins],
                           "outputs": [{"name": p.name, "type": p.type_id} for p in info.output_pins]} for info in infos[:max_results]], "total": len(infos)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def search_blueprint_node_types(blueprint_path: str, search: str, graph_name: str = "EventGraph", max_results: int = 100) -> str:
        """Discover valid node type IDs from Epic's action database before creating nodes."""
        limit(max_results)
        values = list(BlueprintTools.find_node_types(BlueprintTools.get_graph(blueprint(blueprint_path), graph_name), search))
        return {"node_types": values[:max_results], "total": len(values)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_blueprint_node(blueprint_path: str, type_id: str, graph_name: str = "EventGraph", x: int = 0, y: int = 0) -> str:
        """Create a discovered node type using the installed BlueprintGraphEditor. Compile explicitly after editing."""
        bp = blueprint(blueprint_path)
        graph = BlueprintTools.get_graph(bp, graph_name)
        with mutation("Create Blueprint node", bp, graph):
            obj = BlueprintTools.create_node(graph, type_id, unreal.IntPoint(x, y))
        return object_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def connect_blueprint_pins(output_node: str, output_pin: str, input_node: str, input_pin: str) -> str:
        """Connect named output/input pins on exact nodes in the same Blueprint graph; schema validates compatibility."""
        left, right = node_ref(output_node), node_ref(input_node)
        if left.get_outer() != right.get_outer():
            raise ToolError("different_graphs", "Pins must belong to the same graph.")
        out_ref, in_ref = pin_ref(output_node, output_pin, True), pin_ref(input_node, input_pin, False)
        with mutation("Connect Blueprint pins", left, right, left.get_outer()):
            BlueprintTools.connect_pins(out_ref, in_ref)
        return {"connected": True}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_blueprint_pin_value(node_identifier: str, pin_name: str, value: str) -> str:
        """Set a named input pin's Unreal literal text, such as Hello or 2.5; this is not executable code."""
        obj = node_ref(node_identifier)
        pin = pin_ref(node_identifier, pin_name, False)
        with mutation("Set Blueprint pin", obj, obj.get_outer()):
            BlueprintTools.set_pin_value(pin, value)
        return {"value": BlueprintTools.get_pin_value(pin)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_blueprint_function(blueprint_path: str, function_name: str) -> str:
        """Create a new named function graph with Epic's supported BlueprintEditorLibrary."""
        bp = blueprint(blueprint_path)
        name(function_name)
        with mutation("Create Blueprint function", bp):
            graph = BlueprintTools.add_function_graph(bp, function_name)
        return object_info(graph)
