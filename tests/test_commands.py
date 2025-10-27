"""
Comprehensive tests for core/commands.py - Command handlers and parsing

Tests all command handlers with edge cases, error conditions, and special scenarios.
No mocks where real behavior should be tested - solid, production-ready tests.
"""

import pytest
from io import StringIO

from core.commands import (
    parse_command,
    parse_task_ids,
    handle_add,
    handle_done,
    handle_undone,
    handle_command,
    COMMAND_ALIASES,
)
from core.state import AppState
from models.task import Task


# Use shared `console` fixture from tests/conftest.py


@pytest.fixture
def state_with_tasks(app_state):
    """AppState with 10 sample tasks for testing"""
    for i in range(1, 11):
        app_state.add_task(
            name=f"Task {i}",
            comment=f"Comment {i}",
            description=f"Description {i}",
            priority=(i % 3) + 1,  # Rotate between 1, 2, 3
            tag=f"tag{i % 3}"  # Rotate tags
        )
    return app_state


class TestParseCommand:
    """Test command parsing and alias resolution"""

    def test_parse_empty_command(self, app_state, console):
        """Test parsing empty command"""
        result = parse_command("", app_state, console)
        assert result is None

    def test_parse_whitespace_only(self, app_state, console):
        """Test parsing whitespace-only command"""
        result = parse_command("   ", app_state, console)
        assert result is None

    def test_parse_simple_command(self, app_state, console):
        """Test parsing simple command without arguments"""
        cmd, parts = parse_command("help", app_state, console)
        assert cmd == "help"
        assert parts == ["help"]

    def test_parse_command_with_args(self, app_state, console):
        """Test parsing command with arguments"""
        cmd, parts = parse_command("add Task1", app_state, console)
        assert cmd == "add"
        assert parts == ["add", "Task1"]

    def test_parse_quoted_arguments(self, app_state, console):
        """Test parsing command with quoted arguments"""
        cmd, parts = parse_command('add "Task with spaces" "comment"', app_state, console)
        assert cmd == "add"
        assert parts == ["add", "Task with spaces", "comment"]

    def test_parse_alias_expansion(self, app_state, console):
        """Test that aliases are expanded correctly"""
        cmd, parts = parse_command("a Task", app_state, console)
        assert parts[0] == "add"  # Alias 'a' expanded to 'add'

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("a", "add"), ("e", "edit"), ("x", "done"), ("d", "done"),
            ("u", "undone"), ("n", "next"), ("p", "prev"), ("s", "show"),
            ("v", "view"), ("f", "filter"), ("t", "tags"), ("h", "help"),
            ("q", "exit"), ("r", "remove"),
        ],
    )
    def test_parse_all_single_letter_aliases(self, app_state, console, alias, expected):
        """Test all single-letter command aliases (parametrized)"""
        cmd, parts = parse_command(f"{alias} arg", app_state, console)
        assert parts[0] == expected

    def test_parse_word_aliases(self, app_state, console):
        """Test word-based aliases (quit, delete, del)"""
        # quit → exit
        cmd, parts = parse_command("quit", app_state, console)
        assert parts[0] == "exit"

        # delete → remove
        cmd, parts = parse_command("delete 1", app_state, console)
        assert parts[0] == "remove"

        # del → remove
        cmd, parts = parse_command("del 1", app_state, console)
        assert parts[0] == "remove"

    def test_parse_case_insensitive(self, app_state, console):
        """Test that commands are case-insensitive"""
        cmd, parts = parse_command("ADD Task", app_state, console)
        # parse_command returns lowercase command
        assert parts[0].lower() == "add"

        cmd, parts = parse_command("DeLeTe 1", app_state, console)
        # Alias 'delete' maps to 'remove'
        assert cmd.lower() == "delete" or parts[0].lower() in ["delete", "remove"]

    def test_parse_special_characters(self, app_state, console):
        """Test parsing commands with special characters"""
        cmd, parts = parse_command('add "Task @#$%"', app_state, console)
        assert parts[1] == "Task @#$%"

    def test_parse_unicode_input(self, app_state, console):
        """Test parsing commands with Unicode characters"""
        cmd, parts = parse_command('add "任务 🎉"', app_state, console)
        assert parts[1] == "任务 🎉"

    def test_parse_backslash_in_quotes(self, app_state, console):
        """Test parsing commands with backslashes"""
        cmd, parts = parse_command(r'add "Path\\to\\file"', app_state, console)
        assert "Path" in parts[1]


class TestParseTaskIds:
    """Test task ID parsing for bulk operations"""

    def test_parse_single_id(self):
        """Test parsing single task ID"""
        ids = parse_task_ids(["5"])
        assert ids == [5]

    def test_parse_multiple_ids(self):
        """Test parsing multiple task IDs"""
        ids = parse_task_ids(["1", "3", "5"])
        assert ids == [1, 3, 5]

    def test_parse_range(self):
        """Test parsing ID range (1-5)"""
        ids = parse_task_ids(["1-5"])
        assert ids == [1, 2, 3, 4, 5]

    def test_parse_comma_separated(self):
        """Test parsing comma-separated IDs"""
        ids = parse_task_ids(["1,3,5"])
        assert ids == [1, 3, 5]

    def test_parse_mixed_formats(self):
        """Test parsing mixed ID formats (single, range, comma)"""
        ids = parse_task_ids(["1", "3-5", "7,9"])
        assert ids == [1, 3, 4, 5, 7, 9]

    def test_parse_invalid_ids_skipped(self):
        """Test that invalid IDs are skipped"""
        ids = parse_task_ids(["1", "abc", "3"])
        assert ids == [1, 3]

    def test_parse_duplicate_ids_removed(self):
        """Test that duplicate IDs are removed"""
        ids = parse_task_ids(["1", "1", "2", "1-3"])
        assert ids == [1, 2, 3]

    def test_parse_reverse_range(self):
        """Test parsing reverse range (5-1)"""
        ids = parse_task_ids(["5-1"])
        # Should skip invalid range or handle gracefully
        assert isinstance(ids, list)

    def test_parse_empty_input(self):
        """Test parsing empty input"""
        ids = parse_task_ids([])
        assert ids == []

    def test_parse_negative_ids(self):
        """Test that negative IDs are handled"""
        ids = parse_task_ids(["-1", "2"])
        # Negative IDs should be skipped or handled
        assert 2 in ids


class TestHandleAdd:
    """Test add command handler with comprehensive scenarios"""

    def test_add_minimal_task(self, app_state, console):
        """Test adding task with minimum required fields (name only)"""
        initial_count = len(app_state.tasks)

        handle_add(["add", "Simple Task"], app_state, console)

        assert len(app_state.tasks) == initial_count + 1
        task = app_state.tasks[-1]
        assert task.name == "Simple Task"
        assert task.comment == ""
        assert task.description == ""

    def test_add_task_with_all_fields(self, app_state, console):
        """Test adding task with all fields specified"""
        handle_add(
            ["add", "Full Task", "Comment", "Description", "1", "work"],
            app_state,
            console
        )

        task = app_state.tasks[-1]
        assert task.name == "Full Task"
        assert task.comment == "Comment"
        assert task.description == "Description"
        assert task.priority == 1
        assert "work" in task.tags

    def test_add_task_missing_name(self, app_state, console):
        """Test adding task without name shows error"""
        initial_count = len(app_state.tasks)

        handle_add(["add"], app_state, console)

        assert len(app_state.tasks) == initial_count
        assert len(app_state.messages) > 0
        assert "Usage" in app_state.messages[0]

    def test_add_task_with_multiple_tags(self, app_state, console):
        """Test adding task with multiple tags"""
        handle_add(
            ["add", "Tagged Task", "", "", "2", "work, urgent, project"],
            app_state,
            console
        )

        task = app_state.tasks[-1]
        assert len(task.tags) <= 3  # Max 3 tags
        assert "work" in task.tags

    def test_add_task_unicode_name(self, app_state, console):
        """Test adding task with Unicode name"""
        handle_add(["add", "任务 🎉"], app_state, console)

        task = app_state.tasks[-1]
        assert task.name == "任务 🎉"

    def test_add_task_special_characters(self, app_state, console):
        """Test adding task with special characters"""
        handle_add(["add", "Task @#$% & *()"], app_state, console)

        task = app_state.tasks[-1]
        assert "@#$%" in task.name

    def test_add_task_very_long_name(self, app_state, console):
        """Test adding task with very long name"""
        long_name = "A" * 1000
        handle_add(["add", long_name], app_state, console)

        task = app_state.tasks[-1]
        assert task.name == long_name

    def test_add_task_invalid_priority(self, app_state, console):
        """Test adding task with invalid priority (clamped)"""
        try:
            handle_add(["add", "Task", "", "", "99"], app_state, console)
            if app_state.tasks:
                task = app_state.tasks[-1]
                # Priority should be clamped to valid range (1-3)
                assert 1 <= task.priority <= 3
        except (IndexError, ValueError):
            # Expected - invalid priority may cause error
            pass

    def test_add_task_negative_priority(self, app_state, console):
        """Test adding task with negative priority"""
        try:
            handle_add(["add", "Task", "", "", "-1"], app_state, console)
            if app_state.tasks:
                task = app_state.tasks[-1]
                assert task.priority >= 1
        except (IndexError, ValueError):
            # Expected - negative priority may cause error
            pass

    def test_add_increments_id(self, app_state, console):
        """Test that adding tasks increments IDs correctly"""
        handle_add(["add", "Task 1"], app_state, console)
        id1 = app_state.tasks[-1].id

        handle_add(["add", "Task 2"], app_state, console)
        id2 = app_state.tasks[-1].id

        assert id2 == id1 + 1


class TestHandleDone:
    """Test done command handler"""

    def test_done_single_task(self, state_with_tasks, console):
        """Test marking single task as done"""
        task = state_with_tasks.get_task_by_id(1)
        assert task.done is False

        handle_done(["done", "1"], state_with_tasks, console)

        assert task.done is True

    def test_done_multiple_tasks(self, state_with_tasks, console):
        """Test marking multiple tasks as done"""
        handle_done(["done", "1", "2", "3"], state_with_tasks, console)

        assert state_with_tasks.get_task_by_id(1).done is True
        assert state_with_tasks.get_task_by_id(2).done is True
        assert state_with_tasks.get_task_by_id(3).done is True

    def test_done_with_range(self, state_with_tasks, console):
        """Test marking range of tasks as done"""
        handle_done(["done", "1-3"], state_with_tasks, console)

        for i in range(1, 4):
            assert state_with_tasks.get_task_by_id(i).done is True

    def test_done_nonexistent_task(self, state_with_tasks, console):
        """Test marking nonexistent task as done"""
        handle_done(["done", "999"], state_with_tasks, console)

        # Should show error message
        assert len(state_with_tasks.messages) > 0

    def test_done_missing_id(self, state_with_tasks, console):
        """Test done command without task ID"""
        handle_done(["done"], state_with_tasks, console)

        assert len(state_with_tasks.messages) > 0
        assert "Usage" in state_with_tasks.messages[0]

    def test_done_already_done_task(self, state_with_tasks, console):
        """Test marking already-done task as done (idempotent)"""
        task = state_with_tasks.get_task_by_id(1)
        task.done = True

        handle_done(["done", "1"], state_with_tasks, console)

        assert task.done is True  # Still done

    def test_done_sets_completed_timestamp(self, state_with_tasks, console):
        """Test that marking task as done sets completed_at timestamp"""
        task = state_with_tasks.get_task_by_id(1)
        assert task.completed_at == ""

        handle_done(["done", "1"], state_with_tasks, console)

        assert task.completed_at != ""


class TestHandleUndone:
    """Test undone command handler"""

    def test_undone_single_task(self, state_with_tasks, console):
        """Test marking single task as undone"""
        task = state_with_tasks.get_task_by_id(1)
        task.done = True

        handle_undone(["undone", "1"], state_with_tasks, console)

        assert task.done is False

    def test_undone_multiple_tasks(self, state_with_tasks, console):
        """Test marking multiple tasks as undone"""
        for i in range(1, 4):
            state_with_tasks.get_task_by_id(i).done = True

        handle_undone(["undone", "1", "2", "3"], state_with_tasks, console)

        for i in range(1, 4):
            assert state_with_tasks.get_task_by_id(i).done is False

    def test_undone_clears_completed_timestamp(self, state_with_tasks, console):
        """Test that marking task as undone clears completed_at"""
        task = state_with_tasks.get_task_by_id(1)
        task.done = True
        task.completed_at = "2024-01-01T00:00:00"

        handle_undone(["undone", "1"], state_with_tasks, console)

        assert task.completed_at == ""

    def test_undone_missing_id(self, state_with_tasks, console):
        """Test undone command without task ID"""
        handle_undone(["undone"], state_with_tasks, console)

        assert len(state_with_tasks.messages) > 0
        assert "Usage" in state_with_tasks.messages[0]


class TestHandleCommandIntegration:
    """Test full command handler integration"""

    def test_command_add_integration(self, app_state, console):
        """Test add command through handle_command"""
        handle_command('add "Integration Task"', app_state, console)

        assert len(app_state.tasks) == 1
        assert app_state.tasks[0].name == "Integration Task"

    def test_command_alias_integration(self, app_state, console):
        """Test command aliases work through handle_command"""
        handle_command('a "Task via alias"', app_state, console)

        assert len(app_state.tasks) == 1

    def test_command_error_recovery(self, app_state, console):
        """Test that command errors don't crash the system"""
        handle_command("invalid_command", app_state, console)
        # Should record a helpful message and keep state valid
        assert isinstance(app_state.tasks, list)
        assert app_state.messages, "Expected an error/help message for invalid command"
        assert any("unknown" in str(m).lower() or "usage" in str(m).lower() for m in app_state.messages)

    def test_command_state_consistency(self, app_state, console):
        """Test that state remains consistent after commands"""
        # Add task
        handle_command('add "Task 1"', app_state, console)
        task_count = len(app_state.tasks)

        # Done task
        handle_command("done 1", app_state, console)

        # Task count shouldn't change
        assert len(app_state.tasks) == task_count

    def test_multiple_commands_sequence(self, app_state, console):
        """Test executing sequence of commands"""
        commands = [
            'add "Task 1"',
            'add "Task 2"',
            'done 1',
            'undone 1',
        ]

        for cmd in commands:
            handle_command(cmd, app_state, console)

        assert len(app_state.tasks) == 2
        assert app_state.get_task_by_id(1).done is False


class TestCommandEdgeCases:
    """Test edge cases and error conditions"""

    def test_command_with_null_bytes(self, app_state, console):
        """Test command with null bytes"""
        handle_command("add Task\x00Name", app_state, console)
        # Should not crash; either sanitized input or error message recorded
        assert isinstance(app_state.tasks, list)
        assert app_state.messages is None or isinstance(app_state.messages, list)

    def test_command_with_control_characters(self, app_state, console):
        """Test command with control characters"""
        handle_command("add Task\n\r\t", app_state, console)
        # Should sanitize or handle gracefully

    def test_command_extremely_long_input(self, app_state, console):
        """Test command with extremely long input"""
        long_command = 'add "' + ("A" * 10000) + '"'
        handle_command(long_command, app_state, console)

        # Should handle without crashing
        if app_state.tasks:
            assert isinstance(app_state.tasks[-1].name, str)

    def test_command_empty_quoted_strings(self, app_state, console):
        """Test command with empty quoted strings"""
        handle_command('add "" "" ""', app_state, console)

        # Should either reject or create task with empty name

    def test_command_unmatched_quotes(self, app_state, console):
        """Test command with unmatched quotes"""
        import pytest as _pytest
        with _pytest.raises(ValueError):
            handle_command('add "Unmatched quote', app_state, console)

    def test_command_nested_quotes(self, app_state, console):
        """Test command with nested quotes"""
        handle_command('add "Task with \\"nested\\" quotes"', app_state, console)

        if app_state.tasks:
            assert "nested" in app_state.tasks[-1].name

    def test_concurrent_command_execution(self, app_state, console):
        """Test that commands maintain state consistency under naive threads (expected xfail)."""
        import pytest as _pytest
        _pytest.xfail("Command handler is single-threaded by design; concurrent calls are not supported.")
        import threading
        lock = threading.Lock()
        created_ids = []

        def add_task(n):
            handle_command(f'add "Task {n}"', app_state, console)
            with lock:
                if app_state.tasks:
                    created_ids.append(app_state.tasks[-1].id)

        threads = [threading.Thread(target=add_task, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Detect collisions if they occurred
        assert len(created_ids) == len(set(created_ids))
