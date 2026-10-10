import unreal
import toolset_registry
from ..common.runtime import guarded, asset, actor, object_info, mutation
from ..common.validation import asset_path, limit, ToolError


@unreal.uclass()
class AmineSequencerTools(unreal.ToolsetDefinition):
    """Supported LevelSequence creation, bindings and playback range editing."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_level_sequence(destination_path: str) -> str:
        """Create a new unsaved LevelSequence under /Game; never overwrite assets."""
        from toolset_registry.helpers import create_asset
        folder, name = asset_path(destination_path, True).rsplit("/", 1)
        with mutation("Create level sequence"):
            obj = create_asset(folder, name, unreal.LevelSequence.static_class(), unreal.LevelSequenceFactoryNew())
        return object_info(obj)

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_level_sequence_info(sequence_path: str, max_results: int = 100) -> str:
        """Return sequence playback frame range, display rate and bounded binding/track summaries."""
        limit(max_results)
        obj = asset(sequence_path, unreal.LevelSequence)
        rate = unreal.MovieSceneSequenceExtensions.get_display_rate(obj)
        bindings = unreal.MovieSceneSequenceExtensions.get_bindings(obj)
        return {"sequence": object_info(obj), "display_rate": {"numerator": rate.numerator, "denominator": rate.denominator},
                "start_frame": unreal.MovieSceneSequenceExtensions.get_playback_start(obj), "end_frame": unreal.MovieSceneSequenceExtensions.get_playback_end(obj),
                "bindings": [{"name": unreal.MovieSceneBindingExtensions.get_name(b), "tracks": [object_info(t) for t in unreal.MovieSceneBindingExtensions.get_tracks(b)]} for b in bindings[:max_results]]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def set_sequence_playback_range(sequence_path: str, start_frame: int, end_frame: int) -> str:
        """Set playback start/end in display-rate frames. End is exclusive and must exceed start."""
        if end_frame <= start_frame or end_frame - start_frame > 1000000:
            raise ToolError("invalid_frame_range", "End must exceed start; maximum span is 1,000,000 frames.")
        obj = asset(sequence_path, unreal.LevelSequence, True)
        with mutation("Set sequence range", obj, obj.get_movie_scene()):
            unreal.MovieSceneSequenceExtensions.set_playback_start(obj, start_frame)
            unreal.MovieSceneSequenceExtensions.set_playback_end(obj, end_frame)
        return {"start_frame": start_frame, "end_frame": end_frame}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def bind_actor_to_sequence(sequence_path: str, actor_identifier: str) -> str:
        """Add a possessable binding to an existing editor actor. Does not construct tracks/keyframes automatically."""
        obj = asset(sequence_path, unreal.LevelSequence, True)
        target = actor(actor_identifier)
        with mutation("Bind sequence actor", obj, obj.get_movie_scene()):
            binding = unreal.MovieSceneSequenceExtensions.add_possessable(obj, target)
        return {"binding_name": unreal.MovieSceneBindingExtensions.get_name(binding), "actor": target.get_path_name()}
