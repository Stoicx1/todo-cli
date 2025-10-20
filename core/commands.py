from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from core.state import AppState
import shlex
from textwrap import dedent
from assistant import Assistant


gpt = Assistant()

# Command shortcuts and aliases
SHORTCUTS = {
    # Single-letter shortcuts
    'd': 'done',
    'u': 'undone',
    'r': 'remove',
    'e': 'edit',
    's': 'show',
    'n': 'next',
    'p': 'prev',
    'f': 'filter',
    't': 'tags',
    'h': 'help',
    'x': 'exit',
    # Aliases
    'delete': 'remove',  # delete is alias for remove
    'del': 'remove'      # del is also alias for remove
}


def parse_task_ids(id_args: list) -> list:
    """
    Parse task IDs from arguments, supporting:
    - Single IDs: 1 2 3
    - Ranges: 1-5
    - Mixed: 1,3,5-8
    Returns list of unique integer IDs
    """
    ids = set()
    for arg in id_args:
        # Handle comma-separated IDs
        for part in arg.replace(',', ' ').split():
            # Handle ranges (e.g., 1-5)
            if '-' in part:
                try:
                    start, end = part.split('-')
                    start, end = int(start.strip()), int(end.strip())
                    ids.update(range(start, end + 1))
                except ValueError:
                    continue  # Skip invalid ranges
            else:
                # Single ID
                try:
                    ids.add(int(part.strip()))
                except ValueError:
                    continue  # Skip invalid IDs
    return sorted(list(ids))


def parse_command(command: str, state: AppState, console: Console):
    parts = shlex.split(command.strip())
    if not parts:
        state.messages = []
        return
    state.messages = []

    # Expand shortcuts
    cmd = parts[0].lower()
    if cmd in SHORTCUTS:
        parts[0] = SHORTCUTS[cmd]
        cmd = parts[0]

    state.messages.append(f"[debug] Parsed parts: {parts}")
    return cmd, parts


def handle_add(command_arguments: list, state: AppState, console: Console):
    """
    Parses arguments from the 'add' command and adds a new task to the application state.

    Supports flexible input formats:
    - Minimum: add "name"
    - With priority or tag: add "name" 2 or add "name" "tag"
    - With comment and description: add "name" "comment" "description"
    - Full: add "name" "comment" "description" priority "tag"

    Args:
        command_arguments (list): Tokenized command input.
        state (AppState): The current application state, used to store the new task.
        console (Console): Rich console for output (not directly used here).
    """

    # Ensure the task name is provided
    if len(command_arguments) < 2:
        state.messages.append(
            '[!] Usage: add "name" ["comment"] ["description"] [priority] ["tag"]\n    Example: add "Fix bug" "urgent" "Fix the login issue" 1 "work"'
        )
        return

    # Initialize all variables with defaults (CRITICAL BUG FIX)
    name = command_arguments[1]
    comment = ""
    description = ""
    priority = 3
    tag = ""

    # Case: name and either priority or tag
    if len(command_arguments) == 3:
        if command_arguments[2].isdigit():
            priority = int(command_arguments[2])
        else:
            tag = command_arguments[2]

    # Case: name + priority+tag or comment+description
    elif len(command_arguments) == 4:
        if command_arguments[2].isdigit():
            priority = int(command_arguments[2])
            tag = command_arguments[3]
        else:
            comment = command_arguments[2]
            description = command_arguments[3]

    # Case: full input (name, comment, description, priority, tag)
    elif len(command_arguments) >= 5:
        comment = command_arguments[2]
        description = command_arguments[3]
        try:
            priority = int(command_arguments[4])  # Validate priority is a number
        except ValueError:
            state.messages.append(f'[!] Priority must be a number, got: "{command_arguments[4]}"\n    Example: add "Task" "comment" "description" 1 "tag"')
            return
        tag = command_arguments[5] if len(command_arguments) > 5 else ""

    # Add the parsed task to state
    state.add_task(name, comment, description, priority, tag)
    state.messages.append(f"[+] Added task: {name}")


def handle_done(command_arguments: list, state: AppState, console: Console):
    """
    Marks the specified task(s) as done based on the task ID(s).
    Supports bulk operations: done 1 2 3, done 1-5, done 1,3,5-8

    Args:
        command_arguments (list): List of parsed input tokens, expecting task ID(s) starting at index 1.
        state (AppState): The current application state with all tasks.
        console (Console): Rich console instance (not used directly here).
    """
    from datetime import datetime

    # Check if task ID was provided
    if len(command_arguments) < 2:
        state.messages.append('[!] Usage: done <id> [id2 id3...]\n    Example: done 3\n    Bulk: done 1 2 3 or done 1-5')
        return

    # Parse all task IDs (supports ranges and multiple IDs)
    task_ids = parse_task_ids(command_arguments[1:])

    if not task_ids:
        state.messages.append('[!] No valid task IDs provided\n    Example: done 3 or done 1-5')
        return

    # Mark all found tasks as done
    marked = []
    not_found = []

    for task_id in task_ids:
        task = next((t for t in state.tasks if t.id == task_id), None)
        if task:
            task.done = True
            task.completed_at = datetime.now().isoformat()
            marked.append(task_id)
        else:
            not_found.append(task_id)

    # Build result message
    if marked:
        if len(marked) == 1:
            state.messages.append(f"[✓] Task {marked[0]} marked as done")
        else:
            state.messages.append(f"[✓] Tasks {', '.join(map(str, marked))} marked as done")

    if not_found:
        state.messages.append(f"[!] Tasks not found: {', '.join(map(str, not_found))}")


def handle_undone(command_arguments: list, state: AppState, console: Console):
    """
    Unmarks the specified task(s) (sets 'done' to False) based on the task ID(s).
    Supports bulk operations: undone 1 2 3, undone 1-5, undone 1,3,5-8

    Args:
        command_arguments (list): List of parsed input tokens, expecting task ID(s) starting at index 1.
        state (AppState): The current application state with all tasks.
        console (Console): Rich console instance (not used directly here).
    """
    # Check if task ID was provided
    if len(command_arguments) < 2:
        state.messages.append('[!] Usage: undone <id> [id2 id3...]\n    Example: undone 3\n    Bulk: undone 1 2 3 or undone 1-5')
        return

    # Parse all task IDs (supports ranges and multiple IDs)
    task_ids = parse_task_ids(command_arguments[1:])

    if not task_ids:
        state.messages.append('[!] No valid task IDs provided\n    Example: undone 3 or undone 1-5')
        return

    # Unmark all found tasks
    unmarked = []
    not_found = []

    for task_id in task_ids:
        task = next((t for t in state.tasks if t.id == task_id), None)
        if task:
            task.done = False
            task.completed_at = ""  # Clear completion timestamp
            unmarked.append(task_id)
        else:
            not_found.append(task_id)

    # Build result message
    if unmarked:
        if len(unmarked) == 1:
            state.messages.append(f"[✓] Task {unmarked[0]} unmarked")
        else:
            state.messages.append(f"[✓] Tasks {', '.join(map(str, unmarked))} unmarked")

    if not_found:
        state.messages.append(f"[!] Tasks not found: {', '.join(map(str, not_found))}")


def handle_command(command: str, state: AppState, console: Console):
    try:
        cmd, parts = parse_command(command, state, console)
    except Exception as e:
        return

    if cmd == "add":
        handle_add(parts, state, console)

    elif cmd == "done":
        handle_done(parts, state, console)

    elif cmd == "undone":
        handle_undone(parts, state, console)

    elif cmd == "remove":
        if len(parts) < 2:
            state.messages.append('[!] Usage: remove <id> [id2 id3...]\n    Example: remove 3\n    Bulk: remove 1 2 3 or remove 1-5')
            return

        # Parse all task IDs (supports ranges and multiple IDs)
        task_ids = parse_task_ids(parts[1:])

        if not task_ids:
            state.messages.append('[!] No valid task IDs provided\n    Example: remove 3 or remove 1-5')
            return

        # Remove all found tasks
        removed = []
        not_found = []

        for task_id in task_ids:
            task = next((t for t in state.tasks if t.id == task_id), None)
            if task:
                state.tasks.remove(task)
                removed.append(task_id)
            else:
                not_found.append(task_id)

        # Build result message
        if removed:
            if len(removed) == 1:
                state.messages.append(f"[-] Removed task {removed[0]}")
            else:
                state.messages.append(f"[-] Removed tasks {', '.join(map(str, removed))}")

        if not_found:
            state.messages.append(f"[!] Tasks not found: {', '.join(map(str, not_found))}")

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
                # Parse tags - split by comma if multiple tags provided
                tag_str = parts[6]
                if ',' in tag_str:
                    tag_list = [t.strip().lower() for t in tag_str.split(',') if t.strip()]
                    tag_list = tag_list[:3]  # Limit to 3 tags
                else:
                    tag_list = [tag_str.strip().lower()] if tag_str.strip() else []

                # Update both legacy and new tag fields
                task.tag = tag_list[0] if tag_list else ""
                task.tags = tag_list

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

    elif cmd == "show":
        if len(parts) < 2:
            state.messages.append(f'[!] Usage: show "task_id"')
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

        # Initialize table fresh each time
        table = Table(show_header=False, box=None, pad_edge=False)
        table.add_column("Field", style="bold cyan", no_wrap=True)
        table.add_column("Value", style="white", max_width=60, overflow="fold")

        table.add_row("Task", task.name)
        table.add_row("Comment", task.comment)
        table.add_row("Description", task.description)
        table.add_row("Priority", str(task.priority))
        table.add_row("Tag", task.tag)
        table.add_row("Status", "✓" if task.done else "✗")

        temp_console = Console(width=100, record=True)
        temp_console.print(table)
        text_output = temp_console.export_text()
        state.messages.append(text_output)

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

    elif cmd == "save":
        # Manual save command
        state.save_to_file("tasks.json", console)
        state.messages.append("[💾] Tasks saved successfully")

    elif cmd == "help":
        state.messages.append(
            (
                dedent(
                    """
[bold cyan]💡 Quick Start:[/bold cyan]
Type [bold magenta]/[/bold magenta] to see all commands with descriptions in a dropdown menu!

[bold cyan]📝 Common Commands:[/bold cyan]
  [yellow]add[/yellow]              →  Add a new task (opens form)
  [yellow]done[/yellow] <id>        →  Mark task as complete
  [yellow]edit[/yellow] <id>        →  Edit existing task
  [yellow]remove[/yellow] <id>      →  Delete a task

[bold cyan]🔍 Filtering & Sorting:[/bold cyan]
  [yellow]filter[/yellow] done      →  Show completed tasks only
  [yellow]filter[/yellow] undone    →  Show incomplete tasks only
  [yellow]filter[/yellow] tag:name  →  Filter by tag
  [yellow]sort[/yellow] priority    →  Sort by priority
  [yellow]tags[/yellow]             →  List all tags

[bold cyan]🤖 AI Features (No API Key Needed!):[/bold cyan]
  [yellow]insights[/yellow]         →  Comprehensive task analysis
  [yellow]suggest[/yellow]          →  Smart recommendations

[bold cyan]🎨 Other:[/bold cyan]
  [yellow]view[/yellow] compact     →  Switch to compact view (20/page)
  [yellow]next[/yellow] / [yellow]prev[/yellow]    →  Navigate pages
  [yellow]help[/yellow]             →  Show this help
  [yellow]exit[/yellow]             →  Save and quit

[dim]💡 Tip: Start typing any command for auto-complete suggestions![/dim]
        """
                )
            )
        )

    else:
        state.messages.append("Unknown or incomplete command")
