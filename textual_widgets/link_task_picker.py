"""
LinkTaskPicker - Modal to pick a task to link a note to.
"""

from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import DataTable, Static, Input
from textual.app import ComposeResult

from models.task import Task


class LinkTaskPicker(ModalScreen[int | None]):
    """Modal that shows a table of tasks and returns selected task id on Enter."""

    DEFAULT_CSS = """
    LinkTaskPicker { align: center middle; }
    LinkTaskPicker > Container { width: 80; max-width: 95; height: 30; border: thick cyan; background: $surface; padding: 1 1; }
    LinkTaskPicker DataTable { height: 1fr; }
    """

    BINDINGS = [("escape", "cancel", "Close"), ("enter", "choose", "Choose")]

    def __init__(self, tasks: list[Task], **kwargs):
        super().__init__(**kwargs)
        self._tasks = tasks
        self._table: DataTable | None = None

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("[bold cyan]Select a task to link[/bold cyan]", id="title")
            yield Input(placeholder="Type to filter tasks...", id="filter")
            table = DataTable(zebra_stripes=True, cursor_type="row")
            self._table = table
            table.add_column("ID", width=6)
            table.add_column("Prio", width=4)
            table.add_column("Tag", width=10)
            table.add_column("Task")
            self._all_tasks = list(self._tasks)
            self._populate_rows(self._all_tasks)
            yield table

    def _populate_rows(self, tasks: list[Task]) -> None:
        if not self._table:
            return
        self._table.clear()
        for t in tasks:
            pr_label = {1: "H", 2: "M", 3: "L"}.get(t.priority, "?")
            self._table.add_row(str(t.id), pr_label, t.tag or "", t.name or "")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter":
            return
        query = (event.value or "").lower().strip()
        if not query:
            self._populate_rows(self._all_tasks)
            return
        filtered = []
        for t in self._all_tasks:
            if query in (t.name or "").lower() or query in (t.tag or "").lower() or query == str(t.id):
                filtered.append(t)
        self._populate_rows(filtered)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_choose(self) -> None:
        if not self._table or self._table.cursor_row < 0:
            self.dismiss(None)
            return
        row = self._table.cursor_row
        try:
            task_id = int(self._table.rows[row].cells[0].plain)
        except Exception:
            task_id = None
        self.dismiss(task_id)
