# Implementation and validation report

Validated locally on 2026-10-10 against **Unreal Engine 5.8.2**, changelist
56702186, on Windows with the installed Visual Studio toolchain.
Plugin version: **AmineUnrealMCP 0.1.0**.

## Delivered files and architecture

The project plugin is `Plugins/AmineUnrealMCP/AmineUnrealMCP.uplugin`.
`AmineMCPHost.uproject` is a dedicated acceptance host created in this
workspace; unrelated Unreal projects were not used as test targets.

The plugin contains an editor C++ module, a deferred Python bootstrap,
16 typed Python toolset modules and shared validation/runtime/privacy
helpers. There are **111 Python toolset tools and one native MCP image
tool**. Epic's existing ModelContextProtocol server supplies Streamable
HTTP sessions and dispatch; ToolsetRegistry supplies reflected schemas.
The native bridge provides actual viewport readback, logs, package state,
framing, PIE state and a fixed allowlist of Epic async operations.

Read `TOOLS.md` for every generated tool signature and call example,
`ARCHITECTURE.md` for implementation details, and `DEVELOPMENT.md` for
build/reload/delegation instructions. Plugin installation and client setup
are in `Plugins/AmineUnrealMCP/README.md`.

## Verified outcomes

| Validation | Outcome |
| --- | --- |
| Native C++ compilation and linking | Passed against installed UE 5.8.2 |
| Local Python tests | 21 passed |
| Core live MCP acceptance | 45 recorded checks passed |
| Extended live MCP acceptance | 32 recorded checks passed |
| Real Unreal automation execution | One exact discovered ColorConverter test passed; zero failures |
| Viewport images | Actual PNG image content, 1280 × 720; signature/dimensions checked and image visually inspected |
| Listener | Verified bound to 127.0.0.1:8000 |
| Temporary content cleanup | No MCP_TEST_ assets remain; baseline actors/selection/camera restored by core test |
| Source portability | No machine-specific absolute paths found in source/docs/config |

The core run verified project/world inspection, asset registry search,
actor spawn/inspection/transforms/duplication/tags/selection/framing,
static mesh assignment, Blueprint creation/components/variables/defaults,
compile status and diagnostics, node inspection/action discovery, explicit
asset saving, generated Blueprint actor spawning, real image capture,
PIE start/state/stop, bounded logs and cleanup.

The extended run verified safe renderer settings, mesh metadata,
material/expression/instance creation, scalar parameter editing,
property schemas, material compile requests, light creation and settings,
LevelSequence creation/binding/ranges, automation discovery/execution/status
and results. It also verified invalid screenshot inputs and actor deletion
by label are rejected.

Machine-readable evidence is in `Saved/Acceptance/results.json` and
`Saved/Acceptance/extended-results.json`; received PNGs are alongside them.
Build/delegation output is under Saved and is excluded from source control.
These machine-local evidence files and engine binaries are not distributed
in the source repository. Rebuild and rerun acceptance on your installation.

## Failures found and corrected

Live validation found empty-string defaults becoming required schema
parameters, native AICallable methods unavailable as ordinary Python calls,
registry images being serialized as text, asynchronous viewport focus,
misread property-map structure, nullable dependency-query results,
incorrect PIE/renderer property names, Unreal Array JSON serialization
and redundant async result envelopes. These were corrected and the final
core/extended runs passed. Initial C++ header/category/dependency issues
were corrected before the final successful build.

## Installation and Codex connection

During local validation, compatible Win64 native binaries were present in
the host. The isolated editor ran with the MCP endpoint
`http://127.0.0.1:8000/mcp`. Required plugin dependencies are declared in the
descriptor; Niagara/PCG toolsets are optional. No engine source was edited.

A `[mcp_servers.unreal]` entry was appended to the existing user Codex
configuration with this endpoint, a 30-second startup timeout and a
60-second tool timeout. Unrelated configuration was preserved. Open a new
Codex chat or reload the client if the newly added MCP server is not yet
visible. This uses Codex's documented Streamable HTTP `url` configuration:
[official OpenAI documentation](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers).

To restart the host yourself, set UE_ROOT to the verified installation and
run from the repository root:

```powershell
& "$env:UE_ROOT/Engine/Binaries/Win64/UnrealEditor.exe" `
  "$PWD/AmineMCPHost.uproject" -ModelContextProtocolStartServer
```

Supported Unreal console commands, when needed:

```text
ModelContextProtocol.StartServer 8000 /mcp
ModelContextProtocol.RefreshTools
```

Verification commands from the repository root:

```text
python -m unittest discover -s tests -v
python scripts/generate_tool_docs.py
python scripts/mcp_client.py tools/list
python scripts/acceptance.py
python scripts/acceptance_extended.py
```

Use `list_toolsets`, `describe_toolset` and `call_tool` for registry tools.
Call the native `amine_capture_viewport` directly to receive actual image
content with camera/map metadata. The Python `capture_viewport` tool
returns the same capture data as JSON text because of Epic's adapter.

Example prompt:

> Inspect the current Unreal world and its assets. Create a uniquely named
> cube actor, place and frame it, then use amine_capture_viewport to visually
> inspect it. Create an Actor Blueprint with a float variable, set its
> default, compile and inspect errors. Start PIE, inspect logs, stop PIE,
> then report the exact objects changed. Save only the assets I request.

## Limitations and unverified behavior

This is a working v0.1 integration, not evidence that every one of the 111
tools and every Unreal subsystem has been exhaustively tested. Blueprint
graph connection/literal/function authoring, imports, asset moves, optional
Niagara placement and PCG inspection were not all exercised in the final
live runs. Advanced Niagara/PCG graph work depends on Epic's optional
experimental toolsets. Landscape creation and Sequencer track/keyframe
authoring are not implemented in the custom toolsets.

Viewport readback is synchronous and cannot recover a stalled GPU/editor.
Material recompilation is a request; shader completion is not asserted.
Automation runs are bounded to 45 seconds and stop on timeout; the timeout
branch itself was not forced in testing. Logs start at module load and keep
at most 2000 bounded entries. Output redaction handles common credential
formats, not every custom secret or visible text in scene pixels.

Actor mutations use editor transactions; deletion/saving/import side effects
do not provide full transactional rollback. Cleanup leaves the isolated
temporary map dirty after editing, without saving unrelated content.
Separately enabled Epic/third-party toolsets are not sandboxed by the
custom facade. Other Unreal versions require API verification and a rebuild.

## Gemini delegation

Routine generator/test/documentation work was actually executed through
`agy` using verified Gemini 3.8 Flash models. Three scoped jobs completed;
the lead reviewed their output, corrected issues and ran the checks.
`AGENTS.md` records the user's preference: Gemini handles simple coding and
mechanical work; the lead handles architecture, native integration, API
investigation, safety and live debugging. There is no permission bypass or
concurrent ownership of the same files.

## Saved color-block demo

A subsequent MCP smoke test created and saved `/Game/MCPDemo/ColorBlocks/L_ColorBlocks`: one platform, three colored blocks and a point light, using four saved material instances. PIE start/state/stop, map saving and PNG capture passed. No nonempty error messages were received during the isolated PIE log check. The added save_current_level_as tool rejects existing assets; 21 local tests passed after the addition. Scene evidence is under Saved/Demo. Demo assets and local startup-map settings are excluded from the source distribution.

## Camera tools added after core acceptance

`pilot_camera` and `eject_camera` extend the viewport toolset to 111 Python
operations. Piloting a saved CineCameraActor in exact-camera mode was
verified through the live MCP endpoint and its native PNG capture. The
historical 45/32 acceptance counts above precede these two additions and
do not imply exhaustive coverage of the current catalog.
