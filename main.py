"""
Todo CLI - Main Entry Point (Textual UI only)
"""

import sys
from config import DEFAULT_TASKS_FILE
from utils.version import get_version


def _maybe_handle_version_flag(argv: list[str]) -> bool:
    """Print version and exit if --version or -v provided. Returns True if handled."""
    if any(arg in ("--version", "-v") for arg in argv[1:]):
        print(f"todo-cli {get_version()}")
        return True
    return False


def main():
    """
    Main entry point
    Supports dual UI: Textual (modern, default) or Rich (classic, fallback)

    Usage:
        python main.py              # Default: Textual UI (modern reactive TUI)
        python main.py --ui textual # Textual UI (modern)
        python main.py --ui rich    # Rich UI (classic REPL)
    """
    from debug_logger import debug_log
    debug_log.info("=" * 80)
    debug_log.info("MAIN.PY - Application starting")
    debug_log.info("=" * 80)

    # Version flag (print and exit)
    if _maybe_handle_version_flag(sys.argv):
        return

    # Textual TUI only
    try:
        debug_log.info("Importing TodoTextualApp...")
        from textual_app import TodoTextualApp
        debug_log.info(f"Creating TodoTextualApp instance - tasks_file: {DEFAULT_TASKS_FILE}")
        app = TodoTextualApp(tasks_file=DEFAULT_TASKS_FILE)
        debug_log.info("Calling app.run() - Textual framework taking control...")
        app.run()
        debug_log.info("app.run() returned - Application exited normally")
    except ImportError as e:
        debug_log.error(f"Failed to import Textual UI: {e}", exception=e)
        print("Error: Textual UI not available. Install with: pip install textual")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        debug_log.error(f"Unexpected error during Textual UI startup: {e}", exception=e)
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

