# AmineUnrealMCP 0.1.0

Typed local AI control for Unreal Editor 5.8.2, extending Epic's installed ModelContextProtocol, ToolsetRegistry and EditorToolset plugins. The integration provides focused inspection and editing tools rather than an arbitrary Python or shell execution endpoint.

## Architecture and prerequisites

- Unreal Engine **5.8.2** with the experimental ModelContextProtocol, ToolsetRegistry, EditorToolset and PythonScriptPlugin plugins. This version is the implementation target; other versions require API verification and a rebuild.
- An editor C++ toolchain supported by the installed engine to build the native bridge.
- EditorScriptingUtilities, SequencerScripting and AutomationTestToolset. NiagaraToolsets and PCGToolset are optional advanced toolsets.
- An MCP client with Streamable HTTP and image support.

Python defines the typed tools and schemas. A small editor C++ module supplies bounded logs, viewport PNGs, dirty package inspection, function-name reflection, PIE pause state, and a fixed internal adapter to Epic's public native tool handlers. The transport, request dispatch and async completion remain Epic's implementation.

## Installation

Copy this plugin folder into your project's `Plugins/AmineUnrealMCP`. Enable AmineUnrealMCP in the `.uproject` descriptor; its required plugin dependencies are declared in `AmineUnrealMCP.uplugin`. Build the editor target or use Unreal's `RunUAT BuildPlugin` packaging command with your installed engine. Do not copy binaries built for a different engine version.

The repository includes `AmineMCPHost.uproject`, an isolated host for development and acceptance testing. Existing projects elsewhere on the machine are not the test target.

In project `Config/DefaultEngine.ini`, keep the HTTP listener local:

```ini
[HTTPServer.Listeners]
DefaultBindAddress=127.0.0.1
```

In `Config/DefaultEditorPerProjectUserSettings.ini`:

```ini
[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
ServerPortNumber=8000
ServerUrlPath=/mcp
bAutoStartServer=True
bEnableToolSearch=True
```

Existing saved user settings can override these defaults. Launch with `-ModelContextProtocolStartServer` or use the verified Unreal console commands:

```text
ModelContextProtocol.StartServer 8000 /mcp
ModelContextProtocol.RefreshTools
```

Only one editor instance can listen on the same port. Python startup defers registration until all plugin startup scripts finish, then registers the Amine toolsets. Epic's general Python toolsets and native EditorApp/Logs/AgentSkill toolsets are removed from the global agent-facing registry; their supported internal helpers remain available to this plugin. Separately enabled third-party toolsets are not a security sandbox and require their own review.

## Codex connection

Preserve existing MCP entries and add this section to your Codex configuration:

```toml
[mcp_servers.amine_unreal]
url = "http://127.0.0.1:8000/mcp"
tool_timeout_sec = 60
```

Epic's `ModelContextProtocol.GenerateClientConfig Codex` command exists in this installation, but refuses to overwrite an existing TOML configuration. Use a scoped addition instead. A running Codex session may require a restart/reconnection to load the new server.

The default server exposes `list_toolsets`, `describe_toolset` and `call_tool`, alongside native tools registered directly through `IModelContextProtocolModule`. Discover the exact toolset names, inspect their schemas, then call a typed operation:

```json
{"name":"call_tool","arguments":{"toolset_name":"amine_unreal_mcp.tools.project_tools.AmineProjectTools","tool_name":"get_project_info","arguments":{}}}
```

For ordinary tools, decode Epic's `returnValue` JSON string to obtain `{ "success": true, "data": ... }` or `{ "success": false, "error": "code", "message": "..." }`. Note that Epic's registry adapter serializes all ToolsetRegistry results as JSON text, so the Python registry tool `capture_viewport` returns JSON text containing image data and metadata rather than MCP image content. To obtain real `image/png` MCP content blocks with text metadata and `structuredContent` (map, camera, dimensions), invoke the native bridge tool directly:

```json
{"name":"amine_capture_viewport","arguments":{"width":1280,"height":720}}
```

Async native tools may report MCP `isError` on failure. Do not assume live execution success without running against an active session.

Example agent prompt: "Inspect the current map, create a Blueprint with a mesh component and a float variable, compile it, place an instance, capture the viewport with amine_capture_viewport, run PIE and inspect errors. Save only assets you created."

## Capabilities

Project/editor inspection; paginated actor and Asset Registry search; actor transforms, tags, folders, duplication, selection and exact deletion; component inspection/creation/properties and mesh/material assignment; asset duplication, move, dependency/referencer inspection and bounded project-local import; Blueprint creation, variables/defaults, component templates, compilation diagnostics and supported graph node/pin editing; material/instance creation and graph operations; lighting; viewport camera and real PNG images; explicit saving; PIE/Simulate/pause/resume; bounded logs; reflected property/class discovery; LevelSequence creation, ranges and actor bindings; automation testing; Niagara placement/inspection and PCG inspection. Installed Epic Niagara/PCG toolsets can provide deeper authoring.

See the repository's `docs/TOOLS.md` for the generated complete tool list, signatures and examples; `docs/ARCHITECTURE.md` and `docs/DEVELOPMENT.md` describe internals and maintenance.

## Safety, diagnostics and limitations

- Actor display labels are convenience references only. Ambiguous references fail. Deletion requires an exact actor object path.
- Asset writes are restricted to `/Game`. Creation rejects existing destinations. Deletion rejects known referencers, uses exact paths and is not undoable.
- Normal editor mutations use actual transactions and `Modify`; failed transactions are reverted when an undo record exists. Imports, package saves, asset moves/deletion and external importer effects are not fully reversible.
- Saving is explicit. No operation silently saves every dirty asset. Engine/transient maps are rejected by `save_current_level` to avoid unattended Save As dialogs.
- Stop PIE before editing editor objects. Native PIE completion waits for actual engine events; the start/stop implementation has a bounded timeout.
- Screenshots require a rendered, active level viewport. Output defaults to 1280x720 and is letterboxed to preserve aspect ratio; limits are 2560x1440. The framebuffer read is synchronous, as in Epic's implementation; a stalled GPU/editor cannot be recovered by an in-process timeout.
- Material compile requests do not claim that asynchronous shader compilation has completed.
- Log history starts at native module load, retains at most 2000 entries and bounds individual messages and query sizes.
- Blueprint diagnostics include node messages and status; some compiler messages appear only in the logs.
- Sequencer track/keyframe editing and Landscape authoring are not implemented in the custom v0.1 toolsets. Advanced Niagara/PCG APIs are optional and experimental.

Search Unreal Output Log for `[AmineUnrealMCP]` when registration or runtime calls fail. Confirm the Python plugin and ToolsetRegistry are enabled and the native module matches the engine build. Do not enable remote HTTP binding.

## Development and validation

From the repository root:

```text
python -m unittest discover -s tests -v
python scripts/generate_tool_docs.py
python scripts/mcp_client.py tools/list
python scripts/acceptance.py
python scripts/acceptance_extended.py
```

The acceptance client uses Epic's actual MCP HTTP endpoint, validates received PNG MIME/signature/dimensions, exercises temporary actors/Blueprints/PIE and attempts cleanup in `finally`. Use the isolated host. Results go under `Saved/Acceptance`; consult actual recorded results rather than treating this README as proof of a passing run.

The extended client verifies materials, lighting, Sequencer, automation execution and input rejection. Automation calls accept exact discovered names, reject an existing run and stop a requested run after 45 seconds. Only explicit asset saves occur. Output redaction removes common named credentials and bearer/API-key patterns; custom secrets in arbitrary prose or visible viewport pixels require project-specific handling.
