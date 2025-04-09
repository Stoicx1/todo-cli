from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from core.state import AppState


def render_dashboard(console: Console, state: AppState):
    tasks = state.get_current_page_tasks()
    mode = state.view_mode

    table = Table(show_header=True, header_style="bold black on magenta", expand=True)
    table.add_column("ID", justify="center", no_wrap=True)
    table.add_column("Task", justify="left")
    table.add_column("Tag", justify="left")
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")

    for idx, task in enumerate(tasks):
        row_style = "bold white on black" if idx % 2 == 0 else "bold black on white"
        status = "[green]✓[/green]" if task.done else "[red]✗[/red]"
        table.add_row(
            str(task.id),
            task.name,
            task.tag,
            str(task.priority),
            status,
            style=row_style,
        )
        if mode == "detail":
            if task.comment:
                table.add_row("", f"→ {task.comment}", "", "", "", style=row_style)
            if task.description:
                table.add_row("", f"  {task.description}", "", "", "", style=row_style)

    console.clear()
    console.print(table)
    total = len(state.tasks)
    shown = len(tasks)
    console.print(
        f"[dim]| Showing {shown}/{total} | page {state.page + 1} | View: {state.view_mode} | Filter: {state.filter} | Sort: {state.sort}[/dim]"
    )

    console.print("\n")

    if state.messages:
        last_msg = state.messages[-1]
        status_text = Text.from_markup(f"{last_msg}")
        console.print(Panel(status_text, style="dim", title="STATUS", padding=(1, 1)))
