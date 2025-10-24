"""
TaskTable Widget - Custom DataTable for displaying tasks (clean glyphs)
"""

from rich.text import Text
from textual.widgets import DataTable

from models.task import Task
from core.state import AppState
from utils.emoji import emoji
from utils.time import humanize_age


class TaskTable(DataTable):
    """DataTable that renders tasks with clean, cross-platform glyphs.

    Columns: ID | Age | Priority | Tags | Task
    """

    def __init__(self, **kwargs):
        super().__init__(zebra_stripes=True, cursor_type="row", **kwargs)
        self._row_to_task_id: dict[int, int] = {}

    def on_mount(self) -> None:
        self.add_columns_if_needed()

    def add_columns_if_needed(self) -> None:
        if len(self.columns) == 0:
            self.add_column("ID", width=6, key="id")
            self.add_column("Age", width=7, key="age")
            self.add_column("Priority", width=12, key="priority")
            self.add_column("Tags", width=20, key="tags")
            self.add_column("Task", key="task")

    def update_from_state(self, state: AppState) -> None:
        # Clear and rebuild
        self.clear()
        self._row_to_task_id = {}
        self.add_columns_if_needed()

        tasks = state.get_current_page_tasks()
        for idx, task in enumerate(tasks):
            self.add_task_row(idx, task, state.view_mode)

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
        task_text.append(" " + (task.name or ""))

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

    def get_selected_task_id(self) -> int | None:
        if self.cursor_row >= 0 and self.cursor_row in self._row_to_task_id:
            return self._row_to_task_id[self.cursor_row]
        return None

    def select_task_by_id(self, task_id: int) -> bool:
        for row_idx, tid in self._row_to_task_id.items():
            if tid == task_id:
                self.move_cursor(row=row_idx)
                return True
        return False

