import json
import unreal
import toolset_registry
from ..common.runtime import guarded
from ..common.validation import limit, ToolError


@unreal.uclass()
class AmineDebugTools(unreal.ToolsetDefinition):
    """Bounded live Unreal logs captured by the thread-safe native output device since plugin startup."""

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_recent_logs(severity: str | None = None, substring: str | None = None, max_lines: int = 100) -> str:
        """Return recent live log entries in chronological order. Severity: empty, info, warning or error; max 500 lines."""
        limit(max_lines)
        severity = severity or ""
        if severity not in ("", "info", "warning", "error"):
            raise ToolError("invalid_severity", "Use info, warning, error or empty.")
        return {"entries": json.loads(unreal.AmineMCPBridge.get_recent_logs(severity, substring or "", max_lines)), "capacity": 2000}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_errors(substring: str | None = None, max_lines: int = 100) -> str:
        """Return recent runtime/editor/compile error log entries, bounded to 500 lines."""
        limit(max_lines)
        return {"entries": json.loads(unreal.AmineMCPBridge.get_recent_logs("error", substring or "", max_lines))}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_warnings(substring: str | None = None, max_lines: int = 100) -> str:
        """Return recent warning log entries, bounded to 500 lines."""
        limit(max_lines)
        return {"entries": json.loads(unreal.AmineMCPBridge.get_recent_logs("warning", substring or "", max_lines))}

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def clear_custom_log_buffer() -> str:
        """Clear only the plugin's in-memory log buffer; does not clear Unreal Output Log or files."""
        unreal.AmineMCPBridge.clear_log_buffer()
        return {"cleared": True}
