"""Live MCP acceptance. Mutates only uniquely named test actors and /Game/MCP_TEST_* assets.

Run against the isolated host. Cleanup is attempted in finally even after failure.
Results and received PNGs are written to Saved/Acceptance, never source control.
"""
import base64
import json
import struct
import time
import uuid
from pathlib import Path
from mcp_client import Client, text_result

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Saved/Acceptance"
SETS = {"project": "project_tools.AmineProjectTools", "actor": "actor_tools.AmineActorTools", "component": "component_tools.AmineComponentTools",
        "asset": "asset_tools.AmineAssetTools", "blueprint": "blueprint_tools.AmineBlueprintTools", "viewport": "viewport_tools.AmineViewportTools",
        "editor": "editor_tools.AmineEditorTools", "gameplay": "gameplay_tools.AmineGameplayTools", "debug": "debug_tools.AmineDebugTools",
        "reflection": "reflection_tools.AmineReflectionTools", "material": "material_tools.AmineMaterialTools", "lighting": "lighting_tools.AmineLightingTools",
        "sequencer": "sequencer_tools.AmineSequencerTools", "testing": "testing_tools.AmineTestingTools"}


def unwrap(result):
    if result.get("isError"):
        raise RuntimeError(text_result(result))
    texts = text_result(result)
    if not texts:
        return None
    value = json.loads(texts[0])
    if isinstance(value, dict) and "returnValue" in value:
        value = value["returnValue"]
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    if isinstance(value, dict) and "success" in value:
        if not value["success"]:
            raise RuntimeError(value)
        return value["data"]
    return value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    client = Client()
    entries, actors, assets = [], [], []
    token = "MCP_TEST_" + uuid.uuid4().hex[:8]

    def call(group, tool, **kwargs):
        started = time.monotonic()
        try:
            result = client.call("amine_capture_viewport", kwargs) if tool == "capture_viewport" else client.tool("amine_unreal_mcp.tools." + SETS[group], tool, kwargs)
            images = [c for c in result.get("content", []) if c.get("type") == "image"]
            if tool == "capture_viewport":
                assert len(images) == 1, "MCP caller must receive one real image content block"
                assert images[0]["mimeType"] == "image/png"
                data = base64.b64decode(images[0]["data"], validate=True)
                assert data[:8] == b"\x89PNG\r\n\x1a\n"
                dimensions = struct.unpack(">II", data[16:24])
                assert dimensions == (kwargs.get("width", 1280), kwargs.get("height", 720))
                path = OUT / f"viewport-{sum(e['tool'] == tool for e in entries) + 1}.png"
                path.write_bytes(data)
                value = {"mime_type": "image/png", "dimensions": dimensions, "image_file": path.name}
            else:
                value = unwrap(result)
            entries.append({"tool": tool, "passed": True, "seconds": round(time.monotonic() - started, 3), "result": value})
            print(f"PASS {tool}", flush=True)
            return value
        except Exception as exc:
            entries.append({"tool": tool, "passed": False, "error": str(exc), "arguments": kwargs})
            print(f"FAIL {tool}: {exc}", flush=True)
            raise

    state = call("project", "get_editor_state")
    baseline = call("actor", "list_level_actors", max_results=500)
    camera = call("viewport", "get_viewport_camera")
    original_selection = [a["identifier"] for a in state["selected_actors"]]
    try:
        call("project", "get_project_info")
        call("asset", "search_assets", content_path="/Engine/BasicShapes", max_results=10)
        call("viewport", "capture_viewport")
        cube = call("actor", "spawn_actor", class_path="/Script/Engine.StaticMeshActor", label=token, location={"x": 0, "y": 0, "z": 200})
        actors.append(cube["identifier"])
        call("actor", "get_actor", identifier=actors[0])
        component = next(c["identifier"] for c in cube["components"] if "StaticMeshComponent" in c["class"])
        call("component", "assign_static_mesh", component_identifier=component, mesh_path="/Engine/BasicShapes/Cube")
        call("actor", "set_actor_transform", identifier=actors[0], location={"x": 200, "y": 0, "z": 200})
        call("actor", "set_actor_transform", identifier=actors[0], rotation={"pitch": 0, "yaw": 45, "roll": 0})
        call("actor", "set_actor_transform", identifier=actors[0], scale={"x": 1.5, "y": 1.5, "z": 1.5})
        duplicate = call("actor", "duplicate_actor", identifier=actors[0], label=token + "_Copy", offset={"x": 200, "y": 0, "z": 0})
        actors.append(duplicate["identifier"])
        call("actor", "set_actor_tags", identifier=actors[0], tags=[token])
        call("actor", "select_actors", identifiers=actors)
        call("viewport", "focus_actor", identifier=actors[0])
        call("viewport", "capture_viewport")
        path = "/Game/" + token + "_BP"
        bp = call("blueprint", "create_blueprint", destination_path=path)
        assets.append(path)
        call("blueprint", "get_blueprint_parent_class", blueprint_path=path)
        call("blueprint", "add_blueprint_component", blueprint_path=path, class_path="/Script/Engine.StaticMeshComponent", component_name="TestMesh")
        call("blueprint", "list_blueprint_components", blueprint_path=path)
        call("blueprint", "add_blueprint_variable", blueprint_path=path, variable_name="TestValue", type_name="float")
        call("blueprint", "set_blueprint_variable_default", blueprint_path=path, variable_name="TestValue", value_json="42.5")
        compile_state = call("blueprint", "compile_blueprint", blueprint_path=path)
        assert compile_state["compiled"], compile_state
        call("blueprint", "get_blueprint_compile_errors", blueprint_path=path)
        call("blueprint", "get_blueprint_variables", blueprint_path=path)
        call("blueprint", "list_blueprint_nodes", blueprint_path=path)
        call("blueprint", "search_blueprint_node_types", blueprint_path=path, search="Print String", max_results=10)
        call("editor", "save_asset", exact_asset_path=path)
        info = call("blueprint", "get_blueprint_info", blueprint_path=path)
        spawned = call("actor", "spawn_actor", class_path=info["generated_class"], label=token + "_BPActor")
        actors.append(spawned["identifier"])
        call("gameplay", "start_pie", warmup_seconds=0.2)
        assert call("gameplay", "is_pie_running")["running"]
        call("debug", "get_recent_logs", max_lines=20)
        call("gameplay", "stop_pie")
        assert not call("gameplay", "is_pie_running")["running"]
    finally:
        try:
            if unwrap(client.tool("amine_unreal_mcp.tools." + SETS["gameplay"], "is_pie_running"))["running"]:
                call("gameplay", "stop_pie")
            for identifier in reversed(actors):
                try: call("actor", "delete_actor", identifier=identifier)
                except Exception: pass
            for path in reversed(assets):
                try: call("asset", "delete_asset", exact_asset_path=path)
                except Exception: pass
            call("actor", "select_actors", identifiers=original_selection)
            call("viewport", "set_viewport_camera", location=camera["location"], rotation=camera["rotation"])
            remaining = call("actor", "list_level_actors", max_results=500)
            assert remaining["actors"] == baseline["actors"], "Baseline actors changed or cleanup failed"
            assert not call("asset", "search_assets", name_substring=token)["assets"], "Temporary assets remain"
            entries.append({"tool": "verify_cleanup_and_baseline", "passed": True})
        except Exception as exc:
            entries.append({"tool": "verify_cleanup_and_baseline", "passed": False, "error": str(exc)})
        (OUT / "results.json").write_text(json.dumps({"test_token": token, "results": entries}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
