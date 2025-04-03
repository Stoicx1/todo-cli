from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from core.state import AppState
import shlex
from textwrap import dedent


def handle_command(command: str, state: AppState, console: Console):
    parts = shlex.split(command.strip())
    if not parts:
        state.messages = []
        return

    cmd = parts[0].lower()
    state.messages = []
    state.messages.append(f"[debug] Parsed parts: {parts}")

    if cmd == "add":
        if len(parts) < 2:
            state.messages.append(
                f'[!] Usage: add "name" | "comment" | "description" | priority | tag'
            )
            return

        name = parts[1]
        comment = ""
        description = ""
        priority = 3
        tag = ""

        if len(parts) == 3:
            if parts[2].isdigit():
                priority = int(parts[2])
            else:
                tag = parts[2]

        elif len(parts) == 4:
            if parts[2].isdigit():
                priority = int(parts[2])
                tag = parts[3]
            else:
                comment = parts[2]
                description = parts[3]

        elif len(parts) >= 5:
            comment = parts[2]
            description = parts[3]
            try:
                priority = int(parts[4])
            except ValueError:
                state.messages.append("[!] Priority must be a number")
                return
            tag = parts[5] if len(parts) > 5 else ""

        state.add_task(name, comment, description, priority, tag)
        state.messages.append(f"[+] Added task: {name}")

    elif cmd == "done" and len(parts) == 2:
        try:
            task_id = int(parts[1])
        except ValueError:
            state.messages.append("Invalid task ID")
            return
        for task in state.tasks:
            if task.id == task_id:
                task.done = True
                state.messages.append(f"[✓] Task {task_id} marked as done")
                return
        state.messages.append(f"[!] Task {task_id} not found")

    elif cmd == "remove" and len(parts) == 2:
        try:
            task_id = int(parts[1])
        except ValueError:
            state.messages.append("Invalid task ID")
            return
        before = len(state.tasks)
        state.tasks = [t for t in state.tasks if t.id != task_id]
        if len(state.tasks) < before:
            state.messages.append(f"[-] Removed task {task_id}")
        else:
            state.messages.append(f"[!] Task {task_id} not found")

    elif cmd == "next":
        # Ensure next only works if there are more tasks to show
        if (state.page + 1) * state.page_size < len(state.tasks):
            state.page += 1
            state.messages.append("→ Next page")
        else:
            state.messages.append("[!] No more pages")

    elif cmd == "prev":
        if state.page > 0:
            state.page -= 1
            state.messages.append("← Previous page")
        else:
            state.messages.append("[!] Already on the first page")

    elif cmd == "view":
        if len(parts) > 1 and parts[1] in ("compact", "detail"):
            state.view_mode = parts[1]
            state.messages.append(f"[~] Switched to view: {parts[1]}")

    elif cmd == "help":
        state.messages.append(
            (
                dedent(
                    """
[bold cyan]Available Commands:[/bold cyan]

[bold yellow]add[/bold yellow] "name" | "comment" | "description" | priority | tag
    Add a new task

[bold yellow]done[/bold yellow] <id>
    Mark task as done

[bold yellow]remove[/bold yellow] <id>
    Remove task by ID

[bold yellow]next[/bold yellow] / [bold yellow]prev[/bold yellow]
    Pagination for task pages

[bold yellow]view[/bold yellow] compact | detail
    Toggle between compact and detailed view

[bold yellow]help[/bold yellow]
    Show this help message

[bold yellow]quit[/bold yellow] / [bold yellow]exit[/bold yellow]
    Exit the application
"""
                )
            )
        )

    else:
        state.messages.append("Unknown or incomplete command")
