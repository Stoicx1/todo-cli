"""
TaskForm - Modal form for adding/editing tasks
"""

from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, Button, Input, Select
from textual.app import ComposeResult
from textual.validation import Length, Integer

from models.task import Task
from utils.tag_parser import parse_tags
from utils.validators import validate_task_name, sanitize_comment, sanitize_description, clamp_priority
from config import validation


class TaskForm(ModalScreen[dict | None]):
    """
    Modal form for adding or editing tasks

    Returns dict with task data if submitted, None if cancelled
    """

    DEFAULT_CSS = """
    TaskForm {
        align: center middle;
    }

    TaskForm > Container {
        width: 80;
        max-width: 100;
        height: auto;
        border: thick cyan;
        background: $surface;
        padding: 1 2;
    }

    TaskForm Static.title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: cyan;
        padding: 0 0 1 0;
    }

    TaskForm Static.label {
        width: 15;
        content-align: right middle;
        padding: 0 1 0 0;
    }

    TaskForm Input {
        width: 1fr;
    }

    TaskForm Select {
        width: 1fr;
    }

    TaskForm .field-row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    TaskForm Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }

    TaskForm Button {
        margin: 0 1;
        min-width: 12;
    }

    TaskForm Static.error {
        color: red;
        width: 100%;
        height: auto;
        padding: 0 0 1 0;
    }

    TaskForm Static.hint {
        color: $text-muted;
        width: 100%;
        height: auto;
        padding: 0 0 1 15;
        text-style: italic;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "submit", "Submit"),
    ]

    def __init__(
        self,
        task: Task | None = None,
        existing_tags: list[str] = None,
        **kwargs
    ):
        """
        Initialize task form

        Args:
            task: Task to edit (None for new task)
            existing_tags: List of existing tags for suggestions
        """
        super().__init__(**kwargs)
        self._task_data = task
        self.existing_tags = existing_tags or []
        self.is_edit = task is not None

    def compose(self) -> ComposeResult:
        """Compose the form layout"""
        title = "Edit Task" if self.is_edit else "Add New Task"

        with Container():
            yield Static(title, classes="title")
            yield Static("", id="error_message", classes="error")

            # Task Name (required)
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

            # Comment (optional)
            with Horizontal(classes="field-row"):
                yield Static("Comment:", classes="label")
                yield Input(
                    placeholder="Short comment (optional)",
                    value=self._task_data.comment if self._task_data else "",
                    id="comment_input",
                )
            yield Static("Brief note or context", classes="hint")

            # Description (optional)
            with Horizontal(classes="field-row"):
                yield Static("Description:", classes="label")
                yield Input(
                    placeholder="Detailed description (optional)",
                    value=self._task_data.description if self._task_data else "",
                    id="description_input",
                )
            yield Static("Full details and requirements", classes="hint")

            # Priority (select dropdown)
            with Horizontal(classes="field-row"):
                yield Static("Priority:", classes="label")
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
                    placeholder="tag1, tag2, tag3 (max 3)",
                    value=tags_value,
                    id="tags_input",
                )

            if self.existing_tags:
                existing_tags_str = ", ".join(sorted(self.existing_tags[:10]))
                if len(self.existing_tags) > 10:
                    existing_tags_str += f", ... ({len(self.existing_tags)} total)"
                yield Static(f"Existing: {existing_tags_str}", classes="hint")
            else:
                yield Static("Separate tags with commas", classes="hint")

            # Buttons
            with Horizontal(classes="buttons"):
                yield Button("Submit (Ctrl+S)", variant="success", id="submit_btn")
                yield Button("Cancel (Esc)", variant="default", id="cancel_btn")

    def on_mount(self) -> None:
        """Focus name input on mount"""
        self.query_one("#name_input", Input).focus()

    def action_cancel(self) -> None:
        """Cancel and dismiss"""
        self.dismiss(None)

    def action_submit(self) -> None:
        """Validate and submit form"""
        self._submit_form()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "submit_btn":
            self._submit_form()
        elif event.button.id == "cancel_btn":
            self.dismiss(None)

    def _submit_form(self) -> None:
        """Validate and submit form data"""
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
        result = {
            "name": name,
            "comment": comment,
            "description": description,
            "priority": priority,
            "tag": tag_list[0] if tag_list else "",  # Legacy field
            "tags": tag_list,  # New field
        }

        # Dismiss with result
        self.dismiss(result)
