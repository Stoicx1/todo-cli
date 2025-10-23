"""
Terminal Utilities
Cross-platform terminal operations that work with prompt_toolkit
"""

import os
import sys
import platform
from io import StringIO
from typing import Callable, Any
from rich.console import Console


def clear_screen() -> None:
    """
    Clear the terminal screen in a cross-platform way.

    This function works properly with prompt_toolkit on Windows,
    unlike Rich's console.clear() which can output raw ANSI codes.

    Uses:
    - Windows: 'cls' command via os.system()
    - Unix/Mac: 'clear' command via os.system()
    """
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def clear_screen_ansi() -> None:
    """
    Clear the terminal using ANSI escape codes.

    Alternative to clear_screen() that uses ANSI codes directly.
    Faster but may not work on very old terminals.
    """
    # \033[2J = Clear entire screen
    # \033[H = Move cursor to home position (0,0)
    print("\033[2J\033[H", end="", flush=True)


def print_rich_with_prompt_toolkit(render_func: Callable[[Console], Any]) -> None:
    """
    Print Rich content during an active prompt_toolkit session.

    This function properly integrates Rich's ANSI output with prompt_toolkit's
    rendering system, preventing raw ANSI codes from being displayed.

    Solution based on: https://github.com/Textualize/rich/discussions/936

    Args:
        render_func: Function that takes a Console and renders to it
                     Example: lambda console: console.print("Hello")

    Usage:
        # Instead of: console.print(table)
        # Use: print_rich_with_prompt_toolkit(lambda c: c.print(table))
    """
    try:
        from prompt_toolkit.formatted_text import ANSI
        from prompt_toolkit import print_formatted_text

        # Capture Rich output to string
        string_buffer = StringIO()
        temp_console = Console(file=string_buffer, force_terminal=True, width=None)

        # Render to the buffer
        render_func(temp_console)

        # Get the ANSI string
        ansi_output = string_buffer.getvalue()

        # Print using prompt_toolkit's system (properly handles ANSI)
        print_formatted_text(ANSI(ansi_output))

    except ImportError:
        # Fallback if prompt_toolkit not available
        # Create a regular console and print normally
        temp_console = Console()
        render_func(temp_console)
