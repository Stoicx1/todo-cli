"""
TitlePrompt - Simple modal to capture a title string.
"""

from textual.screen import ModalScreen
from textual.containers import Container, Horizontal
from textual.widgets import Input, Button, Static
from textual.app import ComposeResult


class TitlePrompt(ModalScreen[str | None]):
    DEFAULT_CSS = """
    TitlePrompt { align: center middle; }
    TitlePrompt > Container { width: 60; max-width: 90; height: auto; border: thick cyan; background: $surface; padding: 1 1; }
    TitlePrompt Input { width: 100%; }
    TitlePrompt Horizontal { width: 100%; align: center middle; padding: 1 0 0 0; }
    TitlePrompt Button { margin: 0 1; min-width: 10; }
    """

    BINDINGS = [("escape", "cancel", "Cancel"), ("enter", "confirm", "OK")]

    def __init__(self, prompt: str = "Title:", initial: str = "", **kwargs):
        super().__init__(**kwargs)
        self._prompt = prompt
        self._initial = initial
        self._input: Input | None = None

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"[bold cyan]{self._prompt}[/bold cyan]")
            self._input = Input(value=self._initial, placeholder="Enter title...")
            yield self._input
            with Horizontal():
                yield Button("OK", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        if self._input:
            self._input.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_confirm(self) -> None:
        value = self._input.value if self._input else ""
        self.dismiss(value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.action_confirm()
        else:
            self.action_cancel()

