from typing import List
from models.task import Task
from rich.console import Console
import json


class AppState:
    def __init__(self):
        """
        Initialize the application state for the task manager.
        """
        self.tasks: list[Task] = []  # All tasks in memory
        self.next_id: int = 1  # Auto-incrementing task ID
        self.page: int = 0  # Current page number
        self.page_size: int = 5  # Number of tasks per page
        self.view_mode: str = "compact"  # View mode: 'compact' or 'detailed'
        self.messages: list[str] = []  # Messages to display to the user
        self.filter: str = "none"  # Active task filter
        self.sort: str = "priority"  # Active sort method

    def add_task(
        self, name: str, comment: str, description: str, priority: int, tag: str
    ):
        """
        Add a new task to the task list.

        Args:
            name (str): The title or name of the task.
            comment (str): A short comment or note.
            description (str): A more detailed task description.
            priority (int): Task priority (lower = higher priority).
            tag (str): A label/tag to categorize the task.
        """
        task = Task(
            id=self.next_id,
            name=name.strip(),
            comment=comment.strip(),
            description=description.strip(),
            priority=priority,
            tag=tag.strip().lower(),
        )
        self.tasks.append(task)
        self.next_id += 1

    def get_filter_tasks(self, tasks):
        """
        Filters the task list based on the current filter value.

        Supported filters:
            - "all":      Show all tasks.
            - "done":     Show only completed tasks.
            - "undone":   Show only incomplete tasks.
            - "tag:<tag>": Show tasks with the specified tag.
                          (e.g., "tag:work", "tag:psdc")
                          If the tag is missing or "all", show all tasks.

        Args:
            tasks (list): The list of Task objects to filter.

        Returns:
            list: A filtered list of tasks based on the current filter.
        """
        filter_value = self.filter.strip().lower()

        if filter_value == "none":
            return tasks

        if filter_value == "done":
            return [t for t in tasks if getattr(t, "done", False)]

        if filter_value == "undone":
            return [t for t in tasks if not getattr(t, "done", False)]

        if filter_value.startswith("tag:"):
            tag_value = filter_value.split(":", 1)[1].strip()
            if tag_value == "none" or not tag_value:
                return tasks
            return [
                t for t in tasks if getattr(t, "tag", "").strip().lower() == tag_value
            ]

        return tasks  # fallback for unknown filters

    def get_sorted_tasks(self, tasks):
        """
        Sorts the task list based on the current sort setting.

        Supported sort options:
            - "priority": Sort by task priority (ascending).
            - "id":       Sort by task ID (ascending).
            - "name":     Sort alphabetically by task name.

        Args:
            tasks (list): The list of Task objects to sort.

        Returns:
            list: A sorted list of tasks.
        """
        if self.sort == "priority":
            return sorted(tasks, key=lambda t: t.priority)
        if self.sort == "id":
            return sorted(tasks, key=lambda t: t.id)
        if self.sort == "name":
            return sorted(tasks, key=lambda t: t.name)
        return tasks  # Fallback: return unsorted if sort option is unknown

    def get_current_page_tasks(self):
        """
        Applies filtering, sorting, and pagination to the task list
        and returns only the tasks for the current page.

        Returns:
            list: A list of tasks to be displayed on the current page.
        """
        # Set page size dynamically based on view mode
        self.page_size = 20 if self.view_mode == "compact" else 10

        # Step 1: Filter tasks
        show_tasks = self.get_filter_tasks(self.tasks)

        # Step 2: Sort tasks
        show_tasks = self.get_sorted_tasks(show_tasks)

        # Step 3: Paginate tasks
        start = self.page * self.page_size
        end = start + self.page_size
        return show_tasks[start:end]

    def save_to_file(self, filename: str, console: Console):
        """
        Save all tasks to a JSON file.

        Args:
            filename (str): The name of the file to save tasks to.
            console (Console): Rich console for output messages.
        """
        try:
            tasks_data = [task.__dict__ for task in self.tasks]  # Serialize tasks
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(tasks_data, f, indent=4)
            console.print(f"[green][+][/green] Tasks saved to [bold]{filename}[/bold]")
        except Exception as e:
            console.print(f"[red][!][/red] Failed to save tasks: {e}")

    def load_from_file(self, filename: str, console: Console):
        """
        Load tasks from a JSON file.

        Args:
            filename (str): The path to the file to load from.
            console (Console): Rich console for displaying status messages.
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)
                self.tasks = [Task(**task) for task in tasks_data]
                self.next_id = (
                    max(task.id for task in self.tasks) + 1 if self.tasks else 1
                )
            console.print(
                f"[green][+][/green] Tasks loaded from [bold]{filename}[/bold]"
            )

        except FileNotFoundError:
            console.print("[yellow][!][/yellow] No saved tasks found. Starting fresh.")
            self.tasks = []
            self.next_id = 1

        except json.JSONDecodeError:
            console.print(
                "[red][!][/red] Failed to decode JSON. File might be corrupted."
            )
            self.tasks = []
            self.next_id = 1
