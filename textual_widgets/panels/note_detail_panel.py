"""
NoteDetailPanel - View-only note detail panel (replaces NoteDetailModal)

Displays note information in the left panel area without blocking AI chat access.
Uses vim-inspired keybindings for navigation.
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Button, Markdown
from textual.binding import Binding
from textual import work

from models.note import Note
from config import USE_UNICODE


class NoteDetailPanel(VerticalScroll):
    """
    Read-only note detail panel for left panel area

    Keybindings:
        Esc: Return to note list
        e/i: Switch to edit mode (vim-inspired)
        d: Delete note (with confirmation)

    CRITICAL: Uses _note_data instead of _note (potential reserved name)
    """

    DEFAULT_CSS = """
    NoteDetailPanel {
        width: 100%;
        height: 1fr;
        border: solid #404040;
        background: $surface;
        padding: 0 1;
    }

    NoteDetailPanel:focus {
        border: solid #ffdb7a;
    }

    NoteDetailPanel Static.field-label {
        color: cyan;
        text-style: bold;
        padding: 0;
    }

    NoteDetailPanel Static.field-value {
        padding: 0 0 0 2;
    }

    NoteDetailPanel Markdown {
        padding: 0 1;
        background: $panel;
        border: solid $text-muted;
        margin: 0;
    }

    NoteDetailPanel Static.divider {
        width: 100%;
        color: $text-muted;
        padding: 0;
    }

    NoteDetailPanel Static.hint {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 0;
        text-style: italic;
    }

    NoteDetailPanel Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 0;
    }

    NoteDetailPanel Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS = [
        Binding("escape", "back_to_list", "Back to List", priority=True),
        Binding("e", "edit_note", "Edit", show=True),
        Binding("i", "edit_note", "Edit (vim)", show=False),  # vim-inspired
        Binding("d", "delete_note", "Delete", show=True),
    ]

    def __init__(self, note_data: Note, **kwargs):
        """
        Initialize note detail panel

        Args:
            note_data: Note object to display
            **kwargs: Additional widget arguments

        CRITICAL: Uses _note_data instead of _note
        """
        super().__init__(**kwargs)
        self._note_data = note_data

        # Set border title with note ID
        title = note_data.title or "Untitled Note"
        title_short = title[:40] + "..." if len(title) > 40 else title
        self.border_title = f"Note: {title_short}"

    def compose(self) -> ComposeResult:
        """Compose the note detail view"""
        divider = "─" * 60 if USE_UNICODE else "-" * 60
        tag_icon = "#"

        # Tags
        if self._note_data.tags:
            tags_display = ", ".join([f"[cyan]{t}[/cyan]" for t in self._note_data.tags])
            yield Static(f"[bold cyan]Tags:[/bold cyan] {tag_icon} {tags_display}", classes="field-value")

        # Task links
        if self._note_data.task_ids:
            task_links_display = ", ".join([f"[yellow]#{tid}[/yellow]" for tid in self._note_data.task_ids])
            yield Static(f"[bold cyan]Linked Tasks:[/bold cyan] {task_links_display}", classes="field-value")

        # Divider
        yield Static(f"[dim]{divider}[/dim]", classes="divider")

        # Body (markdown rendered)
        if self._note_data.body_md:
            yield Markdown(self._note_data.body_md)
        else:
            yield Static("[dim italic]No content[/dim italic]", classes="field-value")

        # Divider
        yield Static(f"[dim]{divider}[/dim]", classes="divider")

        # Timestamp
        from core.commands import get_relative_time
        if self._note_data.created_at:
            yield Static(
                f"[dim]Created {get_relative_time(self._note_data.created_at)}[/dim]",
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
        from debug_logger import debug_log
        from textual.widgets import Button

        debug_log.info(f"[NOTE_DETAIL] ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸Ãƒâ€¦Ã‚Â¸Ãƒâ€šÃ‚Â¢ Panel mounted for note {self._note_data.id[:8]}")
        debug_log.info(f"[NOTE_DETAIL] Focus state: {self.has_focus}")
        debug_log.info(f"[NOTE_DETAIL] Buttons rendered: {len(self.query(Button))}")
        self.focus()
        debug_log.info(f"[NOTE_DETAIL] After focus() call: {self.has_focus}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        from debug_logger import debug_log

        debug_log.info(f"[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Button pressed: {event.button.id}")
        debug_log.info(f"[NOTE_DETAIL] Panel has focus: {self.has_focus}")
        debug_log.info(f"[NOTE_DETAIL] App focused widget: {self.app.focused}")

        if event.button.id == "edit_btn":
            debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Calling action_edit_note()")
            self.action_edit_note()
            event.stop()  # Prevent event bubbling
        elif event.button.id == "back_btn":
            debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Calling action_back_to_list()")
            self.action_back_to_list()
            event.stop()  # Prevent event bubbling
        elif event.button.id == "delete_btn":
            debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Calling action_delete_note()")
            self.action_delete_note()
            event.stop()  # Prevent event bubbling

    def action_back_to_list(self) -> None:
        """Return to note list (Esc)"""
        from debug_logger import debug_log
        from core.state import LeftPanelMode

        debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ action_back_to_list() called")
        self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
        try:
            self.app.left_panel_mode = LeftPanelMode.LIST_NOTES
        except Exception:
            pass
        debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Switched to LIST_NOTES mode")

    def action_edit_note(self) -> None:
        """Switch to edit mode (e or i)"""
        from debug_logger import debug_log
        from core.state import LeftPanelMode

        debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“Ãƒâ€šÃ‚ÂÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â action_edit_note() called")
        self.app.state.edit_mode_is_new = False
        self.app.state.left_panel_mode = LeftPanelMode.EDIT_NOTE
        try:
            self.app.left_panel_mode = LeftPanelMode.EDIT_NOTE
        except Exception:
            pass
        debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Switched to EDIT_NOTE mode")

    def on_key(self, event) -> None:
        """Consume Esc to avoid double handling after mode switch."""
        if getattr(event, "key", "") == "escape":
            try:
                from debug_logger import debug_log
                debug_log.info("[NOTE_DETAIL] Esc intercepted -> back_to_list() and consume")
            except Exception:
                pass
            try:
                self.action_back_to_list()
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

    @work(exclusive=True)
    async def action_delete_note(self) -> None:
        """Delete note with confirmation (d)"""
        from debug_logger import debug_log
        from textual_widgets.confirm_dialog import ConfirmDialog
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR

        debug_log.info(f"[NOTE_DETAIL] ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬ÂÃƒÂ¢Ã¢â€šÂ¬Ã‹Å“ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â action_delete_note() called for note {self._note_data.id[:8]}")

        # Show confirmation dialog
        title = self._note_data.title or "Untitled"
        debug_log.info(f"[NOTE_DETAIL] Showing confirmation dialog for: {title}")

        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Delete note: {title}?")
        )

        debug_log.info(f"[NOTE_DETAIL] User confirmed: {confirmed}")

        if confirmed:
            # Remove from repository
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            repo.delete(self._note_data.id)
            try:
                self.app.state.mark_notes_dirty()
            except Exception:
                pass

            self.app.notify(f"Note deleted: {title}", severity="information")
            debug_log.info(f"[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Note deleted: {title}")

            # Return to list
            from core.state import LeftPanelMode
            self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES

            # Refresh handled by app watcher
            debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Returned to note list")
        else:
            debug_log.info("[NOTE_DETAIL] ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Delete cancelled by user")

