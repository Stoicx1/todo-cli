from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from core.state import AppState
import sys

# Unicode/emoji support detection for Windows compatibility
USE_UNICODE = (
    sys.stdout.encoding and
    sys.stdout.encoding.lower() in ('utf-8', 'utf8')
)


def render_info_lines(console: Console, state: AppState):
    """
    Render two clean info lines under the table.
    Line 1: Most important stats
    Line 2: Context/navigation info
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
    # Format: page | showing | view | sort
    if USE_UNICODE:
        line1_parts = [
            f"📄 Page [cyan]{current_page}[/cyan][dim]/{total_pages}[/dim]",
            f"👁️  [white]{shown}[/white][dim]/{total}[/dim] showing",
            f"🎨 [magenta]{state.view_mode}[/magenta]",
            f"↕️  [blue]{state.sort}[/blue]"
        ]
    else:
        line1_parts = [
            f"Page [cyan]{current_page}[/cyan][dim]/{total_pages}[/dim]",
            f"[white]{shown}[/white][dim]/{total}[/dim] showing",
            f"[magenta]{state.view_mode}[/magenta]",
            f"Sort: [blue]{state.sort}[/blue]"
        ]
    line1 = " | ".join(line1_parts)

    # Line 2: Task statistics
    # Format: tasks | done | todo
    if USE_UNICODE:
        line2_parts = [
            f"📊 [cyan]{total}[/cyan] tasks",
            f"✅ [green]{completed}[/green] done",
            f"⏳ [yellow]{incomplete}[/yellow] todo"
        ]
    else:
        line2_parts = [
            f"[cyan]{total}[/cyan] tasks",
            f"[green]{completed}[/green] done",
            f"[yellow]{incomplete}[/yellow] todo"
        ]

    # Add filter info if active (appended to line 2)
    if state.filter != "none":
        if USE_UNICODE:
            line2_parts.append(f"🔍 [yellow]{state.filter}[/yellow]")
        else:
            line2_parts.append(f"Filter: [yellow]{state.filter}[/yellow]")

    line2 = " | ".join(line2_parts)

    # Print both lines
    console.print()  # Empty line for spacing
    console.print(line1)
    console.print(f"[dim]{line2}[/dim]")
    console.print()  # Empty line before prompt


def render_dashboard(console: Console, state: AppState):
    tasks = state.get_current_page_tasks()
    mode = state.view_mode

    # Use SIMPLE box style for cleaner, CLI-friendly output (no heavy borders)
    from rich.box import SIMPLE

    table = Table(
        show_header=True,
        header_style="bold cyan",  # Less jarring than magenta
        expand=True,
        box=SIMPLE,  # Clean lines, no heavy borders
        show_edge=False  # Remove outer borders
    )
    # Column order optimized for wide screens: ID | Priority | Tags | Task
    table.add_column("ID", justify="center", no_wrap=True, style="dim", width=4)
    table.add_column("Priority", justify="center", no_wrap=True, width=10)
    table.add_column("Tags", justify="left", style="cyan", width=20)
    table.add_column("Task", justify="left")

    for idx, task in enumerate(tasks):
        # Alternating row background colors for better tracking on wide screens
        # Even rows: darker gray, Odd rows: lighter gray
        row_style = "on grey11" if idx % 2 == 0 else "on grey15"

        # Status and priority icons with ASCII fallback
        if USE_UNICODE:
            status_icon = "✓" if task.done else "✗"
            priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
            priority_icon = priority_icons.get(task.priority, "⚪")
        else:
            status_icon = "Y" if task.done else "N"
            priority_icons = {1: "!", 2: "·", 3: "-"}
            priority_icon = priority_icons.get(task.priority, "?")

        # Status color
        status_color = "green" if task.done else "red"

        # Priority labels
        priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
        priority_label = priority_labels.get(task.priority, "???")

        # Integrate status into task name
        task_display = f"[{status_color}]{status_icon}[/{status_color}] {task.name}"

        # Format priority with icon and label
        priority_display = f"{priority_icon} {priority_label}"

        # Handle multiple tags (up to 3, comma-separated)
        tags_display = task.get_tags_display()

        # Column order: ID | Priority | Tags | Task (reordered for better readability)
        table.add_row(
            str(task.id),
            priority_display,
            tags_display,
            task_display,
            style=row_style,
        )

        # Detail view - show comment and description under Task column
        if mode == "detail":
            arrow = "→" if USE_UNICODE else "->"
            if task.comment:
                # Empty cells for ID, Priority, Tags; comment under Task column
                table.add_row("", "", "", f"  [dim]{arrow} {task.comment}[/dim]", style=row_style)
            if task.description:
                # Empty cells for ID, Priority, Tags; description under Task column
                table.add_row("", "", "", f"    [dim italic]{task.description}[/dim italic]", style=row_style)

    console.clear()
    console.print(table)

    # Show two clean info lines under the table
    render_info_lines(console, state)

    # Show messages if any (in a compact way)
    if state.messages:
        last_msg = state.messages[-1]

        # Check if message is a special renderable object (like Panel)
        if isinstance(last_msg, tuple) and len(last_msg) == 2 and last_msg[0] == "__PANEL__":
            # Render the panel directly without text conversion
            console.print(last_msg[1])
            console.print()  # Add spacing after panel
        else:
            # Show regular message inline
            if USE_UNICODE:
                console.print(f"[dim]💬 {last_msg}[/dim]\n")
            else:
                console.print(f"[dim]{last_msg}[/dim]\n")
