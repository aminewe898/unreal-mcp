"""Development-only startup probe; not an MCP tool and not needed for normal use."""
import json
from pathlib import Path
import unreal

output = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / "ApiProbe.json"
classes = [unreal.EditorAppToolset, unreal.AutomationTestToolset]
data = {cls.__name__: json.loads(unreal.ToolsetRegistry.get_toolset_json_schema(cls)) for cls in classes}
data["AssetEditorSubsystem_methods"] = [m for m in dir(unreal.AssetEditorSubsystem) if "editor" in m.lower()]
data["BlueprintStatus_values"] = [m for m in dir(unreal.BlueprintStatus) if m.startswith("BS_")]
output.write_text(json.dumps(data, indent=2), encoding="utf-8")
