"""
NoteEditorModal - Modal to edit a note (title, tags, body) inside the app.
"""

from typing import Optional
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Button
try:
    from textual.widgets import TextArea  # Textual >=1.0
except Exception:
    TextArea = None  # type: ignore

from models.note import Note


class NoteEditorModal(ModalScreen[Optional[Note]]):
    """A simple in-app editor for notes.

    Edits title, tags (comma separated), and body (multiline).
    Returns an updated Note on save, or None on cancel.
    """

    DEFAULT_CSS = """
    /* Local palette to match app (avoid undefined vars) */
    $primary: #0891b2;
    $secondary: #06b6d4;
    $surface: #1e293b;
    $panel: #334155;
    $text: #f1f5f9;
    $text-muted: #94a3b8;

    NoteEditorModal { align: center middle; }
    NoteEditorModal > Container {
        width: 90;
        max-width: 100;
        height: 90%;
        max-height: 95%;
        border: thick cyan;
        background: $surface;
        color: $text;
        padding: 1 2;
    }
    NoteEditorModal Static.header { width: 100%; content-align: center middle; text-style: bold; color: cyan; padding: 0 0 1 0; }

    /* Field layout - matches TaskForm pattern */
    NoteEditorModal Static.label {
        width: 15;
        content-align: right middle;
        padding: 0 1 0 0;
        color: cyan;
        text-style: bold;
    }

    NoteEditorModal .field-row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    /* Button layout - matches TaskForm pattern */
    NoteEditorModal Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }

    NoteEditorModal Button {
        margin: 0 1;
        min-width: 12;
    }

    /* Ensure inputs are readable */
    /* Match app input styling for consistency and readability */
    NoteEditorModal Input {
        width: 1fr;
        border: solid cyan;
        background: $surface;
    }
    NoteEditorModal Input > .input--placeholder { color: $text-muted; }
    NoteEditorModal Input:focus {
        border: solid yellow;
        background: $panel;
    }
    NoteEditorModal TextArea {
        height: 1fr;
        border: solid cyan;
        background: $surface;
        color: $text;
    }
    NoteEditorModal TextArea:focus {
        border: solid yellow;
        background: $panel;
        color: $text;
    }
    """

    BINDINGS = [("escape", "cancel", "Close"), ("ctrl+s", "save", "Save")]

    def __init__(self, note: Note, is_new: bool = False, **kwargs):
        super().__init__(**kwargs)
        # Work on a shallow copy of the note's key fields
        self._note = note
        self._is_new = is_new
        self._title_val = note.title or ""
        self._tags_val = ", ".join(note.tags or [])
        self._body_val = note.body_md or ""

    def compose(self):
        with Container():
            header_text = "Create Note" if self._is_new else "Edit Note"
            yield Static(header_text, classes="header")

            # Title field
            with Horizontal(classes="field-row"):
                yield Static("Title:", classes="label")
                self._title = Input(
                    value=self._title_val,
                    placeholder="Title...",
                    id="title"
                )
                yield self._title

            # Tags field
            with Horizontal(classes="field-row"):
                yield Static("Tags:", classes="label")
                self._tags = Input(
                    value=self._tags_val,
                    placeholder="tag1, tag2",
                    id="tags"
                )
                yield self._tags

            # Body field (full width, takes remaining space)
            yield Static("Body (Ctrl+S to save):", classes="label")
            if TextArea is None:
                # Fallback to single-line input if TextArea missing (degraded UX)
                self._body = Input(value=self._body_val, placeholder="Body...", classes="field", id="body")
            else:
                self._body = TextArea()
                try:
                    self._body.text = self._body_val
                except Exception:
                    pass
            yield self._body
            # Buttons (yield children inside container; don't mount during compose)
            with Horizontal(classes="buttons"):
                yield Button("Save (Ctrl+S)", variant="primary", id="save")
                yield Button("Cancel (Esc)", variant="default", id="cancel")

    def on_mount(self) -> None:
        """Focus the title input on mount"""
        self.query_one("#title", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        title = self._title.value.strip()
        tags_raw = self._tags.value or ""
        tags = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]
        if TextArea is None:
            body = getattr(self._body, 'value', '') or ''
        else:
            body = self._body.text
        # Update original note object and return it
        self._note.title = title or "Untitled"
        self._note.tags = tags
        self._note.body_md = body
        self.dismiss(self._note)
