"""
Tests for AI tool context validation to prevent editing wrong tasks.

These tests ensure that the critical bug where AI edits wrong tasks
is fixed and prevented from regressing.
"""

import pytest
from datetime import datetime
from core.state import AppState, LeftPanelMode
from models.task import Task
from core import ai_tools


@pytest.fixture
def state_with_tasks():
    """Create AppState with sample tasks for testing"""
    state = AppState()
    state.tasks = [
        Task(
            id=100,
            name="Task being edited",
            comment="This is the focused task",
            description="User is editing this one",
            priority=1,
            tag="backend",
            tags=["backend"],
            done=False,
            created_at=datetime.now().isoformat(),
            updated_at="",
            completed_at=""
        ),
        Task(
            id=420,
            name="Different task",
            comment="This should NOT be edited",
            description="User is NOT editing this",
            priority=2,
            tag="frontend",
            tags=["frontend"],
            done=False,
            created_at=datetime.now().isoformat(),
            updated_at="",
            completed_at=""
        ),
    ]
    return state


class TestEditTaskValidation:
    """Test edit_task tool validation to prevent wrong task edits"""

    def test_edit_task_blocks_when_creating_new(self, state_with_tasks):
        """CRITICAL: edit_task should reject when user is creating NEW task"""
        # Setup: User is creating a NEW task
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = True
        state_with_tasks.selected_task_id = None

        ai_tools.set_app_state(state_with_tasks)

        # Attempt: AI tries to edit existing task #420
        result = ai_tools.edit_task.func(task_id=420, field="name", value="Hacked name")

        # Assert: Should be blocked
        assert "❌ Error" in result
        assert "CREATING a NEW task" in result
        assert "Use the create_task tool" in result
        assert "edit_task" in result.lower()

        # Verify: Task #420 was NOT modified
        task_420 = next(t for t in state_with_tasks.tasks if t.id == 420)
        assert task_420.name == "Different task"  # Unchanged

    def test_edit_task_blocks_when_editing_different_task(self, state_with_tasks):
        """CRITICAL: edit_task should reject when trying to edit non-focused task"""
        # Setup: User is editing task #100
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = 100

        ai_tools.set_app_state(state_with_tasks)

        # Attempt: AI tries to edit different task #420
        result = ai_tools.edit_task.func(task_id=420, field="name", value="Hacked name")

        # Assert: Should be blocked
        assert "❌ Error" in result
        assert "Task #100" in result  # Currently focused task
        assert "Task #420" in result  # Attempted task
        assert "NOT" in result or "not" in result
        assert "currently editing" in result.lower() or "focus" in result.lower()

        # Verify: Task #420 was NOT modified
        task_420 = next(t for t in state_with_tasks.tasks if t.id == 420)
        assert task_420.name == "Different task"  # Unchanged

        # Verify: Task #100 was NOT modified either
        task_100 = next(t for t in state_with_tasks.tasks if t.id == 100)
        assert task_100.name == "Task being edited"  # Unchanged

    def test_edit_task_allows_when_focused(self, state_with_tasks):
        """edit_task should ALLOW editing the currently focused task"""
        # Setup: User is editing task #100
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = 100

        ai_tools.set_app_state(state_with_tasks)

        # Attempt: AI edits the focused task #100
        result = ai_tools.edit_task.func(task_id=100, field="name", value="Updated name")

        # Assert: Should succeed
        assert "✅" in result or "Updated" in result
        assert "100" in result

        # Verify: Task #100 WAS modified
        task_100 = next(t for t in state_with_tasks.tasks if t.id == 100)
        assert task_100.name == "Updated name"  # Changed

        # Verify: Task #420 was NOT modified
        task_420 = next(t for t in state_with_tasks.tasks if t.id == 420)
        assert task_420.name == "Different task"  # Unchanged

    def test_edit_task_allows_in_list_view(self, state_with_tasks):
        """edit_task should allow editing any task when in list view (no focus)"""
        # Setup: User is in list view (not editing)
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = None

        ai_tools.set_app_state(state_with_tasks)

        # Attempt: AI edits task #420 from list view
        result = ai_tools.edit_task.func(task_id=420, field="name", value="Updated from list")

        # Assert: Should succeed (no focus restrictions in list view)
        assert "✅" in result or "Updated" in result

        # Verify: Task #420 WAS modified
        task_420 = next(t for t in state_with_tasks.tasks if t.id == 420)
        assert task_420.name == "Updated from list"  # Changed


class TestContextBuildingForNewTask:
    """Test context building correctly identifies NEW task creation"""

    def test_context_shows_creating_new_task(self, state_with_tasks):
        """Context should clearly indicate NEW task creation mode"""
        from unittest.mock import MagicMock
        from core.ai_agent import TaskAssistantAgent

        # Setup: Creating new task
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = True
        state_with_tasks.selected_task_id = None

        # Mock agent
        agent = MagicMock()
        agent.state = state_with_tasks

        # Build context
        context = TaskAssistantAgent._build_context_string(agent)

        # Assert: Context indicates NEW task creation
        assert "**CURRENT FOCUS**" in context
        assert "CREATING a NEW task" in context
        assert "Creating NEW task" in context
        assert "not saved yet" in context
        assert "DO NOT use edit_task" in context
        assert "create_task tool" in context

    def test_context_shows_editing_existing_task(self, state_with_tasks):
        """Context should show task details when editing existing task"""
        from unittest.mock import MagicMock
        from core.ai_agent import TaskAssistantAgent

        # Setup: Editing existing task #100
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = 100

        # Mock agent
        agent = MagicMock()
        agent.state = state_with_tasks

        # Build context
        context = TaskAssistantAgent._build_context_string(agent)

        # Assert: Context shows task being edited
        assert "**CURRENT FOCUS**" in context
        assert "editing this task" in context.lower()
        assert "Task #100" in context
        assert "Task being edited" in context
        assert "backend" in context

    def test_context_has_no_focus_in_list_view(self, state_with_tasks):
        """Context should have no CURRENT FOCUS in list view"""
        from unittest.mock import MagicMock
        from core.ai_agent import TaskAssistantAgent

        # Setup: List view
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = None

        # Mock agent
        agent = MagicMock()
        agent.state = state_with_tasks

        # Build context
        context = TaskAssistantAgent._build_context_string(agent)

        # Assert: No current focus
        assert "CURRENT FOCUS" not in context
        assert "Workspace Summary" in context


class TestGetCurrentEditContextTool:
    """Test get_current_edit_context tool returns correct info for NEW tasks"""

    def test_get_current_edit_context_shows_new_task(self, state_with_tasks):
        """get_current_edit_context should indicate NEW task creation"""
        # Setup: Creating new task
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = True
        state_with_tasks.selected_task_id = None

        ai_tools.set_app_state(state_with_tasks)

        # Call tool
        result = ai_tools.get_current_edit_context.func()

        # Assert: Indicates NEW task creation
        assert "**CREATING NEW Task**" in result
        assert "Creation mode" in result
        assert "not saved yet" in result
        assert "DO NOT use edit_task" in result
        assert "create_task" in result

    def test_get_current_edit_context_shows_existing_task(self, state_with_tasks):
        """get_current_edit_context should show details of existing task being edited"""
        # Setup: Editing task #100
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = 100

        ai_tools.set_app_state(state_with_tasks)

        # Call tool
        result = ai_tools.get_current_edit_context.func()

        # Assert: Shows task #100 details
        assert "**EDITING Task #100**" in result
        assert "Task being edited" in result
        assert "backend" in result

    def test_get_current_edit_context_in_list_view(self, state_with_tasks):
        """get_current_edit_context should return helpful message in list view"""
        # Setup: List view
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS
        state_with_tasks.edit_mode_is_new = False
        state_with_tasks.selected_task_id = None

        ai_tools.set_app_state(state_with_tasks)

        # Call tool
        result = ai_tools.get_current_edit_context.func()

        # Assert: Indicates no current focus
        assert "ℹ️" in result or "No task" in result
        assert "list view" in result.lower() or "not currently" in result.lower()


class TestSystemPromptBoundaries:
    """Test that system prompt includes tool usage boundaries"""

    def test_system_prompt_has_boundaries_section(self):
        """System prompt should have TOOL USAGE BOUNDARIES section"""
        from unittest.mock import MagicMock, patch

        state = AppState()
        memory = MagicMock()

        # Mock OpenAI to avoid API key requirement
        with patch('core.ai_agent.ChatOpenAI'), \
             patch('core.ai_agent.create_agent'), \
             patch('core.ai_agent.os.getenv', return_value='dummy_key'):

            from core.ai_agent import TaskAssistantAgent
            agent = TaskAssistantAgent(state, memory)
            prompt = agent.system_prompt

            # Assert: Boundaries section exists
            assert "TOOL USAGE BOUNDARIES" in prompt
            assert "CRITICAL" in prompt

    def test_system_prompt_has_creating_new_rules(self):
        """System prompt should have rules for CREATING NEW task"""
        from unittest.mock import MagicMock, patch

        state = AppState()
        memory = MagicMock()

        with patch('core.ai_agent.ChatOpenAI'), \
             patch('core.ai_agent.create_agent'), \
             patch('core.ai_agent.os.getenv', return_value='dummy_key'):

            from core.ai_agent import TaskAssistantAgent
            agent = TaskAssistantAgent(state, memory)
            prompt = agent.system_prompt

            # Assert: NEW task creation rules
            assert "CREATING NEW task" in prompt
            assert "DO NOT use edit_task" in prompt
            assert "create_task" in prompt

    def test_system_prompt_has_editing_existing_rules(self):
        """System prompt should have rules for EDITING existing task"""
        from unittest.mock import MagicMock, patch

        state = AppState()
        memory = MagicMock()

        with patch('core.ai_agent.ChatOpenAI'), \
             patch('core.ai_agent.create_agent'), \
             patch('core.ai_agent.os.getenv', return_value='dummy_key'):

            from core.ai_agent import TaskAssistantAgent
            agent = TaskAssistantAgent(state, memory)
            prompt = agent.system_prompt

            # Assert: Editing rules
            assert "EDITING Task #X" in prompt
            assert "ONLY use edit_task with task_id=X" in prompt


@pytest.mark.integration
class TestFullBugScenario:
    """Integration test reproducing the original bug scenario"""

    def test_original_bug_scenario_is_fixed(self, state_with_tasks):
        """
        Reproduce original bug: User creating NEW task, AI tries to edit Task #420.
        This should now be BLOCKED.
        """
        from unittest.mock import MagicMock
        from core.ai_agent import TaskAssistantAgent

        # Setup: User clicks "Create New Task"
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.edit_mode_is_new = True
        state_with_tasks.selected_task_id = None

        ai_tools.set_app_state(state_with_tasks)

        # Build context (what AI sees)
        agent = MagicMock()
        agent.state = state_with_tasks
        context = TaskAssistantAgent._build_context_string(agent)

        # Assert: AI should see "CREATING NEW task"
        assert "CREATING a NEW task" in context
        assert "DO NOT use edit_task" in context

        # Simulate: AI tries to edit Task #420 (the bug)
        result = ai_tools.edit_task.func(task_id=420, field="name", value="Something fancy")

        # Assert: Should be BLOCKED
        assert "❌ Error" in result
        assert "CREATING a NEW task" in result

        # Verify: Task #420 remains unchanged
        task_420 = next(t for t in state_with_tasks.tasks if t.id == 420)
        assert task_420.name == "Different task"
        assert task_420.description == "User is NOT editing this"

        print("\n✅ Original bug is FIXED! AI cannot edit wrong tasks anymore.")
