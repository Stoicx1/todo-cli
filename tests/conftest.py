"""
Shared pytest fixtures and configuration for all tests
"""

import pytest
import tempfile
from pathlib import Path
from io import StringIO

from core.state import AppState
from models.task import Task


@pytest.fixture
def app_state():
    """
    Create a fresh AppState instance for each test

    Returns:
        AppState: A new AppState instance with default settings
    """
    return AppState()


@pytest.fixture
def populated_state():
    """
    Create an AppState with sample tasks for testing

    Returns:
        AppState: AppState with 5 sample tasks
    """
    state = AppState()

    # Add diverse sample tasks
    state.add_task("Write tests", "Unit tests", "Create comprehensive test suite", 1, "work, testing")
    state.add_task("Review code", "Code review", "Review pull request #42", 2, "work")
    state.add_task("Buy groceries", "Shopping", "Milk, eggs, bread", 3, "personal")
    state.add_task("Fix bug", "Critical", "Fix login issue", 1, "work, urgent")
    state.add_task("Update docs", "", "Update README", 2, "work")

    # Mark some as done
    state.get_task_by_id(2).done = True
    state.get_task_by_id(5).done = True

    return state


@pytest.fixture
def sample_task():
    """
    Create a sample task for testing

    Returns:
        Task: A sample task instance
    """
    return Task(
        id=1,
        name="Sample Task",
        comment="This is a comment",
        description="This is a detailed description",
        priority=1,
        tag="work",
        tags=["work", "testing"],
        done=False,
    )


@pytest.fixture
def temp_dir(tmp_path):
    """
    Create a temporary directory for test files

    Args:
        tmp_path: pytest built-in fixture for temporary directories

    Returns:
        Path: Path to temporary directory
    """
    return tmp_path


@pytest.fixture
def temp_json_file(tmp_path):
    """
    Create a temporary JSON file path

    Args:
        tmp_path: pytest built-in fixture for temporary directories

    Returns:
        Path: Path to temporary JSON file
    """
    return tmp_path / "test_tasks.json"


class Console:
    """Minimal console stub with print() compatible API used by AppState."""

    def __init__(self, file=None, force_terminal: bool = False, width: int = 100):
        self.file = file or StringIO()
        self.width = width

    def print(self, *args, **kwargs):
        try:
            text = " ".join(str(a) for a in args)
            self.file.write(text + "\n")
        except Exception:
            pass


class NullConsole(Console):
    """A fast console that discards output for performance-sensitive tests."""
    def __init__(self):
        super().__init__(file=StringIO(), force_terminal=False, width=120)


@pytest.fixture
def console():
    """Default console for tests (captured output)."""
    return Console(file=StringIO(), force_terminal=False, width=100)


@pytest.fixture
def null_console():
    """High-performance console discarding output (for performance tests)."""
    return NullConsole()

# Custom assertion helpers
def assert_task_equals(actual, expected):
    assert actual.id == expected.id
    assert actual.name == expected.name
    assert actual.priority == expected.priority
    assert actual.tag == expected.tag
    assert actual.tags == expected.tags


def assert_error_message(messages, pattern: str):
    assert any(pattern.lower() in str(m).lower() for m in messages)


def assert_timestamp_valid(ts: str):
    assert isinstance(ts, str) and len(ts) >= 19 and "T" in ts


def assert_performance_baseline(duration_ms: float, max_ms: float):
    assert duration_ms <= max_ms


@pytest.fixture
def tasks_list():
    """
    Create a list of diverse tasks for testing filtering and sorting

    Returns:
        list[Task]: List of 10 sample tasks with various attributes
    """
    tasks = [
        Task(id=1, name="High priority work", comment="", description="", priority=1, tag="work", tags=["work"], done=False),
        Task(id=2, name="Medium priority work", comment="", description="", priority=2, tag="work", tags=["work"], done=False),
        Task(id=3, name="Low priority work", comment="", description="", priority=3, tag="work", tags=["work"], done=True),
        Task(id=4, name="High priority personal", comment="", description="", priority=1, tag="personal", tags=["personal"], done=False),
        Task(id=5, name="Medium priority personal", comment="", description="", priority=2, tag="personal", tags=["personal"], done=True),
        Task(id=6, name="Urgent work task", comment="", description="", priority=1, tag="work", tags=["work", "urgent"], done=False),
        Task(id=7, name="Project task", comment="", description="", priority=2, tag="project", tags=["project", "work"], done=False),
        Task(id=8, name="Quick fix", comment="", description="", priority=1, tag="work", tags=["work"], done=True),
        Task(id=9, name="Long term goal", comment="", description="", priority=3, tag="personal", tags=["personal"], done=False),
        Task(id=10, name="Shopping", comment="", description="", priority=3, tag="personal", tags=["personal", "shopping"], done=False),
    ]
    return tasks


@pytest.fixture(autouse=True)
def reset_test_environment():
    """
    Automatically run before each test to ensure clean environment

    This fixture runs automatically for all tests (autouse=True)
    """
    # Setup: runs before each test
    yield
    # Teardown: runs after each test
    # Add any cleanup code here if needed


# Helper functions for tests

def create_task_dict(id=1, name="Test", comment="", description="", priority=2, tag="", tags=None, done=False):
    """
    Helper function to create task dictionaries for JSON serialization tests

    Args:
        id: Task ID
        name: Task name
        comment: Task comment
        description: Task description
        priority: Task priority (1-3)
        tag: Legacy single tag
        tags: List of tags
        done: Task completion status

    Returns:
        dict: Task data as dictionary
    """
    return {
        "id": id,
        "name": name,
        "comment": comment,
        "description": description,
        "priority": priority,
        "tag": tag,
        "tags": tags or [],
        "done": done,
        "created_at": "2024-01-01T00:00:00",
        "completed_at": "",
        "updated_at": "2024-01-01T00:00:00",
    }
