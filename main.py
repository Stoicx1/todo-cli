"""
Todo CLI - Main Entry Point
Supports both Rich (classic) and Textual (modern) UIs
"""

import argparse
import sys

from app import TodoApp
from config import DEFAULT_TASKS_FILE


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

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Todo CLI - Modern Task Management with AI Chat",
        epilog="Choose your UI: --ui textual (modern, default) or --ui rich (classic)"
    )

    parser.add_argument(
        "--ui",
        choices=["rich", "textual"],
        default="textual",
        help="UI framework to use (default: textual)"
    )

    args = parser.parse_args()
    debug_log.info(f"Command line args parsed - UI mode: {args.ui}")

    # Launch appropriate UI
    if args.ui == "textual":
        # Modern Textual TUI
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
            print(f"Error: Textual UI not available. Install with: pip install textual")
            print(f"Details: {e}")
            sys.exit(1)
        except Exception as e:
            debug_log.error(f"Unexpected error during Textual UI startup: {e}", exception=e)
            print(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    else:
        # Classic Rich CLI (default)
        app = TodoApp(
            tasks_file=DEFAULT_TASKS_FILE,
            use_questionary_forms=True
        )

        # Setup (load data, create session)
        app.setup()

        # Run main loop
        app.run()


if __name__ == "__main__":
    main()
