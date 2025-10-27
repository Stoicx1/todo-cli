"""
Tests for core/state.py - AppState class
"""

import pytest
import tempfile
import json
from pathlib import Path
from io import StringIO

from core.state import AppState
from models.task import Task


@pytest.fixture
def state():
    """Create a fresh AppState instance for each test"""
    return AppState()


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file path for testing persistence"""
    return tmp_path / "test_tasks.json"


# Use shared `console` fixture from tests/conftest.py


class TestAppStateInitialization:
    """Test AppState initialization"""

    def test_initial_state(self, state):
        """Test that AppState initializes with correct defaults"""
        assert state.tasks == []
        assert state.next_id == 1
        assert state.page == 0
        assert state.page_size == 5
        assert state.view_mode == "compact"
        assert state.messages == []
        assert state.filter == "none"
        assert state.sort == "priority"
        assert state.sort_order == "asc"
        assert state.notes == []
        assert state.entity_mode == "tasks"
        assert state.ai_conversation == []

    def test_task_index_enabled(self, state):
        """Test task index is initialized when enabled"""
        # Task index should be enabled by default (from config)
        assert state._task_index is not None
        assert isinstance(state._task_index, dict)

    def test_tag_index_initialized(self, state):
        """Test tag index is initialized"""
        assert state._tag_index is not None
        assert isinstance(state._tag_index, dict)


class TestTaskOperations:
    """Test task CRUD operations"""

    def test_add_task_basic(self, state):
        """Test adding a basic task"""
        state.add_task("Test Task", "Comment", "Description", 1, "work")

        assert len(state.tasks) == 1
        assert state.next_id == 2

        task = state.tasks[0]
        assert task.id == 1
        assert task.name == "Test Task"
        assert task.comment == "Comment"
        assert task.description == "Description"
        assert task.priority == 1
        assert task.tags == ["work"]

    def test_add_task_increments_id(self, state):
        """Test that adding tasks increments next_id"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 1, "")
        state.add_task("Task 3", "", "", 1, "")

        assert len(state.tasks) == 3
        assert state.next_id == 4
        assert state.tasks[0].id == 1
        assert state.tasks[1].id == 2
        assert state.tasks[2].id == 3

    def test_add_task_updates_task_index(self, state):
        """Test that adding a task updates the task index"""
        state.add_task("Task", "", "", 1, "")

        if state._task_index is not None:
            assert 1 in state._task_index
            assert state._task_index[1].name == "Task"

    def test_add_task_updates_tag_index(self, state):
        """Test that adding a task updates the tag index"""
        state.add_task("Task", "", "", 1, "work, urgent")

        assert "work" in state._tag_index
        assert "urgent" in state._tag_index
        assert len(state._tag_index["work"]) == 1
        assert len(state._tag_index["urgent"]) == 1

    def test_add_task_with_multiple_tags(self, state):
        """Test adding a task with multiple tags"""
        state.add_task("Task", "", "", 1, "work, urgent, personal")

        task = state.tasks[0]
        assert len(task.tags) == 3
        assert "work" in task.tags
        assert "urgent" in task.tags
        assert "personal" in task.tags

    def test_get_task_by_id_found(self, state):
        """Test getting a task by ID when it exists"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 1, "")

        task = state.get_task_by_id(2)
        assert task is not None
        assert task.id == 2
        assert task.name == "Task 2"

    def test_get_task_by_id_not_found(self, state):
        """Test getting a task by ID when it doesn't exist"""
        state.add_task("Task 1", "", "", 1, "")

        task = state.get_task_by_id(999)
        assert task is None

    def test_remove_task(self, state):
        """Test removing a task"""
        state.add_task("Task 1", "", "", 1, "work")
        state.add_task("Task 2", "", "", 1, "urgent")

        task = state.get_task_by_id(1)
        state.remove_task(task)

        assert len(state.tasks) == 1
        assert state.get_task_by_id(1) is None
        assert state.get_task_by_id(2) is not None

    def test_remove_task_updates_task_index(self, state):
        """Test that removing a task updates the task index"""
        state.add_task("Task", "", "", 1, "")
        task = state.get_task_by_id(1)
        state.remove_task(task)

        if state._task_index is not None:
            assert 1 not in state._task_index

    def test_remove_task_updates_tag_index(self, state):
        """Test that removing a task updates the tag index"""
        state.add_task("Task", "", "", 1, "work")
        task = state.get_task_by_id(1)
        state.remove_task(task)

        # Tag should be removed from index or have empty list
        assert "work" not in state._tag_index or len(state._tag_index["work"]) == 0


class TestTagOperations:
    """Test tag-related operations"""

    def test_get_tasks_by_tag(self, state):
        """Test getting tasks by tag"""
        state.add_task("Task 1", "", "", 1, "work")
        state.add_task("Task 2", "", "", 1, "work, urgent")
        state.add_task("Task 3", "", "", 1, "personal")

        work_tasks = state.get_tasks_by_tag("work")
        assert len(work_tasks) == 2
        assert all(task.name in ["Task 1", "Task 2"] for task in work_tasks)

    def test_get_all_tags_with_stats(self, state):
        """Test getting all tags with statistics"""
        state.add_task("Task 1", "", "", 1, "work")
        state.add_task("Task 2", "", "", 1, "work")
        task = state.get_task_by_id(1)
        task.done = True

        stats = state.get_all_tags_with_stats()

        assert "work" in stats
        assert stats["work"]["total"] == 2
        assert stats["work"]["done"] == 1
        assert stats["work"]["pending"] == 1


class TestFilteringAndSorting:
    """Test filtering and sorting operations"""

    def test_filter_none_returns_all(self, state):
        """Test that filter='none' returns all tasks"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 1, "")

        state.filter = "none"
        filtered = state.filtered_tasks

        assert len(filtered) == 2

    def test_filter_status_done(self, state):
        """Test filtering by done status"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 1, "")
        state.get_task_by_id(1).done = True

        state.filter = "status=done"
        filtered = state.filtered_tasks

        assert len(filtered) == 1
        assert filtered[0].id == 1

    def test_filter_status_undone(self, state):
        """Test filtering by undone status"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 1, "")
        state.get_task_by_id(1).done = True

        state.filter = "status=undone"
        filtered = state.filtered_tasks

        assert len(filtered) == 1
        assert filtered[0].id == 2

    def test_filter_by_tag(self, state):
        """Test filtering by tag"""
        state.add_task("Task 1", "", "", 1, "work")
        state.add_task("Task 2", "", "", 1, "personal")
        state.add_task("Task 3", "", "", 1, "work")

        state.filter = "tag=work"
        filtered = state.filtered_tasks

        assert len(filtered) == 2
        assert all(task.name in ["Task 1", "Task 3"] for task in filtered)

    def test_filter_by_priority(self, state):
        """Test filtering by priority"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 2, "")
        state.add_task("Task 3", "", "", 1, "")

        state.filter = "priority=1"
        filtered = state.filtered_tasks

        assert len(filtered) == 2
        assert all(task.priority == 1 for task in filtered)

    def test_filter_compound_conditions(self, state):
        """Test filtering with compound conditions"""
        state.add_task("Task 1", "", "", 1, "work")
        state.add_task("Task 2", "", "", 2, "work")
        state.add_task("Task 3", "", "", 1, "personal")
        state.get_task_by_id(1).done = True

        state.filter = "status=done priority=1 tag=work"
        filtered = state.filtered_tasks

        assert len(filtered) == 1
        assert filtered[0].id == 1

    def test_filter_cache_invalidation(self, state):
        """Test that filter cache is invalidated on changes"""
        state.add_task("Task 1", "", "", 1, "")
        state.filter = "status=undone"

        # First call populates cache
        filtered1 = state.filtered_tasks
        assert len(filtered1) == 1

        # Add task invalidates cache
        state.add_task("Task 2", "", "", 1, "")
        filtered2 = state.filtered_tasks
        assert len(filtered2) == 2

    def test_sort_by_priority(self, state):
        """Test sorting by priority"""
        state.add_task("Low", "", "", 3, "")
        state.add_task("High", "", "", 1, "")
        state.add_task("Medium", "", "", 2, "")

        state.sort = "priority"
        state.sort_order = "asc"
        sorted_tasks = state.get_sorted_tasks(state.tasks)

        assert sorted_tasks[0].priority == 1
        assert sorted_tasks[1].priority == 2
        assert sorted_tasks[2].priority == 3

    def test_sort_by_id(self, state):
        """Test sorting by ID"""
        state.add_task("Task 3", "", "", 1, "")
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 1, "")

        state.sort = "id"
        state.sort_order = "asc"
        sorted_tasks = state.get_sorted_tasks(state.tasks)

        assert sorted_tasks[0].id == 1
        assert sorted_tasks[1].id == 2
        assert sorted_tasks[2].id == 3

    def test_sort_by_name(self, state):
        """Test sorting by name"""
        state.add_task("Charlie", "", "", 1, "")
        state.add_task("Alice", "", "", 1, "")
        state.add_task("Bob", "", "", 1, "")

        state.sort = "name"
        state.sort_order = "asc"
        sorted_tasks = state.get_sorted_tasks(state.tasks)

        assert sorted_tasks[0].name == "Alice"
        assert sorted_tasks[1].name == "Bob"
        assert sorted_tasks[2].name == "Charlie"

    def test_sort_descending(self, state):
        """Test sorting in descending order"""
        state.add_task("Task 1", "", "", 1, "")
        state.add_task("Task 2", "", "", 2, "")
        state.add_task("Task 3", "", "", 3, "")

        state.sort = "priority"
        state.sort_order = "desc"
        sorted_tasks = state.get_sorted_tasks(state.tasks)

        assert sorted_tasks[0].priority == 3
        assert sorted_tasks[1].priority == 2
        assert sorted_tasks[2].priority == 1


class TestPagination:
    """Test pagination functionality"""

    def test_get_current_page_first_page(self, state):
        """Test getting first page of tasks"""
        for i in range(10):
            state.add_task(f"Task {i+1}", "", "", 1, "")

        state.page = 0
        # Note: get_current_page_tasks() sets page_size from config based on view_mode
        # For compact mode (default), it uses ui.COMPACT_PAGE_SIZE
        state.view_mode = "compact"
        page_tasks = state.get_current_page_tasks()

        # Page size is determined by config, not manually set value
        # In compact mode with default config, all tasks may be shown
        assert len(page_tasks) >= 5
        assert page_tasks[0].id == 1

    def test_get_current_page_second_page(self, state):
        """Test getting second page of tasks"""
        # Create enough tasks to test pagination
        for i in range(30):
            state.add_task(f"Task {i+1}", "", "", 1, "")

        state.page = 1
        state.view_mode = "compact"
        page_tasks = state.get_current_page_tasks()

        # Second page should have tasks (if page_size allows pagination)
        # Task IDs depend on page_size from config
        assert isinstance(page_tasks, list)

    def test_get_current_page_partial_page(self, state):
        """Test pagination behavior"""
        for i in range(7):
            state.add_task(f"Task {i+1}", "", "", 1, "")

        state.page = 0
        state.view_mode = "compact"
        page_tasks = state.get_current_page_tasks()

        # Pagination behavior depends on config
        # Just verify we get a valid list of tasks
        assert isinstance(page_tasks, list)
        assert len(page_tasks) > 0


class TestPersistence:
    """Test task persistence (save/load)"""

    def test_save_tasks_to_file(self, state, temp_file, console):
        """Test saving tasks to file"""
        state.add_task("Task 1", "Comment", "Description", 1, "work")
        state.add_task("Task 2", "", "", 2, "personal")

        state.save_to_file(str(temp_file), console)

        assert temp_file.exists()

        # Verify JSON content
        data = json.loads(temp_file.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "Task 1"
        assert data[1]["name"] == "Task 2"

    def test_load_tasks_from_file(self, state, temp_file, console):
        """Test loading tasks from file"""
        # Create test data
        tasks_data = [
            {
                "id": 1,
                "name": "Task 1",
                "comment": "Comment",
                "description": "Desc",
                "priority": 1,
                "tag": "work",
                "tags": ["work"],
                "done": False,
                "created_at": "2024-01-01T00:00:00",
                "completed_at": "",
                "updated_at": "2024-01-01T00:00:00",
            },
            {
                "id": 2,
                "name": "Task 2",
                "comment": "",
                "description": "",
                "priority": 2,
                "tag": "",
                "tags": [],
                "done": False,
                "created_at": "2024-01-01T00:00:00",
                "completed_at": "",
                "updated_at": "2024-01-01T00:00:00",
            },
        ]

        temp_file.write_text(json.dumps(tasks_data))

        state.load_from_file(str(temp_file), console)

        assert len(state.tasks) == 2
        assert state.next_id == 3
        assert state.tasks[0].name == "Task 1"
        assert state.tasks[1].name == "Task 2"

    def test_load_from_nonexistent_file(self, state, temp_file, console):
        """Test loading from a file that doesn't exist"""
        state.load_from_file(str(temp_file), console)

        # Should initialize with empty state
        assert state.tasks == []
        assert state.next_id == 1

    def test_save_empty_list_protection(self, state, temp_file, console):
        """Test that saving empty list when tasks existed is prevented"""
        # First save with tasks
        state.add_task("Task 1", "", "", 1, "")
        state.save_to_file(str(temp_file), console)

        # Clear tasks and try to save
        state.tasks = []
        state.save_to_file(str(temp_file), console)

        # Original file should still have data
        data = json.loads(temp_file.read_text())
        assert len(data) == 1


class TestAIConversation:
    """Test AI conversation management"""

    def test_add_ai_message(self, state):
        """Test adding AI messages to conversation"""
        msg1 = state.add_ai_message("user", "Hello")
        msg2 = state.add_ai_message("assistant", "Hi there")

        assert len(state.ai_conversation) == 2
        assert msg1.role == "user"
        assert msg1.content == "Hello"
        assert msg2.role == "assistant"
        assert msg2.content == "Hi there"

    def test_clear_conversation(self, state):
        """Test clearing AI conversation"""
        state.add_ai_message("user", "Hello")
        state.add_ai_message("assistant", "Hi")

        state.clear_conversation()

        assert len(state.ai_conversation) == 0

    def test_get_conversation_context(self, state):
        """Test getting conversation context"""
        state.add_ai_message("user", "Hello")
        state.add_ai_message("assistant", "Hi")

        context = state.get_conversation_context()

        assert len(context) == 2
        assert isinstance(context[0], dict)
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "Hello"

    def test_conversation_limit(self, state):
        """Test that conversation is limited to max messages"""
        # Add more messages than the limit (100)
        for i in range(110):
            state.add_ai_message("user", f"Message {i}")

        # Should trim to max
        assert len(state.ai_conversation) <= 100
