"""
LangChain AI Tools for Task Management

Provides 8 tools that allow the LangChain agent to interact with tasks:
- create_task: Create new tasks
- edit_task: Modify existing tasks
- complete_task / uncomplete_task: Toggle task status
- delete_task: Delete tasks permanently
- search_tasks: Filter and find tasks
- get_task_details: Get full task information
- get_task_statistics: Get workspace summary

All tools access AppState directly for immediate execution.
"""

from typing import Optional, List
from langchain.tools import tool
from datetime import datetime

from models.task import Task
from utils.tag_parser import parse_tags
from config import validation, ai as ai_config
from debug_logger import debug_log
from services.notes import FileNoteRepository
from config import DEFAULT_NOTES_DIR


# Global AppState reference (set by agent initialization)
_app_state = None


def set_app_state(state):
    """
    Set the global AppState reference for tools to use.
    Called once during agent initialization.
    """
    global _app_state
    _app_state = state
    debug_log.info(f"[AI_TOOLS] AppState initialized - {len(state.tasks) if state else 0} tasks loaded")


def _get_state():
    """Get AppState or raise error if not initialized"""
    if _app_state is None:
        debug_log.error("[AI_TOOLS] _get_state() called but AppState not initialized!")
        raise RuntimeError("AppState not initialized. Call set_app_state() first.")
    return _app_state


def _validate_priority(priority: int) -> bool:
    """Validate priority is in valid range (1-3)"""
    return validation.MIN_PRIORITY <= priority <= validation.MAX_PRIORITY


def _find_task_by_id(task_id: int) -> Optional[Task]:
    """Find task by ID in AppState"""
    state = _get_state()
    for task in state.tasks:
        if task.id == task_id:
            return task
    return None


def _save_tasks():
    """Save tasks to file after modification"""
    from config import DEFAULT_TASKS_FILE

    state = _get_state()
    debug_log.info(f"[AI_TOOLS] _save_tasks() called - {len(state.tasks)} tasks in state")
    debug_log.debug(f"[AI_TOOLS] Task IDs in state: {sorted([t.id for t in state.tasks])}")

    state.save_to_file(str(DEFAULT_TASKS_FILE), None)
    debug_log.info(f"[AI_TOOLS] _save_tasks() completed")


# ============================================================================
# TOOL 1: CREATE TASK
# ============================================================================

@tool
def create_task(
    name: str,
    priority: int = 2,
    tag: str = "",
    description: str = "",
    comment: str = ""
) -> str:
    """
    Create a new task in the task list.

    Args:
        name: Task name (required, 1-200 characters)
        priority: Priority level - 1 (HIGH), 2 (MEDIUM), 3 (LOW). Default: 2
        tag: Tags for categorization - COMMA-SEPARATED for multiple tags (optional, max 50 chars)
             Examples: "backend", "frontend,urgent", "psdc,webasto,fa070"
        description: Detailed technical description or requirements (optional, max 2000 chars)
                    Use this for: specifications, technical details, requirements, acceptance criteria
        comment: Short contextual note or reference (optional, max 500 chars)
                Use this for: quick notes, ticket references, related info

    Returns:
        Success message with task ID and details, or error message

    Usage Guidelines:
        - ALWAYS extract ALL information from user requests into appropriate fields
        - If user mentions multiple tags, use comma-separated format: "tag1,tag2,tag3"
        - If user provides detailed requirements/specs, put in description field
        - If user provides context/notes/references, put in comment field
        - Priority mapping: "high"→1, "medium"→2, "low"→3, "urgent"→1

    Examples:
        # Simple task with single tag
        create_task(name="Fix login bug", priority=1, tag="backend")

        # Multiple tags (comma-separated)
        create_task(name="Update API docs", priority=2, tag="backend,documentation,api")

        # With description (detailed requirements)
        create_task(
            name="FA070 Trac send prism measurement data",
            priority=1,
            tag="webasto,psdc,fa070",
            description="For each prism, send all Cognex inspection results into LCS system. Include measurement data, timestamps, and quality metrics."
        )

        # With comment (contextual note)
        create_task(name="Code review", priority=2, tag="review", comment="Review PR #42 - authentication module")

        # Full example with all fields
        create_task(
            name="Implement OAuth2 authentication",
            priority=1,
            tag="backend,security,authentication",
            description="Implement OAuth2 authorization code flow with PKCE. Support Google and GitHub providers. Store refresh tokens securely.",
            comment="Related to issue #123, blocked by certificate setup"
        )
    """
    debug_log.debug(f"[AI_TOOLS] create_task() called - name='{name[:50]}', priority={priority}, tag='{tag}'")

    try:
        state = _get_state()

        # Validate inputs
        name = name.strip()
        if not name or len(name) < validation.MIN_TASK_NAME_LENGTH:
            debug_log.debug(f"[AI_TOOLS] Validation failed - name is empty")
            return f"❌ Error: Task name cannot be empty"

        if len(name) > validation.MAX_TASK_NAME_LENGTH:
            debug_log.debug(f"[AI_TOOLS] Validation failed - name too long ({len(name)} chars)")
            return f"❌ Error: Task name too long (max {validation.MAX_TASK_NAME_LENGTH} chars)"

        if not _validate_priority(priority):
            debug_log.debug(f"[AI_TOOLS] Validation failed - invalid priority {priority}")
            return f"❌ Error: Priority must be 1 (HIGH), 2 (MEDIUM), or 3 (LOW)"

        tag = tag.strip().lower()
        if tag and len(tag) > validation.MAX_TAG_LENGTH:
            debug_log.debug(f"[AI_TOOLS] Validation failed - tag too long ({len(tag)} chars)")
            return f"❌ Error: Tag too long (max {validation.MAX_TAG_LENGTH} chars)"

        if len(description) > validation.MAX_DESCRIPTION_LENGTH:
            debug_log.debug(f"[AI_TOOLS] Validation failed - description too long ({len(description)} chars)")
            return f"❌ Error: Description too long (max {validation.MAX_DESCRIPTION_LENGTH} chars)"

        if len(comment) > validation.MAX_COMMENT_LENGTH:
            debug_log.debug(f"[AI_TOOLS] Validation failed - comment too long ({len(comment)} chars)")
            return f"❌ Error: Comment too long (max {validation.MAX_COMMENT_LENGTH} chars)"

        # Create task via AppState (ensures IDs, tags, indices stay consistent)
        debug_log.debug(f"[AI_TOOLS] Adding task via AppState.add_task()...")
        state.add_task(
            name=name,
            comment=comment.strip(),
            description=description.strip(),
            priority=priority,
            tag=tag
        )
        new_id = state.tasks[-1].id if state.tasks else None
        debug_log.info(f"[AI_TOOLS] Task created successfully - ID={new_id}, name='{name[:30]}'")

        # Persist to disk
        _save_tasks()

        # Format response
        priority_labels = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}
        priority_label = priority_labels.get(priority, "UNKNOWN")

        result = f"Created task #{new_id}: {name}"
        result += f"\n   Priority: {priority_label}"
        if tag:
            result += f"\n   Tag: {tag}"
        if comment:
            result += f"\n   Comment: {comment}"

        try:
            # Switch UI context to tasks so user sees the new task
            state.entity_mode = 'tasks'
            state.page = 0
        except Exception:
            pass
        return result

        # Generate next ID
        next_id = max([t.id for t in state.tasks], default=0) + 1
        debug_log.debug(f"[AI_TOOLS] Generated next ID: {next_id}")

        # Create task
        new_task = Task(
            id=next_id,
            name=name,
            priority=priority,
            tag=tag,
            description=description.strip(),
            comment=comment.strip(),
            done=False
        )

        # Add to state and save
        state.tasks.append(new_task)
        state.invalidate_filter_cache()  # CRITICAL: Invalidate cache after state modification
        debug_log.debug(f"[AI_TOOLS] Task added to state, calling save...")
        _save_tasks()
        debug_log.info(f"[AI_TOOLS] Task created successfully - ID={next_id}, name='{name[:30]}'")

        # Format response
        priority_labels = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}
        priority_label = priority_labels.get(priority, "UNKNOWN")

        result = f"Created task #{new_id if 'new_id' in locals() else 'N/A'}: {name}"
        result += f"\n   Priority: {priority_label}"
        if tag:
            result += f"\n   Tag: {tag}"
        if comment:
            result += f"\n   Comment: {comment}"

        return result

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] create_task() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to create task - {str(e)}"


# ============================================================================
# TOOL 2: EDIT TASK
# ============================================================================

@tool
def edit_task(task_id: int, field: str, value: str) -> str:
    """
    Edit an existing task's field.

    Args:
        task_id: ID of the task to edit
        field: Field to edit - "name", "priority", "tag", "description", "comment"
        value: New value for the field
               For tag field: Use comma-separated format for multiple tags (e.g., "tag1,tag2,tag3")
               For priority: Use "1" (HIGH), "2" (MEDIUM), or "3" (LOW)

    Returns:
        Success message with updated field, or error message

    Usage Guidelines:
        - When editing tags, use comma-separated format for multiple tags
        - When adding to existing tags, fetch current tags first and append new ones

    Examples:
        # Edit priority
        edit_task(task_id=5, field="priority", value="1")

        # Edit name
        edit_task(task_id=10, field="name", value="Updated task name")

        # Edit tag (single)
        edit_task(task_id=3, field="tag", value="urgent")

        # Edit tag (multiple - comma-separated)
        edit_task(task_id=7, field="tag", value="backend,api,urgent")

        # Edit description
        edit_task(task_id=12, field="description", value="Detailed requirements for the feature implementation")

        # Edit comment
        edit_task(task_id=8, field="comment", value="Related to PR #42")
    """
    debug_log.debug(f"[AI_TOOLS] edit_task() called - task_id={task_id}, field='{field}', value='{value[:30]}'")

    try:
        state = _get_state()

        # Find task
        task = _find_task_by_id(task_id)
        if not task:
            debug_log.debug(f"[AI_TOOLS] Task not found - ID={task_id}")
            return f"❌ Error: Task #{task_id} not found"

        # Validate and apply field update
        field = field.lower().strip()

        if field == "name":
            value = value.strip()
            if not value or len(value) < validation.MIN_TASK_NAME_LENGTH:
                debug_log.debug(f"[AI_TOOLS] Validation failed - empty name")
                return f"❌ Error: Task name cannot be empty"
            if len(value) > validation.MAX_TASK_NAME_LENGTH:
                debug_log.debug(f"[AI_TOOLS] Validation failed - name too long")
                return f"❌ Error: Task name too long (max {validation.MAX_TASK_NAME_LENGTH} chars)"
            task.name = value

        elif field == "priority":
            try:
                priority = int(value)
                if not _validate_priority(priority):
                    debug_log.debug(f"[AI_TOOLS] Validation failed - invalid priority {priority}")
                    return f"❌ Error: Priority must be 1 (HIGH), 2 (MEDIUM), or 3 (LOW)"
                task.priority = priority
            except ValueError:
                debug_log.debug(f"[AI_TOOLS] Validation failed - priority not a number: {value}")
                return f"❌ Error: Priority must be a number (1, 2, or 3)"

        elif field == "tag":
            tag = value.strip().lower()
            if len(tag) > validation.MAX_TAG_LENGTH:
                debug_log.debug(f"[AI_TOOLS] Validation failed - tag too long")
                return f"❌ Error: Tag too long (max {validation.MAX_TAG_LENGTH} chars)"
            task.tag = tag
            # Normalize comma-separated tags and update tag index
            raw = value.strip()
            tags = parse_tags(raw)
            old_tags = list(task.tags)
            task.tags = tags
            task.tag = tags[0] if tags else ""
            state._update_tag_index_for_task(task, old_tags=old_tags)

        elif field == "description":
            if len(value) > validation.MAX_DESCRIPTION_LENGTH:
                debug_log.debug(f"[AI_TOOLS] Validation failed - description too long")
                return f"❌ Error: Description too long (max {validation.MAX_DESCRIPTION_LENGTH} chars)"
            task.description = value.strip()

        elif field == "comment":
            if len(value) > validation.MAX_COMMENT_LENGTH:
                debug_log.debug(f"[AI_TOOLS] Validation failed - comment too long")
                return f"❌ Error: Comment too long (max {validation.MAX_COMMENT_LENGTH} chars)"
            task.comment = value.strip()

        else:
            debug_log.debug(f"[AI_TOOLS] Invalid field: {field}")
            return f"❌ Error: Invalid field '{field}'. Valid fields: name, priority, tag, description, comment"

        # Save changes
        # Touch updated_at after edits
        try:
            task.updated_at = datetime.now().isoformat()
        except Exception:
            pass
        _save_tasks()
        # Invalidate cache after modification
        state.invalidate_filter_cache()  # CRITICAL: Invalidate cache after state modification
        debug_log.info(f"[AI_TOOLS] Task edited successfully - ID={task_id}, field={field}")

        return f"✅ Updated task #{task_id}: {field} = {value}"

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] edit_task() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to edit task - {str(e)}"


# ============================================================================
# TOOL 3: COMPLETE TASK
# ============================================================================

@tool
def complete_task(task_id: int) -> str:
    """
    Mark a task as complete.

    Args:
        task_id: ID of the task to mark as done

    Returns:
        Success message with task name, or error message

    Example:
        complete_task(task_id=5)
    """
    debug_log.debug(f"[AI_TOOLS] complete_task() called - task_id={task_id}")

    try:
        state = _get_state()

        # Find task
        task = _find_task_by_id(task_id)
        if not task:
            debug_log.debug(f"[AI_TOOLS] Task not found - ID={task_id}")
            return f"❌ Error: Task #{task_id} not found"

        if task.done:
            debug_log.debug(f"[AI_TOOLS] Task already done - ID={task_id}")
            return f"ℹ️  Task #{task_id} is already marked as complete"

        # Mark as done
        task.done = True
        try:
            task.completed_at = datetime.now().isoformat()
        except Exception:
            task.completed_at = task.completed_at or ""
        try:
            task.updated_at = datetime.now().isoformat()
        except Exception:
            pass
        state.invalidate_filter_cache()  # CRITICAL: Invalidate cache after state modification
        _save_tasks()
        debug_log.info(f"[AI_TOOLS] Task marked complete - ID={task_id}, name='{task.name[:30]}'")

        return f"✅ Marked task #{task_id} as complete: {task.name}"

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] complete_task() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to complete task - {str(e)}"


# ============================================================================
# TOOL 4: UNCOMPLETE TASK
# ============================================================================

@tool
def uncomplete_task(task_id: int) -> str:
    """
    Mark a completed task as incomplete (undo completion).

    Args:
        task_id: ID of the task to mark as incomplete

    Returns:
        Success message with task name, or error message

    Example:
        uncomplete_task(task_id=5)
    """
    debug_log.debug(f"[AI_TOOLS] uncomplete_task() called - task_id={task_id}")

    try:
        state = _get_state()

        # Find task
        task = _find_task_by_id(task_id)
        if not task:
            debug_log.debug(f"[AI_TOOLS] Task not found - ID={task_id}")
            return f"❌ Error: Task #{task_id} not found"

        if not task.done:
            debug_log.debug(f"[AI_TOOLS] Task already incomplete - ID={task_id}")
            return f"ℹ️  Task #{task_id} is already marked as incomplete"

        # Mark as not done
        task.done = False
        task.completed_at = ""
        state.invalidate_filter_cache()  # CRITICAL: Invalidate cache after state modification
        try:
            task.updated_at = datetime.now().isoformat()
        except Exception:
            pass
        _save_tasks()
        debug_log.info(f"[AI_TOOLS] Task marked incomplete - ID={task_id}")

        return f"✅ Marked task #{task_id} as incomplete: {task.name}"

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] uncomplete_task() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to mark task incomplete - {str(e)}"


# ============================================================================
# TOOL 5: DELETE TASK
# ============================================================================

@tool
def delete_task(task_id: int) -> str:
    """
    Delete a task from the task list permanently.

    Args:
        task_id: ID of the task to delete

    Returns:
        Success message with deleted task name, or error message

    Example:
        delete_task(task_id=5)
    """
    debug_log.debug(f"[AI_TOOLS] delete_task() called - task_id={task_id}")

    try:
        state = _get_state()

        # Find task
        task = _find_task_by_id(task_id)
        if not task:
            debug_log.debug(f"[AI_TOOLS] Task not found - ID={task_id}")
            return f"❌ Error: Task #{task_id} not found"

        # Store name before deletion
        task_name = task.name

        # Remove task
        state.remove_task(task)
        _save_tasks()
        debug_log.info(f"[AI_TOOLS] Task deleted - ID={task_id}, name='{task_name}'")

        return f"✅ Deleted task #{task_id}: {task_name}"

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] delete_task() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to delete task - {str(e)}"


# ============================================================================
# TOOL 6: SEARCH TASKS
# ============================================================================

@tool
def search_tasks(filter_expression: str = "none") -> str:
    """
    Search and filter tasks using filter expressions.

    Args:
        filter_expression: Filter to apply. Options:
            - "none" or "all": Show all tasks
            - "done": Show only completed tasks
            - "undone": Show only incomplete tasks
            - "tag:TAG_NAME": Show tasks with specific tag
            - "priority=1": Show high priority tasks
            - "priority=2": Show medium priority tasks
            - "priority=3": Show low priority tasks

    Returns:
        Formatted list of matching tasks (limited to 10 results)

    Examples:
        search_tasks(filter_expression="undone")
        search_tasks(filter_expression="tag:backend")
        search_tasks(filter_expression="priority=1")
    """
    debug_log.debug(f"[AI_TOOLS] search_tasks() called - filter='{filter_expression}'")

    try:
        state = _get_state()

        # Parse filter
        filter_expr = filter_expression.lower().strip()

        # Apply filter
        if filter_expr in ("none", "all", ""):
            filtered = state.tasks
        elif filter_expr == "done":
            filtered = [t for t in state.tasks if t.done]
        elif filter_expr == "undone":
            filtered = [t for t in state.tasks if not t.done]
        elif filter_expr.startswith("tag:"):
            tag = filter_expr[4:].strip()
            filtered = [t for t in state.tasks if t.tag.lower() == tag]
        elif filter_expr.startswith("priority="):
            try:
                priority = int(filter_expr[9:])
                filtered = [t for t in state.tasks if t.priority == priority]
            except ValueError:
                debug_log.debug(f"[AI_TOOLS] Invalid priority in filter: {filter_expr}")
                return f"❌ Error: Invalid priority filter. Use priority=1, priority=2, or priority=3"
        else:
            debug_log.debug(f"[AI_TOOLS] Invalid filter expression: {filter_expr}")
            return f"❌ Error: Invalid filter expression. Valid filters: none, done, undone, tag:NAME, priority=1/2/3"

        # Limit results
        limit = ai_config.TOOL_SEARCH_LIMIT
        filtered = filtered[:limit]

        debug_log.info(f"[AI_TOOLS] Search completed - filter='{filter_expression}', found {len(filtered)} tasks")

        if not filtered:
            return f"No tasks found matching filter: {filter_expression}"

        # Format results
        result = f"Found {len(filtered)} task(s):\n\n"

        priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
        for task in filtered:
            status = "✅" if task.done else "❌"
            priority_icon = priority_icons.get(task.priority, "⚪")
            priority_label = {1: "HIGH", 2: "MED", 3: "LOW"}.get(task.priority, "?")

            result += f"{status} {priority_icon} [#{task.id}] {task.name}\n"
            result += f"   Priority: {priority_label}"
            if task.tag:
                result += f" | Tag: {task.tag}"
            if task.comment:
                result += f" | Comment: {task.comment}"
            result += "\n\n"

        if len(state.tasks) > limit:
            result += f"\n(Showing first {limit} results. Use more specific filters to narrow down.)"

        return result

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] search_tasks() failed: {str(e)}", exception=e)
        return f"❌ Error: Search failed - {str(e)}"


# ============================================================================
# TOOL 7: GET TASK DETAILS
# ============================================================================

@tool
def get_task_details(task_id: int) -> str:
    """
    Get full details of a specific task.

    Args:
        task_id: ID of the task to view

    Returns:
        Formatted task details including all fields, or error message

    Example:
        get_task_details(task_id=5)
    """
    debug_log.debug(f"[AI_TOOLS] get_task_details() called - task_id={task_id}")

    try:
        state = _get_state()

        # Find task
        task = _find_task_by_id(task_id)
        if not task:
            debug_log.debug(f"[AI_TOOLS] Task not found - ID={task_id}")
            return f"❌ Error: Task #{task_id} not found"

        # Format details
        status = "✅ COMPLETED" if task.done else "❌ INCOMPLETE"
        priority_label = {1: "🔴 HIGH", 2: "🟡 MEDIUM", 3: "🟢 LOW"}.get(task.priority, "UNKNOWN")

        result = f"**Task #{task.id}**: {task.name}\n\n"
        result += f"**Status**: "
        result += f"**Priority**: {priority_label}\n"

        if task.tag:
            result += f"**Tag**: {task.tag}\n"

        if task.comment:
            result += f"**Comment**: {task.comment}\n"

        if task.description:
            result += f"\n**Description**:\n{task.description}\n"

        debug_log.info(f"[AI_TOOLS] Task details retrieved - ID={task_id}")
        return result

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] get_task_details() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to get task details - {str(e)}"


# ============================================================================
# TOOL 8: GET TASK STATISTICS
# ============================================================================

@tool
def get_task_statistics() -> str:
    """
    Get workspace task statistics and summary.

    Returns:
        Formatted statistics including:
        - Total tasks, done, pending
        - Priority distribution
        - Tag distribution
        - Current filter/view info

    Example:
        get_task_statistics()
    """
    debug_log.debug("[AI_TOOLS] get_task_statistics() called")

    try:
        state = _get_state()

        total = len(state.tasks)
        done = sum(1 for t in state.tasks if t.done)
        pending = total - done

        debug_log.debug(f"[AI_TOOLS] Statistics - total={total}, done={done}, pending={pending}")

        # Priority breakdown (incomplete tasks only)
        priority_counts = {1: 0, 2: 0, 3: 0}
        for task in state.tasks:
            if not task.done:
                priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1

        # Tag distribution
        tag_counts = {}
        for task in state.tasks:
            if task.tag:
                tag_counts[task.tag] = tag_counts.get(task.tag, 0) + 1

        # Format response
        result = "📊 **Task Statistics**\n\n"
        result += f"**Total**: {total} tasks\n"
        result += f"**Done**: {done} ({(done/total*100) if total > 0 else 0:.1f}%)\n"
        result += f"**Pending**: {pending}\n\n"

        if pending > 0:
            result += "**Priority Distribution** (incomplete tasks):\n"
            result += f"  🔴 High: {priority_counts[1]}\n"
            result += f"  🟡 Medium: {priority_counts[2]}\n"
            result += f"  🟢 Low: {priority_counts[3]}\n\n"

        if tag_counts:
            result += "**Top Tags**:\n"
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for tag, count in sorted_tags:
                result += f"  • {tag}: {count} task(s)\n"
            result += "\n"

        # Current view info
        result += f"**Current View**: {state.view_mode}\n"
        result += f"**Active Filter**: {state.filter}\n"
        result += f"**Sort Order**: {state.sort} ({state.sort_order})\n"

        debug_log.info(f"[AI_TOOLS] Statistics generated - {total} tasks, {len(tag_counts)} unique tags")
        return result

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] get_task_statistics() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to get statistics - {str(e)}"


# ============================================================================
# TOOL 9: SAVE ALL CHANGES
# ============================================================================

@tool
def save_all_changes() -> str:
    """
    Explicitly save all tasks and notes to disk.

    Use this when:
    - User explicitly asks to "save" or "persist" changes
    - After making multiple modifications and wanting to ensure persistence
    - Before critical operations to ensure data is saved

    Note: Most operations auto-save, but this provides explicit confirmation.

    Returns:
        Success message confirming tasks and notes were saved

    Example:
        save_all_changes()
    """
    debug_log.debug("[AI_TOOLS] save_all_changes() called")

    try:
        state = _get_state()

        # Save tasks to disk
        _save_tasks()
        task_count = len(state.tasks)

        # Refresh notes from disk (notes save automatically via repository)
        state.refresh_notes_from_disk()
        note_count = len(getattr(state, 'notes', []))

        debug_log.info(f"[AI_TOOLS] save_all_changes() completed - {task_count} tasks, {note_count} notes")

        return f"✅ All changes saved to disk\n   Tasks: {task_count}\n   Notes: {note_count}"

    except Exception as e:
        debug_log.error(f"[AI_TOOLS] save_all_changes() failed: {str(e)}", exception=e)
        return f"❌ Error: Failed to save changes - {str(e)}"


# ============================================================================
# TOOL REGISTRY
# ============================================================================

def get_all_tools():
    """
    Get list of all available tools for agent initialization.

    Returns:
        List of LangChain tool functions (21 tools)
    """
    return [
        # Task management (9 tools)
        create_task,
        edit_task,
        complete_task,
        uncomplete_task,
        delete_task,
        search_tasks,
        get_task_details,
        get_task_statistics,
        save_all_changes,  # NEW: Explicit save tool
        # Notes tools (8 tools)
        create_note,
        edit_note,
        link_note,
        unlink_note,
        delete_note,
        search_notes,
        get_note_details,
        get_linked_notes_for_task,
        # Advanced helpers (4 tools)
        get_note_body,
        convert_note_to_task,
        append_note_to_task,
        open_note_in_editor,
    ]


# ============================================================================
# NOTES TOOLS
# ============================================================================

def _notes_repo() -> FileNoteRepository:
    return FileNoteRepository(DEFAULT_NOTES_DIR)


def _parse_csv_ints(value: str) -> List[int]:
    res: List[int] = []
    for part in (value or "").replace(",", " ").split():
        try:
            res.append(int(part))
        except Exception:
            pass
    return res


def _parse_csv_tags(value: str) -> List[str]:
    return [t.strip().lower() for t in (value or "").replace(",", " ").split() if t.strip()]


def _excerpt(text: str, n: int = 160) -> str:
    s = (text or "").strip().replace("\r", "")
    if not s:
        return "(empty)"
    line = next((ln for ln in s.splitlines() if ln.strip()), "")
    return (line[:n] + ("…" if len(line) > n else "")) or "(empty)"


@tool
def create_note(title: str, body_md: str = "", tags: str = "", task_ids: str = "") -> str:
    """
    Create a new note and optionally link it to tasks.

    Args:
        title: Note title (required)
        body_md: Markdown body (optional)
        tags: Space/comma separated tags (optional)
        task_ids: Space/comma separated task IDs to link (optional)

    Returns: Success message with note id and excerpt
    """
    try:
        repo = _notes_repo()
        note = repo.create(
            title=title,
            body_md=body_md or "",
            tags=_parse_csv_tags(tags),
            task_ids=_parse_csv_ints(task_ids),
        )
        state = _get_state()
        try:
            from debug_logger import debug_log
            before = len(getattr(state, 'notes', []))
            debug_log.info(f"[AI_TOOLS] create_note() created id={note.id[:8]} title='{note.title}' (state had {before} notes)")
        except Exception:
            pass
        state.refresh_notes_from_disk()
        # Switch to notes view in UI
        try:
            state.entity_mode = 'notes'
            state.page = 0
        except Exception:
            pass
        try:
            from debug_logger import debug_log
            after = len(getattr(state, 'notes', []))
            debug_log.info(f"[AI_TOOLS] create_note() state refresh complete (now {after} notes)")
        except Exception:
            pass
        return f"✅ Created note {note.id[:8]}: {note.title} — {_excerpt(note.body_md)}"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] create_note() failed: {e}", exception=e)
        return f"❌ Error: Failed to create note - {e}"


@tool
def edit_note(note_id: str, field: str, value: str, mode: str = "replace") -> str:
    """
    Edit a note field or content.

    Args:
        note_id: Note id or prefix
        field: one of: title, tags, body, add_task, remove_task
        value: new value (for tags: space/comma separated; for body: text)
        mode: for body - "replace" (default) or "append"

    Returns: Success message
    """
    try:
        repo = _notes_repo()
        note = repo.get(note_id)
        if not note:
            return f"❌ Error: Note {note_id} not found"
        field_l = (field or "").strip().lower()
        if field_l == "title":
            note.title = value.strip()
        elif field_l == "tags":
            # Support bulk add/remove with +tag / -tag tokens; otherwise replace
            raw = (value or "").strip()
            tokens = [t.strip() for t in raw.replace(",", " ").split() if t.strip()]
            if any(t.startswith(('+', '-')) for t in tokens):
                # Start from current tags
                tagset = {t for t in (note.tags or [])}
                for tok in tokens:
                    if tok.startswith('+'):
                        t = tok[1:].strip().lower()
                        if t:
                            tagset.add(t)
                    elif tok.startswith('-'):
                        t = tok[1:].strip().lower()
                        if t in tagset:
                            tagset.remove(t)
                note.tags = sorted(tagset)
            else:
                note.tags = _parse_csv_tags(raw)
        elif field_l == "body":
            if (mode or "").lower() == "append":
                note.body_md = (note.body_md or "") + ("\n" if note.body_md else "") + value
            else:
                note.body_md = value
        elif field_l == "add_task":
            for tid in _parse_csv_ints(value):
                repo.link_task(note, tid)
        elif field_l == "remove_task":
            for tid in _parse_csv_ints(value):
                repo.unlink_task(note, tid)
        else:
            return f"❌ Error: Invalid field '{field}'. Valid: title, tags, body, add_task, remove_task"
        # Persist changes
        repo.update(note)
        _get_state().refresh_notes_from_disk()
        return f"### ✅ Note Updated\n- id: `{note.id[:8]}`\n- field: `{field_l}`"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] edit_note() failed: {e}", exception=e)
        return f"❌ Error: Failed to edit note - {e}"


@tool
def link_note(note_id: str, task_id: int) -> str:
    """Link a note to a task (idempotent)."""
    try:
        repo = _notes_repo()
        note = repo.get(note_id)
        if not note:
            return f"❌ Error: Note {note_id} not found"
        repo.link_task(note, task_id)
        _get_state().refresh_notes_from_disk()
        return f"### ✅ Linked\n- note: `{note.id[:8]}`\n- task: `#{task_id}`"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] link_note() failed: {e}", exception=e)
        return f"❌ Error: Failed to link note - {e}"


@tool
def unlink_note(note_id: str, task_id: int) -> str:
    """Unlink a note from a task (idempotent)."""
    try:
        repo = _notes_repo()
        note = repo.get(note_id)
        if not note:
            return f"❌ Error: Note {note_id} not found"
        repo.unlink_task(note, task_id)
        _get_state().refresh_notes_from_disk()
        return f"### ✅ Unlinked\n- note: `{note.id[:8]}`\n- task: `#{task_id}`"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] unlink_note() failed: {e}", exception=e)
        return f"❌ Error: Failed to unlink note - {e}"


@tool
def delete_note(note_id_prefix: str, force: bool = False) -> str:
    """Delete notes by id prefix. Requires >=5 chars or force=True for short prefixes."""
    try:
        if len(note_id_prefix or "") < 5 and not force:
            return "❌ Error: Prefix too short. Use at least 5 chars or set force=True"
        repo = _notes_repo()
        ok = repo.delete(note_id_prefix)
        _get_state().refresh_notes_from_disk()
        return (f"### ✗ Deleted\n- prefix: `{note_id_prefix}`" if ok else f"### ℹ️ No notes deleted\n- prefix: `{note_id_prefix}`")
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] delete_note() failed: {e}", exception=e)
        return f"❌ Error: Failed to delete note - {e}"


@tool
def search_notes(query: str = "", task_id: int | None = None, tag: str = "") -> str:
    """Search notes by text, and optionally filter by task_id or tag. Returns a short list."""
    try:
        repo = _notes_repo()
        notes = repo.list_all()
        if task_id is not None:
            notes = [n for n in notes if task_id in (n.task_ids or [])]
        if tag:
            t = tag.strip().lower()
            notes = [n for n in notes if t in (n.tags or [])]
        q = (query or "").strip().lower()
        if q:
            notes = [n for n in notes if (q in (n.title or '').lower()) or (q in (n.body_md or '').lower()) or any(q in t for t in (n.tags or []))]
        if not notes:
            return "No notes found"
        lines = ["### 🔎 Notes"]
        for n in notes[:20]:
            lines.append(f"• `{n.id[:8]}` | {n.title} | tags: {', '.join(n.tags)} | tasks: {' '.join('#'+str(t) for t in n.task_ids[:5])} | {_excerpt(n.body_md, 60)}")
        return "\n".join(lines)
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] search_notes() failed: {e}", exception=e)
        return f"❌ Error: Failed to search notes - {e}"


@tool
def get_note_details(note_id: str) -> str:
    """Get full note details including linked tasks and first 30 lines of body."""
    try:
        repo = _notes_repo()
        n = repo.get(note_id)
        if not n:
            return f"❌ Error: Note {note_id} not found"
        lines = [f"### 📝 Note `{n.id[:8]}`", n.title]
        if n.tags:
            lines.append(f"- tags: {', '.join(n.tags)}")
        if n.task_ids:
            lines.append(f"- linked tasks: {' '.join('#'+str(t) for t in n.task_ids)}")
        body = (n.body_md or '').splitlines()[:30]
        if body:
            lines.append("\n---")
            lines.extend(body)
        return "\n".join(lines)
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] get_note_details() failed: {e}", exception=e)
        return f"❌ Error: Failed to get note details - {e}"


@tool
def get_linked_notes_for_task(task_id: int) -> str:
    """List notes linked to a specific task (by task_id)."""
    try:
        repo = _notes_repo()
        notes = repo.list_by_task(task_id)
        if not notes:
            return f"No notes linked to task #{task_id}"
        lines = [f"### 🧷 Notes for task #{task_id}"]
        for n in notes[:20]:
            lines.append(f"• `{n.id[:8]}` | {n.title} | tags: {', '.join(n.tags)} | {_excerpt(n.body_md, 60)}")
        return "\n".join(lines)
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] get_linked_notes_for_task() failed: {e}", exception=e)
        return f"❌ Error: Failed to list notes - {e}"


@tool
def get_note_body(note_id: str) -> str:
    """Return the full body text of a note (for summarization by the agent)."""
    try:
        repo = _notes_repo()
        n = repo.get(note_id)
        if not n:
            return f"❌ Error: Note {note_id} not found"
        return n.body_md or "(empty)"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] get_note_body() failed: {e}", exception=e)
        return f"❌ Error: Failed to read note - {e}"


@tool
def convert_note_to_task(note_id: str, priority: int = 2, tags: str = "") -> str:
    """
    Create a task from a note (name=title, description=body). Links note to new task.

    Args:
        note_id: Note id or prefix
        priority: Task priority (1..3)
        tags: Optional space/comma separated tags for the new task (defaults to note tags)
    """
    try:
        repo = _notes_repo()
        n = repo.get(note_id)
        if not n:
            return f"❌ Error: Note {note_id} not found"
        state = _get_state()
        name = n.title or "Untitled"
        comment = f"from note {n.id[:8]}"
        tag_list = _parse_csv_tags(tags) if (tags or "").strip() else list(n.tags or [])
        tag_str = ",".join(tag_list)
        # Use existing add_task pathway via state
        state.add_task(name=name, comment=comment, description=n.body_md or "", priority=max(1, min(3, priority)), tag=tag_str)
        try:
            # Switch UI to tasks view to show the newly created task
            state.entity_mode = 'tasks'
            state.page = 0
        except Exception:
            pass
        new_task_id = state.tasks[-1].id if state.tasks else None
        if new_task_id is not None:
            repo.link_task(n, new_task_id)
            state.refresh_notes_from_disk()
            _save_tasks()
            return f"### ✅ Created task from note\n- note: `{n.id[:8]}`\n- task: `#{new_task_id}`\n- name: {name}"
        return "❌ Error: Failed to create task"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] convert_note_to_task() failed: {e}", exception=e)
        return f"❌ Error: Failed to convert note - {e}"


@tool
def append_note_to_task(note_id: str, task_id: int, header: str = "") -> str:
    """
    Append a note's body to a task's description (with optional header).
    """
    try:
        repo = _notes_repo()
        n = repo.get(note_id)
        if not n:
            return f"❌ Error: Note {note_id} not found"
        task = _find_task_by_id(task_id)
        if not task:
            return f"❌ Error: Task #{task_id} not found"
        block = n.body_md or ""
        if not block:
            return f"ℹ️  Note {note_id} is empty; nothing to append"
        prefix = f"\n\n## {header}\n" if header else "\n\n## Note\n"
        task.description = (task.description or "") + prefix + block
        try:
            task.updated_at = datetime.now().isoformat()
        except Exception:
            pass
        _save_tasks()
        # Ensure link exists for traceability
        repo.link_task(n, task_id)
        _get_state().refresh_notes_from_disk()
        return f"### ✅ Appended note to task\n- note: `{n.id[:8]}`\n- task: `#{task_id}`"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] append_note_to_task() failed: {e}", exception=e)
        return f"❌ Error: Failed to append note - {e}"


@tool
def open_note_in_editor(note_id: str) -> str:
    """Open a note in the local editor ($VISUAL/$EDITOR) and wait for close."""
    try:
        repo = _notes_repo()
        n = repo.get(note_id)
        if not n:
            return f"❌ Error: Note {note_id} not found"
        from utils.editor import open_in_editor
        from config import DEFAULT_EDITOR_CMD
        path = repo._note_path(n.id, n.title)
        rc = open_in_editor(str(path), DEFAULT_EDITOR_CMD)
        _get_state().refresh_notes_from_disk()
        return f"### 📝 Opened in editor\n- note: `{n.id[:8]}`\n- exit code: {rc}"
    except Exception as e:
        debug_log.error(f"[AI_TOOLS] open_note_in_editor() failed: {e}", exception=e)
        return f"❌ Error: Failed to open note - {e}"

