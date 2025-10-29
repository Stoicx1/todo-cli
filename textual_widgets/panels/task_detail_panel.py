"""
TaskDetailPanel - View-only task detail panel (replaces TaskDetailModal)

Displays task information in the left panel area without blocking AI chat access.
Uses vim-inspired keybindings for navigation.
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import Static, Button
from textual.binding import Binding
from textual import work

from models.task import Task
from config import USE_UNICODE


class TaskDetailPanel(VerticalScroll):
    """
    Read-only task detail panel for left panel area

    Keybindings:
        Esc: Return to task list
        e/i: Switch to edit mode (vim-inspired)
        d: Delete task (with confirmation)

    CRITICAL: Uses _task_data instead of _task (reserved by MessagePump)
    """

    DEFAULT_CSS = """
    TaskDetailPanel {
        width: 100%;
        height: 1fr;
        border: solid #404040;
        background: $surface;
        padding: 0 1;
    }

    TaskDetailPanel:focus {
        border: solid #ffdb7a;
    }

    TaskDetailPanel Static.field-label {
        color: cyan;
        text-style: bold;
        padding: 0;
    }

    TaskDetailPanel Static.field-value {
        padding: 0 0 0 2;
    }

    TaskDetailPanel Static.divider {
        width: 100%;
        color: $text-muted;
        padding: 0;
    }

    TaskDetailPanel Static.hint {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 0;
        text-style: italic;
    }

    TaskDetailPanel Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 0;
    }

    TaskDetailPanel Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS = [
        Binding("escape", "back_to_list", "Back to List", priority=True),
        Binding("e", "edit_task", "Edit", show=True),
        Binding("i", "edit_task", "Edit (vim)", show=False),  # vim-inspired
        Binding("d", "delete_task", "Delete", show=True),
    ]

    def __init__(self, task_data: Task, **kwargs):
        """
        Initialize task detail panel

        Args:
            task_data: Task object to display
            **kwargs: Additional widget arguments

        CRITICAL: Uses _task_data instead of _task (reserved attribute)
        """
        super().__init__(**kwargs)
        self._task_data = task_data  # NOT _task - reserved by MessagePump!

        # Set border title
        self.border_title = f"Task #{task_data.id}"

    def compose(self) -> ComposeResult:
        """Compose the task detail view"""
        # Icons and formatting
        status_icon = ("✔" if USE_UNICODE else "+") if self._task_data.done else ("✗" if USE_UNICODE else "-")
        divider = ("─" * 60) if USE_UNICODE else ("-" * 60)
        tag_icon = "#"

        # Status text with color
        status_text = (
            f"[bold green]{status_icon} DONE[/bold green]"
            if self._task_data.done
            else f"[bold yellow]{status_icon} TODO[/bold yellow]"
        )

        # Priority display
        priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
        priority_label = priority_labels.get(self._task_data.priority, "?")
        priority_colors = {1: "red", 2: "yellow", 3: "green"}
        priority_color = priority_colors.get(self._task_data.priority, "white")
        priority_display = f"[{priority_color}]{priority_label}[/{priority_color}]"

        # Task name + status
        yield Static(
            f"[bold white]{self._task_data.name}[/bold white]  {status_text}",
            classes="field-value"
        )

        # Priority
        yield Static("[bold cyan]Priority:[/bold cyan]", classes="field-label")
        yield Static(f"  {priority_display}", classes="field-value")

        # Tags
        if self._task_data.tags:
            tags_display = ", ".join([f"[cyan]{t}[/cyan]" for t in self._task_data.tags])
            yield Static("[bold cyan]Tags:[/bold cyan]", classes="field-label")
            yield Static(f"  {tag_icon} {tags_display}", classes="field-value")

        # Comment
        if self._task_data.comment:
            yield Static("[bold cyan]Comment:[/bold cyan]", classes="field-label")
            yield Static(f"  [dim]{self._task_data.comment}[/dim]", classes="field-value")

        # Description
        if self._task_data.description:
            yield Static("[bold cyan]Description:[/bold cyan]", classes="field-label")
            yield Static(
                f"  [dim italic]{self._task_data.description}[/dim italic]",
                classes="field-value"
            )

        # Divider
        yield Static(f"[dim]{divider}[/dim]", classes="divider")

        # Timestamps (relative times)
        from core.commands import get_relative_time
        if self._task_data.created_at:
            yield Static(
                f"[dim]Created {get_relative_time(self._task_data.created_at)}[/dim]",
                classes="field-value"
            )
        if getattr(self._task_data, "updated_at", ""):
            yield Static(
                f"[dim]Updated {get_relative_time(self._task_data.updated_at)}[/dim]",
                classes="field-value"
            )
        if self._task_data.done and self._task_data.completed_at:
            yield Static(
                f"[dim]Completed {get_relative_time(self._task_data.completed_at)}[/dim]",
                classes="field-value"
            )

        # Hint + Buttons
        yield Static("[dim]E to Edit | Esc to go Back | D to Delete[/dim]", classes="hint")
        with Horizontal(classes="buttons"):
            yield Button("Edit (E)", variant="primary", id="edit_btn")
            yield Button("Back (Esc)", variant="default", id="back_btn")
            yield Button("Delete (D)", variant="error", id="delete_btn")

    def on_mount(self) -> None:
        """Focus the panel on mount"""
        self.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "edit_btn":
            self.action_edit_task()
        elif event.button.id == "back_btn":
            self.action_back_to_list()
        elif event.button.id == "delete_btn":
            self.action_delete_task()

    def action_back_to_list(self) -> None:
        """Return to task list (Esc)"""
        from core.state import LeftPanelMode
        self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS

    def action_edit_task(self) -> None:
        """Switch to edit mode (e or i)"""
        from core.state import LeftPanelMode
        self.app.state.edit_mode_is_new = False
        self.app.state.left_panel_mode = LeftPanelMode.EDIT_TASK

    @work(exclusive=True)
    async def action_delete_task(self) -> None:
        """Delete task with confirmation (d)"""
        from textual_widgets.confirm_dialog import ConfirmDialog

        # Show confirmation dialog
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(
                f"Delete task #{self._task_data.id}: {self._task_data.name}?"
            )
        )

        if confirmed:
            # Remove from state
            self.app.state.remove_task(self._task_data)
            self.app.notify(f"Task #{self._task_data.id} deleted", severity="information")

            # Return to list
            from core.state import LeftPanelMode
            self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
            self.app.refresh_table()
