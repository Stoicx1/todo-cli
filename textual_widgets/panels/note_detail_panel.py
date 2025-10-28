"""
NoteDetailPanel - View-only note detail panel (replaces NoteDetailModal)

Displays note information in the left panel area without blocking AI chat access.
Uses vim-inspired keybindings for navigation.
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Button, Markdown
from textual.binding import Binding

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
        border: solid cyan;
        background: $surface;
        padding: 1 2;
    }

    NoteDetailPanel:focus {
        border: solid yellow;
    }

    NoteDetailPanel Static.title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: cyan;
        padding: 0 0 1 0;
    }

    NoteDetailPanel Static.field-label {
        color: cyan;
        text-style: bold;
        padding: 1 0 0 0;
    }

    NoteDetailPanel Static.field-value {
        padding: 0 0 1 2;
    }

    NoteDetailPanel Markdown {
        padding: 1 2;
        background: $panel;
        border: solid $text-muted;
        margin: 1 0;
    }

    NoteDetailPanel Static.divider {
        width: 100%;
        color: $text-muted;
        padding: 1 0;
    }

    NoteDetailPanel Static.hint {
        color: $text-muted;
        width: 100%;
        text-align: center;
        padding: 1 0 0 0;
        text-style: italic;
    }

    NoteDetailPanel Horizontal.buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
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

    def compose(self) -> ComposeResult:
        """Compose the note detail view"""
        divider = ("─" * 60) if USE_UNICODE else ("-" * 60)
        tag_icon = "#"

        # Title
        title_text = self._note_data.title or "Untitled Note"
        yield Static(
            f"[bold cyan]{title_text}[/bold cyan]",
            classes="title"
        )

        # ID
        yield Static(f"[dim]ID: {self._note_data.id[:16]}...[/dim]", classes="field-value")
        yield Static("", classes="field-value")  # Spacing

        # Tags
        if self._note_data.tags:
            tags_display = ", ".join([f"[cyan]{t}[/cyan]" for t in self._note_data.tags])
            yield Static("[bold cyan]Tags:[/bold cyan]", classes="field-label")
            yield Static(f"  {tag_icon} {tags_display}", classes="field-value")

        # Task links
        if self._note_data.task_links:
            task_links_display = ", ".join([f"[yellow]#{tid}[/yellow]" for tid in self._note_data.task_links])
            yield Static("[bold cyan]Linked Tasks:[/bold cyan]", classes="field-label")
            yield Static(f"  {task_links_display}", classes="field-value")

        # Divider
        yield Static(f"[dim]{divider}[/dim]", classes="divider")

        # Body (markdown rendered)
        if self._note_data.body_md:
            yield Static("[bold cyan]Content:[/bold cyan]", classes="field-label")
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
        self.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "edit_btn":
            self.action_edit_note()
        elif event.button.id == "back_btn":
            self.action_back_to_list()
        elif event.button.id == "delete_btn":
            self.action_delete_note()

    def action_back_to_list(self) -> None:
        """Return to note list (Esc)"""
        from core.state import LeftPanelMode
        self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES

    def action_edit_note(self) -> None:
        """Switch to edit mode (e or i)"""
        from core.state import LeftPanelMode
        self.app.state.edit_mode_is_new = False
        self.app.state.left_panel_mode = LeftPanelMode.EDIT_NOTE

    async def action_delete_note(self) -> None:
        """Delete note with confirmation (d)"""
        from textual_widgets.confirm_dialog import ConfirmDialog
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR

        # Show confirmation dialog
        title = self._note_data.title or "Untitled"
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(f"Delete note: {title}?")
        )

        if confirmed:
            # Remove from repository
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            repo.delete(self._note_data.id)

            self.app.notify(f"Note deleted: {title}", severity="information")

            # Return to list
            from core.state import LeftPanelMode
            self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES

            # Refresh note table
            if hasattr(self.app, 'refresh_note_table'):
                self.app.refresh_note_table()
