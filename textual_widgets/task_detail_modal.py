"""
TaskDetailModal - Modal for displaying task details with edit option
"""

from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Button
from textual.app import ComposeResult

from models.task import Task
from config import USE_UNICODE


class TaskDetailModal(ModalScreen[str | None]):
    """
    Modal for displaying task details with edit/close options

    Returns 'edit' if user wants to edit, None if cancelled
    """

    DEFAULT_CSS = """
    TaskDetailModal {
        align: center middle;
    }

    TaskDetailModal > Container {
        width: 70;
        max-width: 90;
        height: auto;
        max-height: 90%;
        border: thick cyan;
        background: $surface;
        padding: 1 2;
    }

    TaskDetailModal Static.title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: cyan;
        padding: 0 0 1 0;
    }

    TaskDetailModal ScrollableContainer {
        width: 100%;
        height: auto;
        max-height: 30;
        border: none;
        padding: 1 0;
    }

    TaskDetailModal Static.content {
        width: 100%;
        height: auto;
    }

    TaskDetailModal Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }

    TaskDetailModal Button {
        margin: 0 1;
        min-width: 12;
    }

    TaskDetailModal Static.hint {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 1 0 0 0;
        text-style: italic;
    }

    TaskDetailModal Static.field-label {
        color: cyan;
        text-style: bold;
        padding: 0 0 0 0;
    }

    TaskDetailModal Static.field-value {
        padding: 0 0 1 2;
    }

    TaskDetailModal Static.divider {
        width: 100%;
        color: $text-muted;
        padding: 1 0;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Close"),
        ("e", "edit", "Edit"),
    ]

    def __init__(self, task: Task, **kwargs):
        """
        Initialize task detail modal

        Args:
            task: Task object to display
        """
        super().__init__(**kwargs)
        self._task_data = task

    def compose(self) -> ComposeResult:
        """Compose the modal layout"""
        # Icons and emojis with ASCII fallback
        if USE_UNICODE:
            status_icon = ("✔" if USE_UNICODE else "+") if self._task_data.done else ("✗" if USE_UNICODE else "-")
            priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
            priority_label = priority_labels.get(self._task_data.priority, "?")
            tag_icon = "#"
            divider = ("─" * 60) if USE_UNICODE else ("-" * 60)
        else:
            status_icon = ("✔" if USE_UNICODE else "+") if self._task_data.done else ("✗" if USE_UNICODE else "-")
            priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
            priority_label = priority_labels.get(self._task_data.priority, "?")
            tag_icon = "#"
            divider = ("─" * 60) if USE_UNICODE else ("-" * 60)

        # Status color
        if self._task_data.done:
            status_text = f"[bold green]{status_icon} DONE[/bold green]"
        else:
            status_text = f"[bold yellow]{status_icon} TODO[/bold yellow]"

        # Priority color and label
        priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
        priority_label = priority_labels.get(self._task_data.priority, "???")
        priority_colors = {1: "red", 2: "yellow", 3: "green"}
        priority_color = priority_colors.get(self._task_data.priority, "white")
        priority_display = f"[{priority_color}]{priority_label}[/{priority_color}]"

        # Build content
        with Container():
            # Title
            title = f"📋 Task #{self._task_data.id}" if USE_UNICODE else f"Task #{self._task_data.id}"
            yield Static(f"[bold cyan]{title}[/bold cyan]", classes="title")

            # Scrollable content area
            with ScrollableContainer():
                # Task name and status
                yield Static(f"[bold white]{self._task_data.name}[/bold white]  {status_text}", classes="content")
                yield Static("", classes="content")  # Spacing

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
                    yield Static(f"  [dim italic]{self._task_data.description}[/dim italic]", classes="field-value")

                # Divider
                yield Static(f"[dim]{divider}[/dim]", classes="divider")

                # Metadata
                if self._task_data.created_at:
                    from core.commands import get_relative_time
                    created_time = get_relative_time(self._task_data.created_at)
                    created_icon = "📅" if USE_UNICODE else "Created:"
                    yield Static(f"[dim]{created_icon} Created {created_time}[/dim]", classes="content")

                if getattr(self._task_data, 'updated_at', ''):
                    from core.commands import get_relative_time
                    updated_time = get_relative_time(self._task_data.updated_at)
                    updated_icon = "✎" if USE_UNICODE else "Updated:"
                    yield Static(f"[dim]{updated_icon} Updated {updated_time}[/dim]", classes="content")

                if self._task_data.done and self._task_data.completed_at:
                    from core.commands import get_relative_time
                    completed_time = get_relative_time(self._task_data.completed_at)
                    completed_icon = "✅" if USE_UNICODE else "Completed:"
                    yield Static(f"[dim]{completed_icon} Completed {completed_time}[/dim]", classes="content")

            # Hint
            yield Static("[dim]E to Edit | Esc to Close[/dim]", classes="hint")

            # Buttons
            with Horizontal(classes="buttons"):
                yield Button("Edit (E)", variant="primary", id="edit")
                yield Button("Close (Esc)", variant="default", id="close")

    def on_mount(self) -> None:
        """Focus close button by default"""
        self.query_one("#close", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "edit":
            self.dismiss("edit")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Handle ESC key"""
        self.dismiss(None)

    def action_edit(self) -> None:
        """Handle E key"""
        self.dismiss("edit")

