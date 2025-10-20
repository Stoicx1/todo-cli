"""
Task Forms - Add and Edit Task Modals
Specific implementations for task creation and editing
"""

from typing import Optional, Dict, Any
from rich.console import Console
from ui.modal_form import ModalForm
from ui.form_fields import (
    TextField,
    TextAreaField,
    PriorityField,
    TagField,
    validate_not_empty,
    validate_priority,
    validate_max_length
)
from core.state import AppState
from models.task import Task


class AddTaskModal(ModalForm):
    """
    Modal form for adding a new task.
    Shows fields: Task Name, Priority, Tags, Comment, Description
    """

    def __init__(self, state: AppState, console: Optional[Console] = None):
        super().__init__(
            title="Add New Task",
            width=60,
            height=25,
            console=console
        )
        self.state = state

        # Get existing tags for autocomplete
        existing_tags = self._get_existing_tags()

        # Get last used priority (smart default)
        last_priority = self._get_last_priority()

        # Add fields
        self._setup_fields(existing_tags, last_priority)

    def _get_existing_tags(self) -> list:
        """Get list of all existing tags from tasks"""
        tags = set()
        for task in self.state.tasks:
            if task.tags:
                tags.update(task.tags)
            elif task.tag:
                tags.add(task.tag)
        return sorted(list(tags))

    def _get_last_priority(self) -> int:
        """Get the last priority used (default to 2 if none)"""
        if self.state.tasks:
            # Get most recent task's priority
            return self.state.tasks[-1].priority
        return 2  # Default to Medium

    def _setup_fields(self, existing_tags: list, last_priority: int):
        """Setup form fields"""
        # Task Name (required)
        self.add_field(TextField(
            name="name",
            label="Task Name",
            required=True,
            max_length=100,
            placeholder="Enter task name...",
            validator=validate_not_empty
        ))

        # Priority (defaults to last used)
        self.add_field(PriorityField(
            name="priority",
            label="Priority",
            default_value=last_priority,
            validator=validate_priority
        ))

        # Tags (autocomplete from existing)
        self.add_field(TagField(
            name="tags",
            label="Tags",
            existing_tags=existing_tags,
            max_tags=3,
            default_value=""
        ))

        # Comment (optional)
        self.add_field(TextField(
            name="comment",
            label="Comment",
            required=False,
            max_length=200,
            placeholder="Optional comment..."
        ))

        # Description (optional, multi-line)
        self.add_field(TextAreaField(
            name="description",
            label="Description",
            required=False,
            max_length=500,
            height=3
        ))

    @staticmethod
    def show_modal(state: AppState, console: Optional[Console] = None) -> Optional[Dict[str, Any]]:
        """
        Show the Add Task modal and return form data if submitted.
        Returns None if cancelled.
        """
        modal = AddTaskModal(state, console)
        result = modal.show()

        if result:
            # Convert tags from list to string for compatibility
            if 'tags' in result and isinstance(result['tags'], list):
                result['tag'] = ','.join(result['tags']) if result['tags'] else ''
            else:
                result['tag'] = ''

        return result


class EditTaskModal(ModalForm):
    """
    Modal form for editing an existing task.
    Pre-fills all fields with current task values.
    """

    def __init__(self, task: Task, state: AppState, console: Optional[Console] = None):
        super().__init__(
            title=f"Edit Task #{task.id}",
            width=60,
            height=25,
            console=console
        )
        self.task = task
        self.state = state

        # Get existing tags for autocomplete
        existing_tags = self._get_existing_tags()

        # Add fields with pre-filled values
        self._setup_fields(existing_tags)

    def _get_existing_tags(self) -> list:
        """Get list of all existing tags from tasks"""
        tags = set()
        for task in self.state.tasks:
            if task.tags:
                tags.update(task.tags)
            elif task.tag:
                tags.add(task.tag)
        return sorted(list(tags))

    def _setup_fields(self, existing_tags: list):
        """Setup form fields with current task values"""
        # Task Name (pre-filled)
        self.add_field(TextField(
            name="name",
            label="Task Name",
            required=True,
            max_length=100,
            default_value=self.task.name,
            validator=validate_not_empty
        ))

        # Priority (pre-filled)
        self.add_field(PriorityField(
            name="priority",
            label="Priority",
            default_value=self.task.priority,
            validator=validate_priority
        ))

        # Tags (pre-filled)
        current_tags = self.task.get_tags_display()  # Comma-separated string
        self.add_field(TagField(
            name="tags",
            label="Tags",
            existing_tags=existing_tags,
            max_tags=3,
            default_value=current_tags
        ))

        # Comment (pre-filled)
        self.add_field(TextField(
            name="comment",
            label="Comment",
            required=False,
            max_length=200,
            default_value=self.task.comment or ""
        ))

        # Description (pre-filled)
        self.add_field(TextAreaField(
            name="description",
            label="Description",
            required=False,
            max_length=500,
            height=3,
            default_value=self.task.description or ""
        ))

    @staticmethod
    def show_modal(task: Task, state: AppState, console: Optional[Console] = None) -> Optional[Dict[str, Any]]:
        """
        Show the Edit Task modal and return form data if submitted.
        Returns None if cancelled.
        """
        modal = EditTaskModal(task, state, console)
        result = modal.show()

        if result:
            # Convert tags from list to string for compatibility
            if 'tags' in result and isinstance(result['tags'], list):
                result['tag'] = ','.join(result['tags']) if result['tags'] else ''
            else:
                result['tag'] = ''

        return result


# Convenience functions for backward compatibility
def modal_add_task(state: AppState, console: Optional[Console] = None) -> Optional[Dict[str, Any]]:
    """
    Show Add Task modal and return form data.
    Convenience function for backward compatibility.
    """
    return AddTaskModal.show_modal(state, console)


def modal_edit_task(task: Task, state: AppState, console: Optional[Console] = None) -> Optional[Dict[str, Any]]:
    """
    Show Edit Task modal and return form data.
    Convenience function for backward compatibility.
    """
    return EditTaskModal.show_modal(task, state, console)
