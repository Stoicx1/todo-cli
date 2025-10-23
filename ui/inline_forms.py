"""
Inline Forms - Simple text-based forms as fallback
Used when questionary forms fail or are disabled
"""

from rich.console import Console
from models.task import Task


def inline_add_task(console: Console) -> str:
    """
    Show inline form for adding a task.

    Args:
        console: Rich console for output

    Returns:
        Command string to execute, or None if cancelled
    """
    console.print("\n[bold green]Add New Task[/bold green]")
    console.print("[dim]Type 'cancel' to abort[/dim]\n")

    task = input("Task Name: ").strip()

    # Check for cancellation
    if task.lower() in ('cancel', 'c', 'q', 'quit'):
        console.print("[yellow]Cancelled[/yellow]")
        return None

    comment = input("Comment: ")
    description = input("Description: ")
    priority = input("Priority (1-3): ") or "2"
    tag = input("Tag(s) [comma-separated, up to 3]: ")

    command = f'add "{task}" "{comment}" "{description}" {priority} "{tag}"'
    return command


def inline_edit_task(console: Console, task: Task) -> str:
    """
    Show inline form for editing a task.

    Args:
        console: Rich console for output
        task: Task to edit

    Returns:
        Command string to execute, or None if cancelled
    """
    console.print("\n[bold yellow]Edit Task[/bold yellow]")
    console.print(f"ID: {task.id}")
    console.print("[dim]Type 'cancel' to abort, or press Enter to keep current values[/dim]\n")

    task_name = input(f"Task Name [{task.name}]: ").strip()

    # Check for cancellation
    if task_name.lower() in ('cancel', 'c', 'q', 'quit'):
        console.print("[yellow]Cancelled[/yellow]")
        return None

    # Use current value if empty
    task_name = task_name or task.name

    comment = input(f"Comment [{task.comment}]: ") or task.comment
    description = input(f"Description [{task.description}]: ") or task.description
    priority = input(f"Priority [{task.priority}]: ") or str(task.priority)

    # Show current tags comma-separated
    current_tags = task.get_tags_display()
    tag = input(f"Tag(s) [{current_tags}]: ") or current_tags

    command = (
        f'edit {task.id} "{task_name}" "{comment}" "{description}" {priority} "{tag}"'
    )
    return command
