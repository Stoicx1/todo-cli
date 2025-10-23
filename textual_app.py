"""
Textual TUI Application for Todo CLI
Modern reactive terminal user interface
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from textual import work

from core.state import AppState
from core.commands import handle_command
from core.suggestions import LocalSuggestions
from assistant import Assistant
from textual_widgets.task_table import TaskTable
from textual_widgets.status_bar import StatusBar
from textual_widgets.command_input import CommandInput
from textual_widgets.task_form import TaskForm
from textual_widgets.confirm_dialog import ConfirmDialog
from textual_widgets.ai_chat_panel import AIChatPanel
from textual_widgets.ai_input import AIInput
from textual_widgets.task_detail_modal import TaskDetailModal
from config import DEFAULT_TASKS_FILE, DEFAULT_AI_CONVERSATION_FILE
from debug_logger import debug_log


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

    # CSS_PATH = "styles/main.tcss"  # Temporarily disabled - using inline CSS

    CSS = """
    /* Color Palette */
    $primary: #0891b2;
    $secondary: #06b6d4;
    $surface: #1e293b;
    $panel: #334155;
    $background: #0f172a;
    $text: #f1f5f9;
    $text-muted: #94a3b8;

    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
        height: 3;
        content-align: center middle;
    }

    Header .header--title {
        color: $text;
        text-style: bold;
    }

    Footer {
        background: $primary;
        color: $text;
    }

    /* Data Table */
    DataTable {
        height: 1fr;
        border: solid cyan;
        background: $surface;
    }

    DataTable > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $secondary;
        color: $text;
    }

    DataTable:focus > .datatable--cursor {
        background: cyan 20%;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--odd-row {
        background: $surface;
    }

    DataTable > .datatable--even-row {
        background: $panel;
    }

    /* Status Bar */
    StatusBar {
        height: 5;
        min-height: 5;
        border: solid cyan;
        background: $panel;
        padding: 0 2;
        content-align: left top;
    }

    /* Buttons */
    Button {
        width: auto;
        min-width: 12;
        height: 3;
        border: solid cyan;
        background: $panel;
        color: $text;
    }

    Button:hover {
        background: cyan 20%;
        border: solid cyan;
    }

    Button:focus {
        background: cyan;
        color: $background;
        text-style: bold;
    }

    /* Input Fields */
    Input {
        border: solid cyan;
        background: $surface;
        color: $text;
    }

    Input:focus {
        border: solid cyan;
        background: $panel;
    }

    /* Command Input */
    #command_input {
        height: 3;
        border: solid cyan;
        background: $panel;
        /* dock: bottom; removed - let it position naturally to avoid overlap with ai_input */
        margin: 0 0 1 0;
    }

    #command_input:focus {
        border: solid yellow;  /* Clear focus indicator - changed from cyan */
        background: $surface;
    }

    /* Modal Screens */
    ModalScreen {
        background: #000000 70%;
    }

    TaskForm Input.-invalid {
        border: solid red;
    }

    TaskForm Select {
        border: solid cyan;
    }

    ConfirmDialog Button#confirm {
        background: red 30%;
        color: white;
    }

    ConfirmDialog Button#confirm:hover {
        background: red;
    }

    ConfirmDialog Button#cancel {
        background: cyan 30%;
    }

    ConfirmDialog Button#cancel:hover {
        background: cyan;
    }

    /* Main Layout */
    #app_layout {
        height: 1fr;
        layout: vertical;
    }

    #main_container {
        height: 1fr;
        layout: horizontal;
    }

    #task_container {
        width: 70%;
        layout: vertical;
    }

    #bottom_section {
        height: 16;
        layout: vertical;
    }

    /* AI Chat Panel */
    #ai_chat_panel {
        width: 30%;
        border: solid cyan;
        background: $panel;
        padding: 1;
    }

    #ai_chat_panel .empty-state {
        color: $text-muted;
        text-align: center;
        padding: 2;
    }

    MessageBubble {
        padding: 1 2;
        margin: 1 0;
        border: solid #94a3b8;
        background: $surface;
        color: $text;
    }

    MessageBubble.user-message {
        border: solid cyan;
        background: cyan 10%;
    }

    MessageBubble.ai-message {
        border: solid cyan;
        background: cyan 10%;
    }

    /* AI Input */
    #ai_input {
        height: 3;
        border: solid cyan;
        background: $panel;
        margin: 1 0;
    }

    #ai_input:focus {
        border: solid cyan;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+k", "toggle_command_mode", "Command", show=True),
        Binding("a", "add_task", "Add Task"),
        Binding("e", "edit_task", "Edit"),
        Binding("x", "mark_done", "Done"),
        Binding("u", "mark_undone", "Undone"),
        Binding("d", "delete_task", "Delete"),
        Binding("f", "filter_tasks", "Filter"),
        Binding("s", "sort_tasks", "Sort"),
        Binding("n", "next_page", "Next Page"),
        Binding("p", "prev_page", "Prev Page"),
        Binding("v", "toggle_view", "View"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "ask_ai", "Ask AI", show=True),
        Binding("ctrl+a", "toggle_ai_panel", "Toggle AI", show=True),
        Binding("ctrl+shift+c", "clear_ai", "Clear AI"),
        Binding("i", "insights", "Insights"),
    ]

    # Reactive attributes (auto-update UI when changed)
    tasks_count = reactive(0)
    page_number = reactive(0)
    filter_text = reactive("none")
    command_mode = reactive(False)  # Toggle command input visibility
    ai_panel_visible = reactive(True)  # AI chat panel visibility

    def __init__(self, tasks_file: str = DEFAULT_TASKS_FILE):
        """
        Initialize Textual Todo App

        Args:
            tasks_file: Path to tasks JSON file
        """
        super().__init__()
        self.tasks_file = tasks_file
        self.state = AppState()
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
            - Left (70%): TaskTable (main content)
            - Right (30%): AI Chat Panel (sidebar, collapsible)
          - Bottom section (fixed height):
            - StatusBar (stats and info)
            - CommandInput (command line, toggled with Ctrl+K)
            - AIInput (AI prompt input, always visible when AI panel shown)
        - Footer (keyboard shortcuts)
        """
        yield Header(show_clock=True)

        # Main vertical layout containing all content
        with Vertical(id="app_layout"):
            # Content area with horizontal split (takes remaining space)
            with Horizontal(id="main_container"):
                # Left side: Task table (70%)
                with Vertical(id="task_container"):
                    yield TaskTable(id="task_table")

                # Right side: AI chat panel (30%, collapsible)
                yield AIChatPanel(self.state, id="ai_chat_panel")

            # Bottom section with fixed heights (StatusBar + inputs)
            with Vertical(id="bottom_section"):
                yield StatusBar(id="status_bar")
                yield CommandInput(id="command_input")
                yield AIInput(id="ai_input")

        yield Footer()

    def on_mount(self) -> None:
        """
        Called when app is mounted (startup)
        Load tasks and populate table
        """
        debug_log.debug("App on_mount() called - app is starting up")

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
        self.state.load_from_file(self.tasks_file, self.console)

        # Load AI conversation history
        self.state.load_conversation_from_file(str(DEFAULT_AI_CONVERSATION_FILE), self.console)

        # Populate table
        self.refresh_table()

        # Populate AI chat panel with error handling
        try:
            ai_panel = self.query_one(AIChatPanel)
            ai_panel.update_from_state()
        except Exception as e:
            self.log.error(f"Failed to initialize AI panel: {e}", exc_info=True)
            debug_log.error(f"AI panel initialization failed: {e}", exception=e)
            ai_panel = None

        # Update reactive attributes
        self.tasks_count = len(self.state.tasks)
        self.page_number = self.state.page

        # Cache widget references with error boundaries
        try:
            self._task_table = self.query_one(TaskTable)
            self._status_bar = self.query_one(StatusBar)
            self._command_input = self.query_one(CommandInput)
            self._ai_panel = ai_panel  # May be None if initialization failed
            self._ai_input = self.query_one(AIInput)

            debug_log.debug("Widget references cached successfully")

        except Exception as e:
            # Critical error - widgets not found during mount
            self.log.error(f"CRITICAL: Failed to cache widget references: {e}", exc_info=True)
            debug_log.error(f"Widget caching failed: {e}", exception=e)

            # Set fallback values to prevent AttributeError later
            if not hasattr(self, '_task_table'):
                self._task_table = None
            if not hasattr(self, '_status_bar'):
                self._status_bar = None
            if not hasattr(self, '_command_input'):
                self._command_input = None
            if not hasattr(self, '_ai_panel'):
                self._ai_panel = None
            if not hasattr(self, '_ai_input'):
                self._ai_input = None

            # Notify user of critical error
            self.notify(
                "Critical error initializing widgets. Some features may not work.",
                severity="error",
                timeout=10
            )

        # Show command input by default (toggle with Ctrl+K)
        if self._command_input:
            self._command_input.display = True
            self.command_mode = True

        # Show AI panel initially
        if self._ai_panel:
            self._ai_panel.display = self.ai_panel_visible

        # Set initial focus to table
        if self._task_table:
            self._task_table.focus()

    def refresh_table(self) -> None:
        """
        Refresh task table with current state
        Called whenever tasks/filters/sort changes

        Includes error boundaries to handle widget reference failures gracefully.
        """
        # Use cached widget references with null checks (safety)
        try:
            if self._task_table:
                self._task_table.update_from_state(self.state)
            else:
                self.log.warning("Task table reference is None, skipping update")

            if self._status_bar:
                self._status_bar.update_from_state(self.state)
            else:
                self.log.warning("Status bar reference is None, skipping update")

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

        # Route form commands to action methods (UX unification)
        if cmd in ("add", "a"):
            self.action_add_task()
            return

        if cmd in ("edit", "e"):
            # Parse task ID if provided: "edit 5"
            if len(parts) >= 2:
                try:
                    task_id = int(parts[1])
                    if self._task_table.select_task_by_id(task_id):
                        self.action_edit_task()
                    else:
                        self.notify(f"Task #{task_id} not found", severity="error")
                except ValueError:
                    self.notify("Invalid task ID - must be a number", severity="error")
            else:
                # No task ID provided, use current selection
                self.action_edit_task()
            return

        if cmd in ("show", "s"):
            # Parse task ID: "show 5"
            if len(parts) >= 2:
                try:
                    task_id = int(parts[1])
                    self.action_show_task(task_id)
                except ValueError:
                    # Not a number - could be a filter expression, let handle_command handle it
                    pass
            else:
                # No task ID provided, use current selection
                task_id = self._task_table.get_selected_task_id()
                if task_id is not None:
                    self.action_show_task(task_id)
                else:
                    self.notify("No task selected - use 'show <id>' or select a task", severity="warning")
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

            # Refresh UI
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

    @work(exclusive=True)
    async def action_add_task(self) -> None:
        """Show add task modal form (runs as worker to support modal dialog)"""
        # Get existing tags for suggestions
        existing_tags = list(self.state._tag_index.keys()) if self.state._tag_index else []

        # Show form modal
        result = await self.push_screen_wait(TaskForm(existing_tags=existing_tags))

        if result:
            # Add task to state
            self.state.add_task(
                name=result["name"],
                comment=result.get("comment", ""),
                description=result.get("description", ""),
                priority=result.get("priority", 2),
                tag=result.get("tag", "")
            )

            # Refresh UI
            self.refresh_table()
            self.notify(f"✓ Task '{result['name'][:30]}...' added", severity="information")

    @work(exclusive=True)
    async def action_edit_task(self) -> None:
        """Show edit task modal form (runs as worker to support modal dialog)"""
        task_id = self._task_table.get_selected_task_id()

        if task_id is None:
            self.notify("No task selected", severity="warning")
            return

        task = self.state.get_task_by_id(task_id)
        if not task:
            self.notify(f"Task #{task_id} not found", severity="error")
            return

        # Get existing tags for suggestions
        existing_tags = list(self.state._tag_index.keys()) if self.state._tag_index else []

        # Show form modal with pre-filled data
        result = await self.push_screen_wait(TaskForm(task=task, existing_tags=existing_tags))

        if result:
            # Store old tags for index update
            old_tags = task.tags.copy()

            # Update task
            task.name = result["name"]
            task.comment = result.get("comment", "")
            task.description = result.get("description", "")
            task.priority = result.get("priority", 2)
            task.tag = result.get("tag", "")
            task.tags = result.get("tags", [])

            # Update indices
            if self.state._task_index is not None:
                self.state._task_index[task.id] = task

            if task.tags != old_tags:
                self.state._update_tag_index_for_task(task, old_tags)

            # Refresh UI
            self.refresh_table()
            self.notify(f"✓ Task #{task_id} updated", severity="information")

    @work(exclusive=True)
    async def action_show_task(self, task_id: int) -> None:
        """
        Show task details modal with edit option

        Args:
            task_id: ID of task to display
        """
        task = self.state.get_task_by_id(task_id)
        if not task:
            self.notify(f"Task #{task_id} not found", severity="error")
            return

        # Show task detail modal
        action = await self.push_screen_wait(TaskDetailModal(task))

        # If user wants to edit, open the edit form
        if action == "edit":
            # Get existing tags for suggestions
            existing_tags = list(self.state._tag_index.keys()) if self.state._tag_index else []

            # Show form modal with pre-filled data
            result = await self.push_screen_wait(TaskForm(task=task, existing_tags=existing_tags))

            if result:
                # Store old tags for index update
                old_tags = task.tags.copy()

                # Update task
                task.name = result["name"]
                task.comment = result.get("comment", "")
                task.description = result.get("description", "")
                task.priority = result.get("priority", 2)
                task.tag = result.get("tag", "")
                task.tags = result.get("tags", [])

                # Update indices
                if self.state._task_index is not None:
                    self.state._task_index[task.id] = task

                if task.tags != old_tags:
                    self.state._update_tag_index_for_task(task, old_tags)

                # Refresh UI
                self.refresh_table()
                self.notify(f"✓ Task #{task_id} updated", severity="information")

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
        filtered_tasks = self.state.get_filter_tasks(self.state.tasks)
        total_pages = (len(filtered_tasks) + self.state.page_size - 1) // self.state.page_size

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

    def action_toggle_ai_panel(self) -> None:
        """Toggle AI chat panel visibility (Ctrl+A)"""
        if not self._ai_panel or not self._ai_input:
            self.notify("AI panel not available", severity="warning")
            return

        self.ai_panel_visible = not self.ai_panel_visible
        self._ai_panel.display = self.ai_panel_visible
        self._ai_input.display = self.ai_panel_visible

        if self.ai_panel_visible:
            self.notify("AI panel shown")
        else:
            self.notify("AI panel hidden")

    def action_ask_ai(self) -> None:
        """Focus AI input field and prompt for question (?)"""
        if not self.ai_panel_visible:
            # Show AI panel first
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

            # Initialize assistant
            debug_log.debug("[STEP 12] Initializing Assistant...")
            assistant = Assistant()
            debug_log.debug(f"[STEP 12] Assistant initialized: {type(assistant).__name__}")

            # Get conversation context (last 20 messages)
            debug_log.debug("[STEP 12] Getting conversation context...")
            conversation_context = self.state.get_conversation_context(max_messages=20)
            debug_log.debug(f"[STEP 12] Context messages: {len(conversation_context)}")

            # Create assistant message placeholder (on main thread)
            debug_log.debug("[STEP 12] Creating assistant message placeholder...")
            response_content = ""

            def create_message():
                """Create message on main thread"""
                msg = self.state.add_ai_message("assistant", "")
                ai_panel.add_message(msg)
                debug_log.debug(f"[STEP 12] Assistant message created: {msg.timestamp}")

            self.call_from_thread(create_message)

            # Stream response chunks
            debug_log.debug("[STEP 12] Starting stream from OpenAI API...")
            chunk_count = 0

            for chunk in assistant.stream_with_context(
                self.state.tasks,
                user_prompt,
                conversation_context
            ):
                chunk_count += 1
                response_content += chunk

                # Log every 10th chunk
                if chunk_count % 10 == 0:
                    debug_log.debug(f"[STEP 12] Received {chunk_count} chunks, {len(response_content)} chars")

                # Update message content on main thread
                def update_content(text_chunk=chunk):
                    """Update message content safely"""
                    ai_panel.append_to_last_message(text_chunk)

                self.call_from_thread(update_content)

            debug_log.debug(f"[STEP 12] Stream complete: {chunk_count} chunks, {len(response_content)} total chars")

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

            # Show completion notification
            self.call_from_thread(self.notify, "AI response complete")
            debug_log.debug("[STEP 12] Worker completed successfully")

        except Exception as e:
            debug_log.error(f"[STEP 12] Worker failed: {type(e).__name__}: {str(e)}", exception=e)

            # Hide streaming indicator
            self.call_from_thread(ai_panel.hide_streaming_indicator)

            # Show error
            error_msg = f"AI error: {str(e)}"
            self.call_from_thread(self.notify, error_msg, severity="error")

            # Add error to conversation
            error_message = self.state.add_ai_message("assistant", f"Error: {str(e)}")
            self.call_from_thread(ai_panel.add_message, error_message)

    def action_quit(self) -> None:
        """Save and quit"""
        self.state.save_to_file(self.tasks_file, self.console)
        self.state.save_conversation_to_file(str(DEFAULT_AI_CONVERSATION_FILE), self.console)
        self.exit()


# For testing: Run directly
if __name__ == "__main__":
    app = TodoTextualApp()
    app.run()
