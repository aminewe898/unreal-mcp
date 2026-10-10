import unreal
import toolset_registry
from ..common.runtime import guarded, encode
from ..common.validation import ToolError


@unreal.uclass()
class AmineGameplayTools(unreal.ToolsetDefinition):
    """Play and Simulate sessions using Epic's real bounded asynchronous completion."""

    @toolset_registry.tool_call
    @staticmethod
    def start_pie(simulate: bool = False, warmup_seconds: float = 0.5) -> unreal.ToolCallAsyncResultString:
        """Start PIE/Simulate in the active viewport. Complete after PostPIEStarted and warmup; Epic enforces a 30-second startup timeout. Reject existing sessions."""
        if not 0 <= warmup_seconds <= 10:
            raise ValueError("Warmup must be 0..10 seconds")
        return unreal.AmineMCPBridge.execute_epic_tool("EditorToolset.EditorAppToolset", "StartPIE", encode({"options": {"bSimulate": simulate, "playMode": "PlayMode_InViewPort", "warmupSeconds": warmup_seconds}}))

    @toolset_registry.tool_call
    @staticmethod
    def stop_pie() -> unreal.ToolCallAsyncResultString:
        """Stop PIE and complete after EndPIE with Epic's 30-second timeout. Reject calls if no session is running."""
        return unreal.AmineMCPBridge.execute_epic_tool("EditorToolset.EditorAppToolset", "StopPIE", "{}")

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def is_pie_running() -> str:
        """Read current PIE/Simulate state without changing the editor."""
        return {"running": unreal.AmineMCPBridge.is_pie_running()}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def pause_pie() -> str:
        """Pause an active PIE world using the same debug pause flag as the editor."""
        if not unreal.AmineMCPBridge.set_pie_paused(True):
            raise ToolError("pie_not_running", "Start PIE before pausing.")
        return {"paused": True}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def resume_pie() -> str:
        """Resume the active PIE world."""
        if not unreal.AmineMCPBridge.set_pie_paused(False):
            raise ToolError("pie_not_running", "No PIE world is running.")
        return {"paused": False}
