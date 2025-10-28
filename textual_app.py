"""
Textual TUI Application for Todo CLI
Modern reactive terminal user interface
"""

import signal
import asyncio
from enum import Enum
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Static
from textual.reactive import reactive
from textual import work

from core.state import AppState
from core.commands import handle_command
from core.suggestions import LocalSuggestions
from textual_widgets.task_table import TaskTable
from textual_widgets.note_table import NoteTable
from textual_widgets.note_detail_modal import NoteDetailModal
from textual_widgets.note_editor_modal import NoteEditorModal
from textual_widgets.link_task_picker import LinkTaskPicker
from textual_widgets.status_bar import StatusBar
from textual_widgets.context_footer import ContextFooter
from textual_widgets.command_input import CommandInput
from textual_widgets.task_form import TaskForm
from textual_widgets.confirm_dialog import ConfirmDialog
from textual_widgets.ai_chat_panel import AIChatPanel
from textual_widgets.ai_input import AIInput
from textual_widgets.task_detail_modal import TaskDetailModal
from textual_widgets.panels import LeftPanelContainer
from config import DEFAULT_TASKS_FILE, DEFAULT_AI_CONVERSATION_FILE
from debug_logger import debug_log
from utils.version import get_version


class LayoutMode(Enum):
    """Layout modes for toggle cycling"""
    TASKS_ONLY = 1
    HORIZONTAL_SPLIT = 2
    AI_ONLY = 3
    VERTICAL_SPLIT = 4


class TodoTextualApp(App):
    """
    Modern Textual-based Todo CLI Application

    Features:
    - Reactive data binding (auto-updates on state changes)
    - Keyboard-first navigation
    - Clean, professional UI
    - Cross-platform compatibility
    """

    TITLE = "Todo CLI (Textual)"
    SUB_TITLE = "Modern Task Management"

    # Enable mouse selection to allow copying text with the mouse.
    # Note: earlier we disabled this to avoid an upstream bug; if issues arise,
    # switch back to False and use Ctrl+Shift+Y (copy) instead.
    ENABLE_SELECTION = True

    CSS_PATH = "styles/theme-default-safe.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+k", "toggle_command_mode", "Command", show=True),
        Binding("/", "show_palette", "Palette", show=True),
        Binding("ctrl+t", "toggle_theme", "Theme", show=True),
        Binding("a", "add_selected", "Add"),
        Binding("e", "edit_selected", "Edit"),
        Binding("x", "mark_done", "Done"),
        Binding("u", "mark_undone", "Undone"),
        Binding("d", "delete_selected", "Delete"),
        Binding("f", "filter_tasks", "Filter"),
        Binding("s", "sort_tasks", "Sort"),
        Binding("n", "next_page", "Next Page"),
        Binding("p", "prev_page", "Prev Page"),
        Binding("v", "toggle_view", "View"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "ask_ai", "Ask AI", show=True),
        Binding("ctrl+a", "toggle_ai_panel", "Toggle AI", show=True),
        Binding("ctrl+shift+c", "clear_ai", "Clear AI"),
        Binding("ctrl+shift+y", "copy_ai", "Copy AI"),
        Binding("i", "insights", "Insights"),
        Binding("m", "toggle_mode", "Mode"),
        Binding("ctrl+e", "edit_note", "Edit Note"),
        Binding("ctrl+l", "link_note", "Link Note"),
        Binding("ctrl+u", "unlink_note", "Unlink Note"),
        Binding("enter", "open_selected", "Open"),
        Binding("ctrl+n", "new_note", "New Note"),
        Binding("delete", "delete_note", "Delete Note"),
        Binding("ctrl+d", "duplicate_note", "Duplicate Note"),
        Binding("shift+n", "quick_note", "Quick Note"),
    ]

    # Reactive attributes (auto-update UI when changed)
    tasks_count = reactive(0)
    page_number = reactive(0)
    filter_text = reactive("none")
    command_mode = reactive(False)  # Toggle command input visibility
    ai_panel_visible = reactive(True)  # AI chat panel visibility
    _current_theme: str | None = None

    # Available themes
    _THEMES = {
        "dark": "styles/theme-default-safe.tcss",
        "light": "styles/theme-light.tcss",
    }
    left_panel_mode = reactive(None, init=False)  # NEW - Panel system mode (synced with state)

    def __init__(self, tasks_file: str = DEFAULT_TASKS_FILE):
        """
        Initialize Textual Todo App

        Args:
            tasks_file: Path to tasks JSON file
        """
        debug_log.info("=" * 80)
        debug_log.info("TodoTextualApp.__init__() - Starting initialization")
        debug_log.info("=" * 80)

        debug_log.info("Calling super().__init__()...")
        super().__init__()
        debug_log.info("super().__init__() completed")

        self.tasks_file = tasks_file
        debug_log.info(f"tasks_file set to: {tasks_file}")

        debug_log.info("Creating AppState instance...")
        self.state = AppState()
        debug_log.info("AppState created successfully")

        # Initialize widget references to None (defensive - set in on_mount)
        self._task_table = None
        self._status_bar = None
        self._command_input = None
        self._ai_panel = None
        self._ai_input = None
        self._task_container = None
        self._note_table = None
        self._notes_filter_input = None
        self._main_container = None
        self._left_panel_container = None  # NEW - Panel system container

        # Layout mode tracking for 4-state toggle
        self.layout_mode = LayoutMode.HORIZONTAL_SPLIT  # Default: 50:50 horizontal

        # Use Textual's built-in self.console (removed external RichConsole)

        # Log app initialization
        debug_log.info(f"TodoTextualApp initialized - tasks_file: {tasks_file}")

    def compose(self) -> ComposeResult:
        """
        Compose the application layout

        Layout:
        - Header (title bar)
        - Main vertical layout:
          - Main content (horizontal split):
            - Left (70%): TaskTable or NoteTable (main content)
            - Right (30%): AI Chat Panel (sidebar, collapsible)
          - Bottom section (fixed height):
            - StatusBar (stats and info)
            - CommandInput (command line, toggled with Ctrl+K)
            - AIInput (AI prompt input, always visible when AI panel shown)
        - Footer (keyboard shortcuts)
        """
        debug_log.info("=" * 80)
        debug_log.info("compose() - Building UI layout")
        debug_log.info("=" * 80)

        debug_log.info("Creating Header widget...")
        yield Header(show_clock=True)
        debug_log.info("Header created")

        # Main vertical layout containing all content
        debug_log.info("Creating main layout containers...")
        with Vertical(id="app_layout"):
            # Content area with horizontal split (takes remaining space)
            with Horizontal(id="main_container"):
                # Left side: LeftPanelContainer (dynamic panel switching)
                debug_log.info("Creating LeftPanelContainer...")
                yield LeftPanelContainer()
                debug_log.info("LeftPanelContainer created")

                # Right side: AI chat panel (30%, collapsible)
                debug_log.info("Creating AIChatPanel widget...")
                yield AIChatPanel(self.state, id="ai_chat_panel")
                debug_log.info("AIChatPanel created")

            # Bottom section with fixed heights (StatusBar + inputs)
            with Vertical(id="bottom_section"):
                debug_log.info("Creating StatusBar widget...")
                yield StatusBar(id="status_bar")
                debug_log.info("StatusBar created")

                debug_log.info("Creating CommandInput widget...")
                yield CommandInput(id="command_input")
                debug_log.info("CommandInput created")

                debug_log.info("Creating AIInput widget...")
                yield AIInput(id="ai_input")
                debug_log.info("AIInput created")

        debug_log.info("Creating ContextFooter widget...")
        yield ContextFooter()
        debug_log.info("ContextFooter created")

        debug_log.info("compose() completed - All widgets created")

    def on_mount(self) -> None:
        """
        Called when app is mounted (startup)
        Load tasks and populate table
        """
        debug_log.info("=" * 80)
        debug_log.info("on_mount() - Application mounting")
        debug_log.info("=" * 80)

        debug_log.debug("App on_mount() called - app is starting up")

        # Update header title to include version at the end
        try:
            ver = get_version()
            self.title = f"{self.TITLE} • v{ver}"
        except Exception:
            # Keep original title on failure; do not crash UI
            pass

        # Apply persisted theme (if any) early
        try:
            self._load_theme_preference()
        except Exception:
            pass

        # Debug: Check if handlers exist
        has_catch_all = hasattr(self, 'on_message')
        has_ai_handler = hasattr(self, 'on_ai_input_prompt_submitted')
        debug_log.debug(f"Handler check: on_message={has_catch_all}, on_ai_input_prompt_submitted={has_ai_handler}")

        # Check if AIInput widget is mounted
        try:
            ai_input = self.query_one(AIInput)
            debug_log.debug(f"AIInput widget found: {ai_input}, id={ai_input.id}")
        except Exception as e:
            debug_log.error(f"AIInput widget not found: {e}")

        # Load tasks from file
        debug_log.info(f"Loading tasks from file: {self.tasks_file}")
        try:
            self.state.load_from_file(self.tasks_file, self.console)
            debug_log.info(f"Tasks loaded successfully - {len(self.state.tasks)} tasks")
        except Exception as e:
            debug_log.error(f"Failed to load tasks: {e}", exception=e)

        # Load AI conversation history
        debug_log.info(f"Loading AI conversation from: {DEFAULT_AI_CONVERSATION_FILE}")
        try:
            self.state.load_conversation_from_file(str(DEFAULT_AI_CONVERSATION_FILE), self.console)
            debug_log.info(f"AI conversation loaded - {len(self.state.ai_conversation)} messages")
        except Exception as e:
            debug_log.error(f"Failed to load AI conversation: {e}", exception=e)

        # Cache widget references BEFORE calling refresh_table()
        # This ensures refresh_table() has access to widgets
        debug_log.info("Caching widget references...")
        try:
            # Cache LeftPanelContainer (NEW - panel system)
            self._left_panel_container = self.query_one(LeftPanelContainer)
            debug_log.info("LeftPanelContainer cached")

            # Tables will be created dynamically by LeftPanelContainer
            # Initially set to None, will be queried when needed
            self._task_table = None
            self._note_table = None

            self._status_bar = self.query_one(StatusBar)
            self._command_input = self.query_one(CommandInput)
            self._ai_input = self.query_one(AIInput)
            try:
                self._footer = self.query_one(ContextFooter)
            except Exception:
                self._footer = None

            # Cache container references for layout management
            self._main_container = self.query_one("#main_container")

            # Cache AI panel reference (may fail if widget not mounted)
            try:
                self._ai_panel = self.query_one(AIChatPanel)
            except Exception:
                self._ai_panel = None
                debug_log.warning("AI panel not found during widget caching")

            debug_log.debug("Widget references cached successfully")

        except Exception as e:
            # Critical error - widgets not found during mount
            self.log.error(f"CRITICAL: Failed to cache widget references: {e}", exc_info=True)
            debug_log.error(f"Widget caching failed: {e}", exception=e)

            # Notify user of critical error
            self.notify(
                "Critical error initializing widgets. Some features may not work.",
                severity="error",
                timeout=10
            )

        # Update reactive attributes
        self.tasks_count = len(self.state.tasks)
        self.page_number = self.state.page

        # Initialize left panel with TaskTable (default LIST_TASKS mode)
        debug_log.info("Initializing left panel container...")
        if self._left_panel_container:
            # Sync panel mode with state
            from core.state import LeftPanelMode
            self.state.left_panel_mode = LeftPanelMode.LIST_TASKS
            self._left_panel_container.current_mode = LeftPanelMode.LIST_TASKS
            debug_log.info("Left panel initialized in LIST_TASKS mode")

        # Populate table (now has cached widget references)
        debug_log.info("Calling refresh_table() to populate UI...")
        try:
            self.refresh_table()
            debug_log.info("refresh_table() completed successfully")
        except Exception as e:
            debug_log.error(f"refresh_table() failed: {e}", exception=e)

        # Populate AI chat panel with error handling
        if self._ai_panel:
            try:
                self._ai_panel.update_from_state()
                debug_log.info("AI panel initialized successfully")
            except Exception as e:
                self.log.error(f"Failed to initialize AI panel: {e}", exc_info=True)
                debug_log.error(f"AI panel initialization failed: {e}", exception=e)

        # Hide command input by default (show with Ctrl+K or /)
        # FIX: Prevents CommandInput from stealing focus asynchronously
        if self._command_input:
            self._command_input.display = False
            self.command_mode = False

        # Show AI panel initially
        if self._ai_panel:
            self._ai_panel.display = self.ai_panel_visible

        # Set initial focus to left panel container
        debug_log.info("Setting initial focus to left panel...")
        if self._left_panel_container:
            self._left_panel_container.focus()
            debug_log.info("Initial focus set to left panel container")
        else:
            debug_log.error("Cannot set focus - left panel container is None")

        # Register signal handlers for graceful shutdown (Ctrl+C, kill)
        # Note: Using signal.signal() instead of asyncio's add_signal_handler()
        # because add_signal_handler() is not supported on Windows
        debug_log.info("Registering signal handlers for graceful shutdown...")
        try:
            # Register SIGINT (Ctrl+C) and SIGTERM (kill command)
            signal.signal(signal.SIGINT, lambda sig, frame: self._handle_signal(sig))
            signal.signal(signal.SIGTERM, lambda sig, frame: self._handle_signal(sig))
            debug_log.info("Signal handlers registered successfully (SIGTERM, SIGINT)")
        except Exception as e:
            debug_log.warning(f"Failed to register signal handlers: {e}")
            debug_log.warning("Graceful shutdown via Ctrl+C may not work properly")

        debug_log.info("=" * 80)
        debug_log.info("on_mount() COMPLETED - App should now be visible")
        debug_log.info("=" * 80)

    # ------------------------------------------------------------------
    # Theme switching
    # ------------------------------------------------------------------
    def _save_theme_preference(self) -> None:
        from pathlib import Path
        import json as _json
        try:
            from config import DEFAULT_SETTINGS_FILE
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            existing: dict = {}
            if settings_path.exists():
                try:
                    existing = _json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}
            existing["theme"] = self._current_theme or "dark"
            tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
            tmp.write_text(_json.dumps(existing, indent=2), encoding="utf-8")
            try:
                import os as _os
                _os.replace(tmp, settings_path)
            except Exception:
                settings_path.write_text(_json.dumps(existing, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_theme_preference(self) -> None:
        from pathlib import Path
        import json as _json
        try:
            from config import DEFAULT_SETTINGS_FILE
            settings_path = Path(DEFAULT_SETTINGS_FILE)
            if settings_path.exists():
                data = _json.loads(settings_path.read_text(encoding="utf-8"))
                name = (data.get("theme") or "dark").lower()
                if name in self._THEMES:
                    # Load preferred theme over default CSS_PATH
                    self._current_theme = name
                    self.load_css(path=self._THEMES[name], merge=False)
        except Exception:
            pass

    def action_toggle_theme(self) -> None:
        nxt = "light" if (self._current_theme or "dark") == "dark" else "dark"
        self.action_switch_theme(nxt)

    def action_switch_theme(self, theme: str) -> None:
        name = (theme or "").strip().lower()
        if name not in self._THEMES:
            try:
                self.console.print(f"[yellow]Unknown theme '{theme}'. Available: {', '.join(self._THEMES)}[/yellow]")
            except Exception:
                pass
            return
        try:
            self.load_css(path=self._THEMES[name], merge=False)
            self._current_theme = name
            self._save_theme_preference()
            try:
                self.refresh()
            except Exception:
                pass
        except Exception as e:
            try:
                self.console.print(f"[red]Failed to load theme '{name}': {e}[/red]")
            except Exception:
                pass

    def watch_left_panel_mode(self, old_mode, new_mode) -> None:
        """
        Reactive watcher - called when left_panel_mode changes

        Syncs app reactive attribute with state and triggers panel switching

        Args:
            old_mode: Previous panel mode
            new_mode: New panel mode
        """
        if new_mode is None:
            return

        debug_log.info(f"[APP] watch_left_panel_mode: {old_mode} → {new_mode}")

        # Sync container if it exists
        if self._left_panel_container:
            self._left_panel_container.current_mode = new_mode
            debug_log.info(f"[APP] LeftPanelContainer synced to mode: {new_mode}")

        # Update status bar if needed
        if self._status_bar:
            self._status_bar.update_from_state(self.state)

    def refresh_table(self) -> None:
        """
        Refresh task table with current state
        Called whenever tasks/filters/sort changes

        Includes error boundaries to handle widget reference failures gracefully.
        """
        # Debug logging to track state synchronization
        debug_log.info(f"[APP] refresh_table() called - {len(self.state.tasks)} tasks in state; mode={getattr(self.state, 'entity_mode', 'tasks')}")
        if self.state.tasks:
            task_ids = sorted([t.id for t in self.state.tasks])
            debug_log.debug(f"[APP] Task IDs in state: {task_ids[:10]}{'...' if len(task_ids) > 10 else ''}")

        # Use cached widget references with null checks (safety)
        try:
            # With panel system, query tables dynamically (they're created by LeftPanelContainer)
            from textual_widgets.task_table import TaskTable
            task_tables = self.query(TaskTable)
            if task_tables:
                task_table = task_tables.first()
                if self.state.entity_mode == "tasks":
                    task_table.display = True
                    task_table.update_from_state(self.state)
                else:
                    task_table.display = False
                debug_log.debug(f"[APP] Task table updated/toggled successfully")
            else:
                debug_log.debug("Task table not found (may be in non-LIST mode)")

            # Query note tables dynamically
            from textual_widgets.note_table import NoteTable
            note_tables = self.query(NoteTable)
            if note_tables:
                note_table = note_tables.first()
                if self.state.entity_mode == "notes":
                    note_table.display = True
                    # Apply notes filter if present
                    filter_value = ""
                    notes = list(self.state.notes)
                    debug_log.debug(f"[APP] Notes in state: {len(notes)}; filter='{filter_value}'")
                    if filter_value:
                        q = filter_value.strip().lower()
                        notes = [
                            n for n in notes
                            if q in n.title.lower()
                            or any(q in t for t in n.tags)
                            or q in (n.body_md or "").lower()
                            or n.id.startswith(q)
                        ]
                        debug_log.debug(f"[APP] Notes after filter: {len(notes)}")
                    note_table.update_with_notes(notes)
                else:
                    note_table.display = False
                debug_log.debug("[APP] Note table updated/toggled successfully")
            else:
                debug_log.debug("Note table not found (may be in non-LIST mode)")

            if self._status_bar:
                self._status_bar.update_from_state(self.state)
                debug_log.debug(f"[APP] Status bar updated successfully")
            else:
                self.log.warning("Status bar reference is None, skipping update")

            if getattr(self, '_footer', None):
                try:
                    self._footer.update_from_state()
                except Exception:
                    pass

        except Exception as e:
            # Widget update failed - log but don't crash
            self.log.error(f"Failed to refresh widgets: {e}", exc_info=True)
            debug_log.error(f"Widget refresh failed: {e}", exception=e)

    # ========================================================================
    # MESSAGE HANDLERS
    # ========================================================================

    def on_command_input_command_submitted(self, message: CommandInput.CommandSubmitted) -> None:
        """
        Handle command submission from CommandInput

        Args:
            message: Command submitted message
        """
        import shlex

        command = message.command.strip()

        if not command:
            return

        # Keep command input visible after submission (for easier multi-command workflow)
        # User can still hide it with Ctrl+K if desired

        # Keep focus on command input for next command
        # self.query_one(TaskTable).focus()  # Commented out - keep focus on command input

        # Parse command to detect form commands
        try:
            parts = shlex.split(command)
            cmd = parts[0].lower() if parts else ""
        except ValueError:
            # Shlex parsing failed (unmatched quotes), fall through to handle_command
            cmd = command.split()[0].lower() if command.split() else ""
            parts = [cmd]

        # Handle special commands that need Textual-specific behavior
        if cmd in ("exit", "quit", "q"):
            self.action_quit()
            return

        if cmd in ("cls", "clear", "c"):
            self.refresh_table()
            self.notify("Screen refreshed")
            return

        # Theme switch (runtime) via command: `theme dark|light`
        if cmd == "theme" and len(parts) >= 2:
            self.action_switch_theme(parts[1])
            return

        # Route form commands to action methods (UX unification)
        if cmd in ("add", "a"):
            # Mode-aware: creates task or note based on entity_mode
            self.action_add_selected()
            return

        if cmd in ("edit", "e"):
            # Mode-aware: edit task or note based on entity_mode
            if len(parts) >= 2:
                try:
                    # Try to select entity by ID
                    if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
                        note_id = parts[1]
                        if self._note_table and self._note_table.select_note_by_id(note_id):
                            pass  # Selection successful
                        else:
                            self.notify(f"Note {note_id[:8]}... not found", severity="error")
                            return
                    else:
                        task_id = int(parts[1])
                        if self._task_table and self._task_table.select_task_by_id(task_id):
                            pass  # Selection successful
                        else:
                            self.notify(f"Task #{task_id} not found", severity="error")
                            return
                except (ValueError, AttributeError) as e:
                    if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
                        self.notify(f"Invalid note ID: {parts[1]}", severity="error")
                    else:
                        self.notify("Invalid task ID - must be a number", severity="error")
                    return
            # Open edit modal for selected entity
            self.action_edit_selected()
            return

        if cmd in ("show", "s"):
            # In notes mode, show Note detail modal
            if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
                note_id = None
                if len(parts) >= 2:
                    note_id = parts[1]
                # Dispatch async action
                try:
                    self.action_open_note(note_id)
                except Exception:
                    pass
                return
            # Tasks mode: show task detail or pass to filter handling
            if len(parts) >= 2:
                try:
                    task_id = int(parts[1])
                    self.action_show_task(task_id)
                except ValueError:
                    # Not a number - let handle_command handle it as filter
                    pass
            else:
                task_id = self._task_table.get_selected_task_id()
                if task_id is not None:
                    self.action_show_task(task_id)
                else:
                    self.notify("No task selected - use 'show <id>' or select a task", severity="warning")
            return

        # Notes commands routed to internal editor/modals
        if cmd == "note":
            if len(parts) >= 2 and parts[1] == "new":
                self.action_new_note()
                return
            if len(parts) >= 3 and parts[1] == "edit":
                # Switch to note edit panel
                from core.state import LeftPanelMode
                note_id = parts[2]

                # Verify note exists
                from services.notes import FileNoteRepository
                from config import DEFAULT_NOTES_DIR
                repo = FileNoteRepository(DEFAULT_NOTES_DIR)
                n = repo.get(note_id)
                if not n:
                    self.notify(f"Note {note_id} not found", severity="error")
                else:
                    self.state.selected_note_id = note_id
                    self.state.edit_mode_is_new = False
                    self.state.left_panel_mode = LeftPanelMode.EDIT_NOTE
                    self.left_panel_mode = LeftPanelMode.EDIT_NOTE
                    debug_log.info(f"[APP] Switched to EDIT_NOTE mode for note {note_id[:8]}")
                return

        # In notes mode, route edit/remove to note actions
        if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
            if cmd in ("edit", "e"):
                note_id = parts[1] if len(parts) >= 2 else None
                try:
                    # Reuse open_note then press edit inside
                    self.action_open_note(note_id)
                except Exception:
                    pass
                return
            if cmd in ("remove", "delete", "del", "r"):
                try:
                    self.action_delete_note()
                except Exception:
                    pass
                return

        # Use existing command handler from core/commands.py
        try:
            handle_command(command, self.state, self.console)

            # Check if state has messages to display
            if self.state.messages:
                # Show last message as notification
                last_msg = self.state.messages[-1]

                # Handle special renderable objects (panels)
                if isinstance(last_msg, tuple) and len(last_msg) == 2 and last_msg[0] == "__PANEL__":
                    # For panels, show a simpler notification
                    self.notify("Command executed (see Rich UI for full output)", timeout=3)
                else:
                    # Show plain text message
                    self.notify(str(last_msg), timeout=5)

            # Refresh UI and toggle tables if mode changed
            self.refresh_table()

        except Exception as e:
            # Log full exception with stack trace for debugging
            import traceback
            self.log.error(f"Command failed: {command}", exc_info=True)

            # Show helpful error message to user
            error_type = type(e).__name__
            error_msg = str(e)[:100]  # Limit to 100 chars
            self.notify(
                f"Command failed: {error_type}: {error_msg}",
                severity="error",
                timeout=10
            )

            # Clear any partial state changes
            self.state.messages = []

            # Refresh UI to show consistent state
            try:
                self.refresh_table()
            except Exception:
                # If refresh fails, log but don't propagate
                self.log.error("Failed to refresh UI after error", exc_info=True)

    def on_input_changed(self, event) -> None:
        try:
            from textual.widgets import Input
            if isinstance(event.input, Input) and event.input.id == "notes_filter":
                # Live-filter notes table
                self.refresh_table()
        except Exception:
            pass

    # ========================================================================
    # ACTION HANDLERS (Keyboard Shortcuts)
    # ========================================================================

    def action_toggle_command_mode(self) -> None:
        """Toggle command input visibility (Ctrl+K)"""
        if self._command_input.display:
            # Hide command mode
            self._command_input.display = False
            self.command_mode = False
            self._task_table.focus()
        else:
            # Show command mode
            self._command_input.display = True
            self.command_mode = True
            self._command_input.focus()
        try:
            if getattr(self, '_footer', None):
                self._footer.update_from_state()
        except Exception:
            pass

    def action_show_palette(self) -> None:
        """Show command input (palette-like) and prefill '/' for discoverability."""
        if not self._command_input:
            return
        self._command_input.display = True
        self.command_mode = True
        # Prefill '/' only if empty to avoid clobbering
        try:
            buf = self._command_input.query_one('Input')  # underlying Input, if exposed
        except Exception:
            buf = None
        try:
            # Fallback: focus is sufficient; user sees hints
            self._command_input.focus()
        except Exception:
            pass
        try:
            if getattr(self, '_footer', None):
                self._footer.update_from_state()
        except Exception:
            pass

    def action_add_task(self) -> None:
        """Switch to edit panel in create mode (NEW - panel system)"""
        from core.state import LeftPanelMode

        # Set state for creating new task
        self.state.edit_mode_is_new = True
        self.state.selected_task_id = None

        # Switch to edit panel
        self.state.left_panel_mode = LeftPanelMode.EDIT_TASK
        self.left_panel_mode = LeftPanelMode.EDIT_TASK

        debug_log.info("[APP] Switched to EDIT_TASK mode (create new)")

    def action_edit_task(self) -> None:
        """Switch to edit task panel for selected task"""
        task_id = self._task_table.get_selected_task_id()

        if task_id is None:
            self.notify("No task selected", severity="warning")
            return

        task = self.state.get_task_by_id(task_id)
        if not task:
            self.notify(f"Task #{task_id} not found", severity="error")
            return

        # Switch to edit panel
        self.state.selected_task_id = task_id
        self.state.edit_mode_is_new = False
        self.state.left_panel_mode = LeftPanelMode.EDIT_TASK
        self.left_panel_mode = LeftPanelMode.EDIT_TASK

        debug_log.info(f"[APP] Switched to EDIT_TASK mode for task #{task_id}")

    def action_show_task(self, task_id: int) -> None:
        """
        Switch to task detail panel

        Args:
            task_id: ID of task to display
        """
        task = self.state.get_task_by_id(task_id)
        if not task:
            self.notify(f"Task #{task_id} not found", severity="error")
            return

        # Switch to detail panel
        self.state.selected_task_id = task_id
        self.state.left_panel_mode = LeftPanelMode.DETAIL_TASK
        self.left_panel_mode = LeftPanelMode.DETAIL_TASK

        debug_log.info(f"[APP] Switched to DETAIL_TASK mode for task #{task_id}")

    def action_mark_done(self) -> None:
        """Mark selected task as done"""
        task_id = self._task_table.get_selected_task_id()

        if task_id is not None:
            task = self.state.get_task_by_id(task_id)
            if task:
                task.done = True
                self.refresh_table()
                self.notify(f"Task #{task_id} marked as done", severity="information")
        else:
            self.notify("No task selected", severity="warning")

    def action_mark_undone(self) -> None:
        """Mark selected task as undone"""
        task_id = self._task_table.get_selected_task_id()

        if task_id is not None:
            task = self.state.get_task_by_id(task_id)
            if task:
                task.done = False
                self.refresh_table()
                self.notify(f"Task #{task_id} marked as undone", severity="information")
        else:
            self.notify("No task selected", severity="warning")

    @work(exclusive=True)
    async def action_delete_task(self) -> None:
        """Delete selected task with confirmation (runs as worker to support modal dialog)"""
        task_id = self._task_table.get_selected_task_id()

        if task_id is None:
            self.notify("No task selected", severity="warning")
            return

        task = self.state.get_task_by_id(task_id)
        if not task:
            self.notify(f"Task #{task_id} not found", severity="error")
            return

        # Show confirmation dialog
        task_preview = task.name[:40] + "..." if len(task.name) > 40 else task.name
        confirmed = await self.push_screen_wait(
            ConfirmDialog(
                message=f'Delete task #{task_id}?\n"{task_preview}"',
                title="⚠️  Confirm Delete",
                confirm_text="Delete",
                cancel_text="Cancel"
            )
        )

        if confirmed:
            self.state.remove_task(task)
            self.refresh_table()
            self.notify(f"✓ Task #{task_id} deleted", severity="warning")
        else:
            self.notify("Delete cancelled", severity="information")

    def action_next_page(self) -> None:
        """Go to next page"""
        # Respect current mode for pagination
        if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
            total_items = len(getattr(self.state, 'notes', []))
        else:
            filtered_tasks = self.state.get_filter_tasks(self.state.tasks)
            total_items = len(filtered_tasks)
        total_pages = (total_items + self.state.page_size - 1) // self.state.page_size if total_items > 0 else 1

        if self.state.page < total_pages - 1:
            self.state.page += 1
            self.refresh_table()
            self.notify(f"Page {self.state.page + 1}/{total_pages}")
        else:
            self.notify("Already on last page", severity="warning")

    def action_prev_page(self) -> None:
        """Go to previous page"""
        if self.state.page > 0:
            self.state.page -= 1
            self.refresh_table()
            self.notify(f"Page {self.state.page + 1}")
        else:
            self.notify("Already on first page", severity="warning")

    def action_toggle_view(self) -> None:
        """Toggle between compact and detail view"""
        if self.state.view_mode == "compact":
            self.state.view_mode = "detail"
        else:
            self.state.view_mode = "compact"

        self.refresh_table()
        self.notify(f"View: {self.state.view_mode}")

    def action_open_selected(self) -> None:
        """Open detail panel for currently selected item (NEW - panel system)

        - In tasks mode: switches to TaskDetailPanel
        - In notes mode: switches to NoteDetailPanel
        """
        from core.state import LeftPanelMode

        mode = getattr(self.state, 'entity_mode', 'tasks')
        debug_log.info(f"[APP] action_open_selected() CALLED (mode={mode})")

        if mode == 'notes':
            # Get selected note ID from note table
            from textual_widgets.note_table import NoteTable
            note_tables = self.query(NoteTable)
            if not note_tables:
                return

            note_table = note_tables.first()
            note_id = note_table.get_selected_note_id()
            if not note_id:
                self.notify("No note selected", severity="warning")
                return

            # Switch to note detail panel
            self.state.selected_note_id = note_id
            self.state.left_panel_mode = LeftPanelMode.DETAIL_NOTE
            self.left_panel_mode = LeftPanelMode.DETAIL_NOTE
            debug_log.info(f"[APP] Switched to DETAIL_NOTE mode")
            return

        # Tasks mode
        from textual_widgets.task_table import TaskTable
        task_tables = self.query(TaskTable)
        if not task_tables:
            return

        task_table = task_tables.first()
        task_id = task_table.get_selected_task_id()
        if not task_id:
            self.notify("No task selected", severity="warning")
            return

        # Switch to task detail panel
        self.state.selected_task_id = task_id
        self.state.left_panel_mode = LeftPanelMode.DETAIL_TASK
        self.left_panel_mode = LeftPanelMode.DETAIL_TASK
        debug_log.info(f"[APP] Switched to DETAIL_TASK mode for task #{task_id}")

    def action_refresh(self) -> None:
        """Refresh display"""
        self.refresh_table()
        self.notify("Refreshed")

    def action_filter_tasks(self) -> None:
        """Show filter input (placeholder - Phase 2)"""
        self.notify("Filter input (coming in Phase 2)")

    def action_sort_tasks(self) -> None:
        """Cycle through sort options"""
        sort_options = ["priority", "id", "name"]
        current_index = sort_options.index(self.state.sort)
        next_index = (current_index + 1) % len(sort_options)
        self.state.sort = sort_options[next_index]

        self.refresh_table()
        self.notify(f"Sort: {self.state.sort}")

    def action_edit_selected(self) -> None:
        """Edit the currently selected item based on mode - switches to edit panel"""
        if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
            # Notes mode - switch to note edit panel
            if not self._note_table:
                return
            note_id = self._note_table.get_selected_note_id()
            if not note_id:
                self.notify("No note selected", severity="warning")
                return

            # Switch to note edit panel
            from core.state import LeftPanelMode
            self.state.selected_note_id = note_id
            self.state.edit_mode_is_new = False
            self.state.left_panel_mode = LeftPanelMode.EDIT_NOTE
            self.left_panel_mode = LeftPanelMode.EDIT_NOTE

            debug_log.info(f"[APP] Switched to EDIT_NOTE mode for note {note_id[:8]}")
            return

        # Tasks mode - delegate to action_edit_task
        self.action_edit_task()

    def action_delete_selected(self) -> None:
        """Delete currently selected entity based on mode."""
        if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
            self.action_delete_note()
            return
        # Tasks mode
        self.action_delete_task()

    def action_add_selected(self) -> None:
        """Add new entity based on current mode.

        - In notes mode: creates a new note (opens NoteEditorModal).
        - In tasks mode: opens TaskForm for new task (existing behavior).
        """
        if getattr(self.state, 'entity_mode', 'tasks') == 'notes':
            self.action_new_note()
        else:
            self.action_add_task()

    def action_toggle_mode(self) -> None:
        """Toggle between tasks and notes mode"""
        self.state.entity_mode = "notes" if self.state.entity_mode == "tasks" else "tasks"
        self.refresh_table()
        # Focus appropriate table
        if self.state.entity_mode == "tasks" and self._task_table:
            self._task_table.focus()
        elif self.state.entity_mode == "notes" and self._note_table:
            self._note_table.focus()
        self.notify(f"Mode: {self.state.entity_mode}")

    def _ensure_note_selection(self) -> str | None:
        if self.state.entity_mode != "notes":
            self.notify("Switch to notes mode (m) to edit/link notes", severity="warning")
            return None
        if not self._note_table:
            self.notify("Note table not available", severity="error")
            return None
        note_id = self._note_table.get_selected_note_id()
        if not note_id:
            self.notify("No note selected", severity="warning")
            return None
        return note_id

    def action_edit_note(self) -> None:
        """Switch to edit note panel for selected note"""
        note_id = self._ensure_note_selection()
        if not note_id:
            return

        # Switch to note edit panel
        from core.state import LeftPanelMode
        self.state.selected_note_id = note_id
        self.state.edit_mode_is_new = False
        self.state.left_panel_mode = LeftPanelMode.EDIT_NOTE
        self.left_panel_mode = LeftPanelMode.EDIT_NOTE

        debug_log.info(f"[APP] Switched to EDIT_NOTE mode for note {note_id[:8]}")

    @work(exclusive=True)
    async def action_link_note(self) -> None:
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR
        note_id = self._ensure_note_selection()
        if not note_id:
            return
        task_id = getattr(self.state, "selected_task_id", None)
        if task_id is None:
            # Open picker modal for choosing a task (await within worker)
            tasks = self.state.get_filter_tasks(self.state.tasks)
            picked = await self.push_screen_wait(LinkTaskPicker(tasks))
            if picked is None:
                self.notify("Link cancelled", severity="information")
                return
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            n2 = repo.get(note_id)
            if not n2:
                self.notify("Note no longer exists", severity="error")
                return
            repo.link_task(n2, int(picked))
            self.state.refresh_notes_from_disk()
            self.refresh_table()
            self.notify(f"Linked note {n2.id[:8]} to task {picked}")
            return
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)
        n = repo.get(note_id)
        if not n:
            self.notify(f"Note {note_id} not found", severity="error")
            return
        repo.link_task(n, task_id)
        self.state.refresh_notes_from_disk()
        self.refresh_table()
        self.notify(f"Linked note {n.id[:8]} to task {task_id}")

    def action_unlink_note(self) -> None:
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR
        note_id = self._ensure_note_selection()
        if not note_id:
            return
        task_id = getattr(self.state, "selected_task_id", None)
        if task_id is None:
            self.notify("Use 'show <task_id>' first to select a task", severity="warning")
            return
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)
        n = repo.get(note_id)
        if not n:
            self.notify(f"Note {note_id} not found", severity="error")
            return
        repo.unlink_task(n, task_id)
        self.state.refresh_notes_from_disk()
        self.refresh_table()
        self.notify(f"Unlinked note {n.id[:8]} from task {task_id}")

    def action_open_note(self, note_id: str | None = None) -> None:
        """Switch to note detail panel"""
        if self.state.entity_mode != "notes" or not self._note_table:
            return
        if not note_id:
            note_id = self._note_table.get_selected_note_id()
        if not note_id:
            self.notify("No note selected", severity="warning")
            return

        # Switch to note detail panel
        from core.state import LeftPanelMode
        self.state.selected_note_id = note_id
        self.state.left_panel_mode = LeftPanelMode.DETAIL_NOTE
        self.left_panel_mode = LeftPanelMode.DETAIL_NOTE

        debug_log.info(f"[APP] Switched to DETAIL_NOTE mode for note {note_id[:8]}")

    def action_new_note(self) -> None:
        """Switch to edit panel in create mode for new note"""
        from core.state import LeftPanelMode

        # Switch to notes mode and edit panel
        self.state.entity_mode = "notes"
        self.state.edit_mode_is_new = True
        self.state.selected_note_id = None  # No existing note
        self.state.left_panel_mode = LeftPanelMode.EDIT_NOTE
        self.left_panel_mode = LeftPanelMode.EDIT_NOTE

        debug_log.info("[APP] Switched to EDIT_NOTE mode (create new)")

    @work(exclusive=True)
    async def action_delete_note(self) -> None:
        if self.state.entity_mode != "notes" or not self._note_table:
            return
        note_id = self._note_table.get_selected_note_id()
        if not note_id:
            self.notify("No note selected", severity="warning")
            return
        from textual_widgets.confirm_dialog import ConfirmDialog
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR
        dialog = ConfirmDialog(
            title="Delete Note",
            message=f"Are you sure you want to delete note {note_id[:8]}?",
            confirm_text="Delete",
            cancel_text="Cancel",
        )
        confirmed = await self.push_screen_wait(dialog)
        if confirmed:
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            ok = repo.delete(note_id)
            self.state.refresh_notes_from_disk()
            self.refresh_table()
            if ok:
                self.notify("Note deleted", severity="warning")
            else:
                self.notify("No note deleted", severity="warning")
        else:
            self.notify("Delete cancelled", severity="information")

    def action_duplicate_note(self) -> None:
        """Quickly duplicate the selected note (keeps links, adds 'Copy of' prefix)."""
        if self.state.entity_mode != "notes" or not self._note_table:
            return
        note_id = self._note_table.get_selected_note_id()
        if not note_id:
            self.notify("No note selected", severity="warning")
            return
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)
        src = repo.get(note_id)
        if not src:
            self.notify("Note not found", severity="error")
            return
        new = repo.create(
            title=f"Copy of {src.title}",
            tags=list(src.tags),
            task_ids=list(src.task_ids),
            body_md=src.body_md,
        )
        self.state.refresh_notes_from_disk()
        self.refresh_table()
        if self._note_table:
            try:
                self._note_table.select_note_by_id(new.id)
                self._note_table.focus()
            except Exception:
                pass
        self.notify(f"Duplicated note {src.id[:8]} → {new.id[:8]}")

    def action_quick_note(self) -> None:
        """Create a quick note - switches to edit panel (same as action_new_note)"""
        from core.state import LeftPanelMode

        # Switch to notes mode and edit panel
        self.state.entity_mode = "notes"
        self.state.edit_mode_is_new = True
        self.state.selected_note_id = None
        self.state.left_panel_mode = LeftPanelMode.EDIT_NOTE
        self.left_panel_mode = LeftPanelMode.EDIT_NOTE

        debug_log.info("[APP] Switched to EDIT_NOTE mode (quick note)")

    # Update footer on focus changes
    def on_focus(self, event) -> None:
        try:
            if getattr(self, '_footer', None):
                self._footer.update_from_state()
        except Exception:
            pass

        self.call_later(_create)

    def action_help(self) -> None:
        """Show help (placeholder - Phase 2)"""
        help_text = """
[bold cyan]Keyboard Shortcuts:[/bold cyan]

a - Add task            n - Next page
e - Edit task           p - Previous page
x - Mark done           v - Toggle view
u - Mark undone         s - Sort
d - Delete task         r - Refresh
f - Filter tasks        i - Insights
? - Ask AI              Ctrl+A - Toggle AI panel
Ctrl+Shift+C - Clear AI q - Quit
        """
        self.notify(help_text)

    # =========================================================================
    # AI ACTIONS (Phase 2.3)
    # =========================================================================

    def _apply_layout_mode(self) -> None:
        """Apply current layout mode by adjusting widget visibility and CSS"""
        if not self._task_container or not self._main_container or not self._ai_panel:
            return

        if self.layout_mode == LayoutMode.TASKS_ONLY:
            # Hide AI, tasks full width
            self._ai_panel.display = False
            self._ai_input.display = False
            self._task_container.display = True
            self._task_container.styles.width = "100%"
            self._task_container.styles.height = "1fr"
            self._main_container.styles.layout = "horizontal"

        elif self.layout_mode == LayoutMode.HORIZONTAL_SPLIT:
            # Show both, 50:50 side by side
            self._task_container.display = True
            self._ai_panel.display = True
            self._ai_input.display = True
            self._task_container.styles.width = "50%"
            self._task_container.styles.height = "1fr"
            self._ai_panel.styles.width = "50%"
            self._ai_panel.styles.height = "1fr"
            self._main_container.styles.layout = "horizontal"

        elif self.layout_mode == LayoutMode.AI_ONLY:
            # Hide tasks, AI full width
            self._task_container.display = False
            self._ai_panel.display = True
            self._ai_input.display = True
            self._ai_panel.styles.width = "100%"
            self._ai_panel.styles.height = "1fr"
            self._main_container.styles.layout = "horizontal"

        elif self.layout_mode == LayoutMode.VERTICAL_SPLIT:
            # Show both, 50:50 stacked (vertical)
            self._task_container.display = True
            self._ai_panel.display = True
            self._ai_input.display = True
            self._task_container.styles.width = "100%"
            self._task_container.styles.height = "50%"
            self._ai_panel.styles.width = "100%"
            self._ai_panel.styles.height = "50%"
            self._main_container.styles.layout = "vertical"

    def action_toggle_ai_panel(self) -> None:
        """Cycle through 4 layout modes: Tasks→H-Split→AI→V-Split (Ctrl+A)"""
        if not self._ai_panel or not self._ai_input:
            self.notify("AI panel not available", severity="warning")
            return

        # Cycle to next mode
        modes = list(LayoutMode)
        current_idx = modes.index(self.layout_mode)
        next_idx = (current_idx + 1) % len(modes)
        self.layout_mode = modes[next_idx]

        # Apply layout changes
        self._apply_layout_mode()

        # Notify user
        mode_names = {
            LayoutMode.TASKS_ONLY: "Tasks only",
            LayoutMode.HORIZONTAL_SPLIT: "50:50 Horizontal",
            LayoutMode.AI_ONLY: "AI only",
            LayoutMode.VERTICAL_SPLIT: "50:50 Vertical"
        }
        self.notify(f"Layout: {mode_names[self.layout_mode]}")

    def action_ask_ai(self) -> None:
        """Focus AI input field and prompt for question (?)"""
        # If AI hidden (TASKS_ONLY mode), cycle to show it
        if self.layout_mode == LayoutMode.TASKS_ONLY:
            self.action_toggle_ai_panel()

        # Focus AI input
        self._ai_input.focus_and_clear()

    def action_clear_ai(self) -> None:
        """Clear AI conversation history (Ctrl+Shift+C)"""
        if not self._ai_panel:
            self.notify("AI panel not available", severity="warning")
            return

        self.state.clear_conversation()

        # Update UI
        self._ai_panel.clear_conversation()

        # Save empty conversation
        self.state.save_conversation_to_file(str(DEFAULT_AI_CONVERSATION_FILE), self.console)

        self.notify("AI conversation cleared")

    def action_insights(self) -> None:
        """Show task insights in AI panel (i)"""
        if not self.state.tasks:
            self.notify("No tasks to analyze", severity="warning")
            return

        # Generate insights
        insights = LocalSuggestions.get_insights_summary(self.state)

        # Add to conversation as system message
        message = self.state.add_ai_message("assistant", f"📊 Task Insights:\n\n{insights}")

        # Update AI panel (with null check)
        if self._ai_panel:
            self._ai_panel.add_message(message)

            # Show AI panel if hidden
            if not self.ai_panel_visible:
                self.action_toggle_ai_panel()
        else:
            # Fallback: show in notification if panel unavailable
            self.notify("Insights generated (AI panel unavailable)", severity="information")

        self.notify("Insights generated")

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard with best-effort cross-platform support."""
        try:
            import sys, subprocess, shutil
            if sys.platform.startswith("win"):
                p = subprocess.run(["cmd", "/c", "clip"], input=text.encode("utf-16le"), capture_output=True)
                return p.returncode == 0
            elif sys.platform == "darwin":
                p = subprocess.run(["pbcopy"], input=text.encode("utf-8"), capture_output=True)
                return p.returncode == 0
            else:
                if shutil.which("xclip"):
                    p = subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), capture_output=True)
                    return p.returncode == 0
                if shutil.which("xsel"):
                    p = subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode("utf-8"), capture_output=True)
                    return p.returncode == 0
        except Exception:
            pass
        # Fallback to tkinter
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(text)
            r.update()
            r.destroy()
            return True
        except Exception:
            return False

    def action_copy_ai(self) -> None:
        """Copy the last AI message to the clipboard (Ctrl+Shift+Y)."""
        if not self._ai_panel or not self.state.ai_conversation:
            self.notify("No AI message to copy", severity="warning")
            return
        last = self.state.ai_conversation[-1]
        content = (last.content or "").strip()
        if not content:
            self.notify("AI message is empty", severity="warning")
            return
        ok = self._copy_to_clipboard(content)
        if ok:
            self.notify("AI message copied to clipboard", severity="information")
        else:
            self.notify("Clipboard not available on this system", severity="error")

    # REMOVED on_message() catch-all to test if it was interfering

    def on_ai_input_prompt_submitted(self, message: AIInput.PromptSubmitted) -> None:
        """Handle AI prompt submission"""
        # LOG: Show handler was called
        debug_log.debug(f"[STEP 3] Handler called with prompt: '{message.prompt[:50]}'")

        prompt = message.prompt

        if not prompt:
            debug_log.debug("[STEP 3] Empty prompt in handler, returning")
            return

        try:
            # LOG: Show panel visibility
            debug_log.debug(f"[STEP 4] AI panel visible: {self.ai_panel_visible}")

            # Show AI panel if hidden
            if not self.ai_panel_visible:
                debug_log.debug("[STEP 5] Toggling AI panel (was hidden)")
                self.action_toggle_ai_panel()
                debug_log.debug("[STEP 5] AI panel toggled successfully")

            # LOG: Creating user message
            debug_log.debug("[STEP 6] Creating user message object...")

            # Add user message to conversation
            user_message = self.state.add_ai_message("user", prompt)

            debug_log.debug(f"[STEP 7] User message created - ID: {user_message.timestamp}, Role: {user_message.role}")

            # LOG: Updating AI panel
            debug_log.debug("[STEP 8] Updating AI chat panel with user message...")

            # Update AI panel (with null check)
            if not self._ai_panel:
                debug_log.error("[STEP 8] AI panel reference is None!")
                self.notify("AI panel not available", severity="error")
                return

            debug_log.debug(f"[STEP 8] AI panel found: {type(self._ai_panel).__name__}")

            self._ai_panel.add_message(user_message)

            debug_log.debug("[STEP 9] AI panel updated successfully")

            # LOG: Starting worker
            debug_log.debug("[STEP 10] Starting streaming worker thread...")

            # Start streaming worker (pass ai_panel to avoid DOM query in worker thread)
            self.stream_ai_response(prompt, self._ai_panel)

            debug_log.debug("[STEP 11] Worker started successfully")

            # Keep short notification visible to user
            self.notify("AI processing...", timeout=2)

        except Exception as e:
            self.log.error(f"AI input error: {e}", exc_info=True)
            debug_log.error(f"[ERROR] AI input handler failed: {type(e).__name__}: {str(e)}", exception=e)
            self.notify(f"[ERROR] {type(e).__name__}: {str(e)[:50]}", severity="error", timeout=10)

    @work(exclusive=True, thread=True)
    async def stream_ai_response(self, user_prompt: str, ai_panel: AIChatPanel) -> None:
        """
        Stream AI response in background worker (async)
        MUST use call_from_thread() for ALL UI updates!

        Args:
            user_prompt: User's question/prompt
            ai_panel: AI chat panel widget (passed to avoid DOM query in worker thread)
        """
        # LOG: Worker thread started
        debug_log.debug(f"[STEP 12] Worker thread started for prompt: '{user_prompt[:50]}'")

        try:
            # Show streaming indicator
            debug_log.debug("[STEP 12] Showing streaming indicator...")
            self.call_from_thread(ai_panel.show_streaming_indicator)

            # Show initial status: Thinking
            debug_log.debug("[STEP 12] Adding 'Thinking...' status message...")
            self.call_from_thread(ai_panel.add_status_message, "🤔 Thinking...")

            # Initialize assistant (optional)
            debug_log.debug("[STEP 12] Initializing Assistant...")
            try:
                from assistant import Assistant  # type: ignore

                # Update status: Loading AI agent
                self.call_from_thread(ai_panel.update_status_message, "🧠 Loading AI agent...")

                assistant = Assistant(state=self.state)
                debug_log.debug(f"[STEP 12] Assistant initialized: {type(assistant).__name__}")
            except Exception as e:
                debug_log.warning(f"[STEP 12] Assistant unavailable: {e}")
                self.call_from_thread(ai_panel.remove_status_messages)
                self.call_from_thread(ai_panel.hide_streaming_indicator)
                self.call_from_thread(self.notify, "AI assistant not available", severity="warning")
                return

            # Get conversation context (last 20 messages)
            debug_log.debug("[STEP 12] Getting conversation context...")
            conversation_context = self.state.get_conversation_context(max_messages=20)
            debug_log.debug(f"[STEP 12] Context messages: {len(conversation_context)}")

            # Update status: Processing request
            self.call_from_thread(ai_panel.update_status_message, "⚡ Processing request...")

            # Create assistant message placeholder (on main thread)
            debug_log.debug("[STEP 12] Creating assistant message placeholder...")
            response_content = ""

            def create_message():
                """Create message on main thread"""
                msg = self.state.add_ai_message("assistant", "")
                ai_panel.add_message(msg)
                debug_log.debug(f"[STEP 12] Assistant message created: {msg.timestamp}")

            self.call_from_thread(create_message)

            # Use LangChain agent with streaming callback
            debug_log.debug("[STEP 12] Starting LangChain agent with streaming...")
            chunk_count = 0
            first_chunk = True  # Track first chunk to remove status messages

            def streaming_callback(chunk):
                """Streaming callback for agent responses"""
                nonlocal chunk_count, response_content, first_chunk
                chunk_count += 1
                response_content += chunk

                # Remove status messages on first chunk (response is starting)
                if first_chunk:
                    first_chunk = False
                    debug_log.debug("[STEP 12] First chunk received - removing status messages")
                    self.call_from_thread(ai_panel.remove_status_messages)

                # Log every 10th chunk
                if chunk_count % 10 == 0:
                    debug_log.debug(f"[STEP 12] Received {chunk_count} chunks, {len(response_content)} chars")

                # Update message content on main thread
                def update_content(text_chunk=chunk):
                    """Update message content safely"""
                    ai_panel.append_to_last_message(text_chunk)

                self.call_from_thread(update_content)

            # Call LangChain agent (uses tools if needed)
            response = assistant.ask(user_prompt, streaming_callback=streaming_callback)
            debug_log.debug(f"[STEP 12] Agent complete: {chunk_count} chunks, {len(response_content)} total chars")

            # Hide streaming indicator
            self.call_from_thread(ai_panel.hide_streaming_indicator)
            debug_log.debug("[STEP 12] Streaming indicator hidden")

            # Save conversation to file
            debug_log.debug("[STEP 12] Saving conversation to file...")
            self.call_from_thread(
                self.state.save_conversation_to_file,
                str(DEFAULT_AI_CONVERSATION_FILE),
                self.console
            )
            debug_log.debug("[STEP 12] Conversation saved")

            # Refresh table to sync UI with state (critical for AI tool changes)
            # Tools may have created/edited/deleted tasks - must update UI
            debug_log.debug("[STEP 12] Refreshing table to sync UI with state...")
            self.call_from_thread(self.refresh_table)
            debug_log.info("[STEP 12] Table refreshed - UI now synced with state")

            # Show completion notification
            self.call_from_thread(self.notify, "AI response complete")
            debug_log.debug("[STEP 12] Worker completed successfully")

        except Exception as e:
            debug_log.error(f"[STEP 12] Worker failed: {type(e).__name__}: {str(e)}", exception=e)

            # Remove status messages on error
            self.call_from_thread(ai_panel.remove_status_messages)

            # Hide streaming indicator
            self.call_from_thread(ai_panel.hide_streaming_indicator)

            # Show error
            error_msg = f"AI error: {str(e)}"
            self.call_from_thread(self.notify, error_msg, severity="error")

            # Add error to conversation
            error_message = self.state.add_ai_message("assistant", f"Error: {str(e)}")
            self.call_from_thread(ai_panel.add_message, error_message)

    def _handle_signal(self, signum: int) -> None:
        """
        Handle termination signals (SIGINT, SIGTERM) gracefully

        Called when user presses Ctrl+C or when process receives termination signal.
        Ensures tasks and conversation are saved before exit.

        Args:
            signum: Signal number (SIGINT=2, SIGTERM=15)
        """
        signal_name = signal.Signals(signum).name
        debug_log.info(f"[SIGNAL] Received {signal_name} (signal {signum}) - saving and exiting...")

        # Use action_quit to save and exit cleanly
        self.action_quit()

    def action_quit(self) -> None:
        """Save and quit"""
        debug_log.info("[APP] action_quit() called - saving tasks and conversation...")
        self.state.save_to_file(self.tasks_file, self.console)
        self.state.save_conversation_to_file(str(DEFAULT_AI_CONVERSATION_FILE), self.console)
        debug_log.info("[APP] Save complete - exiting application")
        self.exit()


# For testing: Run directly
if __name__ == "__main__":
    app = TodoTextualApp()
    app.run()
