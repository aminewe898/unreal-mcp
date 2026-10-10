#!/usr/bin/env python3
"""Standard-library Python tool-documentation generator for AmineUnrealMCP.

Parses tool modules via ast without importing Unreal Engine or plugin binaries.
Discovers tools decorated with toolset_registry.tool_call and outputs docs/TOOLS.md.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any


@dataclass
class ParameterDoc:
    name: str
    type_annotation: str
    default_str: str | None
    is_required: bool
    default_node: ast.AST | None


@dataclass
class ToolDoc:
    name: str
    docstring: str
    parameters: list[ParameterDoc]
    return_type: str
    is_guarded: bool
    is_static: bool
    toolset_name: str
    toolset_class_name: str
    module_relpath: str


@dataclass
class ToolsetDoc:
    class_name: str
    full_name: str
    docstring: str
    module_relpath: str
    tools: list[ToolDoc]


def is_tool_call_decorator(decorator: ast.AST) -> bool:
    """Return True if the decorator matches toolset_registry.tool_call or tool_call."""
    node = decorator
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        if node.attr == "tool_call":
            if isinstance(node.value, ast.Name) and node.value.id in ("toolset_registry", "registry"):
                return True
            return True
    elif isinstance(node, ast.Name) and node.id == "tool_call":
        return True
    return False


def has_decorator_name(func_def: ast.FunctionDef, name: str) -> bool:
    """Check if func_def has a decorator with given identifier or attribute name."""
    for dec in func_def.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name) and target.id == name:
            return True
        elif isinstance(target, ast.Attribute) and target.attr == name:
            return True
    return False


def extract_parameters(func_def: ast.FunctionDef) -> list[ParameterDoc]:
    """Extract ParameterDoc entries honoring ast.unparse for defaults and annotations."""
    params: list[ParameterDoc] = []
    args = func_def.args
    is_static = has_decorator_name(func_def, "staticmethod")

    pos_args = args.args
    defaults = args.defaults
    num_pos = len(pos_args)
    num_defaults = len(defaults)
    first_default_idx = num_pos - num_defaults

    for i, arg in enumerate(pos_args):
        if not is_static and arg.arg in ("self", "cls"):
            continue

        type_annot = ast.unparse(arg.annotation) if arg.annotation is not None else "Any"
        default_node: ast.AST | None = None
        default_str: str | None = None
        is_required = True

        default_idx = i - first_default_idx
        if default_idx >= 0:
            default_node = defaults[default_idx]
            default_str = ast.unparse(default_node)
            is_required = False

        params.append(
            ParameterDoc(
                name=arg.arg,
                type_annotation=type_annot,
                default_str=default_str,
                is_required=is_required,
                default_node=default_node,
            )
        )

    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
        type_annot = ast.unparse(arg.annotation) if arg.annotation is not None else "Any"
        default_str = ast.unparse(kw_default) if kw_default is not None else None
        params.append(
            ParameterDoc(
                name=arg.arg,
                type_annotation=type_annot,
                default_str=default_str,
                is_required=kw_default is None,
                default_node=kw_default,
            )
        )

    return params


def eval_ast_default(node: ast.AST) -> Any:
    """Safely convert common AST default expressions into JSON-serializable Python objects."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            return -node.operand.value
        elif isinstance(node.op, ast.UAdd) and isinstance(node.operand, ast.Constant):
            return node.operand.value
    elif isinstance(node, ast.List):
        return [eval_ast_default(elt) for elt in node.elts]
    elif isinstance(node, ast.Dict):
        return {eval_ast_default(k): eval_ast_default(v) for k, v in zip(node.keys, node.values)}
    elif isinstance(node, ast.Call):
        func_expr = ast.unparse(node.func)
        if func_expr in ("unreal.Vector", "Vector"):
            args = [eval_ast_default(a) for a in node.args]
            if len(args) == 3:
                return {"x": float(args[0]), "y": float(args[1]), "z": float(args[2])}
            elif len(args) == 1:
                return {"x": float(args[0]), "y": float(args[0]), "z": float(args[0])}
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        elif func_expr in ("unreal.Rotator", "Rotator"):
            args = [eval_ast_default(a) for a in node.args]
            if len(args) == 3:
                return {"pitch": float(args[0]), "yaw": float(args[1]), "roll": float(args[2])}
            return {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
        elif func_expr in ("unreal.Transform", "Transform"):
            return {
                "location": {"x": 0.0, "y": 0.0, "z": 0.0},
                "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
            }
        elif func_expr in ("unreal.LinearColor", "LinearColor"):
            args = [eval_ast_default(a) for a in node.args]
            if len(args) == 4:
                return {"r": float(args[0]), "g": float(args[1]), "b": float(args[2]), "a": float(args[3])}
            return {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
    return ast.unparse(node)


def get_placeholder_value(name: str, type_str: str) -> Any:
    """Generate meaningful placeholder values for required parameters."""
    if "Vector" in type_str:
        return {"x": 0.0, "y": 0.0, "z": 0.0}
    if "Rotator" in type_str:
        return {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
    if "Transform" in type_str:
        return {
            "location": {"x": 0.0, "y": 0.0, "z": 0.0},
            "rotation": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
        }
    if "LinearColor" in type_str:
        return {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
    if "MaterialProperty" in type_str:
        return "MP_BaseColor"

    if type_str.startswith("list[") or type_str.startswith("List["):
        if "actor" in name or "identifier" in name:
            return ["/Game/Maps/Main.Main:PersistentLevel.Actor_1"]
        elif "asset" in name or "path" in name:
            return ["/Game/Assets/MyAsset"]
        elif "test" in name:
            return ["Project.Automation.Test1"]
        elif "property" in name:
            return ["RelativeLocation"]
        elif "tag" in name:
            return ["TagA"]
        return ["item_1"]

    if type_str == "int":
        if "frame" in name:
            return 100 if "end" in name else 0
        elif "width" in name:
            return 1280
        elif "height" in name:
            return 720
        elif "slot" in name:
            return 0
        elif "max" in name or "limit" in name:
            return 100
        return 0

    if type_str == "float":
        if "intensity" in name:
            return 1000.0
        elif "kelvin" in name or "temperature" in name:
            return 6500.0
        elif "warmup" in name:
            return 0.5
        return 1.0

    if type_str == "bool":
        if "simulate" in name:
            return False
        return True

    # Parameter-name specific placeholders
    if "component_identifier" in name:
        return "/Game/Maps/Main.Main:PersistentLevel.Actor_1.DefaultSceneRoot"
    elif "parent_identifier" in name:
        return "/Game/Maps/Main.Main:PersistentLevel.ParentActor_1"
    elif "identifier" in name or "actor" in name:
        return "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
    elif "expression_class_path" in name:
        return "/Script/Engine.MaterialExpressionConstant"
    elif "class_path" in name or "parent_class" in name or "base_class" in name:
        return "/Script/Engine.Actor"
    elif "blueprint_path" in name:
        return "/Game/Blueprints/BP_MyActor"
    elif "parent_material_path" in name or "material_path" in name:
        return "/Game/Materials/M_Material"
    elif "instance_path" in name:
        return "/Game/Materials/MI_MaterialInstance"
    elif "mesh_path" in name:
        return "/Game/Meshes/SM_StaticMesh"
    elif "texture_path" in name:
        return "/Game/Textures/T_Texture"
    elif "sequence_path" in name:
        return "/Game/Cinematics/LS_Sequence"
    elif "system_path" in name:
        return "/Game/VFX/NS_System"
    elif "graph_path" in name:
        return "/Game/PCG/PCG_Graph"
    elif "source_path" in name:
        return "/Game/Assets/SourceAsset"
    elif "destination_path" in name:
        return "/Game/Assets/NewAsset"
    elif "destination_folder" in name or "folder" in name:
        return "/Game/SubFolder"
    elif "content_path" in name:
        return "/Game"
    elif "exact_asset_path" in name or "asset_path_value" in name or "asset_path" in name:
        return "/Game/Assets/MyAsset"
    elif "project_relative_filename" in name:
        return "SourceAssets/Model.fbx"
    elif "value_json" in name:
        return '{"PropertyName": "Value"}'
    elif "property_name" in name:
        return "RelativeLocation"
    elif "parameter_name" in name:
        return "Roughness"
    elif "variable_name" in name:
        return "MyVariable"
    elif "component_name" in name:
        return "MyComponent"
    elif "function_name" in name:
        return "MyFunction"
    elif "type_id" in name:
        return "K2Node_CallFunction"
    elif "type_name" in name:
        return "float"
    elif "output_node" in name:
        return "/Game/Blueprints/BP_Actor.BP_Actor:EventGraph.Node_1"
    elif "input_node" in name:
        return "/Game/Blueprints/BP_Actor.BP_Actor:EventGraph.Node_2"
    elif "output_pin" in name or "input_pin" in name:
        return "Execute"
    elif "output_name" in name or "input_name" in name:
        return "Output"
    elif "kind" in name:
        return "point"
    elif "severity" in name:
        return "error"
    elif "label" in name:
        return "MyActor"
    elif "tag" in name:
        return "MyTag"
    elif "search" in name or "substring" in name:
        return "SearchTerm"
    elif "value" in name:
        return "1.0"

    return "example_value"


def build_call_tool_example(tool: ToolDoc) -> dict[str, Any]:
    """Construct an MCP call_tool parameter example honoring defaults."""
    arguments: dict[str, Any] = {}
    for param in tool.parameters:
        if param.default_node is not None:
            arguments[param.name] = eval_ast_default(param.default_node)
        else:
            arguments[param.name] = get_placeholder_value(param.name, param.type_annotation)
    return {
        "toolset_name": tool.toolset_name,
        "tool_name": tool.name,
        "arguments": arguments,
    }


def classify_tool_execution(tool: ToolDoc) -> str:
    """Classify the execution paradigm and result envelope of a tool."""
    if tool.is_guarded:
        return "Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)"
    elif "AmineViewportCapture" in tool.return_type:
        return "Viewport Framebuffer Capture (`unreal.AmineViewportCapture` PNG content + metadata)"
    elif "ToolCallAsyncResult" in tool.return_type:
        return f"Native Asynchronous Operation (`{tool.return_type}`)"
    return f"Direct Return (`{tool.return_type}`)"


def discover_toolsets(tools_dir: Path, repo_root: Path | None = None) -> list[ToolsetDoc]:
    """Parse all Python modules under tools_dir with AST and discover toolsets and tools."""
    if not tools_dir.is_dir():
        return []

    toolsets: list[ToolsetDoc] = []
    py_files = sorted(tools_dir.glob("*.py"))

    for py_file in py_files:
        if py_file.name == "__init__.py":
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=py_file.name)
        except Exception:
            continue

        if repo_root is not None:
            try:
                rel_path = py_file.resolve().relative_to(repo_root.resolve()).as_posix()
            except ValueError:
                rel_path = py_file.name
        else:
            rel_path = py_file.name

        module_stem = py_file.stem

        for stmt in tree.body:
            if isinstance(stmt, ast.ClassDef):
                cls_docstring = ast.get_docstring(stmt) or ""
                full_toolset_name = f"amine_unreal_mcp.tools.{module_stem}.{stmt.name}"
                tools_in_cls: list[ToolDoc] = []

                for item in stmt.body:
                    if isinstance(item, ast.FunctionDef):
                        decorated_tool = any(is_tool_call_decorator(d) for d in item.decorator_list)
                        if not decorated_tool:
                            continue

                        fn_docstring = ast.get_docstring(item) or ""
                        returns_str = ast.unparse(item.returns) if item.returns is not None else "None"
                        params = extract_parameters(item)
                        is_guarded = has_decorator_name(item, "guarded")
                        is_static = has_decorator_name(item, "staticmethod")

                        tools_in_cls.append(
                            ToolDoc(
                                name=item.name,
                                docstring=fn_docstring,
                                parameters=params,
                                return_type=returns_str,
                                is_guarded=is_guarded,
                                is_static=is_static,
                                toolset_name=full_toolset_name,
                                toolset_class_name=stmt.name,
                                module_relpath=rel_path,
                            )
                        )

                if tools_in_cls:
                    tools_in_cls.sort(key=lambda t: t.name)
                    toolsets.append(
                        ToolsetDoc(
                            class_name=stmt.name,
                            full_name=full_toolset_name,
                            docstring=cls_docstring,
                            module_relpath=rel_path,
                            tools=tools_in_cls,
                        )
                    )

    toolsets.sort(key=lambda ts: ts.class_name)
    return toolsets


def generate_markdown(toolsets: list[ToolsetDoc]) -> str:
    """Generate deterministic markdown content for docs/TOOLS.md."""
    total_tools = sum(len(ts.tools) for ts in toolsets)
    total_toolsets = len(toolsets)

    lines: list[str] = [
        "# Unreal MCP Tool Reference",
        "",
        "> **Notice**: This documentation is statically extracted from AmineUnrealMCP tool definitions using Python AST analysis. Examples are declarative structural templates illustrating parameter shapes and defaults for MCP `call_tool`; they do not represent verified execution traces from a running Unreal Engine session.",
        "",
        "## Overview",
        "",
        f"- **Total Toolsets**: {total_toolsets}",
        f"- **Total Registered Tools**: {total_tools} Python toolset tools + 1 native MCP tool (`amine_capture_viewport`)",
        "",
        "### Native MCP Tools (`IModelContextProtocolTool`)",
        "",
        "In addition to the Python toolset tools registered through Epic's ToolsetRegistry, the plugin provides 1 native C++ tool registered directly with Epic's `IModelContextProtocolModule`:",
        "",
        "- `amine_capture_viewport`: Native viewport framebuffer capture returning real PNG image content blocks, text metadata, and structuredContent. Direct MCP tool call example:",
        "  ```json",
        "  {",
        '    "name": "amine_capture_viewport",',
        '    "arguments": {',
        '      "width": 1280,',
        '      "height": 720',
        "    }",
        "  }",
        "  ```",
        "",
        "## Result Formats & Error Handling",
        "",
        "AmineUnrealMCP tools adhere to structured result envelopes and execution models:",
        "",
        "### 1. Guarded Synchronous Tools (`-> str`)",
        "The majority of tools are synchronous and decorated with `@guarded`. Mutation calls execute within scoped editor transactions, while read-only queries run without transaction overhead. All guarded calls execute within structured error boundaries, returning a JSON string envelope:",
        "",
        "- **Success Response**:",
        "  ```json",
        "  {",
        '    "success": true,',
        '    "data": {}',
        "  }",
        "  ```",
        "- **Error Response** (on handled `ToolError` or unexpected exception):",
        "  ```json",
        "  {",
        '    "success": false,',
        '    "error": "error_code",',
        '    "message": "Human-readable description"',
        "  }",
        "  ```",
        "In Epic's Model Context Protocol (MCP) environment, this returned JSON string is placed inside the MCP tool execution response's `returnValue` property (e.g. `{\"returnValue\": \"{\\\"success\\\":true,\\\"data\\\":{}}\"}`).",
        "",
        "### 2. Viewport Framebuffer Capture (`-> unreal.AmineViewportCapture` and Native `amine_capture_viewport`)",
        "Epic's registry adapter serializes all ToolsetRegistry results as JSON text, including nested `FToolsetImage` structures. Consequently, the Python `capture_viewport` tool returns JSON text containing image data and metadata rather than MCP image content blocks. To provide actual MCP image content, the native `FAmineCaptureTool` in `AmineMCPBridge.cpp` registers `amine_capture_viewport` directly through Epic's `IModelContextProtocolModule`. Calling `amine_capture_viewport` returns actual PNG image content plus text metadata and `structuredContent` (map, camera, dimensions).",
        "",
        "### 3. Native Asynchronous Operations (`-> unreal.ToolCallAsyncResultVoid` / `-> unreal.ToolCallAsyncResultString`)",
        "Tools executing asynchronous engine operations (such as automation testing via `discover_automation_tests` and `run_automation_tests`, Play-In-Editor session lifecycle via `start_pie` and `stop_pie`, or Content Browser selection via `sync_content_browser`) return native Epic async tokens. These resolve upon completion or abort; failed or timed-out async operations may surface as MCP `isError: true`.",
        "",
        "## Toolset Index",
        "",
        "| Toolset Class | Source Module | Tools Count | Summary |",
        "| --- | --- | ---: | --- |",
    ]

    for ts in toolsets:
        clean_doc = ts.docstring.replace("\n", " ").strip() if ts.docstring else "Toolset definition."
        lines.append(f"| [`{ts.class_name}`](#{ts.class_name.lower()}) | `{ts.module_relpath}` | {len(ts.tools)} | {clean_doc} |")

    lines.append("")

    for ts in toolsets:
        lines.extend([
            f"## {ts.class_name}",
            "",
            f"**Source File**: `{ts.module_relpath}`  ",
            f"**Description**: {ts.docstring.strip() if ts.docstring else 'No class docstring provided.'}  ",
            f"**Tools in Set**: {len(ts.tools)}",
            "",
            "---",
            "",
        ])

        for tool in ts.tools:
            exec_desc = classify_tool_execution(tool)
            tool_doc = tool.docstring.strip() if tool.docstring else "No description provided."

            lines.extend([
                f"### {tool.name}",
                "",
                f"{tool_doc}",
                "",
                f"- **Execution Category**: {exec_desc}",
                f"- **Return Annotation**: `{tool.return_type}`",
                "",
                "#### Parameters",
                "",
            ])

            if tool.parameters:
                lines.extend([
                    "| Parameter | Type | Default | Required |",
                    "| --- | --- | --- | --- |",
                ])
                for param in tool.parameters:
                    def_str = f"`{param.default_str}`" if param.default_str is not None else "*None*"
                    req_str = "Yes" if param.is_required else "No"
                    lines.append(f"| `{param.name}` | `{param.type_annotation}` | {def_str} | {req_str} |")
            else:
                lines.append("This tool takes no parameters.")

            lines.extend([
                "",
                "#### Example `call_tool` Invocation",
                "",
                "```json",
                json.dumps(build_call_tool_example(tool), indent=2),
                "```",
                "",
            ])

    return "\n".join(lines) + "\n"


def generate_docs(repo_root: Path | None = None, output_path: Path | None = None) -> Path:
    """Discover tools and write markdown documentation to output_path."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    tools_dir = repo_root / "Plugins" / "AmineUnrealMCP" / "Content" / "Python" / "amine_unreal_mcp" / "tools"
    if output_path is None:
        output_path = repo_root / "docs" / "TOOLS.md"

    toolsets = discover_toolsets(tools_dir, repo_root=repo_root)
    markdown_content = generate_markdown(toolsets)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown_content, encoding="utf-8")
    return output_path


def main() -> None:
    """CLI entry point for scripts/generate_tool_docs.py."""
    repo_root = Path(__file__).resolve().parent.parent
    output_file = generate_docs(repo_root=repo_root)
    print(f"[generate_tool_docs] Successfully wrote documentation to {output_file}")


if __name__ == "__main__":
    main()
