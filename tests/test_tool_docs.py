"""Unit tests for generate_tool_docs.py.

Verifies discovery, signature/default extraction, valid JSON examples,
deterministic output, and zero dependency on unreal / plugin imports.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest

# Ensure scripts directory is on sys.path for importing generate_tool_docs
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generate_tool_docs  # noqa: E402


class TestNoUnrealImports(unittest.TestCase):
    """Verify that the tool doc generator operates without importing Unreal."""

    def test_unreal_not_imported(self) -> None:
        """The generator module must not import unreal or plugin modules."""
        self.assertNotIn("unreal", sys.modules, "unreal must not be imported in sys.modules")
        self.assertNotIn("amine_unreal_mcp", sys.modules, "amine_unreal_mcp must not be in sys.modules")

    def test_generator_ast_has_no_unreal_imports(self) -> None:
        """Statically verify generate_tool_docs.py AST imports only standard library."""
        script_file = SCRIPTS_DIR / "generate_tool_docs.py"
        self.assertTrue(script_file.is_file())
        tree = ast.parse(script_file.read_text(encoding="utf-8"))

        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split(".")[0])

        self.assertNotIn("unreal", imported_names)
        self.assertNotIn("amine_unreal_mcp", imported_names)
        self.assertNotIn("toolset_registry", imported_names)


class TestDiscoveryAndHelpers(unittest.TestCase):
    """Verify tool discovery, filtering of helpers, and class inspection."""

    def test_fixture_discovery_and_helper_skipping(self) -> None:
        """Helper functions without @toolset_registry.tool_call must be excluded."""
        fixture_code = '''
import toolset_registry

def helper_one(param: str) -> str:
    """This is a helper and should be skipped."""
    return param

class AmineSampleTools:
    """Sample toolset for testing."""

    @toolset_registry.tool_call
    @staticmethod
    def sample_tool(actor_path: str, count: int = 5) -> str:
        """Registered tool description."""
        return actor_path

    def class_helper(self):
        """Class helper that is not decorated with tool_call."""
        return True

class UndecoratedClass:
    """Class with no tools."""
    def foo(self):
        pass
'''
        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = Path(tmp_dir)
            sample_file = tools_dir / "sample_tools.py"
            sample_file.write_text(fixture_code, encoding="utf-8")

            toolsets = generate_tool_docs.discover_toolsets(tools_dir)
            self.assertEqual(len(toolsets), 1)
            ts = toolsets[0]
            self.assertEqual(ts.class_name, "AmineSampleTools")
            self.assertEqual(ts.docstring, "Sample toolset for testing.")
            self.assertEqual(len(ts.tools), 1)

            tool = ts.tools[0]
            self.assertEqual(tool.name, "sample_tool")
            self.assertEqual(tool.docstring, "Registered tool description.")
            self.assertTrue(tool.is_static)
            self.assertFalse(tool.is_guarded)


class TestSignatureAndDefaultExtraction(unittest.TestCase):
    """Verify accurate extraction of parameter types, defaults, and return annotations."""

    def test_signature_extraction(self) -> None:
        fixture_code = '''
import toolset_registry

class AmineAdvancedTools:
    """Docstring for advanced tools."""

    @toolset_registry.tool_call
    @staticmethod
    def configure(
        identifier: str,
        location: unreal.Vector = unreal.Vector(),
        rotation: unreal.Rotator = unreal.Rotator(),
        scale: unreal.Vector = unreal.Vector(1, 1, 1),
        max_results: int = 100,
        label: str = "",
        enabled: bool = True,
        opt_vector: unreal.Vector | None = None
    ) -> str:
        """Configure editor entity."""
        return "ok"
'''
        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = Path(tmp_dir)
            (tools_dir / "advanced_tools.py").write_text(fixture_code, encoding="utf-8")

            toolsets = generate_tool_docs.discover_toolsets(tools_dir)
            self.assertEqual(len(toolsets), 1)
            tools = toolsets[0].tools
            self.assertEqual(len(tools), 1)
            tool = tools[0]

            self.assertEqual(tool.return_type, "str")
            param_map = {p.name: p for p in tool.parameters}

            # Required parameter
            self.assertIn("identifier", param_map)
            self.assertTrue(param_map["identifier"].is_required)
            self.assertIsNone(param_map["identifier"].default_str)
            self.assertEqual(param_map["identifier"].type_annotation, "str")

            # Default unreal.Vector()
            self.assertIn("location", param_map)
            self.assertFalse(param_map["location"].is_required)
            self.assertEqual(param_map["location"].default_str, "unreal.Vector()")
            self.assertEqual(param_map["location"].type_annotation, "unreal.Vector")

            # Default unreal.Vector(1, 1, 1)
            self.assertIn("scale", param_map)
            self.assertEqual(param_map["scale"].default_str, "unreal.Vector(1, 1, 1)")

            # Primitive defaults
            self.assertEqual(param_map["max_results"].default_str, "100")
            self.assertEqual(param_map["max_results"].type_annotation, "int")
            self.assertEqual(param_map["enabled"].default_str, "True")
            self.assertEqual(param_map["enabled"].type_annotation, "bool")
            self.assertEqual(param_map["opt_vector"].default_str, "None")


class TestValidJsonExamples(unittest.TestCase):
    """Verify that synthesized examples honor defaults and produce valid JSON shapes."""

    def test_example_json_validity_and_defaults(self) -> None:
        fixture_code = '''
import toolset_registry

class AmineSpawnTools:
    """Spawning toolset."""

    @toolset_registry.tool_call
    @staticmethod
    def spawn_actor(
        class_path: str,
        label: str = "TestActor",
        location: unreal.Vector = unreal.Vector(),
        rotation: unreal.Rotator = unreal.Rotator(),
        scale: unreal.Vector = unreal.Vector(1, 1, 1)
    ) -> str:
        """Spawn actor into editor."""
        return "spawned"

    @toolset_registry.tool_call
    @staticmethod
    def set_viewport_camera(
        location: unreal.Vector,
        rotation: unreal.Rotator
    ) -> str:
        """Set viewport camera without defaults."""
        return "set"
'''
        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = Path(tmp_dir)
            (tools_dir / "spawn_tools.py").write_text(fixture_code, encoding="utf-8")

            toolsets = generate_tool_docs.discover_toolsets(tools_dir)
            tool_map = {t.name: t for t in toolsets[0].tools}

            # Test spawn_actor honors defaults and meta-tool dispatch keys
            spawn_ex = generate_tool_docs.build_call_tool_example(tool_map["spawn_actor"])
            json_str = json.dumps(spawn_ex)
            parsed = json.loads(json_str)

            self.assertEqual(set(parsed.keys()), {"toolset_name", "tool_name", "arguments"})
            self.assertEqual(parsed["toolset_name"], "amine_unreal_mcp.tools.spawn_tools.AmineSpawnTools")
            self.assertEqual(parsed["tool_name"], "spawn_actor")
            args = parsed["arguments"]
            self.assertEqual(args["label"], "TestActor")
            self.assertEqual(args["location"], {"x": 0.0, "y": 0.0, "z": 0.0})
            self.assertEqual(args["rotation"], {"pitch": 0.0, "yaw": 0.0, "roll": 0.0})
            self.assertEqual(args["scale"], {"x": 1.0, "y": 1.0, "z": 1.0})
            self.assertTrue(args["class_path"].startswith("/Script/"))

            # Test set_viewport_camera required vector/rotator shapes
            cam_ex = generate_tool_docs.build_call_tool_example(tool_map["set_viewport_camera"])
            parsed_cam = json.loads(json.dumps(cam_ex))
            self.assertEqual(set(parsed_cam.keys()), {"toolset_name", "tool_name", "arguments"})
            self.assertEqual(parsed_cam["toolset_name"], "amine_unreal_mcp.tools.spawn_tools.AmineSpawnTools")
            self.assertEqual(parsed_cam["tool_name"], "set_viewport_camera")
            cam_args = parsed_cam["arguments"]
            self.assertIn("x", cam_args["location"])
            self.assertIn("pitch", cam_args["rotation"])


class TestDeterministicOutput(unittest.TestCase):
    """Verify deterministic, bit-for-bit identical markdown output."""

    def test_output_is_deterministic(self) -> None:
        fixture_code = '''
import toolset_registry

class AmineAlphaTools:
    @toolset_registry.tool_call
    @staticmethod
    def tool_b() -> str:
        """Second tool."""
        return ""

    @toolset_registry.tool_call
    @staticmethod
    def tool_a() -> str:
        """First tool."""
        return ""
'''
        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = Path(tmp_dir)
            (tools_dir / "alpha_tools.py").write_text(fixture_code, encoding="utf-8")

            toolsets_1 = generate_tool_docs.discover_toolsets(tools_dir)
            toolsets_2 = generate_tool_docs.discover_toolsets(tools_dir)

            md1 = generate_tool_docs.generate_markdown(toolsets_1)
            md2 = generate_tool_docs.generate_markdown(toolsets_2)

            self.assertEqual(md1, md2)
            self.assertIn("### tool_a", md1)
            self.assertIn("### tool_b", md1)
            # Stably sorted
            self.assertLess(md1.index("### tool_a"), md1.index("### tool_b"))


class TestWorkspacePluginTools(unittest.TestCase):
    """End-to-end verification against the actual workspace tool definitions."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parent.parent
        self.tools_dir = self.repo_root / "Plugins" / "AmineUnrealMCP" / "Content" / "Python" / "amine_unreal_mcp" / "tools"

    def test_all_workspace_toolsets_discovered(self) -> None:
        toolsets = generate_tool_docs.discover_toolsets(self.tools_dir, repo_root=self.repo_root)
        self.assertEqual(len(toolsets), 16, f"Expected 16 toolsets, found {len(toolsets)}")

        total_tools = sum(len(ts.tools) for ts in toolsets)
        self.assertEqual(total_tools, 111, f"Expected 111 total tools, found {total_tools}")

        # Check key toolsets are present
        class_names = {ts.class_name for ts in toolsets}
        expected_classes = {
            "AmineActorTools", "AmineAssetTools", "AmineBlueprintTools", "AmineComponentTools",
            "AmineDebugTools", "AmineEditorTools", "AmineGameplayTools", "AmineLightingTools",
            "AmineMaterialTools", "AmineNiagaraTools", "AminePCGTools", "AmineProjectTools",
            "AmineReflectionTools", "AmineSequencerTools", "AmineTestingTools", "AmineViewportTools",
        }
        self.assertEqual(class_names, expected_classes)

    def test_all_tools_generate_valid_json(self) -> None:
        toolsets = generate_tool_docs.discover_toolsets(self.tools_dir, repo_root=self.repo_root)
        for ts in toolsets:
            self.assertTrue(ts.full_name.startswith("amine_unreal_mcp.tools."))
            self.assertTrue(ts.full_name.endswith(f".{ts.class_name}"))
            for tool in ts.tools:
                example = generate_tool_docs.build_call_tool_example(tool)
                serialized = json.dumps(example)
                deserialized = json.loads(serialized)
                self.assertEqual(set(deserialized.keys()), {"toolset_name", "tool_name", "arguments"})
                self.assertEqual(deserialized["toolset_name"], ts.full_name)
                self.assertEqual(deserialized["tool_name"], tool.name)
                self.assertIsInstance(deserialized["arguments"], dict)

    def test_markdown_generation_no_absolute_paths(self) -> None:
        toolsets = generate_tool_docs.discover_toolsets(self.tools_dir, repo_root=self.repo_root)
        markdown = generate_tool_docs.generate_markdown(toolsets)

        # Must not contain absolute Windows/Unix local user paths
        self.assertNotIn("C:\\", markdown)
        self.assertNotIn("C:/", markdown)
        self.assertNotIn("/home/", markdown)
        self.assertNotIn("amine", markdown.lower().split("amineunrealmcp")[0])

        # Must contain explanation of result formats and native tool
        self.assertIn("Guarded Synchronous Tools", markdown)
        self.assertIn("Viewport Framebuffer Capture", markdown)
        self.assertIn("Native Asynchronous Operations", markdown)
        self.assertIn("returnValue", markdown)
        self.assertIn("amine_capture_viewport", markdown)
        self.assertIn("111 Python toolset tools + 1 native MCP tool", markdown)


if __name__ == "__main__":
    unittest.main()
