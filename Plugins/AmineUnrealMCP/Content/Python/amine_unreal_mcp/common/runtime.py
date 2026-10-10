"""Serialization, exact resolution and real editor transactions."""
import json
from contextlib import contextmanager
from functools import wraps
import unreal
import toolset_registry
from toolset_registry.helpers import require_editable
from .validation import ToolError, asset_path, resolve_match
from .privacy import redact


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def guarded(function):
    """Return a JSON envelope; preserve the annotated signature for Epic's schema generator."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            with toolset_registry.tool_raising_exceptions():
                return encode(redact({"success": True, "data": function(*args, **kwargs)}))
        except ToolError as exc:
            return encode(redact({"success": False, "error": exc.code, "message": str(exc)}))
        except Exception as exc:
            unreal.log_error(redact(f"[AmineUnrealMCP] {function.__name__}: {exc}"))
            return encode(redact({"success": False, "error": "unreal_operation_failed", "message": str(exc)[:4096]}))
    return wrapped


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def actor(reference: str, exact_only: bool = False):
    return resolve_match(eas().get_all_level_actors(), reference, exact_only)


def asset(reference: str, expected=unreal.Object, writable: bool = False):
    path = asset_path(reference, writable)
    obj = unreal.load_asset(path)
    if obj is None:
        raise ToolError("asset_not_found", f"No asset exists at {path}.")
    if not isinstance(obj, expected):
        raise ToolError("wrong_asset_type", f"{path} must be a {expected.__name__}.")
    return obj


def class_ref(path: str, base=unreal.Object):
    if not path.startswith(("/Script/", "/Game/")) or any(token in path for token in ("..", "'", '"', "\\")):
        raise ToolError("invalid_class_path", "Use a /Script/Module.Class or /Game/Path/BP.BP_C class path.")
    cls = unreal.load_class(None, path)
    if cls is None or not unreal.MathLibrary.class_is_child_of(cls, base.static_class()):
        raise ToolError("invalid_class", f"{path} is not a loaded {base.__name__} subclass.")
    return cls


def vector(value):
    return {"x": value.x, "y": value.y, "z": value.z}


def rotation(value):
    return {"pitch": value.pitch, "yaw": value.yaw, "roll": value.roll}


def transform(obj):
    return {"location": vector(obj.get_actor_location()), "rotation": rotation(obj.get_actor_rotation()), "scale": vector(obj.get_actor_scale3d())}


def object_info(obj):
    return {"identifier": obj.get_path_name(), "name": obj.get_name(), "class": obj.get_class().get_path_name()}


def actor_info(obj, detailed=False):
    info = object_info(obj)
    info.update(transform(obj))
    parent = obj.get_attach_parent_actor()
    components = obj.get_components_by_class(unreal.ActorComponent)
    info.update(label=obj.get_actor_label(), folder=str(obj.get_folder_path()), tags=[str(t) for t in obj.tags], parent=parent.get_path_name() if parent else None,
                components=[object_info(c) for c in components] if detailed else [c.get_class().get_name() for c in components])
    return info


@contextmanager
def mutation(label: str, *objects):
    if unreal.AmineMCPBridge.is_pie_running():
        raise ToolError("pie_active", "Stop PIE before modifying editor objects.")
    for obj in objects:
        if not obj.get_path_name().startswith(("/Game/", "/Temp/")):
            raise ToolError("read_only_package", "Object writes require /Game assets or the active temporary editor map.")
    undo_before = unreal.ToolsetLibrary.get_active_undo_count()
    try:
        with unreal.ScopedEditorTransaction(f"AmineUnrealMCP: {label}"):
            for obj in objects:
                require_editable(obj)
                obj.modify()
            yield
    except Exception:
        # CancelTransaction only removes history: it does not revert UObject writes.
        if unreal.ToolsetLibrary.get_active_undo_count() > undo_before:
            unreal.ToolsetLibrary.undo_transaction(False)
        raise
    unreal.log(f"[AmineUnrealMCP] {label}")


def set_property(obj, property_name: str, value_json: str):
    if len(value_json) > 65536:
        raise ToolError("value_too_large", "Property JSON is limited to 64 KiB.")
    value = json.loads(value_json, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    schema = json.loads(unreal.ToolsetLibrary.list_struct_properties(obj.get_class()))
    properties = schema
    matching = [key for key in properties if key.lower() == property_name.lower()]
    if len(matching) != 1:
        raise ToolError("unknown_property", f"Property {property_name!r} is not exposed. Use list_object_properties to discover names.")
    key = matching[0]
    before = json.loads(unreal.ToolsetLibrary.get_object_properties(obj, [key]))
    with mutation(f"Set {key}", obj):
        if not unreal.ToolsetLibrary.set_object_properties(obj, encode({key: value})):
            raise ToolError("property_write_failed", f"Unreal rejected the value for {key}.")
    return {"identifier": obj.get_path_name(), "before": before, "after": json.loads(unreal.ToolsetLibrary.get_object_properties(obj, [key]))}


def epic_sync(toolset_name: str, tool_name: str, arguments: dict):
    """Read an immediately completed native tool through the cached public Toolset handler."""
    result = unreal.AmineMCPBridge.execute_epic_tool(toolset_name, tool_name, encode(arguments))
    if not result.is_complete:
        raise ToolError("unexpected_async_result", "This inspection operation did not complete synchronously.")
    if result.error:
        raise ToolError("native_tool_failed", result.error)
    value = json.loads(result.value)
    if isinstance(value, dict) and "returnValue" in value:
        value = value["returnValue"]
    return json.loads(value) if isinstance(value, str) else value
