import unreal
import toolset_registry
from editor_toolset.toolsets.asset import AssetTools
from ..common.runtime import guarded, asset, encode, world
from ..common.validation import asset_path, ToolError


@unreal.uclass()
class AmineEditorTools(unreal.ToolsetDefinition):
    """Explicit saving and asset editor operations; never save all dirty packages."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def save_asset(exact_asset_path: str) -> str:
        """Save only this exact /Game asset, leaving unrelated dirty content untouched."""
        path = asset_path(exact_asset_path, True)
        asset(path)
        if not AssetTools.save_assets([path]):
            raise ToolError("save_failed", f"Could not save {path}.")
        return {"saved": [path]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def save_assets(exact_asset_paths: list[str]) -> str:
        """Save only the explicit /Game asset list. Validate every path before writing; report any native failure."""
        if not exact_asset_paths or len(exact_asset_paths) > 100:
            raise ToolError("invalid_asset_count", "Supply 1..100 exact assets.")
        paths = [asset_path(p, True) for p in exact_asset_paths]
        for path in paths:
            asset(path)
        if not AssetTools.save_assets(paths):
            raise ToolError("save_failed", "One or more requested assets failed to save; some may already have been saved.")
        return {"saved": paths}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def save_current_level() -> str:
        """Save the current /Game level only. Reject transient/Engine maps rather than prompting for Save As."""
        level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).get_current_level()
        path = level.get_outermost().get_name()
        asset_path(path, True)
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
            raise ToolError("save_failed", "Current level could not be saved.")
        return {"saved_level": path}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def save_current_level_as(destination_path: str) -> str:
        """Save the active level to a new /Game path, including transient maps."""
        path = asset_path(destination_path, True)
        if unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).does_asset_exist(path):
            raise ToolError("asset_exists", f"Asset already exists at {path}.")
        if unreal.AmineMCPBridge.is_pie_running():
            raise ToolError("pie_active", "Stop PIE before saving the current level.")
        current_world = world()
        if not current_world:
            raise ToolError("no_world", "No active editor world.")
        if not unreal.EditorLoadingAndSavingUtils.save_map(current_world, path):
            raise ToolError("save_failed", f"Could not save current level to {path}.")
        return {"saved_level": path}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_dirty_assets() -> str:
        """List dirty map/content packages from Unreal's native editor API."""
        return {"dirty_packages": list(unreal.AmineMCPBridge.get_dirty_packages())}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def open_asset_editor(exact_asset_path: str) -> str:
        """Open an editor for a verified exact asset."""
        path = asset_path(exact_asset_path)
        obj = asset(path)
        if not unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([obj]):
            raise ToolError("open_editor_failed", "Unreal could not open this asset editor.")
        return {"opened": path}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def close_asset_editor(exact_asset_path: str) -> str:
        """Close editors for one exact asset only if it is clean, avoiding save prompts."""
        path = asset_path(exact_asset_path)
        if AssetTools.is_dirty(path):
            raise ToolError("asset_dirty", "Save this asset explicitly before closing its editor.")
        count = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset(path))
        return {"closed_editor_count": count}

    @toolset_registry.tool_call
    @staticmethod
    def sync_content_browser(exact_asset_paths: list[str]) -> unreal.ToolCallAsyncResultString:
        """Select exact existing assets in the Content Browser. Native async result completes when selection is applied."""
        if not 1 <= len(exact_asset_paths) <= 100:
            raise ValueError("Supply 1..100 paths")
        paths = [asset_path(p) for p in exact_asset_paths]
        for path in paths:
            asset(path)
        return unreal.AmineMCPBridge.execute_epic_tool("EditorToolset.EditorAppToolset", "SelectAssets", encode({"assetPaths": paths}))
