"""
TaskEditPanel - Inline task editing panel (replaces TaskForm modal)

Enables creating/editing tasks with persistent AI chat access.
Implements dirty state tracking and validation.
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Input, Select, Label, Button
from textual.binding import Binding
from textual.reactive import reactive
from textual.validation import Length
from textual import work

from models.task import Task
from utils.tag_parser import parse_tags
from utils.validators import validate_task_name, sanitize_comment, sanitize_description, clamp_priority
from config import validation


class TaskEditPanel(VerticalScroll):
    """
    Inline task edit/create panel for left panel area

    Features:
        - Create new tasks or edit existing
        - Dirty state tracking (warns on unsaved changes)
        - Inline validation
        - AI chat remains accessible during editing

    Keybindings:
        Ctrl+S: Save task
        Esc: Cancel (warns if dirty)

    CRITICAL: Uses _task_data instead of _task (reserved by MessagePump)
    """

    DEFAULT_CSS = """
    TaskEditPanel {
        width: 100%;
        height: 1fr;
        border: solid #404040;
        background: $surface;
        padding: 0 1;
    }

    TaskEditPanel:focus-within {
        border: solid #ffdb7a;
    }

    TaskEditPanel Static.error {
        color: red;
        width: 100%;
        height: auto;
        padding: 0;
    }

    TaskEditPanel Static.label {
        width: 6;
        content-align: right middle;
        padding: 0 1 0 0;
        color: cyan;
        text-style: bold;
    }

    TaskEditPanel .field-row {
        width: 100%;
        height: auto;
        margin: 0;
    }

    TaskEditPanel Input {
        width: 1fr;
        border: solid #404040;
        background: $surface;
    }

    TaskEditPanel Input:focus {
        border: solid #ffdb7a;
        background: $panel;
    }

    TaskEditPanel Select {
        width: 1fr;
        border: solid #404040;
    }

    TaskEditPanel Select:focus {
        border: solid #ffdb7a;
    }

    TaskEditPanel Static.hint {
        color: $text-muted;
        width: 100%;
        height: auto;
        padding: 0 0 0 7;
    }

    TaskEditPanel Static.hint-main {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 0;
    }

    TaskEditPanel Static.dirty-indicator {
        color: #ffdb7a;
        width: 100%;
        text-align: center;
        padding: 0;
    }

    TaskEditPanel Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0;
    }

    TaskEditPanel Button {
        margin: 0 1;
        min-width: 14;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    # Reactive dirty flag
    is_dirty = reactive(False)

    def __init__(
        self,
        task_data: Task | None = None,
        is_new: bool = False,
        existing_tags: list[str] | None = None,
        **kwargs
    ):
        """
        Initialize task edit panel

        Args:
            task_data: Task to edit (None for new task)
            is_new: True if creating new task
            existing_tags: List of existing tags for suggestions
            **kwargs: Additional widget arguments

        CRITICAL: Uses _task_data instead of _task (reserved attribute)
        """
        super().__init__(**kwargs)
        self._task_data = task_data  # NOT _task - reserved by MessagePump!
        self._is_new = is_new
        self.existing_tags = existing_tags or []
        self._original_values = {}  # For dirty tracking

        # Set border title
        if is_new:
            self.border_title = "Create New Task"
        else:
            self.border_title = f"Edit Task #{task_data.id}"

    def compose(self) -> ComposeResult:
        """Compose the edit form"""
        yield Static("", id="error_message", classes="error")
        yield Static("", id="dirty_indicator", classes="dirty-indicator")

        # Name field (required)
        with Horizontal(classes="field-row"):
            yield Static("Name:", classes="label")
            yield Input(
                placeholder="Task name (required)",
                value=self._task_data.name if self._task_data else "",
                id="name_input",
                validators=[
                    Length(
                        minimum=validation.MIN_TASK_NAME_LENGTH,
                        maximum=validation.MAX_TASK_NAME_LENGTH,
                    )
                ]
            )

        # Priority (select dropdown)
        with Horizontal(classes="field-row"):
            yield Static("Prior:", classes="label")
            priority_value = str(self._task_data.priority) if self._task_data else "2"
            yield Select(
                options=[
                    ("🔴 High (1)", "1"),
                    ("🟡 Medium (2)", "2"),
                    ("🟢 Low (3)", "3"),
                ],
                value=priority_value,
                id="priority_select",
            )

        # Tags (comma-separated)
        with Horizontal(classes="field-row"):
            yield Static("Tags:", classes="label")
            tags_value = ", ".join(self._task_data.tags) if self._task_data else ""
            yield Input(
                placeholder="tag1, tag2, tag3",
                value=tags_value,
                id="tags_input",
            )

        # Comment field (optional)
        with Horizontal(classes="field-row"):
            yield Static("Note:", classes="label")
            yield Input(
                placeholder="Short comment (optional)",
                value=self._task_data.comment if self._task_data else "",
                id="comment_input",
            )

        # Description field (optional)
        with Horizontal(classes="field-row"):
            yield Static("Desc:", classes="label")
            yield Input(
                placeholder="Detailed description (optional)",
                value=self._task_data.description if self._task_data else "",
                id="description_input",
            )

        # Hints
        yield Static("[dim]Ctrl+S to Save | Esc to Cancel[/dim]", classes="hint-main")

        # Action buttons
        with Horizontal(classes="buttons"):
            yield Button("💾 Save (Ctrl+S)", variant="primary", id="save_btn")
            yield Button("❌ Cancel (Esc)", variant="default", id="cancel_btn")

    def on_mount(self) -> None:
        """Focus name input and capture original values"""
        self.query_one("#name_input", Input).focus()
        self._capture_original_values()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        from debug_logger import debug_log

        debug_log.info(f"[TASK_EDIT] ✅ Button pressed: {event.button.id}")

        if event.button.id == "save_btn":
            debug_log.info("[TASK_EDIT] → Calling action_save()")
            self.action_save()
            event.stop()
        elif event.button.id == "cancel_btn":
            debug_log.info("[TASK_EDIT] → Calling action_cancel()")
            # action_cancel is @work decorated, so calling it directly creates the worker
            self.action_cancel()
            event.stop()

    def _capture_original_values(self) -> None:
        """Store original values for dirty tracking"""
        try:
            self._original_values = {
                "name": self.query_one("#name_input", Input).value,
                "comment": self.query_one("#comment_input", Input).value,
                "description": self.query_one("#description_input", Input).value,
                "priority": self.query_one("#priority_select", Select).value,
                "tags": self.query_one("#tags_input", Input).value,
            }
        except Exception:
            self._original_values = {}

    def on_input_changed(self, event: Input.Changed) -> None:
        """Mark dirty when any input changes"""
        self._check_dirty_state()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Mark dirty when select changes"""
        self._check_dirty_state()

    def _check_dirty_state(self) -> bool:
        """Check if form has unsaved changes"""
        try:
            current = {
                "name": self.query_one("#name_input", Input).value,
                "comment": self.query_one("#comment_input", Input).value,
                "description": self.query_one("#description_input", Input).value,
                "priority": self.query_one("#priority_select", Select).value,
                "tags": self.query_one("#tags_input", Input).value,
            }

            # Compare with original
            is_changed = any(
                current[key] != self._original_values.get(key, "")
                for key in current
            )

            self.is_dirty = is_changed

            # Update dirty indicator
            dirty_indicator = self.query_one("#dirty_indicator", Static)
            if is_changed:
                dirty_indicator.update("[yellow]● Unsaved changes[/yellow]")
            else:
                dirty_indicator.update("")

            return is_changed

        except Exception:
            return False

    def action_save(self) -> None:
        """Validate and save task (Ctrl+S)"""
        from debug_logger import debug_log

        debug_log.info("[TASK_EDIT] 💾 action_save() called")

        # Get field values
        name = self.query_one("#name_input", Input).value.strip()
        comment = self.query_one("#comment_input", Input).value.strip()
        description = self.query_one("#description_input", Input).value.strip()
        priority_str = self.query_one("#priority_select", Select).value
        tags_str = self.query_one("#tags_input", Input).value.strip()

        # Clear previous errors
        error_msg = self.query_one("#error_message", Static)
        error_msg.update("")

        # Validate task name
        is_valid, error = validate_task_name(name)
        if not is_valid:
            error_msg.update(f"❌ {error}")
            self.query_one("#name_input", Input).focus()
            return

        # Parse priority
        try:
            priority = int(priority_str) if priority_str else 2
            priority = clamp_priority(priority)
        except ValueError:
            priority = 2

        # Parse tags
        tag_list = parse_tags(tags_str) if tags_str else []

        # Sanitize inputs
        comment = sanitize_comment(comment)
        description = sanitize_description(description)

        # Build result dict
        data = {
            "name": name,
            "comment": comment,
            "description": description,
            "priority": priority,
            "tag": tag_list[0] if tag_list else "",  # Legacy field
            "tags": tag_list,  # New field
        }

        # Save via state
        if self._is_new:
            self.app.state.add_task(**data)
            self.app.notify(f"Task created: {name}", severity="success")
            debug_log.info(f"[TASK_EDIT] ✅ Task created: {name}")
        else:
            # Update existing task
            task = self._task_data
            task.name = name
            task.comment = comment
            task.description = description
            task.priority = priority
            task.tags = tag_list
            task.tag = tag_list[0] if tag_list else ""

            # Update timestamp
            from datetime import datetime
            task.updated_at = datetime.now().isoformat()

            # Invalidate filter cache
            self.app.state.invalidate_filter_cache()

            self.app.notify(f"Task #{task.id} updated", severity="success")
            debug_log.info(f"[TASK_EDIT] ✅ Task #{task.id} updated: {name}")

        # Return to list view
        from core.state import LeftPanelMode
        self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
        # Also update app reactive property so watcher triggers panel switch
        try:
            self.app.left_panel_mode = LeftPanelMode.LIST_TASKS
        except Exception:
            pass
        try:
            current_mode = getattr(self.app._left_panel_container, "current_mode", None)
            debug_log.info(f"[TASK_EDIT] -> Switched to LIST_TASKS (state+app). container_current_mode={current_mode}")
        except Exception:
            debug_log.info("[TASK_EDIT] -> Switched to LIST_TASKS (state+app)")
        self.app.refresh_table()

        # Save to file
        self.app.state.save_to_file(self.app.tasks_file, self.app.console)

    @work(exclusive=True)
    async def action_cancel(self) -> None:
        """Cancel editing with dirty check (Esc)"""
        from core.state import LeftPanelMode
        from debug_logger import debug_log

        # Check if dirty
        if self.is_dirty:
            from textual_widgets.confirm_dialog import ConfirmDialog

            confirmed = await self.app.push_screen_wait(
                ConfirmDialog("Discard unsaved changes?")
            )

            if not confirmed:
                return

        # Navigation after cancel:
        # - If creating new: go to LIST (table)
        # - If editing existing: go to DETAIL (stay on selected item)
        if self._is_new:
            self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
            try:
                self.app.left_panel_mode = LeftPanelMode.LIST_TASKS
            except Exception:
                pass
            debug_log.info("[TASK_EDIT] -> Cancel (new): LIST_TASKS (state+app)")
        else:
            self.app.state.left_panel_mode = LeftPanelMode.DETAIL_TASK
            try:
                self.app.left_panel_mode = LeftPanelMode.DETAIL_TASK
            except Exception:
                pass
            debug_log.info("[TASK_EDIT] -> Cancel (edit): DETAIL_TASK (state+app)")

        # Refresh table to show current state
        if hasattr(self.app, 'refresh_table'):
            self.app.refresh_table()

    def on_key(self, event) -> None:
        """Intercept Esc to prevent bubbling to next view after mode switch."""
        if getattr(event, "key", "") == "escape":
            try:
                from debug_logger import debug_log
                debug_log.info("[TASK_EDIT] Esc intercepted -> invoking action_cancel() and consuming event")
            except Exception:
                pass
            # Invoke cancel and consume
            try:
                self.action_cancel()
            except Exception:
                pass
            try:
                event.stop(); event.prevent_default()
            except Exception:
                pass
            return
        try:
            return super().on_key(event)
        except Exception:
            return
