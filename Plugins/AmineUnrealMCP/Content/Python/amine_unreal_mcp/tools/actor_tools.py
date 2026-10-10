import unreal
import toolset_registry
from ..common.runtime import guarded, actor, actor_info, transform, eas, mutation, class_ref, set_property
from ..common.validation import finite, limit, ToolError


@unreal.uclass()
class AmineActorTools(unreal.ToolsetDefinition):
    """Bounded scene inspection and undoable exact actor operations."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_level_actors(class_path: str | None = None, label_substring: str | None = None, folder: str | None = None, tag: str | None = None, selected_only: bool = False, max_results: int = 100, offset: int = 0) -> str:
        """List live editor actors with transform and component summaries; paths are canonical identifiers."""
        limit(max_results)
        if offset < 0:
            raise ToolError("invalid_offset", "Offset cannot be negative.")
        cls = class_ref(class_path, unreal.Actor) if class_path else None
        matches = [a for a in (eas().get_selected_level_actors() if selected_only else eas().get_all_level_actors())
                   if (not cls or unreal.MathLibrary.class_is_child_of(a.get_class(), cls)) and (label_substring or "").lower() in a.get_actor_label().lower()
                   and (not folder or str(a.get_folder_path()) == folder) and (not tag or a.actor_has_tag(tag))]
        matches.sort(key=lambda a: a.get_path_name())
        return {"actors": [actor_info(a) for a in matches[offset:offset + max_results]], "total": len(matches), "next_offset": offset + max_results if offset + max_results < len(matches) else None}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_actor(identifier: str) -> str:
        """Inspect an actor by exact path, internal name or unambiguous exact label."""
        return actor_info(actor(identifier), True)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def spawn_actor(class_path: str, label: str | None = None, location: unreal.Vector = unreal.Vector(), rotation: unreal.Rotator = unreal.Rotator(), scale: unreal.Vector = unreal.Vector(1, 1, 1), folder: str | None = None) -> str:
        """Spawn an Actor subclass or Blueprint generated class into the editor; return its exact path. Units are cm and degrees."""
        finite([location.x, location.y, location.z, rotation.pitch, rotation.yaw, rotation.roll, scale.x, scale.y, scale.z])
        cls = class_ref(class_path, unreal.Actor)
        with mutation("Spawn actor"):
            obj = eas().spawn_actor_from_class(cls, location, rotation)
            if not obj:
                raise ToolError("spawn_failed", f"Could not spawn {class_path}.")
            obj.modify()
            obj.set_actor_scale3d(scale)
            if label:
                obj.set_actor_label(label)
            if folder:
                obj.set_folder_path(folder)
        return actor_info(obj, True)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_actor_transform(identifier: str, location: unreal.Vector | None = None, rotation: unreal.Rotator | None = None, scale: unreal.Vector | None = None) -> str:
        """Set any supplied world transform fields; omitted fields are preserved. Return before and after."""
        obj = actor(identifier)
        before = transform(obj)
        for value in (location, scale):
            if value is not None:
                finite([value.x, value.y, value.z])
        if rotation is not None:
            finite([rotation.pitch, rotation.yaw, rotation.roll])
        with mutation("Transform actor", obj, *([obj.root_component] if obj.root_component else [])):
            if location is not None:
                obj.set_actor_location(location, False, True)
            if rotation is not None:
                obj.set_actor_rotation(rotation, True)
            if scale is not None:
                obj.set_actor_scale3d(scale)
        return {"identifier": obj.get_path_name(), "before": before, "after": transform(obj)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_actor_label(identifier: str, label: str) -> str:
        """Change the display label without changing the canonical actor path."""
        obj = actor(identifier)
        with mutation("Label actor", obj):
            obj.set_actor_label(label)
        return actor_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_actor_folder(identifier: str, folder: str) -> str:
        """Move an actor to an Outliner folder; empty string means the root."""
        obj = actor(identifier)
        with mutation("Set actor folder", obj):
            obj.set_folder_path(folder)
        return actor_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_actor_tags(identifier: str, tags: list[str]) -> str:
        """Replace actor tags, preserving only the supplied values."""
        if len(tags) > 100:
            raise ToolError("too_many_tags", "At most 100 tags are accepted.")
        obj = actor(identifier)
        with mutation("Set actor tags", obj):
            obj.tags = [unreal.Name(t) for t in dict.fromkeys(tags)]
        return actor_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def duplicate_actor(identifier: str, label: str | None = None, offset: unreal.Vector = unreal.Vector()) -> str:
        """Duplicate a resolved actor; return the new actor path. No asset is saved."""
        obj = actor(identifier)
        finite([offset.x, offset.y, offset.z])
        with mutation("Duplicate actor", obj):
            duplicate = eas().duplicate_actor(obj, obj.get_world(), offset)
            if not duplicate:
                raise ToolError("duplicate_failed", "Unreal could not duplicate the actor.")
            if label:
                duplicate.set_actor_label(label)
        return actor_info(duplicate, True)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def delete_actor(identifier: str) -> str:
        """Delete only the exact live editor actor path. Labels and fuzzy references are rejected. Undoable."""
        obj = actor(identifier, True)
        before = actor_info(obj)
        with mutation("Delete actor", obj):
            if not eas().destroy_actor(obj):
                raise ToolError("delete_failed", "Unreal refused to destroy this actor.")
        return {"deleted": before}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def attach_actor(identifier: str, parent_identifier: str) -> str:
        """Attach to a resolved parent, keeping world transform. Reject self-attachment and cycles."""
        obj, parent = actor(identifier), actor(parent_identifier)
        current = parent
        while current:
            if current == obj:
                raise ToolError("attachment_cycle", "Attachment would create a cycle.")
            current = current.get_attach_parent_actor()
        with mutation("Attach actor", obj):
            if not obj.attach_to_actor(parent, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False):
                raise ToolError("attach_failed", "Unreal rejected attachment; check root components.")
        return actor_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def detach_actor(identifier: str) -> str:
        """Detach the actor, keeping world transform."""
        obj = actor(identifier)
        with mutation("Detach actor", obj):
            obj.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
        return actor_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def select_actors(identifiers: list[str]) -> str:
        """Replace editor actor selection after resolving every reference. Empty list clears selection."""
        if len(identifiers) > 500:
            raise ToolError("too_many_actors", "At most 500 actors may be selected.")
        objects = [actor(identifier) for identifier in identifiers]
        eas().set_selected_level_actors(objects)
        return {"selected": [obj.get_path_name() for obj in objects]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def clear_selection() -> str:
        """Clear editor actor selection."""
        eas().clear_actor_selection_set()
        return {"selected": []}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_actor_property(identifier: str, property_name: str, value_json: str) -> str:
        """Set one reflected actor property using a JSON value; discover names first with list_object_properties."""
        return set_property(actor(identifier), property_name, value_json)
