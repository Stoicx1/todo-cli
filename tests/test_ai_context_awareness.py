"""
Tests for AI context awareness functionality.

Tests the context-aware AI system that detects when a user is editing
a specific task or note and provides focused context in responses.
"""

import pytest
from datetime import datetime
from core.state import AppState, LeftPanelMode
from models.task import Task
from models.note import Note
from core import ai_tools
from core.ai_agent import TaskAssistantAgent


@pytest.fixture
def state_with_tasks():
    """Create AppState with sample tasks"""
    state = AppState()
    state.tasks = [
        Task(
            id=1,
            name="Fix login bug",
            comment="Urgent - production issue",
            description="Users cannot log in with OAuth2",
            priority=1,
            tag="backend",
            tags=["backend", "bug"],
            done=False,
            created_at=datetime.now().isoformat(),
            updated_at="",
            completed_at=""
        ),
        Task(
            id=2,
            name="Update documentation",
            comment="",
            description="",
            priority=2,
            tag="docs",
            tags=["docs"],
            done=False,
            created_at=datetime.now().isoformat(),
            updated_at="",
            completed_at=""
        ),
        Task(
            id=3,
            name="Code review PR#42",
            comment="",
            description="",
            priority=1,
            tag="review",
            tags=["review"],
            done=True,
            created_at=datetime.now().isoformat(),
            updated_at="",
            completed_at=""
        ),
    ]
    return state


@pytest.fixture
def state_with_notes():
    """Create AppState with sample notes"""
    state = AppState()
    state.notes = [
        Note(
            id="abc12345678",
            title="Meeting notes",
            body_md="# Meeting\n\nDiscussed new features",
            tags=["meeting"],
            task_ids=[1, 2],
            created_at=datetime.now().isoformat()
        ),
        Note(
            id="def98765432",
            title="Design decisions",
            body_md="Decided to use microservices",
            tags=["architecture", "design"],
            task_ids=[],
            created_at=datetime.now().isoformat()
        ),
    ]
    return state


class TestContextStringBuilding:
    """Test _build_context_string() method for edit mode awareness"""

    def test_list_tasks_mode_no_focus(self, state_with_tasks):
        """When in LIST_TASKS mode, no CURRENT FOCUS section"""
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS

        # Mock agent (we only need _build_context_string)
        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_tasks

        # Import and test the method directly
        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "CURRENT FOCUS" not in context
        assert "CURRENT VIEW" not in context
        assert "Workspace Summary" in context
        assert "Total tasks: 3" in context

    def test_edit_task_mode_shows_focus(self, state_with_tasks):
        """When editing a task, CURRENT FOCUS section appears"""
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.selected_task_id = 1
        state_with_tasks.edit_mode_is_new = False

        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_tasks

        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "**CURRENT FOCUS**" in context
        assert "Fix login bug" in context
        assert "Priority: HIGH" in context
        assert "Tags: backend, bug" in context
        assert "Comment: Urgent - production issue" in context
        assert "Description: Users cannot log in with OAuth2" in context
        assert "Workspace Summary" in context

    def test_edit_task_mode_new_task(self, state_with_tasks):
        """When creating a new task, shows 'Creating NEW task'"""
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.selected_task_id = 1
        state_with_tasks.edit_mode_is_new = True

        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_tasks

        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "**CURRENT FOCUS**" in context
        assert "Mode: Creating NEW task" in context

    def test_detail_task_mode_shows_view(self, state_with_tasks):
        """When viewing task detail, shows CURRENT VIEW"""
        state_with_tasks.left_panel_mode = LeftPanelMode.DETAIL_TASK
        state_with_tasks.selected_task_id = 2

        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_tasks

        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "**CURRENT VIEW**" in context
        assert "Update documentation" in context
        assert "Priority: MEDIUM" in context

    def test_edit_note_mode_shows_focus(self, state_with_notes):
        """When editing a note, CURRENT FOCUS section appears"""
        state_with_notes.left_panel_mode = LeftPanelMode.EDIT_NOTE
        state_with_notes.selected_note_id = "abc12345678"
        state_with_notes.edit_mode_is_new = False

        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_notes

        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "**CURRENT FOCUS**" in context
        assert "Meeting notes" in context
        assert "Tags: meeting" in context
        assert "Linked to tasks: #1, #2" in context
        assert "Body excerpt: # Meeting" in context

    def test_available_tags_in_workspace_summary(self, state_with_tasks):
        """Workspace summary includes available tags for suggestions"""
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS

        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_tasks

        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "Available tags:" in context
        # Tags should be sorted
        assert "backend" in context
        assert "bug" in context
        assert "docs" in context
        assert "review" in context


class TestGetCurrentEditContextTool:
    """Test get_current_edit_context() tool"""

    def test_edit_task_returns_full_details(self, state_with_tasks):
        """Tool returns full task details when editing"""
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.selected_task_id = 1

        ai_tools.set_app_state(state_with_tasks)
        # Call the function directly (it's wrapped by @tool decorator)
        result = ai_tools.get_current_edit_context.func()

        assert "**EDITING Task #1**" in result
        assert "Fix login bug" in result
        assert "**Priority**: 🔴 HIGH" in result
        assert "**Tags**: backend, bug" in result
        assert "**Comment**: Urgent - production issue" in result
        assert "**Description**:" in result
        assert "Users cannot log in with OAuth2" in result

    def test_create_task_shows_creating(self, state_with_tasks):
        """Tool shows 'CREATING NEW' when creating task"""
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.selected_task_id = None  # No task selected when creating new
        state_with_tasks.edit_mode_is_new = True

        ai_tools.set_app_state(state_with_tasks)
        result = ai_tools.get_current_edit_context.func()

        assert "**CREATING NEW Task**" in result
        assert "Creation mode" in result
        assert "DO NOT use edit_task" in result

    def test_detail_task_returns_viewing(self, state_with_tasks):
        """Tool returns 'VIEWING' when in detail mode"""
        state_with_tasks.left_panel_mode = LeftPanelMode.DETAIL_TASK
        state_with_tasks.selected_task_id = 2

        ai_tools.set_app_state(state_with_tasks)
        result = ai_tools.get_current_edit_context.func()

        assert "**VIEWING Task #2**" in result
        assert "Update documentation" in result

    def test_edit_note_returns_full_details(self, state_with_notes):
        """Tool returns full note details when editing"""
        from unittest.mock import patch

        state_with_notes.left_panel_mode = LeftPanelMode.EDIT_NOTE
        state_with_notes.selected_note_id = "abc12345678"
        ai_tools.set_app_state(state_with_notes)

        # Mock the notes repository to return our in-memory note
        note = state_with_notes.notes[0]
        with patch('core.ai_tools._notes_repo') as mock_repo:
            mock_repo.return_value.get.return_value = note
            result = ai_tools.get_current_edit_context.func()

        assert "**EDITING Note abc12345**" in result
        assert "Meeting notes" in result
        assert "**Tags**: meeting" in result
        assert "**Linked to tasks**: #1, #2" in result
        assert "**Body**:" in result
        assert "# Meeting" in result

    def test_list_mode_returns_no_focus(self, state_with_tasks):
        """Tool returns helpful message when in list mode"""
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS

        ai_tools.set_app_state(state_with_tasks)
        result = ai_tools.get_current_edit_context.func()

        assert "ℹ️" in result
        assert "No task or note is currently being edited" in result
        assert "list view mode" in result
        assert "Creating new tasks" in result

    def test_task_not_found(self, state_with_tasks):
        """Tool returns error when task not found"""
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.selected_task_id = 999  # Non-existent

        ai_tools.set_app_state(state_with_tasks)
        result = ai_tools.get_current_edit_context.func()

        assert "❌ Error" in result
        assert "Task #999 not found" in result


class TestSystemPromptContextAwareness:
    """Test that system prompt includes context awareness instructions"""

    def test_system_prompt_has_context_section(self):
        """System prompt includes CONTEXT AWARENESS section"""
        from unittest.mock import MagicMock, patch

        # Create a minimal mock setup
        state = AppState()
        memory = MagicMock()

        # Mock the OpenAI initialization to avoid API key requirement
        with patch('core.ai_agent.ChatOpenAI'), \
             patch('core.ai_agent.create_agent'), \
             patch('core.ai_agent.os.getenv', return_value='dummy_key'):

            agent = TaskAssistantAgent(state, memory)
            prompt = agent.system_prompt

            assert "CONTEXT AWARENESS" in prompt
            assert "CURRENT FOCUS" in prompt
            assert "Prioritize the current item" in prompt
            assert "When user says \"this task\"" in prompt or "Interpret references" in prompt

    def test_system_prompt_mentions_new_tool(self):
        """System prompt mentions get_current_edit_context tool"""
        from unittest.mock import MagicMock, patch

        state = AppState()
        memory = MagicMock()

        with patch('core.ai_agent.ChatOpenAI'), \
             patch('core.ai_agent.create_agent'), \
             patch('core.ai_agent.os.getenv', return_value='dummy_key'):

            agent = TaskAssistantAgent(state, memory)
            prompt = agent.system_prompt

            assert "get_current_edit_context" in prompt


class TestToolRegistry:
    """Test that the new tool is registered"""

    def test_tool_count(self):
        """Tool registry now has 22 tools"""
        tools = ai_tools.get_all_tools()
        assert len(tools) == 22

    def test_new_tool_in_registry(self):
        """get_current_edit_context is in the tool list"""
        tools = ai_tools.get_all_tools()
        tool_names = [t.name for t in tools]
        assert "get_current_edit_context" in tool_names


@pytest.mark.integration
class TestEndToEndContextAwareness:
    """Integration tests for context-aware behavior"""

    def test_context_changes_with_panel_mode(self, state_with_tasks):
        """Context string changes as panel mode changes"""
        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state_with_tasks

        from core.ai_agent import TaskAssistantAgent

        # Start in list mode - no focus
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS
        context1 = TaskAssistantAgent._build_context_string(agent)
        assert "CURRENT FOCUS" not in context1

        # Switch to edit mode - focus appears
        state_with_tasks.left_panel_mode = LeftPanelMode.EDIT_TASK
        state_with_tasks.selected_task_id = 1
        context2 = TaskAssistantAgent._build_context_string(agent)
        assert "**CURRENT FOCUS**" in context2
        assert "Fix login bug" in context2

        # Switch to detail mode - view appears
        state_with_tasks.left_panel_mode = LeftPanelMode.DETAIL_TASK
        context3 = TaskAssistantAgent._build_context_string(agent)
        assert "**CURRENT VIEW**" in context3

        # Back to list mode - no focus
        state_with_tasks.left_panel_mode = LeftPanelMode.LIST_TASKS
        context4 = TaskAssistantAgent._build_context_string(agent)
        assert "CURRENT FOCUS" not in context4

    def test_workspace_tags_collected_from_tasks_and_notes(self):
        """Available tags collected from both tasks and notes"""
        state = AppState()
        state.tasks = [
            Task(
                id=1,
                name="Task 1",
                comment="",
                description="",
                priority=1,
                tag="backend",
                tags=["backend", "api"],
                done=False,
                created_at=datetime.now().isoformat(),
                updated_at="",
                completed_at=""
            )
        ]
        state.notes = [
            Note(id="abc123", title="Note 1", body_md="", tags=["meeting", "design"], task_ids=[], created_at=datetime.now().isoformat())
        ]
        state.left_panel_mode = LeftPanelMode.LIST_TASKS

        from unittest.mock import MagicMock
        agent = MagicMock()
        agent.state = state

        from core.ai_agent import TaskAssistantAgent
        context = TaskAssistantAgent._build_context_string(agent)

        assert "Available tags:" in context
        # Should include tags from both tasks and notes
        assert "api" in context or "backend" in context
        assert "design" in context or "meeting" in context
