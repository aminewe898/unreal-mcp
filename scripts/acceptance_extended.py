"""Additional real MCP checks against the isolated AmineMCPHost only."""
import json
import uuid
from acceptance import Client, ROOT, SETS, unwrap


def main():
    client = Client()
    token = "MCP_TEST_" + uuid.uuid4().hex[:8]
    results, assets, actors = [], [], []

    def call(group, tool, **arguments):
        try:
            value = unwrap(client.tool("amine_unreal_mcp.tools." + SETS[group], tool, arguments))
            results.append({"tool": tool, "passed": True, "result": value})
            print("PASS", tool, flush=True)
            return value
        except Exception as error:
            results.append({"tool": tool, "passed": False, "error": str(error)})
            print("FAIL", tool, error, flush=True)
            raise

    try:
        call("project", "get_project_settings")
        for arguments in ({"width": 0}, {"height": 1441}, {"width": 64.5}, {"width": True}, {"extra": 1}):
            assert client.call("amine_capture_viewport", arguments).get("isError"), arguments
        results.append({"tool": "capture_rejects_invalid_inputs", "passed": True})
        mesh = call("material", "get_static_mesh_info", mesh_path="/Engine/BasicShapes/Cube")
        assert mesh["lod_count"] >= 1
        material_path, instance_path, sequence_path = ["/Game/" + token + suffix for suffix in ("_M", "_MI", "_LS")]
        material = call("material", "create_material", destination_path=material_path)
        assets.append(material_path)
        call("material", "get_material_info", material_path=material_path)
        expression = call("material", "add_material_node", material_path=material_path, expression_class_path="/Script/Engine.MaterialExpressionScalarParameter")
        call("reflection", "list_object_properties", identifier=expression["identifier"])
        call("material", "compile_material", material_path=material_path)
        call("material", "create_material_instance", destination_path=instance_path, parent_material_path=material_path)
        assets.append(instance_path)
        info = call("material", "get_material_info", material_path=instance_path)
        parameter = info["parameters"][0]["name"]
        value = call("material", "set_material_instance_scalar", instance_path=instance_path, parameter_name=parameter, value=0.75)
        assert value["value"] == 0.75
        light = call("lighting", "create_light", label=token)
        actors.append(light["identifier"])
        rejected = client.tool("amine_unreal_mcp.tools." + SETS["actor"], "delete_actor", {"identifier": token})
        try:
            unwrap(rejected)
        except RuntimeError:
            results.append({"tool": "reject_actor_deletion_by_label", "passed": True})
        else:
            raise AssertionError("Label-based deletion must be rejected")
        call("lighting", "set_light_intensity", identifier=actors[0], intensity=500)
        call("lighting", "set_light_color", identifier=actors[0], color={"r": 1, "g": 0.5, "b": 0.25, "a": 1})
        call("lighting", "set_light_temperature", identifier=actors[0], kelvin=5000)
        call("sequencer", "create_level_sequence", destination_path=sequence_path)
        assets.append(sequence_path)
        call("sequencer", "set_sequence_playback_range", sequence_path=sequence_path, start_frame=10, end_frame=100)
        call("sequencer", "bind_actor_to_sequence", sequence_path=sequence_path, actor_identifier=actors[0])
        info = call("sequencer", "get_level_sequence_info", sequence_path=sequence_path)
        assert (info["start_frame"], info["end_frame"]) == (10, 100)
        assert len(info["bindings"]) == 1
        call("testing", "discover_automation_tests")
        call("testing", "list_automation_tests", name_substring="ToolsetRegistry", max_results=10)
        discovered = call("testing", "list_automation_tests", name_substring="AI.ToolsetRegistry.ColorConverterSpec.Converts FColor property to and from JSON", max_results=10)
        assert len(discovered["tests"]) == 1
        completed = call("testing", "run_automation_tests", test_names=discovered["tests"])
        assert completed["failed"] == 0 and completed["passed"] == 1, completed
        call("testing", "get_automation_test_status")
        call("testing", "get_automation_test_results")
    finally:
        for identifier in reversed(actors):
            try: call("actor", "delete_actor", identifier=identifier)
            except Exception: pass
        for path in reversed(assets):
            try: call("asset", "delete_asset", exact_asset_path=path)
            except Exception: pass
        remaining = call("asset", "search_assets", name_substring=token)
        results.append({"tool": "verify_extended_cleanup", "passed": not remaining["assets"]})
        output = ROOT / "Saved/Acceptance/extended-results.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"test_token": token, "results": results}, indent=2), encoding="utf-8")
    assert all(entry["passed"] for entry in results), "Extended checks or cleanup failed"


if __name__ == "__main__":
    main()
