# Development

## Add a tool

1. Inspect the installed engine headers, Python reflection or Epic toolset implementations. Verify the exact API, flags, parameters and version before coding. Consult current Context7 documentation as secondary evidence.
2. Place the operation in the matching focused tools module. Use a typed static method on an Amine ToolsetDefinition subclass. Preserve stable existing tool names.
3. Describe identifier requirements, units, side effects and failures in its docstring. Keep results bounded; avoid loading unrelated assets.
4. Use common validation/resolution helpers and real mutation transactions. Never test deletion against user content or silently save every dirty asset.
5. Return the common success/error envelope for ordinary tools. Return real Epic async result types for operations that complete later. Images must use ToolsetImage.
6. Add a new module to `MODULES` in the package bootstrap if needed. Keep C++ helpers narrow and only add module dependencies required by verified APIs.
7. Run unit tests, rebuild C++ when changed, run actual MCP discovery, and test the operation against the isolated host. Record failures and limitations honestly.
8. Regenerate `docs/TOOLS.md` from source. Keep machine-specific paths out of source.

## Reload

The installed registry supports recursive Python reload. In Unreal's Python console:

```python
import amine_unreal_mcp
amine_unreal_mcp.reload_tools()
```

The helper refreshes the MCP catalog with the verified `ModelContextProtocol.RefreshTools` console command. Native C++ changes require a normal editor rebuild/restart. Blueprint compile/reinstancing can invalidate component/node handles; re-query paths after structural operations.

## Build

Use the installed engine's `Engine/Build/BatchFiles/RunUAT.bat`:

```powershell
& "$env:UE_ROOT/Engine/Build/BatchFiles/RunUAT.bat" BuildPlugin `
  "-Plugin=$PWD/Plugins/AmineUnrealMCP/AmineUnrealMCP.uplugin" `
  "-Package=$PWD/Saved/PackagedAminePlugin" -TargetPlatforms=Win64
```

Set `UE_ROOT` to your verified engine installation path. The package must be outside the source plugin folder. Do not pass `-NoHostPlatform` when validating an editor-only plugin: it can skip the editor compilation and produce misleading packaging success.

For the included content-only development host, copy the compiled binaries
into its source plugin after a successful package build:

```powershell
Copy-Item "$PWD/Saved/PackagedAminePlugin/Binaries" "$PWD/Plugins/AmineUnrealMCP" -Recurse -Force
```

Before the first launch, copy `Config/DefaultEngine.ini.example` to
`Config/DefaultEngine.ini`. The working configuration is ignored because
Unreal can append local startup maps and device credentials. The source
checkout deliberately excludes root scene assets and exported source art.

## Validation

`tests/test_validation.py` covers exact actor resolution, ambiguous labels, deletion restrictions, asset paths, finite transforms, bounds, names, descriptors and Python syntax without Unreal. The documentation generator's tests also run without Unreal.

`scripts/mcp_client.py` is a standard-library test client for Epic's existing server. It negotiates protocol/session state; it is not a replacement MCP transport. `scripts/acceptance.py` exercises the real HTTP discovery/call/image pipeline and creates only uniquely named test objects. Run it in the dedicated host, where selection/camera restoration and baseline actor comparison are safe. Results are under Saved/Acceptance.

The development startup probe is a local trusted script for inspecting reflected APIs, not an agent-facing execution tool. Avoid testing in a user's active dirty editor session. Never claim a successful live test based solely on mocks, syntax checks or a successful build.

## Delegation

Delegation uses `gemini-3.8-flash-low` for mechanical edits and `gemini-3.8-flash-medium` for simple coding, all via `agy --mode accept-edits`. Give each task an explicit file ownership list, require no unrelated edits, and ensure the lead engineer reviews and tests its output. The lead engineer owns Unreal API verification, architecture, safety decisions, C++ integration and live debugging. Never run two agents against the same owned files concurrently.
