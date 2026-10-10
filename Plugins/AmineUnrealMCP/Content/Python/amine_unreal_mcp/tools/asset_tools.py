from pathlib import Path
import unreal
import toolset_registry
from editor_toolset.toolsets.asset import AssetTools
from ..common.runtime import guarded, asset, object_info, class_ref, mutation
from ..common.validation import asset_path, limit, ToolError


def registry_links(path, referencers=False):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    if registry.is_loading_assets():
        raise ToolError("asset_registry_loading", "Retry after asset registry discovery completes.")
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
        include_searchable_names=True, include_soft_management_references=True, include_hard_management_references=True)
    query = registry.get_referencers if referencers else registry.get_dependencies
    return sorted(str(value) for value in (query(path.split(".")[0], options) or []))


@unreal.uclass()
class AmineAssetTools(unreal.ToolsetDefinition):
    """Asset Registry search without loading assets; explicit /Game asset writes and saves."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def search_assets(content_path: str = "/Game", name_substring: str | None = None, class_path: str | None = None, recursive: bool = True, max_results: int = 100, offset: int = 0) -> str:
        """Search registry metadata without loading assets. Class filter is a /Script class path. Paginated results."""
        limit(max_results)
        if offset < 0:
            raise ToolError("invalid_offset", "Offset cannot be negative.")
        asset_path(content_path.rstrip("/") + "/Placeholder")
        cls = class_ref(class_path) if class_path else None
        paths = sorted(AssetTools.find_assets(content_path, name_substring or "", cls, recursive))
        return {"assets": paths[offset:offset + max_results], "total": len(paths), "next_offset": offset + max_results if offset + max_results < len(paths) else None}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_asset_info(asset_path_value: str) -> str:
        """Read registry class and metadata for one exact asset without loading its contents."""
        path = asset_path(asset_path_value)
        if not unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).does_asset_exist(path):
            raise ToolError("asset_not_found", f"No asset at {path}.")
        return {"path": path, "class": AssetTools.get_asset_class(path), "tags": dict(AssetTools.get_asset_tags(path)), "dirty": AssetTools.is_dirty(path)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def duplicate_asset(source_path: str, destination_path: str) -> str:
        """Duplicate an exact asset to an unused /Game path; never overwrite existing assets."""
        source, destination = asset_path(source_path), asset_path(destination_path, True)
        if AssetTools.exists(destination):
            raise ToolError("asset_exists", f"{destination} already exists.")
        with mutation("Duplicate asset"):
            if not AssetTools.duplicate(source, destination):
                raise ToolError("duplicate_failed", "Unreal refused asset duplication.")
        return {"source": source, "destination": destination}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def move_asset(source_path: str, destination_path: str) -> str:
        """Move/rename an exact /Game asset to an unused /Game path. Unreal may save packages/create redirectors."""
        source, destination = asset_path(source_path, True), asset_path(destination_path, True)
        if AssetTools.exists(destination):
            raise ToolError("asset_exists", f"{destination} already exists.")
        with mutation("Move asset"):
            if not AssetTools.move(source, destination):
                raise ToolError("move_failed", "Unreal refused asset move.")
        return {"source": source, "destination": destination}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def delete_asset(exact_asset_path: str) -> str:
        """Delete one exact /Game asset only if registry reports no referencers. Asset deletion is not undoable."""
        path = asset_path(exact_asset_path, True)
        asset(path)
        referencers = registry_links(path, True)
        if referencers:
            raise ToolError("asset_referenced", f"Asset has referencers: {referencers[:20]}. Resolve references before deletion.")
        with mutation("Delete asset"):
            if not AssetTools.delete(path):
                raise ToolError("delete_failed", "Unreal refused asset deletion.")
        return {"deleted": path, "undoable": False}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def create_folder(content_path: str) -> str:
        """Create a Content Browser folder under /Game."""
        path = asset_path(content_path, True)
        if not AssetTools.create_folder(path):
            raise ToolError("folder_create_failed", f"Could not create {path}.")
        return {"folder": path}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_folder(content_path: str, max_results: int = 100) -> str:
        """List immediate folders and asset paths without loading assets."""
        limit(max_results)
        asset_path(content_path.rstrip("/") + "/Placeholder")
        return {"folders": list(AssetTools.list_folders(content_path, False))[:max_results], "assets": list(AssetTools.find_assets(content_path, recursive=False))[:max_results]}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_asset_dependencies(exact_asset_path: str, max_results: int = 100) -> str:
        """Return bounded Asset Registry dependency package paths."""
        limit(max_results)
        values = registry_links(asset_path(exact_asset_path))
        return {"dependencies": values[:max_results], "total": len(values)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_asset_referencers(exact_asset_path: str, max_results: int = 100) -> str:
        """Return bounded Asset Registry referencer package paths."""
        limit(max_results)
        values = registry_links(asset_path(exact_asset_path), True)
        return {"referencers": values[:max_results], "total": len(values)}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def import_asset(project_relative_filename: str, destination_folder: str) -> str:
        """Import an existing file inside the project into /Game, without overwriting or automatically saving assets."""
        root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
        source = (root / project_relative_filename).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ToolError("invalid_import_path", "Import file must exist within the project, including after resolving symlinks.")
        destination = asset_path(destination_folder, True)
        if AssetTools.exists(destination + "/" + source.stem):
            raise ToolError("asset_exists", "Destination asset already exists.")
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(source))
        task.set_editor_property("destination_path", destination)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", False)
        with mutation("Import asset"):
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = list(task.get_editor_property("imported_object_paths"))
        if not paths:
            raise ToolError("import_failed", "Importer produced no assets; inspect logs for format/importer errors.")
        return {"imported": paths}
