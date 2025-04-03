from typing import List
from models.task import Task
from rich.console import Console
import json


class AppState:
    def __init__(self):
        self.tasks: List[Task] = []
        self.next_id: int = 1
        self.page: int = 0
        self.page_size: int = 5
        self.view_mode: str = "compact"  # or "detailed"
        self.messages: list[str] = []

    def add_task(
        self, name: str, comment: str, description: str, priority: int, tag: str
    ):
        task = Task(
            id=self.next_id,
            name=name,
            comment=comment,
            description=description,
            priority=priority,
            tag=tag,
        )
        self.tasks.append(task)
        self.next_id += 1

    def get_sorted_tasks(self):
        return sorted(self.tasks, key=lambda t: not t.done)

    def get_current_page_tasks(self):
        # Dynamically set page_size based on view mode
        if self.view_mode == "compact":
            self.page_size = 10
        else:
            self.page_size = 5
        #
        sorted_tasks = self.get_sorted_tasks()
        start = self.page * self.page_size  # Use the correct page_size here
        end = start + self.page_size
        return sorted_tasks[start:end]

    def save_to_file(self, filename: str, console: Console):
        """Save tasks to a JSON file."""
        tasks_data = [
            task.__dict__ for task in self.tasks
        ]  # Convert tasks to dictionaries
        with open(filename, "w") as f:
            json.dump(tasks_data, f, indent=4)
        console.print(f"[+] Tasks saved to {filename}")

    def load_from_file(self, filename: str, console: Console):
        """Load tasks from a JSON file."""
        try:
            with open(filename, "r") as f:
                tasks_data = json.load(f)
                self.tasks = [Task(**task) for task in tasks_data]
                self.next_id = (
                    max(task.id for task in self.tasks) + 1 if self.tasks else 1
                )
            console.print(f"[+] Tasks loaded from {filename}")
        except FileNotFoundError:
            console.print(f"[!] No saved tasks found. Starting with an empty list.")
        except json.JSONDecodeError:
            console.print(f"[!] Error decoding JSON. The file might be corrupted.")
            self.tasks = []  # Initialize an empty task list if the file is corrupted
            self.next_id = 1
