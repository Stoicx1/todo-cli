from utils.emoji import emoji
from utils.terminal import clear_screen, print_rich_with_prompt_toolkit
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from core.state import AppState
from utils.time import humanize_age
from config import USE_UNICODE
from datetime import datetime

def _humanize_age(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso) if iso else None
        if not dt:
            return "-"
        now = datetime.now(dt.tzinfo) if getattr(dt, "tzinfo", None) else datetime.now()
        diff = now - dt
        s = int(diff.total_seconds())
        if s < 60:
            return f"{s}s"
        m = s // 60
        if m < 60:
            return f"{m}m"
        h = m // 60
        if h < 24:
            return f"{h}h"
        d = h // 24
        if d < 365:
            return f"{d}d"
        y = d // 365
        return f"{y}y"
    except Exception:
        return "-"


def _render_ai_panel(console: Console, state: AppState):
    """
    Render the persistent AI panel between the table and the prompt.

    - Shows tail of state.ai_text with scroll via state.ai_scroll
    - Dynamic height; shows streaming indicator
    """
    text = getattr(state, "ai_text", "") or ""
    streaming = getattr(state, "ai_streaming", False)
    if not text and not streaming:
        return

    try:
        term_h = console.size.height
    except Exception:
        term_h = 30
    panel_h = max(8, min(12, term_h // 3))

    lines = text.splitlines()
    total = len(lines)
    scroll = max(0, min(getattr(state, "ai_scroll", 0), max(0, total - 1)))
    end = total - scroll
    start = max(0, end - panel_h)
    visible = lines[start:end]

    if total > 0:
        footer = f"[dim]Lines {start+1}-{end}/{total}  •  Ctrl+Up/Down PgUp/PgDn Ctrl+Home/End[/dim]"
    else:
        footer = "[dim](waiting for output)[/dim]"

    body = "\n".join(visible) if visible else ("[dim]" + ("Streaming..." if streaming else "(no output)") + "[/dim]")
    title = "AI Answer (streaming)" if streaming else "AI Answer"

    panel = Panel(
        body + "\n\n" + footer,
        title=f"[bold cyan]{title}[/bold cyan]",
        title_align="left",
        border_style="cyan",
        box=ROUNDED,
        padding=(0, 1),
        expand=True,
    )
    console.print(panel)
    console.print()

def render_info_lines(console: Console, state: AppState):
    """
    Render professional status panel under the table.
    Shows navigation, statistics, and filter info in a bordered panel.
    """
    total = len(state.tasks)
    completed = sum(1 for t in state.tasks if t.done)
    incomplete = total - completed
    shown = len(state.get_current_page_tasks())

    # Calculate total pages
    filtered_tasks = state.get_filter_tasks(state.tasks)
    total_pages = (len(filtered_tasks) + state.page_size - 1) // state.page_size if len(filtered_tasks) > 0 else 1
    current_page = state.page + 1

    # Line 1: Navigation and view context
    # Format: page • showing • view • sort
    if USE_UNICODE:
        order_icon = "↑" if getattr(state, "sort_order", "asc") == "asc" else "↓"
        line1_parts = [
            f"Page [cyan]{current_page}[/cyan][dim]/{total_pages}[/dim]",
            f"[white]{shown}[/white][dim]/{total}[/dim] showing",
            f"[magenta]{state.view_mode}[/magenta]",
            f"{order_icon} [blue]{state.sort}[/blue] [dim]({state.sort_order})[/dim]"
        ]
    else:
        order_text = "ASC" if getattr(state, "sort_order", "asc") == "asc" else "DESC"
        line1_parts = [
            f"Page [cyan]{current_page}[/cyan][dim]/{total_pages}[/dim]",
            f"[white]{shown}[/white][dim]/{total}[/dim] showing",
            f"[magenta]{state.view_mode}[/magenta]",
            f"Sort: [blue]{state.sort}[/blue] [dim]({order_text})[/dim]"
        ]
    line1 = "  •  ".join(line1_parts)

    # Line 2: Task statistics
    # Format: tasks • done • todo • filter
    if USE_UNICODE:
        line2_parts = [
            f"[cyan]{total}[/cyan] tasks",
            f"[green]{completed}[/green] done",
            f"[yellow]{incomplete}[/yellow] todo"
        ]
    else:
        line2_parts = [
            f"[cyan]{total}[/cyan] tasks",
            f"[green]{completed}[/green] done",
            f"[yellow]{incomplete}[/yellow] todo"
        ]

    # Add filter info if active (appended to line 2)
    if state.filter != "none":
        line2_parts.append(f"Filter: [yellow]{state.filter}[/yellow]")

    line2 = "  •  ".join(line2_parts)

    # Create professional panel with border
    content = f"{line1}\n[dim]{line2}[/dim]"
    panel = Panel(
        content,
        title="[bold cyan]Status[/bold cyan]",
        title_align="left",
        border_style="cyan",
        box=ROUNDED,
        padding=(0, 1),
        expand=False
    )

    # Print panel with spacing
    console.print()  # Empty line for spacing
    console.print(panel)
    console.print()  # Empty line before prompt


def render_dashboard(console: Console, state: AppState, use_prompt_toolkit: bool = True):
    """
    Render the dashboard with task table, status panel, and messages.

    Args:
        console: Rich console instance (only used for terminal size detection)
        state: Application state
        use_prompt_toolkit: If True, uses prompt_toolkit integration for rendering (default: True)
    """
    tasks = state.get_current_page_tasks()
    mode = state.view_mode

    # Use SIMPLE box style for cleaner, CLI-friendly output (no heavy borders)
    from rich.box import SIMPLE

    # Clear screen first
    clear_screen()

    # Define rendering function
    def _render_content(c: Console):
        # Build table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            expand=True,
            box=SIMPLE,
            show_edge=False
        )
        table.add_column("ID", justify="center", no_wrap=True, style="dim", width=4)
        table.add_column("Age", justify="center", no_wrap=True, width=4)
        table.add_column("Prio", justify="center", no_wrap=True, width=6)
        table.add_column("Tags", justify="left", style="cyan", width=20)
        table.add_column("Task", justify="left")

        for idx, task in enumerate(tasks):
            row_style = "" if idx % 2 == 0 else "on grey15"

            if USE_UNICODE:
                status_icon = "✓" if task.done else "✗"
                priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
                priority_icon = priority_icons.get(task.priority, "⚪")
            else:
                status_icon = "Y" if task.done else "N"
                priority_icons = {1: "!", 2: "·", 3: "-"}
                priority_icon = priority_icons.get(task.priority, "?")

            status_color = "green" if task.done else "red"
            priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
            priority_label = priority_labels.get(task.priority, "?")
            task_display = f"[{status_color}]{status_icon}[/{status_color}] {task.name}"
            priority_label = priority_labels.get(task.priority, "?")
            tags_display = task.get_tags_display()
            priority_display = f"{priority_icon} {priority_label}"
            age_display = humanize_age(getattr(task, "created_at", ""))
            table.add_row(
                str(task.id),
                age_display,
                priority_display,
                tags_display,
                task_display,
                style=row_style,
            )
            if mode == "detail":
                arrow = emoji("?", "->")
                if task.comment:
                    table.add_row("", "", "", f"  [dim]{arrow} {task.comment}[/dim]", style=row_style)
                if task.description:
                    table.add_row("", "", "", f"    [dim italic]{task.description}[/dim italic]", style=row_style)

        # Print table
        c.print(table)

        # Render status panel
        render_info_lines(c, state)

        # Render AI panel if active
        _render_ai_panel(c, state)

        # Render messages
        if state.messages:
            last_msg = state.messages[-1]
            if isinstance(last_msg, tuple) and len(last_msg) == 2 and last_msg[0] == "__PANEL__":
                c.print(last_msg[1])
                c.print()
