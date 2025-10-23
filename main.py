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

    # Launch appropriate UI
    if args.ui == "textual":
        # Modern Textual TUI
        try:
            from textual_app import TodoTextualApp

            app = TodoTextualApp(tasks_file=DEFAULT_TASKS_FILE)
            app.run()

        except ImportError as e:
            print(f"Error: Textual UI not available. Install with: pip install textual")
            print(f"Details: {e}")
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
