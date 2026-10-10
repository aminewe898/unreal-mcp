# Unreal MCP Tool Reference

> **Notice**: This documentation is statically extracted from AmineUnrealMCP tool definitions using Python AST analysis. Examples are declarative structural templates illustrating parameter shapes and defaults for MCP `call_tool`; they do not represent verified execution traces from a running Unreal Engine session.

## Overview

- **Total Toolsets**: 16
- **Total Registered Tools**: 111 Python toolset tools + 1 native MCP tool (`amine_capture_viewport`)

### Native MCP Tools (`IModelContextProtocolTool`)

In addition to the Python toolset tools registered through Epic's ToolsetRegistry, the plugin provides 1 native C++ tool registered directly with Epic's `IModelContextProtocolModule`:

- `amine_capture_viewport`: Native viewport framebuffer capture returning real PNG image content blocks, text metadata, and structuredContent. Direct MCP tool call example:
  ```json
  {
    "name": "amine_capture_viewport",
    "arguments": {
      "width": 1280,
      "height": 720
    }
  }
  ```

## Result Formats & Error Handling

AmineUnrealMCP tools adhere to structured result envelopes and execution models:

### 1. Guarded Synchronous Tools (`-> str`)
The majority of tools are synchronous and decorated with `@guarded`. Mutation calls execute within scoped editor transactions, while read-only queries run without transaction overhead. All guarded calls execute within structured error boundaries, returning a JSON string envelope:

- **Success Response**:
  ```json
  {
    "success": true,
    "data": {}
  }
  ```
- **Error Response** (on handled `ToolError` or unexpected exception):
  ```json
  {
    "success": false,
    "error": "error_code",
    "message": "Human-readable description"
  }
  ```
In Epic's Model Context Protocol (MCP) environment, this returned JSON string is placed inside the MCP tool execution response's `returnValue` property (e.g. `{"returnValue": "{\"success\":true,\"data\":{}}"}`).

### 2. Viewport Framebuffer Capture (`-> unreal.AmineViewportCapture` and Native `amine_capture_viewport`)
Epic's registry adapter serializes all ToolsetRegistry results as JSON text, including nested `FToolsetImage` structures. Consequently, the Python `capture_viewport` tool returns JSON text containing image data and metadata rather than MCP image content blocks. To provide actual MCP image content, the native `FAmineCaptureTool` in `AmineMCPBridge.cpp` registers `amine_capture_viewport` directly through Epic's `IModelContextProtocolModule`. Calling `amine_capture_viewport` returns actual PNG image content plus text metadata and `structuredContent` (map, camera, dimensions).

### 3. Native Asynchronous Operations (`-> unreal.ToolCallAsyncResultVoid` / `-> unreal.ToolCallAsyncResultString`)
Tools executing asynchronous engine operations (such as automation testing via `discover_automation_tests` and `run_automation_tests`, Play-In-Editor session lifecycle via `start_pie` and `stop_pie`, or Content Browser selection via `sync_content_browser`) return native Epic async tokens. These resolve upon completion or abort; failed or timed-out async operations may surface as MCP `isError: true`.

## Toolset Index

| Toolset Class | Source Module | Tools Count | Summary |
| --- | --- | ---: | --- |
| [`AmineActorTools`](#amineactortools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/actor_tools.py` | 14 | Bounded scene inspection and undoable exact actor operations. |
| [`AmineAssetTools`](#amineassettools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/asset_tools.py` | 10 | Asset Registry search without loading assets; explicit /Game asset writes and saves. |
| [`AmineBlueprintTools`](#amineblueprinttools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/blueprint_tools.py` | 19 | Supported Blueprint assets, components, defaults, compilation and typed graph editing. |
| [`AmineComponentTools`](#aminecomponenttools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/component_tools.py` | 8 | Inspect, add and modify instance components and assign mesh/material assets. |
| [`AmineDebugTools`](#aminedebugtools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/debug_tools.py` | 4 | Bounded live Unreal logs captured by the thread-safe native output device since plugin startup. |
| [`AmineEditorTools`](#amineeditortools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/editor_tools.py` | 8 | Explicit saving and asset editor operations; never save all dirty packages. |
| [`AmineGameplayTools`](#aminegameplaytools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/gameplay_tools.py` | 5 | Play and Simulate sessions using Epic's real bounded asynchronous completion. |
| [`AmineLightingTools`](#aminelightingtools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/lighting_tools.py` | 4 | Create and adjust supported editor light actors. |
| [`AmineMaterialTools`](#aminematerialtools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/material_tools.py` | 11 | Materials, instances, supported material graph edits and mesh metadata. |
| [`AmineNiagaraTools`](#amineniagaratools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/niagara_tools.py` | 2 | Niagara system inspection and placement; optional plugin capability checks. |
| [`AminePCGTools`](#aminepcgtools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/pcg_tools.py` | 2 | PCG graph/component inspection; graph authoring delegates to installed Epic PCGToolset. |
| [`AmineProjectTools`](#amineprojecttools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/project_tools.py` | 3 | Inspect the active project and editor without dumping private configuration. |
| [`AmineReflectionTools`](#aminereflectiontools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/reflection_tools.py` | 4 | Discover supported properties and classes instead of guessing Unreal APIs. |
| [`AmineSequencerTools`](#aminesequencertools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/sequencer_tools.py` | 4 | Supported LevelSequence creation, bindings and playback range editing. |
| [`AmineTestingTools`](#aminetestingtools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/testing_tools.py` | 6 | Automation discovery, bounded explicit test execution and status via Epic's controller. |
| [`AmineViewportTools`](#amineviewporttools) | `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/viewport_tools.py` | 7 | Actual level viewport images with camera/map context for visual iteration. |

## AmineActorTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/actor_tools.py`  
**Description**: Bounded scene inspection and undoable exact actor operations.  
**Tools in Set**: 14

---

### attach_actor

Attach to a resolved parent, keeping world transform. Reject self-attachment and cycles.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `parent_identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "attach_actor",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "parent_identifier": "/Game/Maps/Main.Main:PersistentLevel.ParentActor_1"
  }
}
```

### clear_selection

Clear editor actor selection.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "clear_selection",
  "arguments": {}
}
```

### delete_actor

Delete only the exact live editor actor path. Labels and fuzzy references are rejected. Undoable.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "delete_actor",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### detach_actor

Detach the actor, keeping world transform.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "detach_actor",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### duplicate_actor

Duplicate a resolved actor; return the new actor path. No asset is saved.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `label` | `str | None` | `None` | No |
| `offset` | `unreal.Vector` | `unreal.Vector()` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "duplicate_actor",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "label": null,
    "offset": {
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    }
  }
}
```

### get_actor

Inspect an actor by exact path, internal name or unambiguous exact label.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "get_actor",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### list_level_actors

List live editor actors with transform and component summaries; paths are canonical identifiers.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `class_path` | `str | None` | `None` | No |
| `label_substring` | `str | None` | `None` | No |
| `folder` | `str | None` | `None` | No |
| `tag` | `str | None` | `None` | No |
| `selected_only` | `bool` | `False` | No |
| `max_results` | `int` | `100` | No |
| `offset` | `int` | `0` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "list_level_actors",
  "arguments": {
    "class_path": null,
    "label_substring": null,
    "folder": null,
    "tag": null,
    "selected_only": false,
    "max_results": 100,
    "offset": 0
  }
}
```

### select_actors

Replace editor actor selection after resolving every reference. Empty list clears selection.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifiers` | `list[str]` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "select_actors",
  "arguments": {
    "identifiers": [
      "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
    ]
  }
}
```

### set_actor_folder

Move an actor to an Outliner folder; empty string means the root.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `folder` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "set_actor_folder",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "folder": "/Game/SubFolder"
  }
}
```

### set_actor_label

Change the display label without changing the canonical actor path.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `label` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "set_actor_label",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "label": "MyActor"
  }
}
```

### set_actor_property

Set one reflected actor property using a JSON value; discover names first with list_object_properties.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `property_name` | `str` | *None* | Yes |
| `value_json` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "set_actor_property",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "property_name": "RelativeLocation",
    "value_json": "{\"PropertyName\": \"Value\"}"
  }
}
```

### set_actor_tags

Replace actor tags, preserving only the supplied values.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `tags` | `list[str]` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "set_actor_tags",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "tags": [
      "TagA"
    ]
  }
}
```

### set_actor_transform

Set any supplied world transform fields; omitted fields are preserved. Return before and after.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `location` | `unreal.Vector | None` | `None` | No |
| `rotation` | `unreal.Rotator | None` | `None` | No |
| `scale` | `unreal.Vector | None` | `None` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "set_actor_transform",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "location": null,
    "rotation": null,
    "scale": null
  }
}
```

### spawn_actor

Spawn an Actor subclass or Blueprint generated class into the editor; return its exact path. Units are cm and degrees.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `class_path` | `str` | *None* | Yes |
| `label` | `str | None` | `None` | No |
| `location` | `unreal.Vector` | `unreal.Vector()` | No |
| `rotation` | `unreal.Rotator` | `unreal.Rotator()` | No |
| `scale` | `unreal.Vector` | `unreal.Vector(1, 1, 1)` | No |
| `folder` | `str | None` | `None` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.actor_tools.AmineActorTools",
  "tool_name": "spawn_actor",
  "arguments": {
    "class_path": "/Script/Engine.Actor",
    "label": null,
    "location": {
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    },
    "rotation": {
      "pitch": 0.0,
      "yaw": 0.0,
      "roll": 0.0
    },
    "scale": {
      "x": 1.0,
      "y": 1.0,
      "z": 1.0
    },
    "folder": null
  }
}
```

## AmineAssetTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/asset_tools.py`  
**Description**: Asset Registry search without loading assets; explicit /Game asset writes and saves.  
**Tools in Set**: 10

---

### create_folder

Create a Content Browser folder under /Game.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `content_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "create_folder",
  "arguments": {
    "content_path": "/Game"
  }
}
```

### delete_asset

Delete one exact /Game asset only if registry reports no referencers. Asset deletion is not undoable.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "delete_asset",
  "arguments": {
    "exact_asset_path": "/Game/Assets/MyAsset"
  }
}
```

### duplicate_asset

Duplicate an exact asset to an unused /Game path; never overwrite existing assets.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `source_path` | `str` | *None* | Yes |
| `destination_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "duplicate_asset",
  "arguments": {
    "source_path": "/Game/Assets/SourceAsset",
    "destination_path": "/Game/Assets/NewAsset"
  }
}
```

### get_asset_dependencies

Return bounded Asset Registry dependency package paths.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_path` | `str` | *None* | Yes |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "get_asset_dependencies",
  "arguments": {
    "exact_asset_path": "/Game/Assets/MyAsset",
    "max_results": 100
  }
}
```

### get_asset_info

Read registry class and metadata for one exact asset without loading its contents.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `asset_path_value` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "get_asset_info",
  "arguments": {
    "asset_path_value": "/Game/Assets/MyAsset"
  }
}
```

### get_asset_referencers

Return bounded Asset Registry referencer package paths.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_path` | `str` | *None* | Yes |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "get_asset_referencers",
  "arguments": {
    "exact_asset_path": "/Game/Assets/MyAsset",
    "max_results": 100
  }
}
```

### import_asset

Import an existing file inside the project into /Game, without overwriting or automatically saving assets.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `project_relative_filename` | `str` | *None* | Yes |
| `destination_folder` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "import_asset",
  "arguments": {
    "project_relative_filename": "SourceAssets/Model.fbx",
    "destination_folder": "/Game/SubFolder"
  }
}
```

### list_folder

List immediate folders and asset paths without loading assets.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `content_path` | `str` | *None* | Yes |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "list_folder",
  "arguments": {
    "content_path": "/Game",
    "max_results": 100
  }
}
```

### move_asset

Move/rename an exact /Game asset to an unused /Game path. Unreal may save packages/create redirectors.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `source_path` | `str` | *None* | Yes |
| `destination_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "move_asset",
  "arguments": {
    "source_path": "/Game/Assets/SourceAsset",
    "destination_path": "/Game/Assets/NewAsset"
  }
}
```

### search_assets

Search registry metadata without loading assets. Class filter is a /Script class path. Paginated results.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `content_path` | `str` | `'/Game'` | No |
| `name_substring` | `str | None` | `None` | No |
| `class_path` | `str | None` | `None` | No |
| `recursive` | `bool` | `True` | No |
| `max_results` | `int` | `100` | No |
| `offset` | `int` | `0` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.asset_tools.AmineAssetTools",
  "tool_name": "search_assets",
  "arguments": {
    "content_path": "/Game",
    "name_substring": null,
    "class_path": null,
    "recursive": true,
    "max_results": 100,
    "offset": 0
  }
}
```

## AmineBlueprintTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/blueprint_tools.py`  
**Description**: Supported Blueprint assets, components, defaults, compilation and typed graph editing.  
**Tools in Set**: 19

---

### add_blueprint_component

Add a named Blueprint component with supported subsystem APIs; compile and return its template path.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `class_path` | `str` | *None* | Yes |
| `component_name` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "add_blueprint_component",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "class_path": "/Script/Engine.Actor",
    "component_name": "MyComponent"
  }
}
```

### add_blueprint_variable

Add a member variable: bool, int, float, byte, string, name, text, Vector, Rotator, Transform, Vector2D or LinearColor. Compile afterward.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `variable_name` | `str` | *None* | Yes |
| `type_name` | `str` | `'float'` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "add_blueprint_variable",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "variable_name": "MyVariable",
    "type_name": "float"
  }
}
```

### compile_blueprint

Compile now and return real compiler status and graph-node diagnostic messages. Compilation errors remain inspectable.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "compile_blueprint",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### connect_blueprint_pins

Connect named output/input pins on exact nodes in the same Blueprint graph; schema validates compatibility.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `output_node` | `str` | *None* | Yes |
| `output_pin` | `str` | *None* | Yes |
| `input_node` | `str` | *None* | Yes |
| `input_pin` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "connect_blueprint_pins",
  "arguments": {
    "output_node": "/Game/Blueprints/BP_Actor.BP_Actor:EventGraph.Node_1",
    "output_pin": "Execute",
    "input_node": "/Game/Blueprints/BP_Actor.BP_Actor:EventGraph.Node_2",
    "input_pin": "Execute"
  }
}
```

### create_blueprint

Create a Blueprint at a new /Game path with a verified parent class. Does not save automatically.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `destination_path` | `str` | *None* | Yes |
| `parent_class_path` | `str` | `'/Script/Engine.Actor'` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "create_blueprint",
  "arguments": {
    "destination_path": "/Game/Assets/NewAsset",
    "parent_class_path": "/Script/Engine.Actor"
  }
}
```

### create_blueprint_function

Create a new named function graph with Epic's supported BlueprintEditorLibrary.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `function_name` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "create_blueprint_function",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "function_name": "MyFunction"
  }
}
```

### create_blueprint_node

Create a discovered node type using the installed BlueprintGraphEditor. Compile explicitly after editing.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `type_id` | `str` | *None* | Yes |
| `graph_name` | `str` | `'EventGraph'` | No |
| `x` | `int` | `0` | No |
| `y` | `int` | `0` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "create_blueprint_node",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "type_id": "K2Node_CallFunction",
    "graph_name": "EventGraph",
    "x": 0,
    "y": 0
  }
}
```

### get_blueprint_compile_errors

Read stored node compiler diagnostics; consult get_errors for broader compiler output.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "get_blueprint_compile_errors",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### get_blueprint_compile_status

Read compile status and node messages without triggering compilation.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "get_blueprint_compile_status",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### get_blueprint_info

Return parent, generated class, member variables, graph identifiers and actual compile status/messages.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "get_blueprint_info",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### get_blueprint_parent_class

Return the parent class's canonical path.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "get_blueprint_parent_class",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### get_blueprint_variables

Return declared member variable names and their current class default values.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "get_blueprint_variables",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### list_blueprint_components

Enumerate Blueprint component templates through Epic's SubobjectDataSubsystem helper.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "list_blueprint_components",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor"
  }
}
```

### list_blueprint_nodes

Return bounded graph node paths, discovered type IDs, input/output pin names and literal values.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `graph_name` | `str` | `'EventGraph'` | No |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "list_blueprint_nodes",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "graph_name": "EventGraph",
    "max_results": 100
  }
}
```

### remove_blueprint_component

Remove one exact component template belonging to this Blueprint; inherited/native components may be rejected.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `component_identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "remove_blueprint_component",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "component_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1.DefaultSceneRoot"
  }
}
```

### search_blueprint_node_types

Discover valid node type IDs from Epic's action database before creating nodes.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `search` | `str` | *None* | Yes |
| `graph_name` | `str` | `'EventGraph'` | No |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "search_blueprint_node_types",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "search": "SearchTerm",
    "graph_name": "EventGraph",
    "max_results": 100
  }
}
```

### set_blueprint_class_default

Set one reflected class default property, including inherited properties. Does not save.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `property_name` | `str` | *None* | Yes |
| `value_json` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "set_blueprint_class_default",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "property_name": "RelativeLocation",
    "value_json": "{\"PropertyName\": \"Value\"}"
  }
}
```

### set_blueprint_pin_value

Set a named input pin's Unreal literal text, such as Hello or 2.5; this is not executable code.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `node_identifier` | `str` | *None* | Yes |
| `pin_name` | `str` | *None* | Yes |
| `value` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "set_blueprint_pin_value",
  "arguments": {
    "node_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "pin_name": "example_value",
    "value": "1.0"
  }
}
```

### set_blueprint_variable_default

Set an existing member's class default with one JSON value; compile before editing newly added variables.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `blueprint_path` | `str` | *None* | Yes |
| `variable_name` | `str` | *None* | Yes |
| `value_json` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.blueprint_tools.AmineBlueprintTools",
  "tool_name": "set_blueprint_variable_default",
  "arguments": {
    "blueprint_path": "/Game/Blueprints/BP_MyActor",
    "variable_name": "MyVariable",
    "value_json": "{\"PropertyName\": \"Value\"}"
  }
}
```

## AmineComponentTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/component_tools.py`  
**Description**: Inspect, add and modify instance components and assign mesh/material assets.  
**Tools in Set**: 8

---

### add_component

Add an instance component using Epic's SubobjectDataSubsystem integration. Return its exact path.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `actor_identifier` | `str` | *None* | Yes |
| `class_path` | `str` | *None* | Yes |
| `component_name` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "add_component",
  "arguments": {
    "actor_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "class_path": "/Script/Engine.Actor",
    "component_name": "MyComponent"
  }
}
```

### assign_material

Assign an existing material to a PrimitiveComponent slot; validate slot index.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `component_identifier` | `str` | *None* | Yes |
| `material_path` | `str` | *None* | Yes |
| `slot_index` | `int` | `0` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "assign_material",
  "arguments": {
    "component_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1.DefaultSceneRoot",
    "material_path": "/Game/Materials/M_Material",
    "slot_index": 0
  }
}
```

### assign_static_mesh

Assign an existing StaticMesh asset to an exact StaticMeshComponent.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `component_identifier` | `str` | *None* | Yes |
| `mesh_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "assign_static_mesh",
  "arguments": {
    "component_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1.DefaultSceneRoot",
    "mesh_path": "/Game/Meshes/SM_StaticMesh"
  }
}
```

### get_component

Inspect a component, optionally reading explicitly requested reflected properties.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `properties` | `list[str]` | `[]` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "get_component",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "properties": []
  }
}
```

### list_actor_components

Return exact component paths, names and class paths for an editor actor.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "list_actor_components",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### remove_component

Remove one exact component using Epic's supported subsystem. Native/inherited removal may be rejected.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "remove_component",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### set_component_property

Set one exposed component property with a JSON value and return before/after.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `property_name` | `str` | *None* | Yes |
| `value_json` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "set_component_property",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "property_name": "RelativeLocation",
    "value_json": "{\"PropertyName\": \"Value\"}"
  }
}
```

### set_component_transform

Set a SceneComponent's relative transform. Non-scene components are rejected.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `transform` | `unreal.Transform` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.component_tools.AmineComponentTools",
  "tool_name": "set_component_transform",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "transform": {
      "location": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      },
      "rotation": {
        "pitch": 0.0,
        "yaw": 0.0,
        "roll": 0.0
      },
      "scale": {
        "x": 1.0,
        "y": 1.0,
        "z": 1.0
      }
    }
  }
}
```

## AmineDebugTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/debug_tools.py`  
**Description**: Bounded live Unreal logs captured by the thread-safe native output device since plugin startup.  
**Tools in Set**: 4

---

### clear_custom_log_buffer

Clear only the plugin's in-memory log buffer; does not clear Unreal Output Log or files.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.debug_tools.AmineDebugTools",
  "tool_name": "clear_custom_log_buffer",
  "arguments": {}
}
```

### get_errors

Return recent runtime/editor/compile error log entries, bounded to 500 lines.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `substring` | `str | None` | `None` | No |
| `max_lines` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.debug_tools.AmineDebugTools",
  "tool_name": "get_errors",
  "arguments": {
    "substring": null,
    "max_lines": 100
  }
}
```

### get_recent_logs

Return recent live log entries in chronological order. Severity: empty, info, warning or error; max 500 lines.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `severity` | `str | None` | `None` | No |
| `substring` | `str | None` | `None` | No |
| `max_lines` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.debug_tools.AmineDebugTools",
  "tool_name": "get_recent_logs",
  "arguments": {
    "severity": null,
    "substring": null,
    "max_lines": 100
  }
}
```

### get_warnings

Return recent warning log entries, bounded to 500 lines.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `substring` | `str | None` | `None` | No |
| `max_lines` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.debug_tools.AmineDebugTools",
  "tool_name": "get_warnings",
  "arguments": {
    "substring": null,
    "max_lines": 100
  }
}
```

## AmineEditorTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/editor_tools.py`  
**Description**: Explicit saving and asset editor operations; never save all dirty packages.  
**Tools in Set**: 8

---

### close_asset_editor

Close editors for one exact asset only if it is clean, avoiding save prompts.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "close_asset_editor",
  "arguments": {
    "exact_asset_path": "/Game/Assets/MyAsset"
  }
}
```

### get_dirty_assets

List dirty map/content packages from Unreal's native editor API.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "get_dirty_assets",
  "arguments": {}
}
```

### open_asset_editor

Open an editor for a verified exact asset.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "open_asset_editor",
  "arguments": {
    "exact_asset_path": "/Game/Assets/MyAsset"
  }
}
```

### save_asset

Save only this exact /Game asset, leaving unrelated dirty content untouched.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "save_asset",
  "arguments": {
    "exact_asset_path": "/Game/Assets/MyAsset"
  }
}
```

### save_assets

Save only the explicit /Game asset list. Validate every path before writing; report any native failure.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_paths` | `list[str]` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "save_assets",
  "arguments": {
    "exact_asset_paths": [
      "/Game/Assets/MyAsset"
    ]
  }
}
```

### save_current_level

Save the current /Game level only. Reject transient/Engine maps rather than prompting for Save As.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "save_current_level",
  "arguments": {}
}
```

### save_current_level_as

Save the active level to a new /Game path, including transient maps.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `destination_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "save_current_level_as",
  "arguments": {
    "destination_path": "/Game/Assets/NewAsset"
  }
}
```

### sync_content_browser

Select exact existing assets in the Content Browser. Native async result completes when selection is applied.

- **Execution Category**: Native Asynchronous Operation (`unreal.ToolCallAsyncResultString`)
- **Return Annotation**: `unreal.ToolCallAsyncResultString`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `exact_asset_paths` | `list[str]` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.editor_tools.AmineEditorTools",
  "tool_name": "sync_content_browser",
  "arguments": {
    "exact_asset_paths": [
      "/Game/Assets/MyAsset"
    ]
  }
}
```

## AmineGameplayTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/gameplay_tools.py`  
**Description**: Play and Simulate sessions using Epic's real bounded asynchronous completion.  
**Tools in Set**: 5

---

### is_pie_running

Read current PIE/Simulate state without changing the editor.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.gameplay_tools.AmineGameplayTools",
  "tool_name": "is_pie_running",
  "arguments": {}
}
```

### pause_pie

Pause an active PIE world using the same debug pause flag as the editor.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.gameplay_tools.AmineGameplayTools",
  "tool_name": "pause_pie",
  "arguments": {}
}
```

### resume_pie

Resume the active PIE world.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.gameplay_tools.AmineGameplayTools",
  "tool_name": "resume_pie",
  "arguments": {}
}
```

### start_pie

Start PIE/Simulate in the active viewport. Complete after PostPIEStarted and warmup; Epic enforces a 30-second startup timeout. Reject existing sessions.

- **Execution Category**: Native Asynchronous Operation (`unreal.ToolCallAsyncResultString`)
- **Return Annotation**: `unreal.ToolCallAsyncResultString`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `simulate` | `bool` | `False` | No |
| `warmup_seconds` | `float` | `0.5` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.gameplay_tools.AmineGameplayTools",
  "tool_name": "start_pie",
  "arguments": {
    "simulate": false,
    "warmup_seconds": 0.5
  }
}
```

### stop_pie

Stop PIE and complete after EndPIE with Epic's 30-second timeout. Reject calls if no session is running.

- **Execution Category**: Native Asynchronous Operation (`unreal.ToolCallAsyncResultString`)
- **Return Annotation**: `unreal.ToolCallAsyncResultString`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.gameplay_tools.AmineGameplayTools",
  "tool_name": "stop_pie",
  "arguments": {}
}
```

## AmineLightingTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/lighting_tools.py`  
**Description**: Create and adjust supported editor light actors.  
**Tools in Set**: 4

---

### create_light

Create one light: directional, point, spot, rect or sky. Position in cm, rotation in degrees. Does not save.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `kind` | `str` | `'point'` | No |
| `label` | `str` | `'MCP_Light'` | No |
| `location` | `unreal.Vector` | `unreal.Vector()` | No |
| `rotation` | `unreal.Rotator` | `unreal.Rotator()` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.lighting_tools.AmineLightingTools",
  "tool_name": "create_light",
  "arguments": {
    "kind": "point",
    "label": "MCP_Light",
    "location": {
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    },
    "rotation": {
      "pitch": 0.0,
      "yaw": 0.0,
      "roll": 0.0
    }
  }
}
```

### set_light_color

Set a light color from linear RGBA. Unreal's sRGB conversion is disabled for this linear input.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `color` | `unreal.LinearColor` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.lighting_tools.AmineLightingTools",
  "tool_name": "set_light_color",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "color": {
      "r": 1.0,
      "g": 1.0,
      "b": 1.0,
      "a": 1.0
    }
  }
}
```

### set_light_intensity

Set a light's nonnegative intensity in its currently configured Unreal units.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `intensity` | `float` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.lighting_tools.AmineLightingTools",
  "tool_name": "set_light_intensity",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "intensity": 1000.0
  }
}
```

### set_light_temperature

Set color temperature to 1000..15000 K and toggle temperature use.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `kelvin` | `float` | *None* | Yes |
| `enabled` | `bool` | `True` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.lighting_tools.AmineLightingTools",
  "tool_name": "set_light_temperature",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "kelvin": 6500.0,
    "enabled": true
  }
}
```

## AmineMaterialTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/material_tools.py`  
**Description**: Materials, instances, supported material graph edits and mesh metadata.  
**Tools in Set**: 11

---

### add_material_node

Add a MaterialExpression subclass to a /Game Material using MaterialEditingLibrary.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `material_path` | `str` | *None* | Yes |
| `expression_class_path` | `str` | *None* | Yes |
| `x` | `int` | `0` | No |
| `y` | `int` | `0` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "add_material_node",
  "arguments": {
    "material_path": "/Game/Materials/M_Material",
    "expression_class_path": "/Script/Engine.MaterialExpressionConstant",
    "x": 0,
    "y": 0
  }
}
```

### compile_material

Request a material recompile. Shader compilation may continue asynchronously; consult logs before claiming readiness.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `material_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "compile_material",
  "arguments": {
    "material_path": "/Game/Materials/M_Material"
  }
}
```

### connect_material_nodes

Connect exact expression paths belonging to the same Material. Names must match discovered expression pins.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `output_node` | `str` | *None* | Yes |
| `output_name` | `str` | *None* | Yes |
| `input_node` | `str` | *None* | Yes |
| `input_name` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "connect_material_nodes",
  "arguments": {
    "output_node": "/Game/Blueprints/BP_Actor.BP_Actor:EventGraph.Node_1",
    "output_name": "Output",
    "input_node": "/Game/Blueprints/BP_Actor.BP_Actor:EventGraph.Node_2",
    "input_name": "Output"
  }
}
```

### connect_material_output

Connect an expression output to a material property, e.g. MCP enum MP_BaseColor; use describe_toolset for enum values.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `node_identifier` | `str` | *None* | Yes |
| `output_name` | `str` | *None* | Yes |
| `material_property` | `unreal.MaterialProperty` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "connect_material_output",
  "arguments": {
    "node_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "output_name": "Output",
    "material_property": "MP_BaseColor"
  }
}
```

### create_material

Create an empty Material at an unused /Game path. Prefer instances when possible to reduce shader compilation.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `destination_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "create_material",
  "arguments": {
    "destination_path": "/Game/Assets/NewAsset"
  }
}
```

### create_material_instance

Create an unsaved MaterialInstanceConstant at an unused /Game path with a verified parent.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `destination_path` | `str` | *None* | Yes |
| `parent_material_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "create_material_instance",
  "arguments": {
    "destination_path": "/Game/Assets/NewAsset",
    "parent_material_path": "/Game/Materials/M_Material"
  }
}
```

### get_material_info

Inspect material/instance identity and exposed parameter names/types.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `material_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "get_material_info",
  "arguments": {
    "material_path": "/Game/Materials/M_Material"
  }
}
```

### get_static_mesh_info

Return mesh bounds, material slots, LOD count and native Nanite state.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `mesh_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "get_static_mesh_info",
  "arguments": {
    "mesh_path": "/Game/Meshes/SM_StaticMesh"
  }
}
```

### set_material_instance_scalar

Set a scalar parameter that exists on the instance's parent. Return the effective value.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `instance_path` | `str` | *None* | Yes |
| `parameter_name` | `str` | *None* | Yes |
| `value` | `float` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "set_material_instance_scalar",
  "arguments": {
    "instance_path": "/Game/Materials/MI_MaterialInstance",
    "parameter_name": "Roughness",
    "value": 1.0
  }
}
```

### set_material_instance_texture

Set an existing texture parameter to a verified Texture asset.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `instance_path` | `str` | *None* | Yes |
| `parameter_name` | `str` | *None* | Yes |
| `texture_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "set_material_instance_texture",
  "arguments": {
    "instance_path": "/Game/Materials/MI_MaterialInstance",
    "parameter_name": "Roughness",
    "texture_path": "/Game/Textures/T_Texture"
  }
}
```

### set_material_instance_vector

Set an existing vector parameter using linear RGBA values; HDR values are allowed.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `instance_path` | `str` | *None* | Yes |
| `parameter_name` | `str` | *None* | Yes |
| `value` | `unreal.LinearColor` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.material_tools.AmineMaterialTools",
  "tool_name": "set_material_instance_vector",
  "arguments": {
    "instance_path": "/Game/Materials/MI_MaterialInstance",
    "parameter_name": "Roughness",
    "value": {
      "r": 1.0,
      "g": 1.0,
      "b": 1.0,
      "a": 1.0
    }
  }
}
```

## AmineNiagaraTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/niagara_tools.py`  
**Description**: Niagara system inspection and placement; optional plugin capability checks.  
**Tools in Set**: 2

---

### get_niagara_system_info

Inspect an existing NiagaraSystem. Discover Epic Niagara toolsets for deeper emitter/module graph operations.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `system_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.niagara_tools.AmineNiagaraTools",
  "tool_name": "get_niagara_system_info",
  "arguments": {
    "system_path": "/Game/VFX/NS_System"
  }
}
```

### place_niagara_system

Place one existing NiagaraSystem as a NiagaraActor, without changing the system asset.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `system_path` | `str` | *None* | Yes |
| `location` | `unreal.Vector` | `unreal.Vector()` | No |
| `label` | `str` | `'MCP_Niagara'` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.niagara_tools.AmineNiagaraTools",
  "tool_name": "place_niagara_system",
  "arguments": {
    "system_path": "/Game/VFX/NS_System",
    "location": {
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    },
    "label": "MCP_Niagara"
  }
}
```

## AminePCGTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/pcg_tools.py`  
**Description**: PCG graph/component inspection; graph authoring delegates to installed Epic PCGToolset.  
**Tools in Set**: 2

---

### get_pcg_graph_info

Inspect an exact PCGGraph asset and exposed property schemas; no generation is triggered.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `graph_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.pcg_tools.AminePCGTools",
  "tool_name": "get_pcg_graph_info",
  "arguments": {
    "graph_path": "/Game/PCG/PCG_Graph"
  }
}
```

### list_pcg_components

List exact PCG component paths on one actor. Use component property/reflection tools for safe editing.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `actor_identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.pcg_tools.AminePCGTools",
  "tool_name": "list_pcg_components",
  "arguments": {
    "actor_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

## AmineProjectTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/project_tools.py`  
**Description**: Inspect the active project and editor without dumping private configuration.  
**Tools in Set**: 3

---

### get_editor_state

Return map, current level, selection, actor count, PIE and dirty packages.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.project_tools.AmineProjectTools",
  "tool_name": "get_editor_state",
  "arguments": {}
}
```

### get_project_info

Return project paths, engine version, enabled plugins, modules and active map.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.project_tools.AmineProjectTools",
  "tool_name": "get_project_info",
  "arguments": {}
}
```

### get_project_settings

Read only renderer settings relevant to lighting; omit arbitrary config and credentials.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.project_tools.AmineProjectTools",
  "tool_name": "get_project_settings",
  "arguments": {}
}
```

## AmineReflectionTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/reflection_tools.py`  
**Description**: Discover supported properties and classes instead of guessing Unreal APIs.  
**Tools in Set**: 4

---

### describe_class

Return exposed class property schemas and Blueprint-callable function names, bounded to 500 each.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `class_path` | `str` | *None* | Yes |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.reflection_tools.AmineReflectionTools",
  "tool_name": "describe_class",
  "arguments": {
    "class_path": "/Script/Engine.Actor",
    "max_results": 100
  }
}
```

### get_object_properties

Read only the explicit list of up to 100 reflected properties.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `property_names` | `list[str]` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.reflection_tools.AmineReflectionTools",
  "tool_name": "get_object_properties",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "property_names": [
      "RelativeLocation"
    ]
  }
}
```

### list_object_properties

Return exposed reflected property schemas for an object or Blueprint CDO, bounded and filterable.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |
| `name_substring` | `str | None` | `None` | No |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.reflection_tools.AmineReflectionTools",
  "tool_name": "list_object_properties",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1",
    "name_substring": null,
    "max_results": 100
  }
}
```

### list_subclasses

Find derived native/Blueprint classes through Epic's Asset Registry helper without loading every asset.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `base_class_path` | `str` | *None* | Yes |
| `name_substring` | `str | None` | `None` | No |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.reflection_tools.AmineReflectionTools",
  "tool_name": "list_subclasses",
  "arguments": {
    "base_class_path": "/Script/Engine.Actor",
    "name_substring": null,
    "max_results": 100
  }
}
```

## AmineSequencerTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/sequencer_tools.py`  
**Description**: Supported LevelSequence creation, bindings and playback range editing.  
**Tools in Set**: 4

---

### bind_actor_to_sequence

Add a possessable binding to an existing editor actor. Does not construct tracks/keyframes automatically.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `sequence_path` | `str` | *None* | Yes |
| `actor_identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.sequencer_tools.AmineSequencerTools",
  "tool_name": "bind_actor_to_sequence",
  "arguments": {
    "sequence_path": "/Game/Cinematics/LS_Sequence",
    "actor_identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### create_level_sequence

Create a new unsaved LevelSequence under /Game; never overwrite assets.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `destination_path` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.sequencer_tools.AmineSequencerTools",
  "tool_name": "create_level_sequence",
  "arguments": {
    "destination_path": "/Game/Assets/NewAsset"
  }
}
```

### get_level_sequence_info

Return sequence playback frame range, display rate and bounded binding/track summaries.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `sequence_path` | `str` | *None* | Yes |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.sequencer_tools.AmineSequencerTools",
  "tool_name": "get_level_sequence_info",
  "arguments": {
    "sequence_path": "/Game/Cinematics/LS_Sequence",
    "max_results": 100
  }
}
```

### set_sequence_playback_range

Set playback start/end in display-rate frames. End is exclusive and must exceed start.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `sequence_path` | `str` | *None* | Yes |
| `start_frame` | `int` | *None* | Yes |
| `end_frame` | `int` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.sequencer_tools.AmineSequencerTools",
  "tool_name": "set_sequence_playback_range",
  "arguments": {
    "sequence_path": "/Game/Cinematics/LS_Sequence",
    "start_frame": 0,
    "end_frame": 100
  }
}
```

## AmineTestingTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/testing_tools.py`  
**Description**: Automation discovery, bounded explicit test execution and status via Epic's controller.  
**Tools in Set**: 6

---

### discover_automation_tests

Discover the local automation worker and tests asynchronously before listing or running tests.

- **Execution Category**: Native Asynchronous Operation (`unreal.ToolCallAsyncResultString`)
- **Return Annotation**: `unreal.ToolCallAsyncResultString`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.testing_tools.AmineTestingTools",
  "tool_name": "discover_automation_tests",
  "arguments": {}
}
```

### get_automation_test_results

Return the most recent explicit test run's real results.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.testing_tools.AmineTestingTools",
  "tool_name": "get_automation_test_results",
  "arguments": {}
}
```

### get_automation_test_status

Return actual controller execution/completion state.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.testing_tools.AmineTestingTools",
  "tool_name": "get_automation_test_status",
  "arguments": {}
}
```

### list_automation_tests

List discovered automation tests, bounded to 500. Call discover_automation_tests first.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `name_substring` | `str` | `'Amine'` | No |
| `max_results` | `int` | `100` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.testing_tools.AmineTestingTools",
  "tool_name": "list_automation_tests",
  "arguments": {
    "name_substring": "Amine",
    "max_results": 100
  }
}
```

### run_automation_tests

Run 1..20 exact discovered automation tests with a 45-second timeout. Reject existing runs. Return actual results; tests may mutate content.

- **Execution Category**: Native Asynchronous Operation (`unreal.ToolCallAsyncResultString`)
- **Return Annotation**: `unreal.ToolCallAsyncResultString`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `test_names` | `list[str]` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.testing_tools.AmineTestingTools",
  "tool_name": "run_automation_tests",
  "arguments": {
    "test_names": [
      "Project.Automation.Test1"
    ]
  }
}
```

### stop_automation_tests

Cancel the current automation run and resolve its pending async result as an error.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.testing_tools.AmineTestingTools",
  "tool_name": "stop_automation_tests",
  "arguments": {}
}
```

## AmineViewportTools

**Source File**: `Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/tools/viewport_tools.py`  
**Description**: Actual level viewport images with camera/map context for visual iteration.  
**Tools in Set**: 7

---

### capture_viewport

Return a real MCP PNG image plus camera/map metadata from the active level framebuffer. Letterboxed; 64..2560 x 64..1440. Requires a rendered editor viewport.

- **Execution Category**: Viewport Framebuffer Capture (`unreal.AmineViewportCapture` PNG content + metadata)
- **Return Annotation**: `unreal.AmineViewportCapture`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `width` | `int` | `1280` | No |
| `height` | `int` | `720` | No |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "capture_viewport",
  "arguments": {
    "width": 1280,
    "height": 720
  }
}
```

### eject_camera

Eject the viewport from any piloted camera.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "eject_camera",
  "arguments": {}
}
```

### focus_actor

Frame one resolved actor in the level viewport. Requires PIE to be stopped.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "focus_actor",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### frame_selection

Frame the current actor selection; fail if no actors are selected.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "frame_selection",
  "arguments": {}
}
```

### get_viewport_camera

Return level viewport camera position in cm and rotation in degrees.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

This tool takes no parameters.

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "get_viewport_camera",
  "arguments": {}
}
```

### pilot_camera

Pilot the viewport through a camera actor.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `identifier` | `str` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "pilot_camera",
  "arguments": {
    "identifier": "/Game/Maps/Main.Main:PersistentLevel.Actor_1"
  }
}
```

### set_viewport_camera

Move the editor camera; actor transforms and assets remain unchanged.

- **Execution Category**: Guarded JSON Envelope (`str` wrapped in Epic MCP `returnValue`)
- **Return Annotation**: `str`

#### Parameters

| Parameter | Type | Default | Required |
| --- | --- | --- | --- |
| `location` | `unreal.Vector` | *None* | Yes |
| `rotation` | `unreal.Rotator` | *None* | Yes |

#### Example `call_tool` Invocation

```json
{
  "toolset_name": "amine_unreal_mcp.tools.viewport_tools.AmineViewportTools",
  "tool_name": "set_viewport_camera",
  "arguments": {
    "location": {
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    },
    "rotation": {
      "pitch": 0.0,
      "yaw": 0.0,
      "roll": 0.0
    }
  }
}
```

