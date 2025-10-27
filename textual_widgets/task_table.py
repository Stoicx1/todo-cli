"""
TaskTable Widget - Custom DataTable for displaying tasks (clean glyphs)
"""

from rich.text import Text
from textual.widgets import DataTable
from textual.binding import Binding

from models.task import Task
from core.state import AppState
from utils.emoji import emoji
from utils.time import humanize_age
from config import USE_UNICODE


class TaskTable(DataTable):
    """DataTable that renders tasks with clean, cross-platform glyphs.

    Columns: ID | Age | Prio | Tags | Task
    """

    BINDINGS = [
        Binding("enter", "open_selected", "Open detail", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(zebra_stripes=True, cursor_type="row", **kwargs)
        self._row_to_task_id: dict[int, int] = {}

    def on_mount(self) -> None:
        self.add_columns_if_needed()

    def add_columns_if_needed(self) -> None:
        if len(self.columns) == 0:
            self.add_column("ID", width=4, key="id")
            self.add_column("Age", width=4, key="age")
            self.add_column("Prio", width=4, key="priority")
            self.add_column("Tags", width=20, key="tags")
            self.add_column("Task", key="task")

    def update_from_state(self, state: AppState) -> None:
        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] 🔄 update_from_state START (view_mode={state.view_mode})")
        except Exception:
            pass

        # Preserve previous selection if possible
        previous_selected = self.get_selected_task_id()

        # Clear and rebuild
        self.clear()
        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] 🗑️  CLEARED table")
        except Exception:
            pass

        self._row_to_task_id = {}
        self.add_columns_if_needed()

        tasks = state.get_current_page_tasks()
        # Preload notes map and cache note objects
        self._notes_by_task = getattr(state, "_notes_by_task", {})
        try:
            self._notes_cache = {t.id: state.get_notes_for_task(t.id) for t in tasks}
        except Exception:
            self._notes_cache = {}
        for idx, task in enumerate(tasks):
            self.add_task_row(idx, task, state.view_mode)

        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] ➕ ADDED {len(tasks)} rows")
        except Exception:
            pass

        # Restore selection or default to first row for consistent Enter behavior
        if previous_selected is not None and self.select_task_by_id(previous_selected):
            pass
        else:
            if len(self.rows) > 0:
                try:
                    self.move_cursor(row=0)
                except Exception:
                    pass


    def add_task_row(self, row_idx: int, task: Task, view_mode: str) -> None:
        # ID
        id_text = Text(str(task.id), style="dim")

        # Age
        age_text = Text(humanize_age(getattr(task, "created_at", "")), style="dim")

        # Priority (label + color)
        priority_label = {1: "HIGH", 2: "MED", 3: "LOW"}.get(getattr(task, "priority", 2), "?")
        priority_color = {1: "red", 2: "yellow", 3: "green"}.get(getattr(task, "priority", 2), "white")
        priority_text = Text(priority_label, style=priority_color)

        # Tags
        tags_text = Text(task.get_tags_display(), style="cyan")

        # Task name with status icon
        status_icon = emoji("✔", "+") if getattr(task, "done", False) else emoji("✗", "-")
        status_color = "green" if getattr(task, "done", False) else "red"
        task_text = Text()
        task_text.append(status_icon, style=status_color)
        # Note indicator (Unicode-aware)
        note_count = len(getattr(self, "_notes_by_task", {}).get(task.id, []))
        if note_count > 0:
            if USE_UNICODE:
                indicator = f" [dim]📄x{note_count}[/dim]"
            else:
                indicator = f" [dim][N:{note_count}][/dim]"
        else:
            indicator = ""
        task_text.append(" " + (task.name or "") + indicator)

        # Map row to task ID
        current_row = len(self.rows)
        self._row_to_task_id[current_row] = task.id

        # Add main row
        self.add_row(id_text, age_text, priority_text, tags_text, task_text, key=str(task.id))

        # Detail rows
        if view_mode == "detail":
            if task.comment:
                current_row = len(self.rows)
                self._row_to_task_id[current_row] = task.id
                self.add_row(Text(""), Text(""), Text(""), Text(""), Text(f"  • {task.comment}", style="dim"))
            if task.description:
                current_row = len(self.rows)
                self._row_to_task_id[current_row] = task.id
                self.add_row(Text(""), Text(""), Text(""), Text(""), Text(f"    {task.description}", style="dim italic"))
            # Linked notes excerpts (up to 2)
            notes = getattr(self, "_notes_cache", {}).get(task.id, [])
            for n in notes[:2]:
                current_row = len(self.rows)
                self._row_to_task_id[current_row] = task.id
                self.add_row(Text(""), Text(""), Text(""), Text(""), Text(f"  • {n.title} — {n.excerpt(80)}", style="dim"))

    def get_selected_task_id(self) -> int | None:
        if self.cursor_row >= 0 and self.cursor_row in self._row_to_task_id:
            return self._row_to_task_id[self.cursor_row]
        return None

    def select_task_by_id(self, task_id: int) -> bool:
        for row_idx, tid in self._row_to_task_id.items():
            if tid == task_id:
                self.move_cursor(row=row_idx)
                # Log selection state
                try:
                    from debug_logger import debug_log
                    appearance = "🔆 BRIGHT (focused)" if self.has_focus else "🌑 DIM (unfocused)"
                    debug_log.info(f"[TASK_TABLE] Selected task #{task_id} at row {row_idx} - appearance: {appearance}")
                except Exception:
                    pass
                return True
        return False

    def on_focus(self) -> None:
        """Log when table gains focus"""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] ✅ GAINED FOCUS (rows={len(self.rows)}, cursor={self.cursor_row})")
        except Exception:
            pass

    def on_blur(self) -> None:
        """Log when table loses focus"""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] ❌ LOST FOCUS (rows={len(self.rows)}, cursor={self.cursor_row})")
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key events - log for debugging"""
        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] 🔑 KEY PRESSED: {event.key}")
        except Exception:
            pass

    def action_open_selected(self) -> None:
        """Handle Enter key at widget level - delegates to app's action"""
        # Guard: Only respond to Enter when this table has focus
        if not self.has_focus:
            try:
                from debug_logger import debug_log
                debug_log.info(f"[TASK_TABLE] ⏎ ENTER KEY IGNORED - table not focused")
            except Exception:
                pass
            return

        try:
            from debug_logger import debug_log
            debug_log.info(f"[TASK_TABLE] ⏎ ENTER KEY - delegating to app.action_open_selected()")
        except Exception:
            pass

        if hasattr(self.app, 'action_open_selected'):
            try:
                # Delegate to app's @work decorated action
                self.app.action_open_selected()
            except Exception as e:
                try:
                    from debug_logger import debug_log
                    debug_log.error(f"[TASK_TABLE] Failed to delegate Enter: {e}", exception=e)
                except Exception:
                    pass
