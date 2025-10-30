"""
NoteEditPanel - Inline note editing panel (replaces NoteEditorModal)

Enables creating/editing notes with persistent AI chat access.
Implements dirty state tracking and markdown body editing.
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.widgets import Static, Input, Label, Button
from textual.binding import Binding
from textual.reactive import reactive
from textual import work

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
        border: solid #404040;
        background: $surface;
        padding: 0 1;
    }

    NoteEditPanel:focus-within {
        border: solid #ffdb7a;
    }

    NoteEditPanel Static.error {
        color: red;
        width: 100%;
        height: auto;
        padding: 0;
    }

    NoteEditPanel Static.label {
        width: 6;
        content-align: right middle;
        padding: 0 1 0 0;
        color: cyan;
        text-style: bold;
    }

    NoteEditPanel .field-row {
        width: 100%;
        height: auto;
        margin: 0;
    }

    NoteEditPanel Input {
        width: 1fr;
        border: solid #404040;
        background: $surface;
    }

    NoteEditPanel Input:focus {
        border: solid #ffdb7a;
        background: $panel;
    }

    NoteEditPanel TextArea {
        height: 1fr;
        min-height: 12;
        border: solid #404040;
        background: $surface;
        color: $text;
    }

    NoteEditPanel TextArea:focus {
        border: solid #ffdb7a;
        background: $panel;
    }

    NoteEditPanel Static.hint {
        color: $text-muted;
        width: 100%;
        height: auto;
        padding: 0 0 0 7;
    }

    NoteEditPanel Static.hint-main {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 0;
    }

    NoteEditPanel Static.dirty-indicator {
        color: #ffdb7a;
        width: 100%;
        text-align: center;
        padding: 0;
    }

    NoteEditPanel Static.section-label {
        color: cyan;
        padding: 0;
    }

    NoteEditPanel Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0;
    }

    NoteEditPanel Button {
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

        # Set border title
        if is_new:
            self.border_title = "Create New Note"
        else:
            self.border_title = "Edit Note"

    def compose(self) -> ComposeResult:
        """Compose the edit form"""
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

        # Body field (markdown)
        yield Static("Body:", classes="section-label")

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

        # Hints
        yield Static("[dim]Ctrl+S to Save | Esc to Cancel[/dim]", classes="hint-main")

        # Action buttons
        with Horizontal(classes="buttons"):
            yield Button("💾 Save (Ctrl+S)", variant="primary", id="save_btn")
            yield Button("❌ Cancel (Esc)", variant="default", id="cancel_btn")

    def on_mount(self) -> None:
        """Focus title input and capture original values"""
        self.query_one("#title_input", Input).focus()
        self._capture_original_values()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        from debug_logger import debug_log

        debug_log.info(f"[NOTE_EDIT] ✅ Button pressed: {event.button.id}")

        if event.button.id == "save_btn":
            debug_log.info("[NOTE_EDIT] → Calling action_save()")
            self.action_save()
            event.stop()
        elif event.button.id == "cancel_btn":
            debug_log.info("[NOTE_EDIT] → Calling action_cancel()")
            # action_cancel is @work decorated, so calling it directly creates the worker
            self.action_cancel()
            event.stop()

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
        from debug_logger import debug_log
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR
        from datetime import datetime

        debug_log.info("[NOTE_EDIT] 💾 action_save() called")

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
                task_ids=[],
                created_at=datetime.now().isoformat()
            )
            saved_note = repo.save(note)
            self.app.notify(f"Note created: {title}", severity="success")
            debug_log.info(f"[NOTE_EDIT] ✅ Note created: {title}")

            # Update app state
            self.app.state.selected_note_id = saved_note.id

        else:
            # Update existing note
            self._note_data.title = title
            self._note_data.tags = tags
            self._note_data.body_md = body
            repo.save(self._note_data)
            self.app.notify(f"Note updated: {title}", severity="success")
            debug_log.info(f"[NOTE_EDIT] ✅ Note updated: {title}")

        # Return to list view
        from core.state import LeftPanelMode
        self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
        # Also update app reactive property so watcher triggers panel switch
        try:
            self.app.left_panel_mode = LeftPanelMode.LIST_NOTES
        except Exception:
            pass
        try:
            current_mode = getattr(self.app._left_panel_container, "current_mode", None)
            debug_log.info(f"[NOTE_EDIT] -> Switched to LIST_NOTES (state+app). container_current_mode={current_mode}")
        except Exception:
            debug_log.info("[NOTE_EDIT] -> Switched to LIST_NOTES (state+app)")

        # Refresh note table
        if hasattr(self.app, 'refresh_note_table'):
            self.app.refresh_note_table()

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
            self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
            try:
                self.app.left_panel_mode = LeftPanelMode.LIST_NOTES
            except Exception:
                pass
            debug_log.info("[NOTE_EDIT] -> Cancel (new): LIST_NOTES (state+app)")
        else:
            self.app.state.left_panel_mode = LeftPanelMode.DETAIL_NOTE
            try:
                self.app.left_panel_mode = LeftPanelMode.DETAIL_NOTE
            except Exception:
                pass
            debug_log.info("[NOTE_EDIT] -> Cancel (edit): DETAIL_NOTE (state+app)")

        # Refresh note table to show current state
        if hasattr(self.app, 'refresh_note_table'):
            self.app.refresh_note_table()

    def on_key(self, event) -> None:
        """Intercept Esc to prevent bubbling to next view after mode switch."""
        if getattr(event, "key", "") == "escape":
            try:
                from debug_logger import debug_log
                debug_log.info("[NOTE_EDIT] Esc intercepted -> invoking action_cancel() and consuming event")
            except Exception:
                pass
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
