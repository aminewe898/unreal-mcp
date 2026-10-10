"""Plugin content bootstrap run by Unreal's Python Editor Script Plugin."""
import unreal


def _register_after_startup(delta_time):
    # Every plugin's init_unreal.py must finish before excluding Epic's script
    # escape hatch; otherwise EditorToolset's later startup re-registers it.
    unreal.unregister_slate_post_tick_callback(_startup_handle)
    try:
        import amine_unreal_mcp
        amine_unreal_mcp.register()
    except Exception:
        import traceback
        unreal.log_error("[AmineUnrealMCP] Registration failed:\n" + traceback.format_exc())


_startup_handle = unreal.register_slate_post_tick_callback(_register_after_startup)
