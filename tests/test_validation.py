import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validation", ROOT / "Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/common/validation.py")
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class Actor:
    def __init__(self, path, label, name):
        self.path, self.label, self.name = path, label, name
    def get_path_name(self): return self.path
    def get_actor_label(self): return self.label
    def get_name(self): return self.name


class ValidationTests(unittest.TestCase):
    def test_duplicate_labels_require_exact_path(self):
        objects = [Actor("/Game/Map:Door_1", "Door", "Door_1"), Actor("/Game/Map:Door_2", "Door", "Door_2")]
        with self.assertRaisesRegex(validation.ToolError, "matched 2"):
            validation.resolve_match(objects, "Door")
        self.assertIs(validation.resolve_match(objects, "/Game/Map:Door_2"), objects[1])

    def test_delete_rejects_even_unique_label(self):
        with self.assertRaises(validation.ToolError):
            validation.resolve_match([Actor("/Game/Map:One", "One", "One")], "One", True)

    def test_missing_and_substring_never_resolve(self):
        with self.assertRaises(validation.ToolError):
            validation.resolve_match([Actor("/Game/Map:Door", "Door", "Door")], "Doo")

    def test_read_engine_write_game(self):
        self.assertEqual(validation.asset_path("/Engine/BasicShapes/Cube.Cube"), "/Engine/BasicShapes/Cube")
        with self.assertRaises(validation.ToolError):
            validation.asset_path("/Engine/BasicShapes/Cube", True)
        self.assertEqual(validation.asset_path("/Game/Test/BP.BP", True), "/Game/Test/BP")

    def test_invalid_asset_references(self):
        for path in ("/Game/../Secret", "/Game/A:B", "C:/secret", "/Game//A", "/Game/Foo.Other", "/Game/A*", "/Game/A'", "/Game/Folder/"):
            with self.subTest(path=path), self.assertRaises(validation.ToolError):
                validation.asset_path(path)

    def test_bounded_limits(self):
        for value in (0, -1, 501, True):
            with self.assertRaises(validation.ToolError):
                validation.limit(value)
        self.assertEqual(validation.limit(500), 500)

    def test_finite_values(self):
        validation.finite([0, -2.5, 100])
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(validation.ToolError):
                validation.finite([value])

    def test_names(self):
        self.assertEqual(validation.name("MCP_TEST_1"), "MCP_TEST_1")
        for value in ("", "0bad", "Name with spaces", "../Name"):
            with self.assertRaises(validation.ToolError):
                validation.name(value)

    def test_descriptor_and_python_syntax(self):
        import ast
        import json
        plugin = ROOT / "Plugins/AmineUnrealMCP"
        descriptor = json.loads((plugin / "AmineUnrealMCP.uplugin").read_text())
        self.assertEqual(descriptor["VersionName"], "0.1.0")
        for path in (plugin / "Content/Python").rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
