"""
NoteTable Widget - DataTable for displaying notes
"""

from rich.text import Text
from textual.widgets import DataTable
from textual.binding import Binding

from models.note import Note
from core.state import AppState
from utils.time import humanize_age


class NoteTable(DataTable):
    """DataTable for notes with simple columns and selection helpers.

    Columns: ID | Age | Tags | Title
    """

    BINDINGS = [
        Binding("enter", "open_selected", "Open detail", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(zebra_stripes=True, cursor_type="row", **kwargs)
        self._row_to_note_id: dict[int, str] = {}

    def on_mount(self) -> None:
        self.add_columns_if_needed()

    def add_columns_if_needed(self) -> None:
        if len(self.columns) == 0:
            self.add_column("ID", width=12, key="id")
            self.add_column("Age", width=4, key="age")
            self.add_column("Tags", width=20, key="tags")
            self.add_column("Title", key="title")

    def update_from_state(self, state: AppState) -> None:
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] 🔄 update_from_state START")
        except Exception:
            pass

        # Preserve selection
        previous_selected = self.get_selected_note_id()

        self.clear()
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] 🗑️  CLEARED table")
        except Exception:
            pass

        self._row_to_note_id = {}
        self.add_columns_if_needed()
        notes = list(getattr(state, "notes", []))
        for idx, note in enumerate(notes):
            self.add_note_row(idx, note)

        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] ➕ ADDED {len(notes)} rows")
        except Exception:
            pass

        if previous_selected and self.select_note_by_id(previous_selected):
            pass
        else:
            if len(self.rows) > 0:
                try:
                    self.move_cursor(row=0)
                except Exception:
                    pass

    def update_with_notes(self, notes: list[Note]) -> None:
        """Update table rows with a provided list of notes (bypasses state)."""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] 🔄 update_with_notes START")
        except Exception:
            pass

        # Preserve selection
        previous_selected = self.get_selected_note_id()

        self.clear()
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] 🗑️  CLEARED table")
        except Exception:
            pass

        self._row_to_note_id = {}
        self.add_columns_if_needed()
        for idx, note in enumerate(notes):
            self.add_note_row(idx, note)

        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] ➕ ADDED {len(notes)} rows")
        except Exception:
            pass

        if previous_selected and self.select_note_by_id(previous_selected):
            pass
        else:
            if len(self.rows) > 0:
                try:
                    self.move_cursor(row=0)
                except Exception:
                    pass

    def add_note_row(self, row_idx: int, note: Note) -> None:
        id_text = Text(note.id[:12], style="dim")
        age_text = Text(humanize_age(getattr(note, "created_at", "")), style="dim")
        tags_text = Text(", ".join(note.tags), style="cyan")
        title_parts = Text()
        title_parts.append(note.title or "")
        # Linked task chips dimmed
        if getattr(note, "task_ids", None):
            chips = " ".join(f"#{tid}" for tid in note.task_ids[:5])
            title_parts.append(f"  [dim]{chips}[/dim]")

        current_row = len(self.rows)
        self._row_to_note_id[current_row] = note.id
        self.add_row(id_text, age_text, tags_text, title_parts, key=note.id)

    def get_selected_note_id(self) -> str | None:
        if self.cursor_row >= 0 and self.cursor_row in self._row_to_note_id:
            return self._row_to_note_id[self.cursor_row]
        return None

    def select_note_by_id(self, note_id: str) -> bool:
        for row_idx, nid in self._row_to_note_id.items():
            if nid.startswith(note_id):
                try:
                    self.move_cursor(row=row_idx)
                    # Log selection state
                    from debug_logger import debug_log
                    appearance = "🔆 BRIGHT (focused)" if self.has_focus else "🌑 DIM (unfocused)"
                    debug_log.info(f"[NOTE_TABLE] Selected note {note_id[:8]} at row {row_idx} - appearance: {appearance}")
                    return True
                except Exception:
                    return False
        return False

    def on_focus(self) -> None:
        """Log when table gains focus"""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] ✅ GAINED FOCUS (rows={len(self.rows)}, cursor={self.cursor_row})")
        except Exception:
            pass

    def on_blur(self) -> None:
        """Log when table loses focus"""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] ❌ LOST FOCUS (rows={len(self.rows)}, cursor={self.cursor_row})")
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key events - log for debugging"""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] 🔑 KEY PRESSED: {event.key}")
        except Exception:
            pass

    def action_open_selected(self) -> None:
        """Handle Enter key at widget level - delegates to app's action"""
        # Guard: Only respond to Enter when this table has focus
        if not self.has_focus:
            try:
                from debug_logger import debug_log
                debug_log.info(f"[NOTE_TABLE] ⏎ ENTER KEY IGNORED - table not focused")
            except Exception:
                pass
            return

        try:
            from debug_logger import debug_log
            debug_log.info(f"[NOTE_TABLE] ⏎ ENTER KEY - delegating to app.action_open_selected()")
        except Exception:
            pass

        if hasattr(self.app, 'action_open_selected'):
            try:
                # Delegate to app's @work decorated action
                self.app.action_open_selected()
            except Exception as e:
                try:
                    from debug_logger import debug_log
                    debug_log.error(f"[NOTE_TABLE] Failed to delegate Enter: {e}", exception=e)
                except Exception:
                    pass
