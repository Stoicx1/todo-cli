from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from core.state import AppState
import shlex
from textwrap import dedent
from assistant import Assistant

gpt = Assistant()


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

    elif cmd == "undone" and len(parts) == 2:
        try:
            task_id = int(parts[1])
        except ValueError:
            state.messages.append("Invalid task ID")
            return
        for task in state.tasks:
            if task.id == task_id:
                task.done = False
                state.messages.append(f"[✓] Task {task_id} unmarked")
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

    elif cmd == "edit":
        if len(parts) < 2:
            state.messages.append(
                '[!] Usage: edit <id> "name" "comment" "description" priority "tag"'
            )
            return

        try:
            task_id = int(parts[1])
        except ValueError:
            state.messages.append("[!] Task ID must be a number")
            return

        task = next((t for t in state.tasks if t.id == task_id), None)
        if not task:
            state.messages.append(f"[!] Task {task_id} not found")
            return

        # Safely update each field if provided
        try:
            if len(parts) > 2 and parts[2] != "-":
                task.name = parts[2]
            if len(parts) > 3 and parts[3] != "-":
                task.comment = parts[3]
            if len(parts) > 4 and parts[4] != "-":
                task.description = parts[4]
            if len(parts) > 5 and parts[5].isdigit():
                task.priority = int(parts[5])
            if len(parts) > 6 and parts[6] != "-":
                task.tag = parts[6].lower().strip()

            state.messages.append(f"[~] Task {task_id} updated")
        except Exception as e:
            state.messages.append(f"[!] Failed to update task: {e}")

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

    elif cmd == "sort":
        if len(parts) < 2:
            state.messages.append(f'[!] Usage: sort "id" / "name / "priotiry"')
            return
        if len(parts) > 1 and parts[1] in ("id", "name", "priority"):
            state.sort = parts[1]
            state.messages.append(f"[~] Sorted by: {parts[1]}")

    elif cmd == "filter":
        if len(parts) < 2:
            state.messages.append(
                f'[!] Usage: filter "none" / "done" / "undone" / "tag:tagname"'
            )
            return

        arg = parts[1]
        if arg in ("none", "done", "undone") or arg.startswith("tag:"):
            state.filter = arg
            state.page = 0  # reset to first page when filter changes
            state.messages.append(f"[~] Filter set to: {arg}")
        else:
            state.messages.append(f"[!] Unknown filter: {arg}")

    elif cmd == "tags":
        tags = {t.tag.strip().lower() for t in state.tasks if t.tag}
        if tags:
            tag_list = ", ".join(sorted(tags))
            state.messages.append(
                f"[~] Tags in use: [bold green]{tag_list}[/bold green]"
            )
        else:
            state.messages.append("[~] No tags found.")

    elif cmd == "?":
        if not state.tasks:
            state.messages.append("[!] No tasks to analyze.")
            return

        user_prompt = Prompt.ask(
            "🤖 GPT Prompt", default="Which tasks should I prioritize today?"
        )
        gpt.console = console  # use your current rich console
        state.messages.append(dedent(gpt.ask(state.tasks, user_prompt)))

    elif cmd == "help":
        state.messages.append(
            (
                dedent(
                    """
[bold cyan]Available Commands:[/bold cyan]

[bold yellow]add[/bold yellow] "name" | "comment" | "description" | priority | tag
    Add a new task

[bold yellow]edit[/bold yellow] <id> "name" "comment" "description" priority "tag"
    Edit an existing task. Use "-" to skip a field

[bold yellow]done[/bold yellow] <id>
    Mark task as done

[bold yellow]undone[/bold yellow] <id>
    Mark task as not done

[bold yellow]remove[/bold yellow] <id>
    Remove task by ID

[bold yellow]view[/bold yellow] compact | detail
    Toggle between compact and detailed view

[bold yellow]next[/bold yellow] / [bold yellow]prev[/bold yellow]
    Paginate through task pages

[bold yellow]sort[/bold yellow] id | name | priority
    Sort tasks by ID, name, or priority (ascending)

[bold yellow]filter[/bold yellow] none | done | undone | tag:<tag>
    Filter tasks by status or tag
    Example: filter tag:psdc

[bold yellow]tags[/bold yellow]
    Show all unique tags in use

[bold yellow]?[/bold yellow]
    Ask for an assistance

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
