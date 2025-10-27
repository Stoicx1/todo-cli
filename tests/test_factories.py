"""
Test factories for generating realistic test data

Provides factories for creating tasks, states, and other test objects
with realistic data for comprehensive testing.

Moved to tests root to avoid import conflicts.
"""

import random
import string
from datetime import datetime, timedelta
from typing import List, Optional

from models.task import Task
from core.state import AppState


class TaskFactory:
    """Factory for creating realistic Task instances"""

    # Sample data for realistic tasks
    TASK_NAMES = [
        "Write documentation", "Fix bug in login", "Review pull request",
        "Update dependencies", "Refactor database layer", "Add unit tests",
        "Deploy to production", "Design new feature", "Optimize performance",
        "Security audit", "Update README", "Create API endpoint",
    ]

    COMMENTS = [
        "High priority", "Urgent", "Low priority", "Nice to have",
        "Critical bug", "Enhancement", "Technical debt", "Quick fix",
    ]

    DESCRIPTIONS = [
        "Detailed implementation notes here",
        "See ticket #123 for more details",
        "This is a critical issue affecting users",
    ]

    TAGS = [
        "work", "personal", "urgent", "bug", "feature", "enhancement",
        "technical-debt", "security", "performance", "documentation",
    ]

    @staticmethod
    def create(
        id: Optional[int] = None,
        name: Optional[str] = None,
        comment: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        tag: Optional[str] = None,
        tags: Optional[List[str]] = None,
        done: Optional[bool] = None,
        created_at: Optional[str] = None,
    ) -> Task:
        """Create a single Task instance with optional overrides"""
        if id is None:
            id = random.randint(1, 10000)
        if name is None:
            name = random.choice(TaskFactory.TASK_NAMES)
        if comment is None and random.random() > 0.3:
            comment = random.choice(TaskFactory.COMMENTS)
        elif comment is None:
            comment = ""
        if description is None and random.random() > 0.5:
            description = random.choice(TaskFactory.DESCRIPTIONS)
        elif description is None:
            description = ""
        if priority is None:
            priority = random.randint(1, 3)
        if tags is None and random.random() > 0.4:
            num_tags = random.randint(1, 3)
            tags = random.sample(TaskFactory.TAGS, num_tags)
            tag = tags[0] if not tag else tag
        elif tags is None:
            tags = []
            tag = tag or ""
        if done is None:
            done = random.random() > 0.7
        if created_at is None:
            days_ago = random.randint(0, 30)
            dt = datetime.now() - timedelta(days=days_ago)
            created_at = dt.isoformat()

        return Task(
            id=id,
            name=name,
            comment=comment,
            description=description,
            priority=priority,
            tag=tag,
            tags=tags,
            done=done,
            created_at=created_at,
            completed_at="" if not done else (datetime.now() - timedelta(days=random.randint(0, 10))).isoformat(),
            updated_at=created_at,
        )

    @staticmethod
    def create_batch(count: int, **kwargs) -> List[Task]:
        """Create multiple tasks with unique IDs"""
        return [TaskFactory.create(id=i+1, **kwargs) for i in range(count)]


class StateFactory:
    """Factory for creating AppState instances with realistic data"""

    @staticmethod
    def create_empty() -> AppState:
        """Create empty AppState"""
        return AppState()

    @staticmethod
    def create_with_tasks(count: int = 10, **task_kwargs) -> AppState:
        """Create AppState populated with tasks"""
        state = AppState()
        tasks = TaskFactory.create_batch(count, **task_kwargs)

        for task in tasks:
            state.tasks.append(task)
            state.next_id = max(state.next_id, task.id + 1)

        state._rebuild_index()
        state._rebuild_tag_index()

        return state


# Convenience functions
def make_task(**kwargs) -> Task:
    """Shorthand for TaskFactory.create()"""
    return TaskFactory.create(**kwargs)


def make_tasks(count: int, **kwargs) -> List[Task]:
    """Shorthand for TaskFactory.create_batch()"""
    return TaskFactory.create_batch(count, **kwargs)


def make_state(count: int = 10, **kwargs) -> AppState:
    """Shorthand for StateFactory.create_with_tasks()"""
    return StateFactory.create_with_tasks(count, **kwargs)
