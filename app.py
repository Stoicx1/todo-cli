"""
TodoApp - Main Application Class
Encapsulates session management, input handling, and main loop
"""

from typing import Optional
import os
import sys
import platform
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import ThreadedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout
import threading
import time

from core.state import AppState
from core.commands import handle_command
from core.suggestions import LocalSuggestions
from assistant import Assistant
from ui.renderer import render_dashboard
from ui.command_palette import create_command_completer
from ui.questionary_forms import questionary_add_task, questionary_edit_task
from ui.inline_forms import inline_add_task, inline_edit_task
from ui.feedback import show_success
from utils.tag_parser import parse_tags
from utils.validators import (
    validate_task_name,
    sanitize_text,
    sanitize_comment,
    sanitize_description,
    clamp_priority
)
from utils.terminal import clear_screen
from config import ui, validation, DEFAULT_TASKS_FILE, DEFAULT_HISTORY_FILE, USE_UNICODE


def _enable_windows_ansi() -> None:
    """
    Enable ANSI escape sequences on Windows.

    On Windows 10+, ANSI is supported but needs to be enabled.
    This enables Virtual Terminal Processing for the console.
    """
    if platform.system() != "Windows":
        return

    try:
        # Try to enable ANSI support on Windows
        import ctypes
        kernel32 = ctypes.windll.kernel32

        # Get stdout handle
        stdout_handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11

        # Get current mode
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode))

        # Enable Virtual Terminal Processing (ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004)
        ENABLE_VT_PROCESSING = 0x0004
        kernel32.SetConsoleMode(stdout_handle, mode.value | ENABLE_VT_PROCESSING)
    except Exception:
        # If this fails, Rich will fallback to legacy mode
        pass


def create_console() -> Console:
    """
    Create a properly configured Rich Console with cross-platform support.

    Features:
    - Auto-detects terminal capabilities
    - Enables ANSI on Windows
    - Graceful fallback for older terminals
    - Forces terminal mode even when piped (for better rendering)

    Returns:
        Configured Console instance
    """
    # Enable ANSI on Windows first
    _enable_windows_ansi()

    # Detect if we're in a modern terminal
    is_windows_terminal = os.environ.get("WT_SESSION") is not None
    is_vscode = os.environ.get("TERM_PROGRAM") == "vscode"

    # Determine color system (auto-detect best available)
    # Rich will automatically downgrade if terminal doesn't support
    color_system = "auto"

    # Force terminal mode unless explicitly disabled
    force_terminal = os.environ.get("FORCE_COLOR", "1") != "0"

    # Legacy Windows mode (only for very old Windows)
    # Modern Windows 10+ supports ANSI natively
    legacy_windows = False
    if platform.system() == "Windows":
        # Check Windows version
        try:
            version = platform.version()
            # Windows 10 is version 10.0+
            major = int(version.split('.')[0])
            legacy_windows = major < 10
        except Exception:
            legacy_windows = False

    # Create console with best settings
    console = Console(
        force_terminal=force_terminal,      # Treat as terminal even if piped
        force_interactive=False,            # Don't force interactive (breaks pager)
        legacy_windows=legacy_windows,      # Use modern ANSI on Windows 10+
        color_system=color_system,          # Auto-detect best colors (truecolor/256/standard)
        safe_box=True,                      # Fallback to ASCII if Unicode box chars fail
        emoji=True,                         # Enable emoji rendering (with fallback)
        markup=True,                        # Enable Rich markup
        highlight=True,                     # Enable syntax highlighting
        soft_wrap=False,                    # Don't wrap long lines
        tab_size=4,                         # Standard tab size
    )

    return console


class TodoApp:
    """
    Main Todo CLI Application

    Responsibilities:
    - Session management (prompt_toolkit)
    - Main REPL loop
    - Command routing
    - Dashboard rendering
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        state: Optional[AppState] = None,
        tasks_file: str = DEFAULT_TASKS_FILE,
        use_questionary_forms: bool = True
    ):
        """
        Initialize TodoApp

        Args:
            console: Rich console instance (created if None)
            state: AppState instance (created if None)
            tasks_file: Path to tasks JSON file
            use_questionary_forms: Whether to use questionary forms (fallback to inline)
        """
        self.console = console or create_console()
        self.state = state or AppState()
        self.tasks_file = tasks_file
        self.use_questionary_forms = use_questionary_forms

        # Will be initialized in setup()
        self.session: Optional[PromptSession] = None
        self._ai_thread: Optional[threading.Thread] = None

    def setup(self) -> None:
        """Initialize application (load data, create session)"""
        # Load tasks from file
        self.state.load_from_file(self.tasks_file, self.console)

        # Create prompt session
        self.session = self._create_session()

        # Initial render (before prompt_toolkit session, don't use integration)
        render_dashboard(self.console, self.state, use_prompt_toolkit=False)

    def _create_session(self) -> PromptSession:
        """
        Create configured prompt_toolkit session

        Returns:
            Configured PromptSession instance
        """
        # Create command completer
        completer = create_command_completer(self.state)
        threaded_completer = ThreadedCompleter(completer)

        # Setup history
        history = FileHistory(str(DEFAULT_HISTORY_FILE))

        # Create custom style for completion menu
        completion_style = Style.from_dict({
            'completion-menu': 'bg:default',
            'completion-menu.completion': 'bg:default',
            'completion-menu.completion.current': 'bg:#444444 #ffffff',
            'completion-menu.meta.current': 'bg:#444444 #ffffff',
            'completion-menu.multi-column-meta': 'bg:default',
        })

        # Create key bindings
        kb = self._create_key_bindings()

        # Create session
        return PromptSession(
            completer=threaded_completer,
            complete_while_typing=True,
            history=history,
            enable_history_search=False,  # Critical: avoid conflict
            mouse_support=True,
            reserve_space_for_menu=ui.MENU_RESERVE_LINES,
            complete_style=CompleteStyle.MULTI_COLUMN,
            style=completion_style,
            key_bindings=kb
        )

    def _create_key_bindings(self) -> KeyBindings:
        """
        Create custom key bindings

        Returns:
            KeyBindings instance with ESC handler
        """
        kb = KeyBindings()

        @kb.add('escape')
        def clear_input(event):
            """Clear input buffer on ESC key"""
            event.current_buffer.reset()

        # AI panel scrolling shortcuts
        def _scroll(delta: int):
            lines = (self.state.ai_text or "").splitlines()
            total = len(lines)
            if total == 0:
                return
            self.state.ai_scroll = max(0, min(self.state.ai_scroll + delta, max(0, total - 1)))
            self._redraw_dashboard()

        def _panel_height() -> int:
            try:
                h = self.console.size.height
            except Exception:
                h = 30
            return max(8, min(12, h // 3))

        @kb.add('c-up')
        def ai_scroll_up(event):
            _scroll(+3)

        @kb.add('c-down')
        def ai_scroll_down(event):
            _scroll(-3)

        @kb.add('pageup')
        def ai_page_up(event):
            _scroll(+_panel_height())

        @kb.add('pagedown')
        def ai_page_down(event):
            _scroll(-_panel_height())

        @kb.add('c-home')
        def ai_top(event):
            lines = (self.state.ai_text or "").splitlines()
            self.state.ai_scroll = max(0, len(lines) - 1)
            self._redraw_dashboard()

        @kb.add('c-end')
        def ai_bottom(event):
            self.state.ai_scroll = 0
            self._redraw_dashboard()

        return kb

    def _redraw_dashboard(self) -> None:
        """Redraw the dashboard safely from any context."""
        try:
            render_dashboard(self.console, self.state)
        except Exception:
            pass

    def _create_prompt(self) -> HTML:
        """
        Create prompt HTML

        Returns:
            Formatted HTML prompt
        """
        if USE_UNICODE:
            prompt_text = '<violet>❯</violet> <dim>Type / for commands</dim> <violet>›</violet> '
        else:
            prompt_text = '<violet>></violet> <dim>Type / for commands</dim> <violet>></violet> '

        return HTML(prompt_text)

    def run(self) -> None:
        """
        Main application loop

        Runs until user exits (exit/quit/x command or Ctrl+C)
        """
        try:
            with patch_stdout():
                while True:
                    # Get user input
                    user_input = self.session.prompt(self._create_prompt()).strip()

                    # Handle input
                    should_continue = self.handle_input(user_input)

                    if not should_continue:
                        break

                    # Re-render dashboard
                    clear_screen()
                    render_dashboard(self.console, self.state)

        except (KeyboardInterrupt, EOFError):
            # User pressed Ctrl+C or Ctrl+D
            self.shutdown()

    def handle_input(self, user_input: str) -> bool:
        """
        Handle user input

        Args:
            user_input: Raw user input string

        Returns:
            True to continue loop, False to exit
        """
        # Empty input - just refresh
        if not user_input:
            return True

        # Clear screen command
        if user_input.lower() in ("cls", "clear", "c"):
            self.state.messages = []
            return True

        # Insights command (local AI)
        if user_input.lower() == "insights":
            self._handle_insights()
            return True

        # Suggest command (local AI)
        if user_input.lower() == "suggest":
            self._handle_suggest()
            return True
        
        # Ask GPT (streaming) command
        if user_input.strip() == "?":
            self._handle_ai_question()
            return True

        # Clear AI panel command
        if user_input.lower() == "clearai":
            self.state.ai_text = ""
            self.state.ai_scroll = 0
            self.state.ai_streaming = False
            self.state.messages.append("[green]AI panel cleared[/green]")
            return True

        # Tags command handled by core/commands to persist output in state.messages
        # (Avoid direct console prints here to prevent immediate clear on next render)

        # Exit commands (including shortcuts: q)
        if user_input.lower() in ("exit", "quit", "x", "q"):
            self.shutdown()
            return False

        # Add command with form (including shortcut: a)
        if user_input.strip() in ("add", "a"):
            self._handle_add_form()
            return True

        # Edit command with form (including shortcut: e)
        if user_input.startswith("edit ") or user_input.startswith("e "):
            self._handle_edit_form(user_input)
            return True

        # All other commands
        handle_command(user_input, self.state, self.console)
        return True
    def _handle_ai_question(self) -> None:
        """Ask GPT with streaming tail view, then show full answer in pager."""
        if not self.state.tasks:
            self.state.messages.append("[red]?[/red] No tasks to analyze.")
            return

        user_prompt = Prompt.ask(
            "GPT Prompt", default="Which tasks should I prioritize today?"
        )

        assistant = Assistant()

        # Initialize streaming state
        self.state.ai_text = ""
        self.state.ai_streaming = True
        self.state.ai_scroll = 0  # Show tail (bottom)

        # Clear and show initial state
        clear_screen()
        render_dashboard(self.console, self.state)

        last_redraw = time.time()
        redraw_interval = 0.1  # Redraw every 100ms

        try:
            # Stream chunks and update panel
            for chunk in assistant.stream_chunks(self.state.tasks, user_prompt):
                self.state.ai_text += chunk

                # Throttled redraw for performance
                now = time.time()
                if now - last_redraw >= redraw_interval:
                    clear_screen()
                    render_dashboard(self.console, self.state)
                    last_redraw = now

            # Final redraw to show complete response
            self.state.ai_streaming = False
            clear_screen()
            render_dashboard(self.console, self.state)

            # Show full response in pager
            try:
                with self.console.pager():
                    self.console.print(self.state.ai_text)
            except Exception:
                # Pager failed, keep response in panel
                pass

            # Keep AI panel visible (don't clear)
            # User can manually clear with 'clearai' command

        except Exception as e:
            self.state.ai_streaming = False
            self.state.messages.append(f"[red]AI error:[/red] {e}")
            self.state.ai_text = ""

    def _handle_insights(self) -> None:
        """Handle insights command: push a panel into state.messages"""
        insights = LocalSuggestions.get_insights_summary(self.state)
        from rich.box import ROUNDED
        title = "📊 Task Insights" if USE_UNICODE else "Task Insights"
        panel = Panel(
            insights,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2),
        )
        # Store as renderable for renderer to display persistently
        self.state.messages.append(("__PANEL__", panel))

    def _handle_suggest(self) -> None:
        """Handle suggest command: push suggestions panel into state.messages"""
        suggestions = LocalSuggestions.get_smart_suggestions(self.state)
        from rich.box import ROUNDED
        bulb = "💡" if USE_UNICODE else "*"
        lines = [f"  {s}" for s in suggestions]
        content = "\n".join(lines) if lines else "  No suggestions available"
        title = f"{bulb} Smart Suggestions"
        panel = Panel(
            content,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2),
        )
        # Store as renderable for renderer to display persistently
        self.state.messages.append(("__PANEL__", panel))

    def _handle_tags(self) -> None:
        """Handle tags command - now with O(1) performance!"""
        tag_stats = self.state.get_all_tags_with_stats()  # O(1) lookup!

        if tag_stats:
            self.console.print("\n[bold cyan]🏷️ Available Tags:[/bold cyan]")
            for tag in sorted(tag_stats.keys()):
                stats = tag_stats[tag]
                self.console.print(
                    f"  • {tag}: {stats['done']}/{stats['total']} completed"
                )
        else:
            self.console.print("[yellow]No tags found[/yellow]")
        self.console.print()

    def _handle_add_form(self) -> None:
        """Handle add command with questionary form"""
        if self.use_questionary_forms:
            try:
                result = questionary_add_task(self.state)
                if result:
                    # VALIDATE TASK NAME
                    is_valid, error = validate_task_name(result['name'])
                    if not is_valid:
                        x_mark = "✗" if USE_UNICODE else "X"
                        self.console.print(f"[red]{x_mark} {error}[/red]")
                        return

                    # SANITIZE ALL INPUTS
                    self.state.add_task(
                        name=sanitize_text(
                            result['name'],
                            validation.MAX_TASK_NAME_LENGTH,
                            allow_empty=False
                        ),
                        comment=sanitize_comment(result.get('comment', '')),
                        description=sanitize_description(result.get('description', '')),
                        priority=clamp_priority(result.get('priority', 2)),
                        tag=result.get('tag', '')
                    )
                    clear_screen()
                    render_dashboard(self.console, self.state)
                    show_success(
                        f"Task '{result['name'][:50]}...' added successfully!",
                        self.console
                    )
                else:
                    clear_screen()
                    render_dashboard(self.console, self.state)
                    self.console.print("[yellow]Cancelled[/yellow]")
            except Exception as e:
                self.console.print(f"[yellow]Form error: {e}. Using inline form...[/yellow]")
                self._handle_add_inline()
        else:
            self._handle_add_inline()

    def _handle_add_inline(self) -> None:
        """Fallback: inline add form"""
        filled_input = inline_add_task(self.console)
        if filled_input:
            handle_command(filled_input, self.state, self.console)

    def _handle_edit_form(self, user_input: str) -> None:
        """Handle edit command with questionary form"""
        parts = user_input.split()
        if len(parts) == 2 and parts[1].isdigit():
            task_id = int(parts[1])
            task = self.state.get_task_by_id(task_id)  # Using O(1) lookup!

            if task and self.use_questionary_forms:
                try:
                    result = questionary_edit_task(task, self.state)
                    if result:
                        # VALIDATE TASK NAME
                        is_valid, error = validate_task_name(result['name'])
                        if not is_valid:
                            x_mark = "✗" if USE_UNICODE else "X"
                            self.console.print(f"[red]{x_mark} {error}[/red]")
                            return

                        # UPDATE WITH SANITIZATION
                        old_tags = task.tags.copy()
                        task.name = sanitize_text(
                            result['name'],
                            validation.MAX_TASK_NAME_LENGTH,
                            allow_empty=False
                        )
                        task.comment = sanitize_comment(result.get('comment', ''))
                        task.description = sanitize_description(result.get('description', ''))
                        task.priority = clamp_priority(result.get('priority', 2))

                        # Handle tags using utility
                        if 'tag' in result:
                            tag_list = parse_tags(
                                result['tag'],
                                warn_callback=lambda msg: self.console.print(msg)
                            )
                            task.tag = tag_list[0] if tag_list else ""
                            task.tags = tag_list

                        # UPDATE INDEX (fixes BUG #6 - task index not updated on edit)
                        if self.state._task_index is not None:
                            self.state._task_index[task.id] = task

                        # UPDATE TAG INDEX to keep tag-based features consistent
                        self.state._update_tag_index_for_task(task, old_tags)

                        clear_screen()
                        render_dashboard(self.console, self.state)
                        show_success(f"Task #{task_id} updated successfully!", self.console)
                    else:
                        clear_screen()
                        render_dashboard(self.console, self.state)
                        self.console.print("[yellow]Cancelled[/yellow]")
                except Exception as e:
                    self.console.print(f"[yellow]Form error: {e}. Using inline form...[/yellow]")
                    self._handle_edit_inline(task)
            elif task:
                self._handle_edit_inline(task)
            else:
                self.console.print(f"[red]Task #{task_id} not found[/red]")
        else:
            # Invalid edit syntax - let command handler show error
            handle_command(user_input, self.state, self.console)

    def _handle_edit_inline(self, task) -> None:
        """Fallback: inline edit form"""
        filled_input = inline_edit_task(self.console, task)
        if filled_input:
            handle_command(filled_input, self.state, self.console)

    def shutdown(self) -> None:
        """Shutdown application (save and exit)"""
        self.state.save_to_file(self.tasks_file, self.console)
        self.console.print("\n[yellow]Goodbye![/yellow]")






