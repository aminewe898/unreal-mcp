# AmineUnrealMCP

AmineUnrealMCP (v0.1.0) is an editor-only Unreal Engine 5.8.2 plugin hosted in `Plugins/AmineUnrealMCP`. It extends Epic's installed `ModelContextProtocol` and `ToolsetRegistry` plugins using a native C++ bridge alongside 16 typed Python toolsets. The repository provides an isolated test environment via `AmineMCPHost.uproject`.

## Capabilities & Limitations

- **Operations**: 111 typed Python operations plus the native `amine_capture_viewport` real PNG capture.
- **Supported Areas**: Actor, asset, Blueprint, material, lighting, viewport, PIE, log, Sequencer binding, and automation inspection/editing.
- **Safety**: No arbitrary Python execution or shell execution endpoints. Optional third-party toolsets are not sandboxed.
- **Out of Scope**: Landscape creation and custom Sequencer track/keyframe authoring are unsupported.
- **Engine Support**: Verified on UE 5.8.2 on Windows. Other engine versions are unverified.

## Prerequisites & Requirements

- Unreal Engine 5.8.2 with installed `ModelContextProtocol` plugin.
- Windows C++ toolchain (Visual Studio / MSVC).
- Python 3.10 or newer for the standalone development scripts.
- Note: This is an editor plugin, not a standalone server. The repository ships source only; rebuild on your engine installation. No engine binaries or proprietary scene assets are included (root `Content/` and `SourceAssets/` are intentionally excluded; plugin Python content is included).

## Quick Start

1. **Configure Environment**:
   ```powershell
   Copy-Item Config/DefaultEngine.ini.example Config/DefaultEngine.ini
   ```
   *(Note: `Config/DefaultEngine.ini` is git-ignored as the editor writes machine-specific settings and tokens).*
2. **Build Plugin**: Build the C++ plugin following [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
3. **Launch Host Editor**:
   Open `AmineMCPHost.uproject` with the server flag:
   ```cmd
   UnrealEditor.exe "path\to\AmineMCPHost.uproject" -ModelContextProtocolStartServer
   ```
4. **Connect MCP Client**:
   Target the local HTTP endpoint at `http://127.0.0.1:8000/mcp`. Do not bind or expose this endpoint remotely.

## Tests & Validation

Run local static checks and documentation generation:
```powershell
python -m unittest discover -s tests -v
python scripts/generate_tool_docs.py
```
*Validation status: Historical native build and 45 core + 32 extended live checks passed in the host project; tests do not represent exhaustive coverage.*

## Documentation

- [Tools Reference](docs/TOOLS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development & Building](docs/DEVELOPMENT.md)
- [Validation Guide](docs/VALIDATION.md)
- [Plugin Details](Plugins/AmineUnrealMCP/README.md)
