from typing import Optional, Any



from core.state import AppState
from services.notes import FileNoteRepository
from config import DEFAULT_NOTES_DIR, DEFAULT_EDITOR_CMD
from utils.editor import open_in_editor
import shlex
from textwrap import dedent
from datetime import datetime
try:
    from assistant import Assistant
except Exception:
    Assistant = None  # type: ignore
from ui.min_feedback import (
    confirm,
    OperationSummary,
)
from utils.tag_parser import parse_tags
from utils.validators import validate_priority, sanitize_comment, sanitize_description, clamp_priority
from config import ui, USE_UNICODE, DEBUG_PARSER
from utils.emoji import emoji
from debug_logger import debug_log


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


def _log_state_snapshot(prefix: str, state: AppState) -> None:
    """
    Log current state snapshot for debugging.

    Args:
        prefix: Label for this snapshot (e.g., "BEFORE", "AFTER")
        state: AppState instance to snapshot
    """
    task_count = len(state.tasks)
    task_ids = sorted([t.id for t in state.tasks])

    # Show first 20 IDs to avoid excessive logging
    if len(task_ids) <= 20:
        ids_str = str(task_ids)
    else:
        ids_str = f"{task_ids[:20]}... ({len(task_ids)} total)"

    debug_log.info(f"[COMMANDS:{prefix}] State - {task_count} tasks, IDs: {ids_str}")


# Global assistant instance (lazy initialization)
# Will be initialized on first use with proper state
gpt = None


def _get_or_create_assistant(state):
    global gpt
    if Assistant is None:
        return None
    if gpt is None:
        gpt = Assistant(state=state)
    return gpt


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


def parse_command(command: str, state: AppState, console: Any) -> Optional[tuple[str, list[str]]]:
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


def handle_add(command_arguments: list[str], state: AppState, console: Any) -> None:
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
    debug_log.info(f"[handle_add] Called with {len(command_arguments)} arguments")

    # Ensure the task name is provided
    if len(command_arguments) < 2:
        debug_log.debug("[handle_add] Missing task name")
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
    debug_log.info(f"[handle_add] Adding task - name='{name[:50]}', priority={priority}, tag='{tag}'")
    state.add_task(name, comment, description, priority, tag)
    new_id = state.tasks[-1].id if state.tasks else None
    debug_log.info(f"[handle_add] Task added successfully - ID={new_id}")
    state.messages.append(f"[green]?[/green] Added task: {name}")


def handle_done(command_arguments: list[str], state: AppState, console: Any) -> None:
    """
    Marks the specified task(s) as done based on the task ID(s).
    Supports bulk operations: done 1 2 3, done 1-5, done 1,3,5-8

    Args:
        command_arguments (list): List of parsed input tokens, expecting task ID(s) starting at index 1.
        state (AppState): The current application state with all tasks.
        console (Console): Rich console instance (not used directly here).
    """
    from datetime import datetime

    debug_log.info(f"[handle_done] Called with {len(command_arguments)} arguments")

    # Check if task ID was provided
    if len(command_arguments) < 2:
        debug_log.debug("[handle_done] Missing task ID")
        state.messages.append('[red]?[/red] Usage: done <id> [id2 id3...]\n    Example: done 3\n    Bulk: done 1 2 3 or done 1-5')
        return

    # Parse all task IDs (supports ranges and multiple IDs)
    task_ids = parse_task_ids(command_arguments[1:])
    debug_log.debug(f"[handle_done] Parsed task IDs: {task_ids}")

    if not task_ids:
        debug_log.debug("[handle_done] No valid task IDs parsed")
        state.messages.append('[red]?[/red] No valid task IDs provided\n    Example: done 3 or done 1-5')
        return

    # Mark all found tasks as done (using O(1) index lookup)
    marked = []
    not_found = []

    for task_id in task_ids:
        task = state.get_task_by_id(task_id)  # O(1) lookup instead of O(n)
        if task:
            debug_log.debug(f"[handle_done] Marking task {task_id} as done")
            task.done = True
            task.completed_at = datetime.now().isoformat()
            try:
                task.updated_at = datetime.now().isoformat()
            except Exception:
                pass
            task.completed_at = datetime.now().isoformat()
            marked.append(task_id)
        else:
            debug_log.debug(f"[handle_done] Task {task_id} not found")
            not_found.append(task_id)

    debug_log.info(f"[handle_done] Marked {len(marked)} tasks, {len(not_found)} not found")

    # Build result message
    if marked:
        if len(marked) == 1:
            state.messages.append(f"[✓] Task {marked[0]} marked as done")
        else:
            state.messages.append(f"[✓] Tasks {', '.join(map(str, marked))} marked as done")

    if not_found:
        state.messages.append(f"[red]?[/red] Tasks not found: {', '.join(map(str, not_found))}")


def handle_undone(command_arguments: list[str], state: AppState, console: Any) -> None:
    """
    Unmarks the specified task(s) (sets 'done' to False) based on the task ID(s).
    Supports bulk operations: undone 1 2 3, undone 1-5, undone 1,3,5-8

    Args:
        command_arguments (list): List of parsed input tokens, expecting task ID(s) starting at index 1.
        state (AppState): The current application state with all tasks.
        console (Console): Rich console instance (not used directly here).
    """
    debug_log.info(f"[handle_undone] Called with {len(command_arguments)} arguments")

    # Check if task ID was provided
    if len(command_arguments) < 2:
        debug_log.debug("[handle_undone] Missing task ID")
        state.messages.append('[red]?[/red] Usage: undone <id> [id2 id3...]\n    Example: undone 3\n    Bulk: undone 1 2 3 or undone 1-5')
        return

    # Parse all task IDs (supports ranges and multiple IDs)
    task_ids = parse_task_ids(command_arguments[1:])
    debug_log.debug(f"[handle_undone] Parsed task IDs: {task_ids}")

    if not task_ids:
        debug_log.debug("[handle_undone] No valid task IDs parsed")
        state.messages.append('[red]?[/red] No valid task IDs provided\n    Example: undone 3 or undone 1-5')
        return

    # Unmark all found tasks (using O(1) index lookup)
    unmarked = []
    not_found = []

    for task_id in task_ids:
        task = state.get_task_by_id(task_id)  # O(1) lookup
        if task:
            try:
                task.updated_at = datetime.now().isoformat()
            except Exception:
                pass
            debug_log.debug(f"[handle_undone] Unmarking task {task_id}")
            task.done = False
            task.completed_at = ""
            task.completed_at = ""  # Clear completion timestamp
            unmarked.append(task_id)
        else:
            debug_log.debug(f"[handle_undone] Task {task_id} not found")
            not_found.append(task_id)

    debug_log.info(f"[handle_undone] Unmarked {len(unmarked)} tasks, {len(not_found)} not found")

    # Build result message
    if unmarked:
        if len(unmarked) == 1:
            state.messages.append(f"[✓] Task {unmarked[0]} unmarked")
        else:
            state.messages.append(f"[✓] Tasks {', '.join(map(str, unmarked))} unmarked")

    if not_found:
        state.messages.append(f"[red]?[/red] Tasks not found: {', '.join(map(str, not_found))}")


def handle_command(command: str, state: AppState, console: Any) -> None:
    # Log command received
    debug_log.info(f"[COMMANDS] Received command: '{command}'")
    _log_state_snapshot("BEFORE", state)

    try:
        cmd, parts = parse_command(command, state, console)
    except Exception as e:
        debug_log.error(f"[COMMANDS] Failed to parse command: {e}", exception=e)
        return

    if cmd is None:
        debug_log.debug("[COMMANDS] Empty command, skipping")
        return

    # Map command aliases to full commands
    original_cmd = cmd
    if cmd in COMMAND_ALIASES:
        cmd = COMMAND_ALIASES[cmd]
        debug_log.debug(f"[COMMANDS] Alias '{original_cmd}' → '{cmd}'")

    debug_log.info(f"[COMMANDS] Executing: {cmd} with {len(parts)-1} args")

    if cmd == "add":
        handle_add(parts, state, console)

    elif cmd == "done":
        handle_done(parts, state, console)

    elif cmd == "undone":
        handle_undone(parts, state, console)

    elif cmd == "remove":
        debug_log.info(f"[remove] Attempting to remove tasks from args: {parts[1:]}")

        if len(parts) < 2:
            debug_log.debug("[remove] Missing task ID")
            state.messages.append('[red]?[/red] Usage: remove <id> [id2 id3...]\n    Example: remove 3\n    Bulk: remove 1 2 3 or remove 1-5')
            return

        # Parse all task IDs (supports ranges and multiple IDs)
        task_ids = parse_task_ids(parts[1:])
        debug_log.debug(f"[remove] Parsed task IDs: {task_ids}")

        if not task_ids:
            debug_log.debug("[remove] No valid task IDs parsed")
            state.messages.append('[red]?[/red] No valid task IDs provided\n    Example: remove 3 or remove 1-5')
            return

        # Confirmation dialog for bulk delete (using config threshold)
        if len(task_ids) > ui.BULK_DELETE_THRESHOLD:
            debug_log.info(f"[remove] Bulk delete ({len(task_ids)} tasks) - asking for confirmation")
            if not confirm(f"Delete {len(task_ids)} tasks?", default=False):
                debug_log.info("[remove] User cancelled bulk deletion")
                state.messages.append("[yellow]Deletion cancelled[/yellow]")
                return
            debug_log.info("[remove] User confirmed bulk deletion")

        # Remove all found tasks (using O(1) index lookup)
        removed = []
        not_found = []

        for task_id in task_ids:
            task = state.get_task_by_id(task_id)  # O(1) lookup
            if task:
                debug_log.debug(f"[remove] Removing task {task_id}")
                state.remove_task(task)  # Use new method that updates index
                removed.append(task_id)
            else:
                debug_log.debug(f"[remove] Task {task_id} not found")
                not_found.append(task_id)

        debug_log.info(f"[remove] Removed {len(removed)} tasks, {len(not_found)} not found")

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
        debug_log.info(f"[edit] Attempting to edit task with args: {parts[1:]}")

        if len(parts) < 2:
            debug_log.debug("[edit] Missing task ID")
            state.messages.append(
                '[red]?[/red] Usage: edit <id> "name" "comment" "description" priority "tag"'
            )
            return

        try:
            task_id = int(parts[1])
            debug_log.debug(f"[edit] Parsed task ID: {task_id}")
        except ValueError:
            debug_log.debug(f"[edit] Invalid task ID (not a number): {parts[1]}")
            state.messages.append("[red]?[/red] Task ID must be a number")
            return

        task = state.get_task_by_id(task_id)  # O(1) lookup
        if not task:
            debug_log.warning(f"[edit] Task {task_id} not found in state")
            state.messages.append(f"[red]?[/red] Task {task_id} not found")
            return

        debug_log.info(f"[edit] Found task {task_id} - name='{task.name[:30]}'")

        # Store old tags for tag index update
        old_tags = task.tags.copy()

        # Safely update each field if provided
        try:
            if len(parts) > 2 and parts[2] != "-":
                debug_log.debug(f"[edit] Updating name: '{task.name[:30]}' → '{parts[2][:30]}'")
                task.name = parts[2]
            if len(parts) > 3 and parts[3] != "-":
                debug_log.debug(f"[edit] Updating comment")
                task.comment = sanitize_comment(parts[3])
            if len(parts) > 4 and parts[4] != "-":
                debug_log.debug(f"[edit] Updating description")
                task.description = sanitize_description(parts[4])
            if len(parts) > 5 and parts[5].isdigit():
                debug_log.debug(f"[edit] Updating priority: {task.priority} → {parts[5]}")
                task.priority = clamp_priority(int(parts[5]))
            if len(parts) > 6 and parts[6] != "-":
                debug_log.debug(f"[edit] Updating tags from '{parts[6]}'")
                # Parse tags using centralized utility (DRY)
                tag_list = parse_tags(
                    parts[6],
                    warn_callback=lambda msg: console.print(msg)
                )
                debug_log.debug(f"[edit] Parsed tags: {tag_list}")

                # Update both legacy and new tag fields
                task.tag = tag_list[0] if tag_list else ""
                task.tags = tag_list

            try:
                task.updated_at = datetime.now().isoformat()
            except Exception:
                pass
            # UPDATE TASK INDEX (defensive - ensures consistency)
            if state._task_index is not None:
                state._task_index[task.id] = task
                debug_log.debug(f"[edit] Updated task index for task {task_id}")

            # UPDATE TAG INDEX (if tags changed)
            if task.tags != old_tags:
                debug_log.debug(f"[edit] Tags changed: {old_tags} → {task.tags}")
                state._update_tag_index_for_task(task, old_tags)

            debug_log.info(f"[edit] Task {task_id} updated successfully")
            state.messages.append(f"[~] Task {task_id} updated")
        except Exception as e:
            debug_log.error(f"[edit] Failed to update task {task_id}: {e}", exception=e)
            state.messages.append(f"[red]?[/red] Failed to update task: {e}")

    elif cmd == "next":
        debug_log.debug(f"[next] Current page: {state.page}, page_size: {state.page_size}, total tasks: {len(state.tasks)}")
        # Ensure next only works if there are more rows to show (respect mode)
        total_items = len(state.tasks) if getattr(state, 'entity_mode', 'tasks') == 'tasks' else len(getattr(state, 'notes', []))
        if (state.page + 1) * state.page_size < total_items:
            state.page += 1
            debug_log.info(f"[next] Moved to page {state.page}")
            state.messages.append("→ Next page")
        else:
            debug_log.debug("[next] Already on last page")
            state.messages.append("[red]?[/red] No more pages")

    elif cmd == "prev":
        debug_log.debug(f"[prev] Current page: {state.page}")
        if state.page > 0:
            state.page -= 1
            debug_log.info(f"[prev] Moved to page {state.page}")
            state.messages.append("← Previous page")
        else:
            debug_log.debug("[prev] Already on first page")
            state.messages.append("[red]?[/red] Already on the first page")

    elif cmd == "view":
        debug_log.info(f"[view] Args: {parts[1:]}")
        if len(parts) > 1 and parts[1] in ("compact", "detail"):
            old_mode = state.view_mode
            state.view_mode = parts[1]
            debug_log.info(f"[view] Changed view mode: {old_mode} → {parts[1]}")
            state.messages.append(f"[~] Switched to view: {parts[1]}")

    elif cmd == "sort":
        debug_log.info(f"[sort] Args: {parts[1:]}")
        # Supported:
        #   sort                           → toggle order (quick flip)
        #   sort <id|name|priority|age> [asc|desc]
        #   sort <priority> high|low       → friendly aliases
        #   sort order <asc|desc>
        if len(parts) == 1:
            # Quick toggle with no args
            old_order = state.sort_order
            state.sort_order = "desc" if state.sort_order == "asc" else "asc"
            debug_log.info(f"[sort] Toggled order: {old_order} → {state.sort_order}")
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
        if field not in ("id", "name", "priority", "age"):
            state.messages.append('[red]?[/red] Usage: sort \"id\" / \"name\" / \"priority\" / \"age\" [asc|desc]')
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

        debug_log.info(f"[sort] Set sort: field={state.sort}, order={state.sort_order}")
        state.messages.append(f"[~] Sorted by: {state.sort} ({state.sort_order})")

    elif cmd == "filter":
        debug_log.info(f"[filter] Args: {parts[1:]}")

        if len(parts) < 2:
            debug_log.debug("[filter] Missing filter expression")
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
        debug_log.debug(f"[filter] Expression: '{filter_expr}'")

        # Validate filter expression
        from utils.filter_parser import parse_filter_expression, get_filter_description

        try:
            conditions = parse_filter_expression(filter_expr)
            if conditions or filter_expr.lower() in ("none", "all"):
                old_filter = state.filter
                state.filter = filter_expr
                state.page = 0  # reset to first page when filter changes
                debug_log.info(f"[filter] Applied filter: '{old_filter}' → '{filter_expr}', reset page to 0")

                # Show human-readable description
                if filter_expr.lower() in ("none", "all"):
                    state.messages.append("[~] Filter cleared (showing all tasks)")
                else:
                    description = get_filter_description(conditions)
                    state.messages.append(f"[~] Filter active: {description}")
            else:
                debug_log.warning(f"[filter] Invalid filter expression: '{filter_expr}'")
                state.messages.append(f"[red]?[/red] Invalid filter expression: {filter_expr}")
        except Exception as e:
            debug_log.error(f"[filter] Filter parsing error: {e}", exception=e)
            state.messages.append(f"[red]?[/red] Filter error: {e}")

   
    # -------------------- Notes & Mode --------------------
    elif cmd == "mode":
        if len(parts) >= 2 and parts[1] in ("tasks", "notes"):
            old = state.entity_mode
            state.entity_mode = parts[1]
            state.messages.append(f"[~] Mode: {old} → {state.entity_mode}")
        else:
            state.messages.append('[red]?[/red] Usage: mode tasks|notes')

    elif cmd == "notes":
        # Switch to notes mode and set filters for renderer
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)
        state.refresh_notes_from_disk()
        state.entity_mode = 'notes'
        state.page = 0
        if len(parts) >= 2:
            arg = ' '.join(parts[1:])
            if arg.isdigit():
                state.notes_task_id_filter = int(arg)
                state.notes_query = ""
                state.messages.append(f"[~] Showing notes linked to task {arg}")
            else:
                if arg.lower() in ("clear", "none", "all"):
                    state.notes_query = ""
                    state.notes_task_id_filter = None
                    state.messages.append("[~] Notes filter cleared")
                else:
                    state.notes_query = arg
                    state.notes_task_id_filter = None
                    state.messages.append(f"[~] Notes search: '{arg}'")
        else:
            state.notes_query = ""
            state.notes_task_id_filter = None
        return

    elif cmd == "note":
        # Subcommands: new|edit|show|link|unlink
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)
        if len(parts) == 1:
            state.messages.append('[red]?[/red] Usage: note new|edit|show|link|unlink ...')
            return
        sub = parts[1]
        if sub == "new":
            # note new [--title "..."] [--task 12] [--tag x]
            title = ""
            task_id: int | None = None
            tags: list[str] = []
            # very light option parsing
            i = 2
            while i < len(parts):
                p = parts[i]
                if p in ("--title", "-t") and i + 1 < len(parts):
                    title = parts[i + 1]
                    i += 2
                elif p == "--task" and i + 1 < len(parts) and parts[i + 1].isdigit():
                    task_id = int(parts[i + 1])
                    i += 2
                elif p in ("--tag", "-g") and i + 1 < len(parts):
                    tags.append(parts[i + 1])
                    i += 2
                else:
                    i += 1
            note = repo.create(title=title or "New Note", tags=tags, task_ids=[task_id] if task_id else [])
            # open in editor
            path = repo._note_path(note.id, note.title)
            open_in_editor(str(path), DEFAULT_EDITOR_CMD)
            state.refresh_notes_from_disk()
            state.messages.append(f"[green]✓[/green] Note created: {note.title} ({note.id[:8]})")

        elif sub == "edit" and len(parts) >= 3:
            note_id = parts[2]
            # open by id prefix
            # find matching filename
            # ensure exists
            n = repo.get(note_id)
            if not n:
                state.messages.append(f"[red]?[/red] Note {note_id} not found")
                return
            path = repo._note_path(n.id, n.title)
            open_in_editor(str(path), DEFAULT_EDITOR_CMD)
            state.refresh_notes_from_disk()
            state.messages.append(f"[~] Edited note {n.id[:8]}")

        elif sub == "show" and len(parts) >= 3:
            note_id = parts[2]
            n = repo.get(note_id)
            if not n:
                state.messages.append(f"[red]?[/red] Note {note_id} not found")
                return
            from utils.time import humanize_age
            age = humanize_age(n.created_at)
            trefs = ' '.join(f"#{tid}" for tid in n.task_ids)
            body_preview = (n.body_md or "").strip().splitlines()[:8]
            panel = "\n".join([
                f"[bold]{n.title}[/bold]  [dim]{n.id} • {age} • tags: {', '.join(n.tags)}[/dim]",
                f"linked: {trefs}" if trefs else "linked: (none)",
                "",
                *([ln for ln in body_preview] or ["[dim](empty)[/dim]"])
            ])
            state.messages.append(panel)

        elif sub in ("link", "unlink") and len(parts) >= 4 and parts[3].isdigit():
            note_id = parts[2]
            task_id = int(parts[3])
            n = repo.get(note_id)
            if not n:
                state.messages.append(f"[red]?[/red] Note {note_id} not found")
                return
            if sub == "link":
                repo.link_task(n, task_id)
                state.messages.append(f"[green]✓[/green] Linked note {n.id[:8]} ↔ task {task_id}")
            else:
                repo.unlink_task(n, task_id)
                state.messages.append(f"[green]✓[/green] Unlinked note {n.id[:8]} ↔ task {task_id}")
            state.refresh_notes_from_disk()
        elif sub == "quick" and len(parts) >= 3:
            # note quick "Title" [--task <id>]
            title = parts[2]
            link_task = None
            i = 3
            while i < len(parts):
                p = parts[i]
                if p == "--task" and i + 1 < len(parts) and parts[i + 1].isdigit():
                    link_task = int(parts[i + 1])
                    i += 2
                else:
                    i += 1
            if link_task is None:
                filtered = state.get_filter_tasks(state.tasks)
                if filtered:
                    link_task = filtered[0].id
            note = repo.create(title=title, task_ids=[link_task] if link_task else [])
            # Open in editor (respect env)
            path = repo._note_path(note.id, note.title)
            open_in_editor(str(path), DEFAULT_EDITOR_CMD)
            state.refresh_notes_from_disk()
            state.entity_mode = 'notes'
            state.page = 0
            state.messages.append(f"[green]✓[/green] Quick note created: {note.title} ({note.id[:8]})")
        else:
            # Delete: note delete <note_id_prefix>; Duplicate: note duplicate <id> [--title] [--task]
            if sub == "delete" and len(parts) >= 3:
                note_id = parts[2]
                force = any(p == "--force" for p in parts[3:])
                if len(note_id) < 5 and not force:
                    state.messages.append("[red]?[/red] Prefix too short. Use at least 5 chars or add --force")
                    return
                ok = repo.delete(note_id)
                state.refresh_notes_from_disk()
                if ok:
                    state.messages.append(f"[red]✗[/red] Deleted note(s) matching {note_id}")
                else:
                    state.messages.append(f"[yellow]No notes deleted for {note_id}[/yellow]")
            elif sub == "duplicate" and len(parts) >= 3:
                src_id = parts[2]
                src = repo.get(src_id)
                if not src:
                    state.messages.append(f"[red]?[/red] Note {src_id} not found")
                    return
                # Parse optional args
                title = f"Copy of {src.title}"
                link_task: int | None = None
                i = 3
                while i < len(parts):
                    p = parts[i]
                    if p in ("--title", "-t") and i + 1 < len(parts):
                        title = parts[i + 1]
                        i += 2
                    elif p == "--task" and i + 1 < len(parts) and parts[i + 1].isdigit():
                        link_task = int(parts[i + 1])
                        i += 2
                    else:
                        i += 1
                new = repo.create(
                    title=title,
                    tags=list(src.tags),
                    task_ids=[link_task] if link_task is not None else list(src.task_ids),
                    body_md=src.body_md,
                )
                state.refresh_notes_from_disk()
                state.entity_mode = 'notes'
                state.page = 0
                state.messages.append(f"[green]✓[/green] Duplicated note {src.id[:8]} → {new.id[:8]}")
            else:
                state.messages.append('[red]?[/red] Usage: note new|edit|show|link|unlink|delete|duplicate ...')

    elif cmd == "show":
        debug_log.info(f"[show] Called with args: {parts[1:]}")

        if len(parts) < 2:
            debug_log.debug("[show] Missing argument")
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
            debug_log.debug(f"[show] Argument is numeric - showing task details for ID {task_id}")
            # It's a task ID - show task details (existing behavior)
        except ValueError:
            # Not a number - treat as filter expression (NEW behavior)
            filter_expr = ' '.join(parts[1:])
            debug_log.debug(f"[show] Argument is filter expression: '{filter_expr}'")

            from utils.filter_parser import parse_filter_expression, get_filter_description

            try:
                conditions = parse_filter_expression(filter_expr)
                if conditions or filter_expr.lower() in ("none", "all"):
                    state.filter = filter_expr
                    state.page = 0
                    debug_log.info(f"[show] Applied filter: '{filter_expr}'")

                    if filter_expr.lower() in ("none", "all"):
                        state.messages.append("[~] Filter cleared (showing all tasks)")
                    else:
                        description = get_filter_description(conditions)
                        state.messages.append(f"[~] Showing: {description}")
                else:
                    debug_log.warning(f"[show] Invalid filter expression: '{filter_expr}'")
                    state.messages.append(f"[red]?[/red] Invalid filter expression: {filter_expr}")
            except Exception as e:
                debug_log.error(f"[show] Filter parsing error: {e}", exception=e)
                state.messages.append(f"[red]?[/red] Filter error: {e}")
            return

        # Task ID path - show task details
        task = state.get_task_by_id(task_id)  # O(1) lookup
        if not task:
            debug_log.warning(f"[show] Task {task_id} not found in state")
            state.messages.append(f"[red]?[/red] Task {task_id} not found")
            return

        debug_log.info(f"[show] Found task {task_id} - name='{task.name[:30]}', displaying details")
        # Mark as selected for quick note actions
        try:
            state.selected_task_id = task_id
        except Exception:
            pass

        # Build rich panel with task details
        # Icons and emojis with ASCII fallback
        if USE_UNICODE:
            status_icon = "✓" if task.done else "⏳"
            priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
            priority_icon = priority_icons.get(task.priority, "⚪")
            tag_icon = "#"  # Safe, consistent width
            updated_icon = "Updated:"
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
        priority_label = priority_labels.get(task.priority, "?")
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
        if getattr(task, "updated_at", ""):
            updated_time = get_relative_time(task.updated_at)
            content_lines.append(f"[dim]Updated: Updated {updated_time}[/dim]")

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

        # Fallback: store plain text instead of Rich panel (no Rich dependency)
        state.messages.append(f"{panel_title}\n\n{panel_content}")

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
        from ui.ai_renderer import create_streaming_callback
        gpt = _get_or_create_assistant(state)
        if gpt is None:
            state.messages.append("[yellow]??  Agent not available[/yellow]")
            return

        # Extract question (inline or prompt)
        question = " ".join(parts[1:]) if len(parts) > 1 else ""

        if not question:
            question = "What should I work on today?"




        # Create streaming callback
        callback = create_streaming_callback(console)
        callback.on_start()

        # Ask agent (with streaming)
        try:
            response = gpt.ask(question, streaming_callback=callback)
            callback.on_end()

            # Add brief confirmation to messages
            state.messages.append("[dim]Last AI response saved to conversation history[/dim]")

        except Exception as e:
            callback.on_end()
            state.messages.append(f"[red]❌ AI Error: {str(e)}[/red]")

    elif cmd == "save":
        # Manual save command
        state.save_to_file("tasks.json", console)
        state.messages.append("[💾] Tasks saved successfully")

    elif cmd == "help":
        # Detailed help: help <command>
        if len(parts) > 1:
            topic = COMMAND_ALIASES.get(parts[1].lower(), parts[1].lower())
            from textwrap import dedent as _ded
            def _block(title, body):
                return _ded(f"\n[bold cyan]{title}[/bold cyan]\n{body}\n")
            details = {
                "add": _block("add (a)", "Usage: add → opens form\n       add \"name\" \"comment\" \"description\" <priority> \"tags\"\nNotes: tags: comma-separated up to 3; priority 1..3; created_at set automatically."),
                "edit": _block("edit (e)", "Usage: edit <id> → opens form\nNotes: updates updated_at; tags accept comma list."),
                "done": _block("done (x/d)", "Usage: done <id> [ids...]\nNotes: sets completed_at and updated_at."),
                "undone": _block("undone (u)", "Usage: undone <id> [ids...]\nNotes: clears completed_at; sets updated_at."),
                "remove": _block("remove (r)", "Usage: remove <id> [ids...] → delete with confirmation."),
                "show": _block("show (s)", "Usage: show <id> → details with Created/Updated/Completed\n       show <filter> → apply filter (e.g., show age>=3d)"),
                "filter": _block("filter (f)", "Usage: filter <expr>\nFields: status, priority, tag, age\nExamples: status=done, priority>=2, tag=psdc+webasto, age>=3d"),
                "sort": _block("sort", "Usage: sort <id|name|priority|age> [asc|desc]\nExamples: sort age desc (oldest first)"),
                "tags": _block("tags (t)", "Usage: tags → list all tags"),
                "insights": _block("insights", "Usage: insights → local analysis (no API key needed)"),
                "suggest": _block("suggest", "Usage: suggest → quick recommendations (local)"),
                "?": _block("? (AI)", "Usage: ? <question> → ask AI (requires API key)\nSubcommands: ? clear | ? memory | ? export [file] | ? reset"),
                "save": _block("save", "Usage: save → persist tasks immediately"),
                "exit": _block("exit (q)", "Usage: exit | quit | q → save and quit"),
                "view": _block("view (v)", "Usage: view compact | view detail"),
                "next": _block("next (n)", "Usage: next → next page"),
                "prev": _block("prev (p)", "Usage: prev → previous page"),
            }
            body = details.get(topic)
            if body:
                state.messages.append(body)
                return
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

[bold cyan]🤖 AI Features:[/bold cyan]
  [bold]Local AI (No API Key Needed):[/bold]
  [yellow]insights[/yellow]              →  Comprehensive task analysis
  [yellow]suggest[/yellow]               →  Smart recommendations

  [bold]GPT Agent (Requires OpenAI API Key):[/bold]
  [yellow]?[/yellow] [question]          →  Ask AI anything (creates/edits/searches tasks!)
  [yellow]? clear[/yellow]               →  Clear conversation history
  [yellow]? memory[/yellow]              →  Show conversation stats
  [yellow]? export[/yellow] [file]       →  Export chat to markdown
  [yellow]? reset[/yellow]               →  Reset conversation (with confirmation)

  [dim]Notes with AI:[/dim]
    [dim]? create a note titled "Meeting minutes" linked to task 12[/dim]
    [dim]? search notes "webasto" and link the first to task 3[/dim]
    [dim]? summarize note abcd1234[/dim]
    [dim]? convert note abcd1234 into a task with priority 1 and tags backend,api[/dim]
    [dim]? open note abcd1234 in editor[/dim]

  [dim]Examples:[/dim]
    [dim]? create a high priority task for code review[/dim]
    [dim]? what are my urgent tasks?[/dim]
    [dim]? mark task 5 as done[/dim]

[bold cyan]🎨 Navigation & View:[/bold cyan]
  [yellow]next[/yellow] / [yellow]n[/yellow]             →  Next page
  [yellow]prev[/yellow] / [yellow]p[/yellow]             →  Previous page
  [yellow]view[/yellow] / [yellow]v[/yellow] compact     →  Switch to compact view (20/page)
  [yellow]help[/yellow] / [yellow]h[/yellow]             →  Show this help
  [yellow]exit[/yellow] / [yellow]q[/yellow]             →  Save and quit

[dim]💡 Tip: Use shortcuts for faster workflow! Type [yellow]x 5[/yellow] instead of [yellow]done 5[/yellow][/dim]

[bold cyan]📝 Notes:[/bold cyan]
  [yellow]mode notes[/yellow]              →  Switch to notes list
  [yellow]notes[/yellow] [task_id|query]   →  List/search notes (or for a task)
  [yellow]notes clear[/yellow]             →  Clear notes filters
  [yellow]note new[/yellow] --title "..." [--task 12] [--tag x]
  [yellow]note edit[/yellow] <note_id_prefix>
  [yellow]note link[/yellow] <note_id> <task_id>  /  [yellow]note unlink[/yellow] ...
  [yellow]note delete[/yellow] <note_id_prefix>   /  [yellow]note duplicate[/yellow] <note_id_prefix>
  [dim]Shortcuts:[/dim] Ctrl+N create note for selected task, Ctrl+O open latest note
        """
                )
            )
        )

    else:
        debug_log.warning(f"[COMMANDS] Unknown command: '{cmd}'")
        state.messages.append("Unknown or incomplete command")

    # Log state after command execution
    _log_state_snapshot("AFTER", state)
    debug_log.info(f"[COMMANDS] Command '{cmd}' completed")









