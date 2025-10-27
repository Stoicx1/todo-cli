"""
Integration tests for complete task workflows

Tests the full lifecycle of tasks through the system:
create → edit → tag → filter → sort → complete → delete

No mocks - real state, real commands, real persistence.
Tests verify system behavior end-to-end.
"""

import pytest
import json
from io import StringIO
from pathlib import Path

from core.state import AppState
from tests.test_factories import StateFactory
from core.commands import handle_command
from models.task import Task


# Use shared `console` fixture from tests/conftest.py


@pytest.fixture
def temp_tasks_file(tmp_path):
    """Temporary file for task persistence"""
    return tmp_path / "tasks.json"


class TestTaskLifecycle:
    """Test complete task lifecycle"""

    def test_create_edit_complete_delete_workflow(self, app_state, console):
        """Test full task lifecycle: create → edit → complete → delete"""
        # Step 1: Create task
        handle_command('add "New Feature" "High priority" "Implement user auth" 1 "work"', app_state, console)

        assert len(app_state.tasks) == 1
        task = app_state.tasks[0]
        task_id = task.id
        assert task.name == "New Feature"
        assert task.priority == 1
        assert "work" in task.tags
        assert task.done is False

        # Step 2: Edit task
        handle_command(f'edit {task_id} "User Authentication" - "Updated description" 2 "work, security"', app_state, console)

        task = app_state.get_task_by_id(task_id)
        assert task.name == "User Authentication"
        assert task.priority == 2
        assert "security" in task.tags

        # Step 3: Mark as done
        handle_command(f'done {task_id}', app_state, console)

        task = app_state.get_task_by_id(task_id)
        assert task.done is True
        assert task.completed_at != ""

        # Step 4: Delete task
        initial_count = len(app_state.tasks)
        handle_command(f'remove {task_id}', app_state, console)

        assert len(app_state.tasks) == initial_count - 1
        assert app_state.get_task_by_id(task_id) is None

    def test_create_multiple_tasks_workflow(self, app_state, console):
        """Test creating multiple tasks and verifying state"""
        # Create 5 tasks
        for i in range(1, 6):
            handle_command(f'add "Task {i}" "Comment {i}" "" {(i % 3) + 1} "tag{i % 3}"', app_state, console)

        assert len(app_state.tasks) == 5

        # Verify all tasks created correctly
        for i, task in enumerate(app_state.tasks, 1):
            assert task.name == f"Task {i}"
            assert task.comment == f"Comment {i}"
            assert task.id == i

    def test_bulk_operations_workflow(self, app_state, console, monkeypatch):
        """Test bulk operations on multiple tasks"""
        # Mock confirmation to always return True (avoid stdin in tests)
        import core.commands
        monkeypatch.setattr(core.commands, 'confirm', lambda msg, **kwargs: True)

        # Create 10 tasks
        for i in range(1, 11):
            handle_command(f'add "Task {i}"', app_state, console)

        assert len(app_state.tasks) == 10

        # Bulk mark as done (tasks 1-5)
        handle_command('done 1-5', app_state, console)

        for i in range(1, 6):
            assert app_state.get_task_by_id(i).done is True

        for i in range(6, 11):
            assert app_state.get_task_by_id(i).done is False

        # Bulk delete (tasks 6-10) - confirmation mocked
        handle_command('remove 6-10', app_state, console)

        assert len(app_state.tasks) == 5

        # Verify remaining tasks are 1-5
        for i in range(1, 6):
            assert app_state.get_task_by_id(i) is not None


class TestFilterWorkflow:
    """Test filtering workflows"""

    def test_filter_by_status_workflow(self, app_state, console):
        """Test filtering by task status"""
        # Create tasks with mixed statuses
        for i in range(1, 11):
            handle_command(f'add "Task {i}"', app_state, console)

        # Mark some as done
        handle_command('done 1 3 5 7 9', app_state, console)

        # Filter for done tasks
        app_state.filter = "status=done"
        filtered = app_state.filtered_tasks

        assert len(filtered) == 5
        assert all(task.done for task in filtered)

        # Filter for undone tasks
        app_state.filter = "status=undone"
        filtered = app_state.filtered_tasks

        assert len(filtered) == 5
        assert all(not task.done for task in filtered)

    def test_filter_by_priority_workflow(self, app_state, console):
        """Test filtering by priority"""
        # Create tasks with different priorities
        for priority in [1, 1, 2, 2, 3, 3]:
            handle_command(f'add "Task P{priority}" "" "" {priority}', app_state, console)

        # Filter high priority
        app_state.filter = "priority=1"
        filtered = app_state.filtered_tasks

        assert len(filtered) == 2
        assert all(task.priority == 1 for task in filtered)

        # Filter medium or low priority
        app_state.filter = "priority=2,3"
        filtered = app_state.filtered_tasks

        assert len(filtered) == 4

    def test_compound_filter_workflow(self, app_state, console):
        """Test compound filtering"""
        # Create diverse tasks
        handle_command('add "High Work" "" "" 1 "work"', app_state, console)
        handle_command('add "High Personal" "" "" 1 "personal"', app_state, console)
        handle_command('add "Med Work" "" "" 2 "work"', app_state, console)
        handle_command('add "Med Personal" "" "" 2 "personal"', app_state, console)

        # Mark some done
        handle_command('done 1 3', app_state, console)

        # Filter: done AND work
        app_state.filter = "status=done tag=work"
        filtered = app_state.filtered_tasks

        assert len(filtered) == 2
        assert all(task.done and "work" in task.tags for task in filtered)


class TestSortWorkflow:
    """Test sorting workflows"""

    def test_sort_by_priority_workflow(self, app_state, console):
        """Test sorting by priority"""
        # Create tasks with mixed priorities
        handle_command('add "Low" "" "" 3', app_state, console)
        handle_command('add "High" "" "" 1', app_state, console)
        handle_command('add "Med" "" "" 2', app_state, console)

        # Sort by priority ascending
        app_state.sort = "priority"
        app_state.sort_order = "asc"
        sorted_tasks = app_state.get_sorted_tasks(app_state.tasks)

        assert sorted_tasks[0].priority == 1
        assert sorted_tasks[1].priority == 2
        assert sorted_tasks[2].priority == 3

        # Sort descending
        app_state.sort_order = "desc"
        sorted_tasks = app_state.get_sorted_tasks(app_state.tasks)

        assert sorted_tasks[0].priority == 3
        assert sorted_tasks[1].priority == 2
        assert sorted_tasks[2].priority == 1

    def test_filter_then_sort_workflow(self, app_state, console):
        """Test filtering then sorting"""
        # Create tasks
        for i in range(1, 6):
            priority = (i % 3) + 1
            handle_command(f'add "Task {i}" "" "" {priority} "work"', app_state, console)

        # Mark some done
        handle_command('done 1 2', app_state, console)

        # Filter undone, then sort by priority
        app_state.filter = "status=undone"
        app_state.sort = "priority"
        app_state.sort_order = "asc"

        filtered = app_state.filtered_tasks
        sorted_tasks = app_state.get_sorted_tasks(filtered)

        # Should have 3 undone tasks, sorted by priority
        assert len(sorted_tasks) == 3
        assert all(not task.done for task in sorted_tasks)
        # Verify sorted
        for i in range(len(sorted_tasks) - 1):
            assert sorted_tasks[i].priority <= sorted_tasks[i+1].priority


class TestPersistenceWorkflow:
    """Test persistence workflows with real file I/O"""

    def test_create_save_load_workflow(self, app_state, console, temp_tasks_file):
        """Test creating tasks, saving, and loading"""
        # Create tasks
        for i in range(1, 6):
            handle_command(f'add "Task {i}"', app_state, console)

        # Save to file
        app_state.save_to_file(str(temp_tasks_file), console)

        assert temp_tasks_file.exists()

        # Create new state and load
        new_state = AppState()
        new_state.load_from_file(str(temp_tasks_file), console)

        # Verify loaded state matches
        assert len(new_state.tasks) == 5
        for i in range(1, 6):
            task = new_state.get_task_by_id(i)
            assert task is not None
            assert task.name == f"Task {i}"

    def test_modify_save_load_workflow(self, app_state, console, temp_tasks_file):
        """Test modify → save → load cycle"""
        # Create and save
        handle_command('add "Original Task"', app_state, console)
        app_state.save_to_file(str(temp_tasks_file), console)

        # Modify task
        task_id = app_state.tasks[0].id
        handle_command(f'edit {task_id} "Modified Task"', app_state, console)
        handle_command(f'done {task_id}', app_state, console)

        # Save again
        app_state.save_to_file(str(temp_tasks_file), console)

        # Load and verify
        new_state = AppState()
        new_state.load_from_file(str(temp_tasks_file), console)

        task = new_state.get_task_by_id(task_id)
        assert task.name == "Modified Task"
        assert task.done is True


class TestIndexConsistency:
    """Test index consistency throughout workflows"""

    def test_index_after_operations(self, app_state, console):
        """Test that indexes remain consistent after operations"""
        # Add tasks
        for i in range(1, 6):
            handle_command(f'add "Task {i}" "" "" {i % 3 + 1} "tag{i % 3}"', app_state, console)

        # Verify task index
        for i in range(1, 6):
            task_index = app_state.get_task_by_id(i)
            task_list = next((t for t in app_state.tasks if t.id == i), None)
            assert task_index is task_list

        # Edit task (changes tags)
        handle_command('edit 1 - - - - "newtag"', app_state, console)

        # Verify tag index updated
        tasks_with_newtag = app_state.get_tasks_by_tag("newtag")
        assert len(tasks_with_newtag) > 0
        assert any(t.id == 1 for t in tasks_with_newtag)

        # Remove task
        handle_command('remove 1', app_state, console)

        # Verify task removed from index
        assert app_state.get_task_by_id(1) is None

    def test_tag_index_after_edits(self, app_state, console):
        """Test tag index consistency after tag edits"""
        # Create tasks with tags
        handle_command('add "Task 1" "" "" 1 "work, urgent"', app_state, console)
        handle_command('add "Task 2" "" "" 1 "work"', app_state, console)

        # Verify initial tag index
        work_tasks = app_state.get_tasks_by_tag("work")
        assert len(work_tasks) == 2

        urgent_tasks = app_state.get_tasks_by_tag("urgent")
        assert len(urgent_tasks) == 1

        # Remove tag from task 1
        task1 = app_state.get_task_by_id(1)
        handle_command('edit 1 - - - - "work"', app_state, console)

        # Verify tag index updated
        urgent_tasks = app_state.get_tasks_by_tag("urgent")
        assert len(urgent_tasks) == 0


class TestErrorRecoveryWorkflow:
    """Test error recovery in workflows"""

    def test_invalid_command_recovery(self, app_state, console):
        """Test system recovers from invalid commands"""
        # Create initial task
        handle_command('add "Valid Task"', app_state, console)
        initial_count = len(app_state.tasks)

        # Execute invalid command - should not crash
        try:
            handle_command('invalid_command', app_state, console)
        except Exception:
            pass  # May raise, but shouldn't corrupt state

        # State should be unchanged or valid
        assert len(app_state.tasks) >= initial_count

        # Should still be able to execute valid commands
        handle_command('add "Another Task"', app_state, console)
        assert len(app_state.tasks) >= initial_count + 1

    def test_partial_edit_failure(self, app_state, console):
        """Test partial edit doesn't corrupt state"""
        handle_command('add "Task 1"', app_state, console)
        task_id = app_state.tasks[0].id

        original_name = app_state.get_task_by_id(task_id).name

        # Try edit with invalid ID - should handle gracefully
        try:
            handle_command('edit 999 "NewName"', app_state, console)
        except Exception:
            pass

        # Original task should be unchanged
        task = app_state.get_task_by_id(task_id)
        assert task.name == original_name


class TestLargeDatasetWorkflow:
    """Test workflows with large datasets"""

    @pytest.mark.slow
    def test_create_1000_tasks(self, console):
        """Test creating 1000 tasks via factory (faster)."""
        state = StateFactory.create_with_tasks(1000)
        assert len(state.tasks) == 1000
        assert state.next_id == 1001

    @pytest.mark.slow
    def test_bulk_operations_large_dataset(self, console):
        """Test bulk operations on large dataset"""
        state = StateFactory.create_with_tasks(500)

        # Bulk mark done (1-250)
        handle_command('done 1-250', state, console)

        # Verify
        done_count = sum(1 for t in state.tasks if t.done)
        assert done_count == 250

    @pytest.mark.slow
    def test_filter_performance_large_dataset(self, console):
        """Test filtering performance with large dataset"""
        # Create 1000 tasks with tags via factory
        state = StateFactory.create_with_tasks(1000)

        # Filter by tag
        state.filter = "tag=tag5"
        filtered = state.filtered_tasks

        # Should have ~100 tasks with tag5
        assert 95 <= len(filtered) <= 105

        # Compound filter
        state.filter = "tag=tag5 priority=1"
        filtered = state.filtered_tasks

        assert all("tag5" in task.tags and task.priority == 1 for task in filtered)
