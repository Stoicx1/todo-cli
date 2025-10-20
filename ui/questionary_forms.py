"""
Questionary Forms - Interactive multi-field forms using questionary library
Provides clean, user-friendly forms for adding and editing tasks
"""

from typing import Optional, Dict, Any, List
import questionary
from questionary import Style
from core.state import AppState
from models.task import Task


# Custom style for forms (optional - can be customized)
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),       # Question mark
    ('question', 'bold'),                # Question text
    ('answer', 'fg:#f44336 bold'),      # User answer
    ('pointer', 'fg:#673ab7 bold'),     # Selection pointer
    ('highlighted', 'fg:#673ab7 bold'), # Highlighted choice
    ('selected', 'fg:#cc5454'),         # Selected choice
    ('separator', 'fg:#cc5454'),        # Separator
    ('instruction', ''),                 # Instructions
    ('text', ''),                        # Plain text
    ('disabled', 'fg:#858585 italic')   # Disabled choices
])


def get_existing_tags(state: AppState) -> List[str]:
    """Get list of all existing tags for autocomplete"""
    tags = set()
    for task in state.tasks:
        if task.tags:
            tags.update(task.tags)
        elif task.tag:
            tags.add(task.tag)
    return sorted(list(tags))


def get_last_priority(state: AppState) -> int:
    """Get the last priority used (for smart defaults)"""
    if state.tasks:
        return state.tasks[-1].priority
    return 2  # Default to Medium


def questionary_add_task(state: AppState) -> Optional[Dict[str, Any]]:
    """
    Show interactive form for adding a new task using questionary.
    Returns dict with field values if submitted, None if cancelled.
    """
    try:
        # Get existing tags for reference (shown in instruction)
        existing_tags = get_existing_tags(state)
        tag_hint = f" (existing: {', '.join(existing_tags[:5])})" if existing_tags else ""

        # Get last used priority for smart default
        last_priority = get_last_priority(state)
        priority_choices = [
            "1 - High",
            "2 - Med",
            "3 - Low"
        ]
        default_priority_idx = last_priority - 1  # Convert 1-3 to 0-2

        print("\n")  # Add spacing before form

        # Create form with all fields
        result = questionary.form(
            name=questionary.text(
                "Task Name:",
                validate=lambda x: len(x.strip()) > 0 or "Task name cannot be empty",
                style=custom_style
            ),
            priority=questionary.select(
                "Priority:",
                choices=priority_choices,
                default=priority_choices[default_priority_idx],
                style=custom_style
            ),
            tags=questionary.text(
                f"Tags (comma-separated, max 3){tag_hint}:",
                default="",
                style=custom_style
            ),
            comment=questionary.text(
                "Comment (optional):",
                default="",
                style=custom_style
            ),
            description=questionary.text(
                "Description (optional):",
                default="",
                style=custom_style
            )
        ).ask()

        if result:
            # Parse priority from "1 - High" to just "1"
            priority_str = result['priority'].split(' ')[0]
            result['priority'] = int(priority_str)

            # Keep tags as string (will be parsed by add_task)
            result['tag'] = result.pop('tags', '')

            return result

        return None

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        return None
    except Exception as e:
        # Unexpected error - return None to fall back to inline form
        print(f"\n[Error] Form error: {e}")
        return None


def questionary_edit_task(task: Task, state: AppState) -> Optional[Dict[str, Any]]:
    """
    Show interactive form for editing an existing task using questionary.
    Pre-fills all fields with current task values.
    Returns dict with field values if submitted, None if cancelled.
    """
    try:
        # Get existing tags for reference
        existing_tags = get_existing_tags(state)
        tag_hint = f" (existing: {', '.join(existing_tags[:5])})" if existing_tags else ""

        # Priority choices
        priority_choices = [
            "1 - High",
            "2 - Med",
            "3 - Low"
        ]
        current_priority_idx = task.priority - 1

        # Current tags as comma-separated string
        current_tags = task.get_tags_display()

        print(f"\n[Editing Task #{task.id}]\n")  # Header

        # Create form with pre-filled values
        result = questionary.form(
            name=questionary.text(
                "Task Name:",
                default=task.name,
                validate=lambda x: len(x.strip()) > 0 or "Task name cannot be empty",
                style=custom_style
            ),
            priority=questionary.select(
                "Priority:",
                choices=priority_choices,
                default=priority_choices[current_priority_idx],
                style=custom_style
            ),
            tags=questionary.text(
                f"Tags (comma-separated, max 3){tag_hint}:",
                default=current_tags,
                style=custom_style
            ),
            comment=questionary.text(
                "Comment (optional):",
                default=task.comment or "",
                style=custom_style
            ),
            description=questionary.text(
                "Description (optional):",
                default=task.description or "",
                style=custom_style
            )
        ).ask()

        if result:
            # Parse priority from "1 - High" to just "1"
            priority_str = result['priority'].split(' ')[0]
            result['priority'] = int(priority_str)

            # Keep tags as string (will be parsed by caller)
            result['tag'] = result.pop('tags', '')

            return result

        return None

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        return None
    except Exception as e:
        # Unexpected error - return None to fall back to inline form
        print(f"\n[Error] Form error: {e}")
        return None


def questionary_confirm(message: str, default: bool = False) -> bool:
    """
    Show a yes/no confirmation dialog.
    Returns True for Yes, False for No.
    """
    try:
        return questionary.confirm(
            message,
            default=default,
            style=custom_style
        ).ask()
    except KeyboardInterrupt:
        return False
