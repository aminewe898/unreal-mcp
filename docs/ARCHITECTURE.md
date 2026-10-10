# Architecture

## Transport and registration

Unreal 5.8.2's installed ModelContextProtocol server owns Streamable HTTP sessions, protocol negotiation, game-thread dispatch, tool search and MCP result/image conversion. AmineUnrealMCP does not implement another server. It binds the host HTTP listener to loopback through the project configuration.

Plugin Python content is mounted by PythonScriptPlugin. `init_unreal.py` registers a one-shot Slate tick callback so all plugin startup scripts can complete before registering the Amine classes and excluding Epic's general scripting/filesystem toolsets. Each Python toolset subclasses `unreal.ToolsetDefinition`, uses `@unreal.uclass()` and marks typed static methods with `@toolset_registry.tool_call`.

## Python and C++

Focused Python modules handle validation, object/asset resolution, schemas, composition and editor APIs. Installed Epic Python tools supply verified Blueprint components, graph edits and material operations. They are imported for implementation but unregistered from the agent-facing catalog.

`AmineMCPBridge` is an editor-only Blueprint function library; it is not itself an unrestricted MCP toolset. It supplies viewport framebuffer capture, bounded logs, dirty package inspection, reflection function names, PIE state/pause and viewport framing.

Some native Epic tools have `AICallable` metadata without `BlueprintCallable`, so Python cannot call them as ordinary static methods. The bridge retains their public `FToolset` handlers before unregistering their global entries. It executes only a fixed list of approved native editor/automation operations using the public `FToolset::ExecuteTool` API. No private headers, transport reinvention, raw Python or shell execution is involved.

## Async execution

Epic owns the completion of PIE, Content Browser selection and automation calls. The bridge forwards the handler's future into `UToolCallAsyncResultString`, retaining the UObject through `TStrongObjectPtr`. It propagates real errors rather than claiming completion when the request is merely queued. UObject work originates on the editor thread; the log sink alone accepts background-thread writes under a lock. Native start/stop PIE uses bounded engine-event watchers.

The bridge unwraps Epic's internal `returnValue` before forwarding string results. Automation execution validates exact discovered test names, rejects a running controller and stops its requested run on a 45-second ticker timeout. Timeout callbacks are removed during module shutdown.

## Images

The native bridge finds `GCurrentLevelEditingViewportClient`, renders/reads the actual framebuffer, forces opaque alpha, preserves aspect ratio with letterboxing and encodes pixels through Epic's `FToolsetImage::SetFromBitmap`. The returned struct contains the image, camera transform, map and pixel dimensions.

At runtime, Epic's registry adapter serializes all ToolsetRegistry results as JSON text, including nested `FToolsetImage` fields. The Python registry tool `capture_viewport` therefore returns JSON text containing image data and metadata rather than MCP image content. To provide actual MCP image content without requiring the caller to browse a file, our native `FAmineCaptureTool` in `AmineMCPBridge.cpp` registers `amine_capture_viewport` directly through Epic's `IModelContextProtocolModule`. Calling `amine_capture_viewport` returns real PNG image content blocks plus text metadata and `structuredContent` (map, camera, dimensions). Capture dimensions and source pixel count are bounded. GPU readback is synchronous and shares the engine's stall limitations. Do not claim live execution success without running against an active session.

## Results and errors

Ordinary tools return a deterministic JSON envelope inside Epic's `returnValue`: success with data, or a stable validation error code/message. Unreal exceptions are logged with the plugin prefix and become explicit failure envelopes. Native async calls and screenshot failures use Epic's MCP error handling. Complex property values use one JSON value argument, not executable commands.

## Identifiers and safety

Actor paths are canonical identifiers. Labels/internal names are accepted only for unambiguous non-deletion lookups; substrings never resolve a mutation target. Components and graph nodes require exact live paths. Asset writes require exact `/Game` package paths. Blueprint generated class/template paths can change after compilation, so query them again after structural edits.

Transactions use Unreal's real ScopedEditorTransaction, explicit Modify calls and supported UndoTransaction rollback after failed mutations that committed an undo record. Cancellation alone does not revert object writes. Asset deletion, save/import side effects and some moves are outside full transaction guarantees. Save operations validate and save only explicit targets. Development tests create unique MCP_TEST objects and attempt cleanup without touching unrelated assets.

## Logs

A native FOutputDevice records severity, category and bounded messages in a thread-safe rolling buffer. Read calls return filtered, bounded chronological entries. The history begins at module startup; it is separate from existing Output Log history and files. Only mutation/failure/registration events are logged by the plugin, avoiding routine read-query noise.

Guarded outputs redact common credential keys, named secrets and bearer/API-key patterns without modifying write arguments. Reflection excludes configuration/subsystem objects, and mutations reject assets outside /Game. Redaction cannot identify every custom secret format or text visible in scene pixels.
