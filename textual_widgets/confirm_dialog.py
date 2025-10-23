"""
ConfirmDialog - Modal confirmation dialog
"""

from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Button
from textual.app import ComposeResult


class ConfirmDialog(ModalScreen[bool]):
    """
    Modal confirmation dialog

    Returns True if confirmed, False if cancelled
    """

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Container {
        width: 60;
        height: auto;
        border: thick cyan;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDialog Static {
        width: 100%;
        content-align: center middle;
        padding: 1 0;
    }

    ConfirmDialog Horizontal {
        width: 100%;
        height: auto;
        align: center middle;
    }

    ConfirmDialog Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(
        self,
        message: str,
        title: str = "Confirm",
        confirm_text: str = "Yes",
        cancel_text: str = "No",
        **kwargs
    ):
        """
        Initialize confirmation dialog

        Args:
            message: Confirmation message to display
            title: Dialog title
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
        """
        super().__init__(**kwargs)
        self.message = message
        self.title = title
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text

    def compose(self) -> ComposeResult:
        """Compose the dialog layout"""
        with Container():
            yield Static(f"[bold cyan]{self.title}[/bold cyan]")
            yield Static(self.message)
            with Horizontal():
                yield Button(self.confirm_text, variant="error", id="confirm")
                yield Button(self.cancel_text, variant="primary", id="cancel")

    def on_mount(self) -> None:
        """Focus cancel button by default (safer)"""
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts"""
        if event.key == "y":
            self.dismiss(True)
        elif event.key == "n" or event.key == "escape":
            self.dismiss(False)
