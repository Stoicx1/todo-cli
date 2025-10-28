"""
NoteEditPanel - Inline note editing panel (replaces NoteEditorModal)

Enables creating/editing notes with persistent AI chat access.
Implements dirty state tracking and markdown body editing.
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.widgets import Static, Input, Label
from textual.binding import Binding
from textual.reactive import reactive

try:
    from textual.widgets import TextArea
except ImportError:
    TextArea = None  # Fallback for older Textual versions

from models.note import Note


class NoteEditPanel(VerticalScroll):
    """
    Inline note edit/create panel for left panel area

    Features:
        - Create new notes or edit existing
        - Dirty state tracking (warns on unsaved changes)
        - Markdown body editing with TextArea
        - AI chat remains accessible during editing

    Keybindings:
        Ctrl+S: Save note
        Esc: Cancel (warns if dirty)

    CRITICAL: Uses _note_data instead of _note
    """

    DEFAULT_CSS = """
    NoteEditPanel {
        width: 100%;
        height: 1fr;
        border: solid yellow;  /* Yellow = edit mode */
        background: $surface;
        padding: 1 2;
    }

    NoteEditPanel:focus-within {
        border: solid yellow 2px;
    }

    NoteEditPanel Static.title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: yellow;
        padding: 0 0 1 0;
    }

    NoteEditPanel Static.error {
        color: red;
        width: 100%;
        height: auto;
        padding: 0 0 1 0;
    }

    NoteEditPanel Static.label {
        width: 15;
        content-align: right middle;
        padding: 0 1 0 0;
        color: cyan;
        text-style: bold;
    }

    NoteEditPanel .field-row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    NoteEditPanel Input {
        width: 1fr;
        border: solid cyan;
        background: $surface;
    }

    NoteEditPanel Input:focus {
        border: solid yellow;
        background: $panel;
    }

    NoteEditPanel TextArea {
        height: 1fr;
        min-height: 15;
        border: solid cyan;
        background: $surface;
        color: $text;
    }

    NoteEditPanel TextArea:focus {
        border: solid yellow;
        background: $panel;
    }

    NoteEditPanel Static.hint {
        color: $text-muted;
        width: 100%;
        height: auto;
        padding: 0 0 1 15;
        text-style: italic;
        font-size: 0.9;
    }

    NoteEditPanel Static.hint-main {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 1 0 0 0;
        text-style: italic;
    }

    NoteEditPanel Static.dirty-indicator {
        color: yellow;
        width: 100%;
        text-align: center;
        padding: 0 0 1 0;
    }

    NoteEditPanel Static.section-label {
        color: cyan;
        text-style: bold;
        padding: 1 0 0 0;
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
        note_data: Note | None = None,
        is_new: bool = False,
        **kwargs
    ):
        """
        Initialize note edit panel

        Args:
            note_data: Note to edit (None for new note)
            is_new: True if creating new note
            **kwargs: Additional widget arguments

        CRITICAL: Uses _note_data instead of _note
        """
        super().__init__(**kwargs)
        self._note_data = note_data
        self._is_new = is_new
        self._original_values = {}  # For dirty tracking

    def compose(self) -> ComposeResult:
        """Compose the edit form"""
        title = "Create New Note" if self._is_new else f"Edit Note"

        yield Static(title, classes="title")
        yield Static("", id="error_message", classes="error")
        yield Static("", id="dirty_indicator", classes="dirty-indicator")

        # Title field
        with Horizontal(classes="field-row"):
            yield Static("Title:", classes="label")
            yield Input(
                value=self._note_data.title if self._note_data else "",
                placeholder="Note title...",
                id="title_input"
            )

        # Tags field
        with Horizontal(classes="field-row"):
            yield Static("Tags:", classes="label")
            tags_value = ", ".join(self._note_data.tags) if self._note_data else ""
            yield Input(
                value=tags_value,
                placeholder="tag1, tag2, tag3",
                id="tags_input"
            )
        yield Static("Comma-separated tags", classes="hint")

        # Body field (markdown)
        yield Static("Body (Markdown):", classes="section-label")

        if TextArea is None:
            # Fallback to Input for older Textual versions
            yield Input(
                value=self._note_data.body_md if self._note_data else "",
                placeholder="Note body...",
                id="body_input"
            )
        else:
            # Use TextArea for multiline markdown
            body_widget = TextArea(id="body_textarea")
            if self._note_data and self._note_data.body_md:
                try:
                    body_widget.text = self._note_data.body_md
                except Exception:
                    pass
            yield body_widget

        # Action hints
        yield Static(
            "[dim]Ctrl+S to save | Esc to cancel | AI chat available on the right →[/dim]",
            classes="hint-main"
        )

    def on_mount(self) -> None:
        """Focus title input and capture original values"""
        self.query_one("#title_input", Input).focus()
        self._capture_original_values()

    def _capture_original_values(self) -> None:
        """Store original values for dirty tracking"""
        try:
            body_value = ""
            if TextArea is not None:
                try:
                    body_value = self.query_one("#body_textarea", TextArea).text
                except Exception:
                    body_value = self.query_one("#body_input", Input).value
            else:
                body_value = self.query_one("#body_input", Input).value

            self._original_values = {
                "title": self.query_one("#title_input", Input).value,
                "tags": self.query_one("#tags_input", Input).value,
                "body": body_value,
            }
        except Exception:
            self._original_values = {}

    def on_input_changed(self, event: Input.Changed) -> None:
        """Mark dirty when any input changes"""
        self._check_dirty_state()

    def on_text_area_changed(self, event) -> None:
        """Mark dirty when TextArea changes"""
        self._check_dirty_state()

    def _check_dirty_state(self) -> bool:
        """Check if form has unsaved changes"""
        try:
            body_value = ""
            if TextArea is not None:
                try:
                    body_value = self.query_one("#body_textarea", TextArea).text
                except Exception:
                    body_value = self.query_one("#body_input", Input).value
            else:
                body_value = self.query_one("#body_input", Input).value

            current = {
                "title": self.query_one("#title_input", Input).value,
                "tags": self.query_one("#tags_input", Input).value,
                "body": body_value,
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
        """Validate and save note (Ctrl+S)"""
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR
        from datetime import datetime

        # Get field values
        title = self.query_one("#title_input", Input).value.strip()
        tags_raw = self.query_one("#tags_input", Input).value.strip()

        # Get body
        if TextArea is not None:
            try:
                body = self.query_one("#body_textarea", TextArea).text
            except Exception:
                body = self.query_one("#body_input", Input).value
        else:
            body = self.query_one("#body_input", Input).value

        # Clear previous errors
        error_msg = self.query_one("#error_message", Static)
        error_msg.update("")

        # Validate title
        if not title:
            title = "Untitled"

        # Parse tags
        tags = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]

        # Save via repository
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)

        if self._is_new:
            # Create new note
            note = Note(
                id="",  # Will be generated
                title=title,
                body_md=body,
                tags=tags,
                task_links=[],
                created_at=datetime.now().isoformat()
            )
            saved_note = repo.save(note)
            self.app.notify(f"Note created: {title}", severity="success")

            # Update app state
            self.app.state.selected_note_id = saved_note.id

        else:
            # Update existing note
            self._note_data.title = title
            self._note_data.tags = tags
            self._note_data.body_md = body
            repo.save(self._note_data)
            self.app.notify(f"Note updated: {title}", severity="success")

        # Return to list view
        from core.state import LeftPanelMode
        self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES

        # Refresh note table
        if hasattr(self.app, 'refresh_note_table'):
            self.app.refresh_note_table()

    async def action_cancel(self) -> None:
        """Cancel editing with dirty check (Esc)"""
        # Check if dirty
        if self.is_dirty:
            from textual_widgets.confirm_dialog import ConfirmDialog

            confirmed = await self.app.push_screen_wait(
                ConfirmDialog("Discard unsaved changes?")
            )

            if not confirmed:
                return

        # Return to previous state
        from core.state import LeftPanelMode

        if self._is_new:
            # Creating new note - return to list
            self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
        else:
            # Editing existing - return to detail view
            self.app.state.left_panel_mode = LeftPanelMode.DETAIL_NOTE
