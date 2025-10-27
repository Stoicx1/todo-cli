"""
NoteDetailModal - Modal to show note details with excerpt and links.
"""

from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Static, Button
from textual.app import ComposeResult

from models.note import Note


class NoteDetailModal(ModalScreen[str | None]):
    """Modal for displaying note details with edit/close options."""

    DEFAULT_CSS = """
    NoteDetailModal { align: center middle; }
    NoteDetailModal > Container { width: 70; max-width: 90; height: auto; max-height: 90%; border: thick cyan; background: $surface; padding: 1 2; }
    NoteDetailModal Static.title { width: 100%; content-align: center middle; text-style: bold; color: cyan; padding: 0 0 1 0; }
    NoteDetailModal ScrollableContainer { width: 100%; height: auto; max-height: 30; border: none; padding: 1 0; }
    NoteDetailModal Static.content { width: 100%; height: auto; }
    NoteDetailModal Horizontal.buttons { width: 100%; height: auto; align: center middle; padding: 1 0 0 0; }
    NoteDetailModal Button { margin: 0 1; min-width: 12; }
    NoteDetailModal Static.hint { color: $text-muted; width: 100%; text-align: center; padding: 1 0 0 0; text-style: italic; }
    NoteDetailModal Static.field-label { color: cyan; text-style: bold; padding: 0 0 0 0; }
    NoteDetailModal Static.field-value { padding: 0 0 1 2; }
    NoteDetailModal Static.divider { width: 100%; color: $text-muted; padding: 1 0; }
    """

    BINDINGS = [("escape", "cancel", "Close"), ("e", "edit", "Edit"), ("l", "link", "Link")]

    def __init__(self, note: Note, **kwargs):
        super().__init__(**kwargs)
        self._note = note

    def compose(self) -> ComposeResult:
        divider = "─" * 60
        task_ids = list(self._note.task_ids or [])
        task_chips = " ".join(f"#{tid}" for tid in task_ids)
        tags = ", ".join(self._note.tags)

        with Container():
            yield Static(f"[bold cyan]{self._note.title}[/bold cyan]", classes="title")
            with ScrollableContainer():
                yield Static(f"[dim]{self._note.id}[/dim]", classes="content")
                if tags:
                    yield Static("[bold cyan]Tags:[/bold cyan]", classes="field-label")
                    yield Static(f"  {tags}", classes="field-value")
                if task_ids:
                    yield Static("[bold cyan]Linked Tasks:[/bold cyan]", classes="field-label")
                    # Buttons for unlinking each task
                    with Horizontal(classes="field-value"):
                        for tid in task_ids:
                            yield Button(f"Unlink #{tid}", id=f"unlink-{tid}")
                yield Static(f"[dim]{divider}[/dim]", classes="divider")
                body_lines = (self._note.body_md or "").splitlines()
                preview = body_lines[:40] if body_lines else ["[dim](empty)[/dim]"]
                yield Static("\n".join(preview), classes="content")

            yield Static("[dim]E to Edit | L to Link | Esc to Close[/dim]", classes="hint")
            with Horizontal(classes="buttons"):
                yield Button("Edit (E)", variant="primary", id="edit")
                yield Button("Link… (L)", variant="primary", id="link")
                yield Button("Close (Esc)", variant="default", id="close")

    def on_mount(self) -> None:
        self.query_one("#close", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "edit":
            self.dismiss("edit")
        elif event.button.id == "link":
            self.dismiss("link")
        elif event.button.id and event.button.id.startswith("unlink-"):
            try:
                tid = event.button.id.split("-", 1)[1]
            except Exception:
                tid = ""
            self.dismiss(f"unlink:{tid}")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_edit(self) -> None:
        self.dismiss("edit")

    def action_link(self) -> None:
        self.dismiss("link")
