from typing import Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from core.state import AppState
import shlex
from textwrap import dedent
from datetime import datetime
from assistant import Assistant
from ui.feedback import (
    confirm,
    OperationSummary
)
from utils.tag_parser import parse_tags
from utils.validators import validate_priority, sanitize_comment, sanitize_description, clamp_priority
from config import ui, USE_UNICODE, DEBUG_PARSER
from utils.emoji import emoji


# Command aliases - Single source of truth for all shortcuts
# Consolidated from COMMAND_ALIASES and SHORTCUTS (Phase 4.1)
COMMAND_ALIASES = {
    # Single-letter shortcuts (primary)
    'a': 'add',
    'e': 'edit',
    'x': 'done',       # x = done (not exit, use 'q' for quit)
    'd': 'done',       # d = done (alternative to 'x')
    'u': 'undone',
    'n': 'next',
    'p': 'prev',
    's': 'show',
    'v': 'view',
    'f': 'filter',
    't': 'tags',
    'h': 'help',
    'q': 'exit',       # q = quit/exit

    # Additional shortcuts
    'r': 'remove',
    'so': 'sort',

    # Word aliases
    'delete': 'remove',
    'del': 'remove',
    'quit': 'exit',
}

# Deprecated - kept for backward compatibility (Phase 4.1)
# Use COMMAND_ALIASES instead
SHORTCUTS = COMMAND_ALIASES


gpt = Assistant()


def get_relative_time(iso_timestamp: str) -> str:
    """Convert ISO timestamp to relative time (e.g., '2 days ago')"""
    if not iso_timestamp:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 2592000:  # 30 days
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 31536000:  # 365 days
            months = int(seconds / 2592000)
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = int(seconds / 31536000)
            return f"{years} year{'s' if years != 1 else ''} ago"
    except (ValueError, AttributeError):
        return "Unknown"


def parse_task_ids(id_args: list[str]) -> list[int]:
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


def parse_command(command: str, state: AppState, console: Console) -> Optional[tuple[str, list[str]]]:
    parts = shlex.split(command.strip())
    if not parts:
        state.messages = []
        return None
    state.messages = []

    # Expand shortcuts
    cmd = parts[0].lower()
    if cmd in SHORTCUTS:
        parts[0] = SHORTCUTS[cmd]
        cmd = parts[0]

    if DEBUG_PARSER:
        state.messages.append(f"[debug] Parsed parts: {parts}")
    return cmd, parts


def handle_add(command_arguments: list[str], state: AppState, console: Console) -> None:
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
            '[red]?[/red] Usage: add "name" ["comment"] ["description"] [priority] ["tag"]\n    Example: add "Fix bug" "urgent" "Fix the login issue" 1 "work"'
        )
        return

    # Initialize all variables with defaults
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

        # Validate priority using utility
        is_valid, error, validated_priority = validate_priority(command_arguments[4])
        if not is_valid:
            state.messages.append(f'[red]?[/red] {error}\n    Example: add "Task" "comment" "description" 1 "tag"')
            return
        priority = validated_priority

        tag = command_arguments[5] if len(command_arguments) > 5 else ""

    # Sanitize text inputs (enforces length limits)
    comment = sanitize_comment(comment)
    description = sanitize_description(description)

    # Clamp priority to valid range (auto-correct)
    priority = clamp_priority(priority)

    # Add the parsed task to state (will use parse_tags internally)
    state.add_task(name, comment, description, priority, tag)
    state.messages.append(f"[green]?[/green] Added task: {name}")


def handle_done(command_arguments: list[str], state: AppState, console: Console) -> None:
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
        state.messages.append('[red]?[/red] Usage: done <id> [id2 id3...]\n    Example: done 3\n    Bulk: done 1 2 3 or done 1-5')
        return

    # Parse all task IDs (supports ranges and multiple IDs)
    task_ids = parse_task_ids(command_arguments[1:])

    if not task_ids:
        state.messages.append('[red]?[/red] No valid task IDs provided\n    Example: done 3 or done 1-5')
        return

    # Mark all found tasks as done (using O(1) index lookup)
    marked = []
    not_found = []

    for task_id in task_ids:
        task = state.get_task_by_id(task_id)  # O(1) lookup instead of O(n)
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
        state.messages.append(f"[red]?[/red] Tasks not found: {', '.join(map(str, not_found))}")


def handle_undone(command_arguments: list[str], state: AppState, console: Console) -> None:
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
        state.messages.append('[red]?[/red] Usage: undone <id> [id2 id3...]\n    Example: undone 3\n    Bulk: undone 1 2 3 or undone 1-5')
        return

    # Parse all task IDs (supports ranges and multiple IDs)
    task_ids = parse_task_ids(command_arguments[1:])

    if not task_ids:
        state.messages.append('[red]?[/red] No valid task IDs provided\n    Example: undone 3 or undone 1-5')
        return

    # Unmark all found tasks (using O(1) index lookup)
    unmarked = []
    not_found = []

    for task_id in task_ids:
        task = state.get_task_by_id(task_id)  # O(1) lookup
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
        state.messages.append(f"[red]?[/red] Tasks not found: {', '.join(map(str, not_found))}")


def handle_command(command: str, state: AppState, console: Console) -> None:
    try:
        cmd, parts = parse_command(command, state, console)
    except Exception as e:
        return

    # Map command aliases to full commands
    if cmd in COMMAND_ALIASES:
        cmd = COMMAND_ALIASES[cmd]

    if cmd == "add":
        handle_add(parts, state, console)

    elif cmd == "done":
        handle_done(parts, state, console)

    elif cmd == "undone":
        handle_undone(parts, state, console)

    elif cmd == "remove":
        if len(parts) < 2:
            state.messages.append('[red]?[/red] Usage: remove <id> [id2 id3...]\n    Example: remove 3\n    Bulk: remove 1 2 3 or remove 1-5')
            return

        # Parse all task IDs (supports ranges and multiple IDs)
        task_ids = parse_task_ids(parts[1:])

        if not task_ids:
            state.messages.append('[red]?[/red] No valid task IDs provided\n    Example: remove 3 or remove 1-5')
            return

        # Confirmation dialog for bulk delete (using config threshold)
        if len(task_ids) > ui.BULK_DELETE_THRESHOLD:
            if not confirm(f"Delete {len(task_ids)} tasks?", default=False):
                state.messages.append("[yellow]Deletion cancelled[/yellow]")
                return

        # Remove all found tasks (using O(1) index lookup)
        removed = []
        not_found = []

        for task_id in task_ids:
            task = state.get_task_by_id(task_id)  # O(1) lookup
            if task:
                state.remove_task(task)  # Use new method that updates index
                removed.append(task_id)
            else:
                not_found.append(task_id)

        # Build result message using visual feedback
        if removed or not_found:
            OperationSummary.show_summary(
                "tasks removed",
                success_count=len(removed),
                failure_count=len(not_found),
                console=console
            )

        # Add to state messages for consistency
        if removed:
            if len(removed) == 1:
                state.messages.append(f"[-] Removed task {removed[0]}")
            else:
                state.messages.append(f"[-] Removed tasks {', '.join(map(str, removed))}")

        if not_found:
            state.messages.append(f"[red]?[/red] Tasks not found: {', '.join(map(str, not_found))}")

    elif cmd == "edit":
        if len(parts) < 2:
            state.messages.append(
                '[red]?[/red] Usage: edit <id> "name" "comment" "description" priority "tag"'
            )
            return

        try:
            task_id = int(parts[1])
        except ValueError:
            state.messages.append("[red]?[/red] Task ID must be a number")
            return

        task = state.get_task_by_id(task_id)  # O(1) lookup
        if not task:
            state.messages.append(f"[red]?[/red] Task {task_id} not found")
            return

        # Store old tags for tag index update
        old_tags = task.tags.copy()

        # Safely update each field if provided
        try:
            if len(parts) > 2 and parts[2] != "-":
                task.name = parts[2]
            if len(parts) > 3 and parts[3] != "-":
                task.comment = sanitize_comment(parts[3])
            if len(parts) > 4 and parts[4] != "-":
                task.description = sanitize_description(parts[4])
            if len(parts) > 5 and parts[5].isdigit():
                task.priority = clamp_priority(int(parts[5]))
            if len(parts) > 6 and parts[6] != "-":
                # Parse tags using centralized utility (DRY)
                tag_list = parse_tags(
                    parts[6],
                    warn_callback=lambda msg: console.print(msg)
                )

                # Update both legacy and new tag fields
                task.tag = tag_list[0] if tag_list else ""
                task.tags = tag_list

            # UPDATE TASK INDEX (defensive - ensures consistency)
            if state._task_index is not None:
                state._task_index[task.id] = task

            # UPDATE TAG INDEX (if tags changed)
            if task.tags != old_tags:
                state._update_tag_index_for_task(task, old_tags)

            state.messages.append(f"[~] Task {task_id} updated")
        except Exception as e:
            state.messages.append(f"[red]?[/red] Failed to update task: {e}")

    elif cmd == "next":
        # Ensure next only works if there are more tasks to show
        if (state.page + 1) * state.page_size < len(state.tasks):
            state.page += 1
            state.messages.append("→ Next page")
        else:
            state.messages.append("[red]?[/red] No more pages")

    elif cmd == "prev":
        if state.page > 0:
            state.page -= 1
            state.messages.append("← Previous page")
        else:
            state.messages.append("[red]?[/red] Already on the first page")

    elif cmd == "view":
        if len(parts) > 1 and parts[1] in ("compact", "detail"):
            state.view_mode = parts[1]
            state.messages.append(f"[~] Switched to view: {parts[1]}")

    elif cmd == "sort":
        # Supported:
        #   sort                           → toggle order (quick flip)
        #   sort <id|name|priority> [asc|desc]
        #   sort <priority> high|low       → friendly aliases
        #   sort order <asc|desc>
        if len(parts) == 1:
            # Quick toggle with no args
            state.sort_order = "desc" if state.sort_order == "asc" else "asc"
            state.messages.append(f"[~] Sort order toggled → {state.sort_order}")
            return

        # Explicit toggle subcommand (aligns with completer suggestion)
        if parts[1] == "toggle":
            state.sort_order = "desc" if state.sort_order == "asc" else "asc"
            state.messages.append(f"[~] Sort order toggled → {state.sort_order}")
            return

        # Case: sort order asc|desc
        if parts[1] == "order":
            if len(parts) >= 3 and parts[2].lower() in ("asc", "desc"):
                state.sort_order = parts[2].lower()
                state.messages.append(f"[~] Sort order set to: {state.sort_order}")
            else:
                state.messages.append('[red]?[/red] Usage: sort order [asc|desc]')
            return

        # Case: sort <field> [asc|desc]
        field = parts[1]
        if field not in ("id", "name", "priority"):
            state.messages.append('[red]?[/red] Usage: sort "id" / "name" / "priority" [asc|desc]')
            return

        # Handle friendly aliases for priority order
        order = None
        if len(parts) >= 3:
            p2 = parts[2].lower()
            if p2 in ("asc", "desc"):
                order = p2
            elif field == "priority" and p2 in ("high", "low"):
                order = "asc" if p2 == "high" else "desc"

        state.sort = field
        if order:
            state.sort_order = order

        state.messages.append(f"[~] Sorted by: {state.sort} ({state.sort_order})")

    elif cmd == "filter":
        if len(parts) < 2:
            state.messages.append(
                '[red]?[/red] Usage: filter <expression>\n'
                '    Examples:\n'
                '      f status=done              → Completed tasks\n'
                '      f priority=1               → High priority\n'
                '      f status=undone tag=psdc   → Incomplete with tag psdc\n'
                '      f priority>=2 tag!=test    → Medium/low, not tagged test\n'
                '      f tag=psdc,webasto         → Either tag (OR)\n'
                '      f tag=psdc+webasto         → Both tags (AND)'
            )
            return

        # Join all parts after "filter" to handle compound expressions
        filter_expr = ' '.join(parts[1:])

        # Validate filter expression
        from utils.filter_parser import parse_filter_expression, get_filter_description

        try:
            conditions = parse_filter_expression(filter_expr)
            if conditions or filter_expr.lower() in ("none", "all"):
                state.filter = filter_expr
                state.page = 0  # reset to first page when filter changes

                # Show human-readable description
                if filter_expr.lower() in ("none", "all"):
                    state.messages.append("[~] Filter cleared (showing all tasks)")
                else:
                    description = get_filter_description(conditions)
                    state.messages.append(f"[~] Filter active: {description}")
            else:
                state.messages.append(f"[red]?[/red] Invalid filter expression: {filter_expr}")
        except Exception as e:
            state.messages.append(f"[red]?[/red] Filter error: {e}")

    elif cmd == "show":
        if len(parts) < 2:
            state.messages.append(
                '[red]?[/red] Usage: show <task_id> or show <filter_expression>\n'
                '    Examples:\n'
                '      show 5                    → Show task #5 details\n'
                '      show done                 → Filter to done tasks\n'
                '      show status=undone tag=psdc → Filter undone psdc tasks'
            )
            return

        # Check if argument is a task ID (numeric) or filter expression
        try:
            task_id = int(parts[1])
            # It's a task ID - show task details (existing behavior)
        except ValueError:
            # Not a number - treat as filter expression (NEW behavior)
            filter_expr = ' '.join(parts[1:])

            from utils.filter_parser import parse_filter_expression, get_filter_description

            try:
                conditions = parse_filter_expression(filter_expr)
                if conditions or filter_expr.lower() in ("none", "all"):
                    state.filter = filter_expr
                    state.page = 0

                    if filter_expr.lower() in ("none", "all"):
                        state.messages.append("[~] Filter cleared (showing all tasks)")
                    else:
                        description = get_filter_description(conditions)
                        state.messages.append(f"[~] Showing: {description}")
                else:
                    state.messages.append(f"[red]?[/red] Invalid filter expression: {filter_expr}")
            except Exception as e:
                state.messages.append(f"[red]?[/red] Filter error: {e}")
            return

        # Task ID path - show task details
        task = state.get_task_by_id(task_id)  # O(1) lookup
        if not task:
            state.messages.append(f"[red]?[/red] Task {task_id} not found")
            return

        # Build rich panel with task details
        # Icons and emojis with ASCII fallback
        if USE_UNICODE:
            status_icon = "✓" if task.done else "⏳"
            priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
            priority_icon = priority_icons.get(task.priority, "⚪")
            tag_icon = "#"  # Safe, consistent width
            created_icon = "📅"
            completed_icon = "✅"
            divider = "─" * 60
        else:
            status_icon = "[DONE]" if task.done else "[TODO]"
            priority_icons = {1: "HIGH", 2: "MED", 3: "LOW"}
            priority_icon = priority_icons.get(task.priority, "?")
            tag_icon = "#"  # Same for ASCII
            created_icon = "Created:"
            completed_icon = "Completed:"
            divider = "-" * 60

        # Status color and text
        if task.done:
            status_text = f"[bold green]{status_icon} DONE[/bold green]"
        else:
            status_text = f"[bold yellow]{status_icon} TODO[/bold yellow]"

        # Priority color and label
        priority_labels = {1: "HIGH", 2: "MED", 3: "LOW"}
        priority_label = priority_labels.get(task.priority, "???")
        priority_colors = {1: "red", 2: "yellow", 3: "green"}
        priority_color = priority_colors.get(task.priority, "white")

        # Border color based on priority
        border_colors = {1: "red", 2: "yellow", 3: "green"}
        border_color = border_colors.get(task.priority, "cyan")

        # Build panel content
        content_lines = []

        # Header: Task name + status
        content_lines.append(f"[bold white]{task.name}[/bold white]  {status_text}")
        content_lines.append("")

        # Priority section
        priority_display = f"{priority_icon} [{priority_color}]{priority_label}[/{priority_color}]"
        content_lines.append(f"[bold cyan]Priority:[/bold cyan] {priority_display}")

        # Tags section (if any)
        if task.tags:
            tags_display = ", ".join([f"[cyan]{t}[/cyan]" for t in task.tags])
            content_lines.append(f"[bold cyan]Tags:[/bold cyan] {tag_icon} {tags_display}")

        content_lines.append("")

        # Details section (comment and description)
        if task.comment:
            content_lines.append(f"[bold cyan]Comment:[/bold cyan]")
            content_lines.append(f"  [dim]{task.comment}[/dim]")
            content_lines.append("")

        if task.description:
            content_lines.append(f"[bold cyan]Description:[/bold cyan]")
            content_lines.append(f"  [dim italic]{task.description}[/dim italic]")
            content_lines.append("")

        # Divider before metadata
        content_lines.append(f"[dim]{divider}[/dim]")

        # Metadata section: timestamps
        created_time = get_relative_time(task.created_at)
        content_lines.append(f"[dim]{created_icon} Created {created_time}[/dim]")

        if task.done and task.completed_at:
            completed_time = get_relative_time(task.completed_at)
            content_lines.append(f"[dim]{completed_icon} Completed {completed_time}[/dim]")

        # Create panel with enhanced title
        panel_content = "\n".join(content_lines)

        # Make title more distinct with icon and styling
        if USE_UNICODE:
            panel_title = f"[bold {border_color}]📋 Task #{task.id}[/bold {border_color}]"
        else:
            panel_title = f"[bold {border_color}][ Task #{task.id} ][/bold {border_color}]"

        # Instead of rendering to text, store the panel object directly
        # This prevents border corruption from text conversion
        from rich.box import ROUNDED

        panel = Panel(
            panel_content,
            title=panel_title,
            title_align="left",
            border_style=border_color,
            padding=(1, 2),
            expand=False,
            box=ROUNDED  # Use rounded box for cleaner borders
        )

        # Store panel as a special message type that will be rendered directly
        # We'll use a marker to indicate this is a renderable object
        state.messages.append(("__PANEL__", panel))

    elif cmd == "tags":
        # Use O(1) tag index instead of O(n) iteration
        tag_stats = state.get_all_tags_with_stats()
        if tag_stats:
            tag_list = ", ".join(sorted(tag_stats.keys()))
            state.messages.append(
                f"[~] Tags in use: [bold green]{tag_list}[/bold green]"
            )
        else:
            state.messages.append("[~] No tags found.")

    elif cmd == "?":
        if not state.tasks:
            state.messages.append("[red]?[/red] No tasks to analyze.")
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
  [yellow]add[/yellow] / [yellow]a[/yellow]          →  Add new task (opens interactive form)
  [yellow]edit[/yellow] / [yellow]e[/yellow] [id]    →  Edit task (opens form, uses selection if no ID)
  [yellow]done[/yellow] / [yellow]x[/yellow] <id>    →  Mark task as complete
  [yellow]undone[/yellow] / [yellow]u[/yellow] <id>  →  Mark task as incomplete
  [yellow]show[/yellow] / [yellow]s[/yellow] <id>    →  Show task details OR filter (show done, show priority=1)
  [yellow]remove[/yellow] <id>     →  Delete a task (with confirmation)

[bold cyan]🔍 Advanced Filtering:[/bold cyan]
  [yellow]f[/yellow] status=done              →  Completed tasks
  [yellow]f[/yellow] status=undone            →  Incomplete tasks
  [yellow]show[/yellow] done                  →  More intuitive! (same as f status=done)
  [yellow]f[/yellow] priority=1               →  High priority only
  [yellow]f[/yellow] priority>=2              →  Medium or low priority
  [yellow]f[/yellow] tag=psdc                 →  Tagged "psdc"
  [yellow]f[/yellow] tag!=test                →  Not tagged "test"
  [yellow]f[/yellow] status=done tag=psdc     →  Completed with tag (AND)
  [yellow]show[/yellow] status=undone tag=psdc  →  Intuitive syntax!
  [yellow]f[/yellow] tag=psdc,webasto         →  Either tag (OR)
  [yellow]f[/yellow] tag=psdc+webasto         →  Both tags (AND)

[bold cyan]📊 Sorting:[/bold cyan]
  [yellow]sort[/yellow] priority              →  Sort by priority
  [yellow]sort[/yellow] priority desc         →  High to low priority
  [yellow]sort[/yellow] name asc              →  Sort by name (A→Z)
  [yellow]tags[/yellow] / [yellow]t[/yellow]                  →  List all tags

[bold cyan]🤖 AI Features (No API Key Needed!):[/bold cyan]
  [yellow]insights[/yellow]              →  Comprehensive task analysis
  [yellow]suggest[/yellow]               →  Smart recommendations

[bold cyan]🎨 Navigation & View:[/bold cyan]
  [yellow]next[/yellow] / [yellow]n[/yellow]             →  Next page
  [yellow]prev[/yellow] / [yellow]p[/yellow]             →  Previous page
  [yellow]view[/yellow] / [yellow]v[/yellow] compact     →  Switch to compact view (20/page)
  [yellow]help[/yellow] / [yellow]h[/yellow]             →  Show this help
  [yellow]exit[/yellow] / [yellow]q[/yellow]             →  Save and quit

[dim]💡 Tip: Use shortcuts for faster workflow! Type [yellow]x 5[/yellow] instead of [yellow]done 5[/yellow][/dim]
        """
                )
            )
        )

    else:
        state.messages.append("Unknown or incomplete command")

