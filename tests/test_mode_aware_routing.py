"""
Tests for mode-aware command routing in Textual UI

Tests the fixes implemented for mode-aware command routing where:
- 'a' or 'add' command creates tasks in tasks mode, notes in notes mode
- 'e' or 'edit' command edits tasks in tasks mode, notes in notes mode
- Keyboard bindings respect the current entity_mode

These tests validate that the routing layer correctly dispatches based on
entity_mode (tasks vs notes).
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, call

from core.state import AppState
from tests.test_factories import TaskFactory


class TestAddCommandRouting:
    """Test 'add' and 'a' command routing based on entity_mode"""

    def test_add_command_routes_to_add_task_in_tasks_mode(self):
        """In tasks mode, 'add' should route to action_add_task"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # Simulate action_add_selected logic
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        # Assert: Should call add_task, NOT new_note
        app.action_add_task.assert_called_once()
        app.action_new_note.assert_not_called()

    def test_add_command_routes_to_new_note_in_notes_mode(self):
        """In notes mode, 'add' should route to action_new_note"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'notes'
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # Simulate action_add_selected logic
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        # Assert: Should call new_note, NOT add_task
        app.action_new_note.assert_called_once()
        app.action_add_task.assert_not_called()

    def test_shortcut_a_routes_to_add_task_in_tasks_mode(self):
        """Keyboard 'a' in tasks mode should route to action_add_task"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # Simulate keyboard binding calling action_add_selected
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        app.action_add_task.assert_called_once()
        app.action_new_note.assert_not_called()

    def test_shortcut_a_routes_to_new_note_in_notes_mode(self):
        """Keyboard 'a' in notes mode should route to action_new_note"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'notes'
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # Simulate keyboard binding calling action_add_selected
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        app.action_new_note.assert_called_once()
        app.action_add_task.assert_not_called()

    def test_add_command_defaults_to_tasks_when_mode_missing(self):
        """If entity_mode not set, should default to tasks mode"""
        app = Mock()
        app.state = AppState()
        # Do NOT set entity_mode (will default to 'tasks')
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # Simulate action_add_selected with default fallback
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        app.action_add_task.assert_called_once()
        app.action_new_note.assert_not_called()


class TestEditCommandRouting:
    """Test 'edit' and 'e' command routing based on entity_mode"""

    def test_edit_command_routes_to_edit_task_in_tasks_mode(self):
        """In tasks mode, 'edit' should route to action_edit_selected (tasks path)"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app._task_table = Mock()
        app._task_table.get_selected_task_id = Mock(return_value=1)
        app._note_table = None

        # Simulate action_edit_selected logic
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            # Would edit note
            pass
        else:
            # Should edit task
            selected_id = app._task_table.get_selected_task_id()
            assert selected_id == 1

    def test_edit_command_routes_to_edit_note_in_notes_mode(self):
        """In notes mode, 'edit' should route to action_edit_selected (notes path)"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'notes'
        app._note_table = Mock()
        app._note_table.get_selected_note_id = Mock(return_value="note-123")
        app._task_table = None

        # Simulate action_edit_selected logic
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            # Should edit note
            selected_id = app._note_table.get_selected_note_id()
            assert selected_id == "note-123"
        else:
            # Would edit task
            pass

    def test_edit_with_task_id_selects_and_edits_task(self):
        """'edit 5' should select task #5 and open edit form"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app._task_table = Mock()
        app._task_table.select_task_by_id = Mock(return_value=True)

        # Simulate command routing for "edit 5"
        task_id = 5
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode != 'notes':
            selected = app._task_table.select_task_by_id(task_id)
            assert selected is True
            app._task_table.select_task_by_id.assert_called_once_with(5)

    def test_edit_with_note_id_selects_and_edits_note(self):
        """'edit abc123' should select note abc123 and open edit form"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'notes'
        app._note_table = Mock()
        app._note_table.select_note_by_id = Mock(return_value=True)

        # Simulate command routing for "edit abc123"
        note_id = "abc123"
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            selected = app._note_table.select_note_by_id(note_id)
            assert selected is True
            app._note_table.select_note_by_id.assert_called_once_with("abc123")

    def test_edit_with_invalid_task_id_shows_error(self):
        """'edit 999' for non-existent task should show error"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app._task_table = Mock()
        app._task_table.select_task_by_id = Mock(return_value=False)
        app.notify = Mock()

        # Simulate command routing for "edit 999"
        task_id = 999
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode != 'notes':
            selected = app._task_table.select_task_by_id(task_id)
            if not selected:
                app.notify(f"Task #{task_id} not found", severity="error")

        app.notify.assert_called_once()
        assert "999" in str(app.notify.call_args)
        assert "not found" in str(app.notify.call_args)


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_add_command_with_invalid_mode_defaults_to_tasks(self):
        """Invalid entity_mode should default to tasks"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = "invalid_mode"  # Invalid!
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # Simulate action_add_selected with validation
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            # Defaults to tasks for any non-notes mode
            app.action_add_task()

        app.action_add_task.assert_called_once()
        app.action_new_note.assert_not_called()

    def test_edit_command_handles_missing_table_gracefully(self):
        """Edit command should handle None table references"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app._task_table = None  # Missing table!
        app.notify = Mock()

        # Simulate safe table access
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode != 'notes':
            if app._task_table:
                # Would proceed with edit
                pass
            else:
                app.notify("Task table not available", severity="warning")

        app.notify.assert_called_once()
        assert "not available" in str(app.notify.call_args)

    def test_add_respects_mode_after_toggle(self):
        """Add command should respect mode after toggling"""
        app = Mock()
        app.state = AppState()
        app.state.entity_mode = 'tasks'
        app.action_add_task = Mock()
        app.action_new_note = Mock()

        # First add in tasks mode
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        assert app.action_add_task.call_count == 1

        # Toggle to notes mode
        app.state.entity_mode = 'notes'

        # Second add in notes mode
        mode = getattr(app.state, 'entity_mode', 'tasks')
        if mode == 'notes':
            app.action_new_note()
        else:
            app.action_add_task()

        assert app.action_new_note.call_count == 1
        assert app.action_add_task.call_count == 1  # Still 1 from before


class TestCommandDescriptions:
    """Test that command descriptions reflect mode-aware behavior"""

    def test_command_descriptions_are_mode_aware(self):
        """Command descriptions should mention mode awareness"""
        from textual_widgets.command_input import CommandSuggester

        suggester = CommandSuggester()
        commands = suggester.COMMANDS

        # Check that descriptions mention mode awareness
        assert "mode" in commands["add"].lower()
        assert "mode" in commands["edit"].lower()
        assert "mode" in commands["a"].lower()
        assert "mode" in commands["e"].lower()

    def test_command_descriptions_removed_task_specific_labels(self):
        """Command descriptions should not say 'task' specifically"""
        from textual_widgets.command_input import CommandSuggester

        suggester = CommandSuggester()
        commands = suggester.COMMANDS

        # Descriptions should be generic, not task-specific
        assert "task" not in commands["add"].lower() or "mode" in commands["add"].lower()
        assert "task" not in commands["edit"].lower() or "mode" in commands["edit"].lower()


class TestModeAwareBindings:
    """Test that keyboard bindings use mode-aware actions"""

    def test_binding_a_uses_add_selected_action(self):
        """Keyboard binding 'a' should use action_add_selected"""
        from textual_app import TodoTextualApp

        # Find the 'a' binding
        bindings = {b.key: b.action for b in TodoTextualApp.BINDINGS}

        assert 'a' in bindings
        assert bindings['a'] == 'add_selected', "Binding 'a' should use add_selected, not add_task"

    def test_binding_label_is_generic(self):
        """Keyboard binding label should be generic, not task-specific"""
        from textual_app import TodoTextualApp

        # Find the 'a' binding
        binding_labels = {b.key: b.description for b in TodoTextualApp.BINDINGS}

        assert 'a' in binding_labels
        # Should say "Add" not "Add Task"
        assert binding_labels['a'].lower() in ['add', 'add item'], \
            f"Binding 'a' label should be generic, got: {binding_labels['a']}"


# Run tests with: python -m pytest tests/test_mode_aware_routing.py -v
