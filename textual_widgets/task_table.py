"""
TaskTable Widget - Custom DataTable for displaying tasks
"""

from textual.widgets import DataTable
from textual.coordinate import Coordinate
from rich.text import Text

from core.state import AppState
from models.task import Task


class TaskTable(DataTable):
    """
    Custom DataTable widget for displaying tasks

    Features:
    - Color-coded priorities (red/yellow/green)
    - Status indicators (✓/✗)
    - Sortable columns
    - Row selection
    """

    def __init__(self, **kwargs):
        """Initialize TaskTable with styling"""
        super().__init__(
            zebra_stripes=True,  # Alternating row colors
            cursor_type="row",   # Highlight full row
            **kwargs
        )

        # Store task ID mapping (row index → task ID)
        self._row_to_task_id = {}

    def on_mount(self) -> None:
        """Setup table columns when mounted"""
        self.add_columns_if_needed()

    def add_columns_if_needed(self) -> None:
        """Add table columns if not already added"""
        if len(self.columns) == 0:
            self.add_column("ID", width=6, key="id")
            self.add_column("Priority", width=12, key="priority")
            self.add_column("Tags", width=20, key="tags")
            self.add_column("Task", key="task")

    def update_from_state(self, state: AppState) -> None:
        """
        Update table data from app state

        Args:
            state: Application state with tasks, filters, sorting
        """
        # Clear existing rows
        self.clear()
        self._row_to_task_id = {}

        # Re-add columns (in case table was cleared)
        self.add_columns_if_needed()

        # Get filtered, sorted, paginated tasks
        tasks = state.get_current_page_tasks()

        # Populate rows
        for idx, task in enumerate(tasks):
            self.add_task_row(idx, task, state.view_mode)

    def add_task_row(self, row_idx: int, task: Task, view_mode: str) -> None:
        """
        Add a single task row to the table

        Args:
            row_idx: Row index in table (unused, kept for compatibility)
            task: Task object to display
            view_mode: "compact" or "detail"
        """
        # Build styled cells
        id_text = Text(str(task.id), style="dim")

        # Priority with color coding
        priority_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}.get(task.priority, "⚪")
        priority_label = {1: "HIGH", 2: "MED", 3: "LOW"}.get(task.priority, "???")
        priority_color = {1: "red", 2: "yellow", 3: "green"}.get(task.priority, "white")
        priority_text = Text(f"{priority_emoji} {priority_label}", style=priority_color)

        # Tags (comma-separated)
        tags_text = Text(task.get_tags_display(), style="cyan")

        # Task name with status
        status_icon = "✓" if task.done else "✗"
        status_color = "green" if task.done else "red"
        task_text = Text()
        task_text.append(status_icon, style=status_color)
        task_text.append(" " + task.name, style="")

        # Store task ID mapping for main row (use actual row count)
        current_row = len(self.rows)
        self._row_to_task_id[current_row] = task.id

        # Add main row
        self.add_row(id_text, priority_text, tags_text, task_text, key=str(task.id))

        # Add detail rows if in detail view
        if view_mode == "detail":
            if task.comment:
                # Map detail row to same task ID
                current_row = len(self.rows)
                self._row_to_task_id[current_row] = task.id

                comment_text = Text(f"  → {task.comment}", style="dim")
                self.add_row(Text(""), Text(""), Text(""), comment_text)

            if task.description:
                # Map detail row to same task ID
                current_row = len(self.rows)
                self._row_to_task_id[current_row] = task.id

                desc_text = Text(f"    {task.description}", style="dim italic")
                self.add_row(Text(""), Text(""), Text(""), desc_text)

    def get_selected_task_id(self) -> int | None:
        """
        Get the task ID of the currently selected row

        Returns:
            Task ID or None if no selection
        """
        if self.cursor_row >= 0 and self.cursor_row in self._row_to_task_id:
            return self._row_to_task_id[self.cursor_row]
        return None

    def select_task_by_id(self, task_id: int) -> bool:
        """
        Select row by task ID

        Args:
            task_id: Task ID to select

        Returns:
            True if task found and selected, False otherwise
        """
        # Find row index for this task ID
        for row_idx, tid in self._row_to_task_id.items():
            if tid == task_id:
                self.move_cursor(row=row_idx)
                return True
        return False
