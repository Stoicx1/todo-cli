"""
Command Palette UI - Claude Code Style
Interactive command menu with dropdown completion and fuzzy search
"""

from typing import List, Dict, Iterable
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from rich.console import Console
from core.state import AppState
import sys
import platform

# Always use emojis but in display_meta (description column) to avoid spacing issues
# Emojis in the main display column cause cursor positioning problems on Windows
# By putting them in display_meta, they're visible but don't affect layout
USE_EMOJI = True


class CommandDefinition:
    """Defines a command with metadata for the palette"""

    def __init__(
        self,
        name: str,
        icon: str,
        description: str,
        category: str,
        usage: str = "",
        requires_args: bool = False
    ):
        self.name = name
        self.icon = icon
        self.description = description
        self.category = category
        self.usage = usage
        self.requires_args = requires_args

    def display_name(self) -> str:
        """Format for menu display"""
        arrow = "→" if USE_EMOJI else "->"
        return f"{self.icon} {self.name:<15} {arrow} {self.description}"

    def get_command_string(self) -> str:
        """Get the command string to execute"""
        return self.name


# Command Registry - All available commands
COMMANDS = [
    # Task Management
    CommandDefinition(
        name="add",
        icon="➕",
        description="Add a new task",
        category="Task Management",
        usage='add "Task Name" "Comment" "Description" priority "tag"',
        requires_args=True
    ),
    CommandDefinition(
        name="edit",
        icon="✏️",
        description="Edit an existing task",
        category="Task Management",
        usage='edit <id> "name" "comment" "description" priority "tag"',
        requires_args=True
    ),
    CommandDefinition(
        name="done",
        icon="✅",
        description="Mark task as complete",
        category="Task Management",
        usage="done <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="undone",
        icon="🔄",
        description="Mark task as incomplete",
        category="Task Management",
        usage="undone <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="remove",
        icon="🗑️",
        description="Delete a task",
        category="Task Management",
        usage="remove <id> (or delete, del)",
        requires_args=True
    ),

    # Shortcuts
    CommandDefinition(
        name="d",
        icon="✅",
        description="Shortcut: done <id>",
        category="Shortcuts",
        usage="d <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="u",
        icon="🔄",
        description="Shortcut: undone <id>",
        category="Shortcuts",
        usage="u <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="r",
        icon="🗑️",
        description="Shortcut: remove <id>",
        category="Shortcuts",
        usage="r <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="e",
        icon="✏️",
        description="Shortcut: edit <id>",
        category="Shortcuts",
        usage="e <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="s",
        icon="🔍",
        description="Shortcut: show <id>",
        category="Shortcuts",
        usage="s <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="n",
        icon="▶️",
        description="Shortcut: next page",
        category="Shortcuts",
        usage="n",
        requires_args=False
    ),
    CommandDefinition(
        name="p",
        icon="◀️",
        description="Shortcut: prev page",
        category="Shortcuts",
        usage="p",
        requires_args=False
    ),
    CommandDefinition(
        name="delete",
        icon="🗑️",
        description="Alias: remove <id>",
        category="Shortcuts",
        usage="delete <id>",
        requires_args=True
    ),
    CommandDefinition(
        name="del",
        icon="🗑️",
        description="Alias: remove <id>",
        category="Shortcuts",
        usage="del <id>",
        requires_args=True
    ),

    # View Controls
    CommandDefinition(
        name="view compact",
        icon="📋",
        description="Switch to compact view (20 tasks/page)",
        category="View Controls",
        usage="view compact",
        requires_args=False
    ),
    CommandDefinition(
        name="view detail",
        icon="📄",
        description="Switch to detailed view (10 tasks/page)",
        category="View Controls",
        usage="view detail",
        requires_args=False
    ),
    CommandDefinition(
        name="show",
        icon="🔍",
        description="Show full details of a task",
        category="View Controls",
        usage="show <id>",
        requires_args=True
    ),

    # Navigation
    CommandDefinition(
        name="next",
        icon="▶️",
        description="Go to next page",
        category="Navigation",
        usage="next",
        requires_args=False
    ),
    CommandDefinition(
        name="prev",
        icon="◀️",
        description="Go to previous page",
        category="Navigation",
        usage="prev",
        requires_args=False
    ),

    # Filtering & Sorting
    CommandDefinition(
        name="filter done",
        icon="✓",
        description="Show only completed tasks",
        category="Filters & Sort",
        usage="filter done",
        requires_args=False
    ),
    CommandDefinition(
        name="filter undone",
        icon="○",
        description="Show only incomplete tasks",
        category="Filters & Sort",
        usage="filter undone",
        requires_args=False
    ),
    CommandDefinition(
        name="filter none",
        icon="🔓",
        description="Clear all filters",
        category="Filters & Sort",
        usage="filter none",
        requires_args=False
    ),
    CommandDefinition(
        name="filter tag:",
        icon="🏷️",
        description="Filter by tag",
        category="Filters & Sort",
        usage="filter tag:<tagname>",
        requires_args=True
    ),
    CommandDefinition(
        name="sort priority",
        icon="⚡",
        description="Sort by priority (current order)",
        category="Filters & Sort",
        usage="sort priority",
        requires_args=False
    ),
    CommandDefinition(
        name="sort id",
        icon="🔢",
        description="Sort by task ID (current order)",
        category="Filters & Sort",
        usage="sort id",
        requires_args=False
    ),
    CommandDefinition(
        name="sort name",
        icon="🔤",
        description="Sort alphabetically by name (current order)",
        category="Filters & Sort",
        usage="sort name",
        requires_args=False
    ),
    # New explicit order variants
    CommandDefinition(
        name="sort priority asc",
        icon="⬆️",
        description="Sort by priority (ascending)",
        category="Filters & Sort",
        usage="sort priority asc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort priority desc",
        icon="⬇️",
        description="Sort by priority (descending)",
        category="Filters & Sort",
        usage="sort priority desc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort id asc",
        icon="⬆️",
        description="Sort by ID (ascending)",
        category="Filters & Sort",
        usage="sort id asc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort id desc",
        icon="⬇️",
        description="Sort by ID (descending)",
        category="Filters & Sort",
        usage="sort id desc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort name asc",
        icon="⬆️",
        description="Sort by name (A→Z)",
        category="Filters & Sort",
        usage="sort name asc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort name desc",
        icon="⬇️",
        description="Sort by name (Z→A)",
        category="Filters & Sort",
        usage="sort name desc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort order asc",
        icon="⬆️",
        description="Set sort order ascending",
        category="Filters & Sort",
        usage="sort order asc",
        requires_args=False
    ),
    CommandDefinition(
        name="sort order desc",
        icon="⬇️",
        description="Set sort order descending",
        category="Filters & Sort",
        usage="sort order desc",
        requires_args=False
    ),

    # Information
    CommandDefinition(
        name="tags",
        icon="🏷️",
        description="List all unique tags in use",
        category="Information",
        usage="tags",
        requires_args=False
    ),
    CommandDefinition(
        name="insights",
        icon="📊",
        description="Show comprehensive task analysis (local AI)",
        category="Information",
        usage="insights",
        requires_args=False
    ),
    CommandDefinition(
        name="suggest",
        icon="💡",
        description="Get smart recommendations (local AI)",
        category="Information",
        usage="suggest",
        requires_args=False
    ),
    CommandDefinition(
        name="help",
        icon="❓",
        description="Show help message",
        category="Information",
        usage="help",
        requires_args=False
    ),

    # AI Assistant
    CommandDefinition(
        name="?",
        icon="🤖",
        description="Ask GPT for task advice (requires API key)",
        category="AI Assistant",
        usage="? <your question>",
        requires_args=True
    ),
    CommandDefinition(
        name="clearai",
        icon="🗑️",
        description="Clear AI answer panel",
        category="AI Assistant",
        usage="clearai",
        requires_args=False
    ),

    # System
    CommandDefinition(
        name="save",
        icon="💾",
        description="Save tasks to file",
        category="System",
        usage="save",
        requires_args=False
    ),
    CommandDefinition(
        name="cls",
        icon="🧹",
        description="Clear screen and refresh dashboard",
        category="System",
        usage="cls (or clear, c)",
        requires_args=False
    ),
    CommandDefinition(
        name="exit",
        icon="🚪",
        description="Save and exit the application",
        category="System",
        usage="exit",
        requires_args=False
    ),
]


def group_commands_by_category() -> Dict[str, List[CommandDefinition]]:
    """Group commands by their category"""
    grouped = {}
    for cmd in COMMANDS:
        if cmd.category not in grouped:
            grouped[cmd.category] = []
        grouped[cmd.category].append(cmd)
    return grouped


class CommandCompleter(Completer):
    """
    Custom completer that shows all commands with categories, icons, and descriptions.
    Provides fuzzy filtering as user types.
    """

    def __init__(self, state: AppState):
        self.state = state
        self.commands = COMMANDS

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """
        Generate completions based on what user has typed.
        Shows all commands when user types '/', filters as they continue typing.
        """
        # CRITICAL FIX: Use text_before_cursor, not text
        word = document.text_before_cursor

        # Check if user typed '/' - show all commands
        if word == '/':
            # When JUST '/' is typed, show ALL commands
            for cmd in self.commands:
                # Use safe ">" prefix in main display
                display = f"> {cmd.name}"

                # Put emoji in description (display_meta) for visual indication
                display_meta = f"{cmd.icon} {cmd.description}"

                yield Completion(
                    text=cmd.name,
                    start_position=-1,  # Replace the '/'
                    display=display,
                    display_meta=display_meta
                )

        elif word.startswith('/') and len(word) > 1:
            # When user types '/something', filter commands
            search_text = word[1:].lower()  # Remove '/' and lowercase

            for cmd in self.commands:
                if search_text in cmd.name.lower():
                    # Use safe ">" prefix in main display
                    display = f"> {cmd.name}"

                    # Put emoji in description (display_meta) for visual indication
                    display_meta = f"{cmd.icon} {cmd.description}"

                    yield Completion(
                        text=cmd.name,
                        start_position=-len(word),  # Replace whole input
                        display=display,
                        display_meta=display_meta
                    )

        # Context-aware completions for 'sort' command
        elif word.startswith('sort'):
            parts = word.strip().split()
            # Base options when typing 'sort' or 'sort '
            if len(parts) == 1 or (len(parts) == 2 and word.endswith(' ')):
                options = [
                    ('sort priority', 'Sort by priority'),
                    ('sort id', 'Sort by task ID'),
                    ('sort name', 'Sort by name'),
                    ('sort order', 'Set sort order'),
                    ('sort toggle', 'Toggle sort order'),
                ]
                for text, meta in options:
                    yield Completion(
                        text=text,
                        start_position=-len(word),
                        display=f"> {text}",
                        display_meta=f"🔧 {meta}"
                    )
                return

            # After field → suggest order
            if len(parts) >= 2:
                field = parts[1]
                if field in ('priority', 'id', 'name'):
                    order_options = [('asc', 'Ascending'), ('desc', 'Descending')]
                    if field == 'priority':
                        order_options.extend([('high', 'Alias for asc'), ('low', 'Alias for desc')])
                    for opt, meta in order_options:
                        suggestion = f"sort {field} {opt}"
                        yield Completion(
                            text=suggestion,
                            start_position=-len(word),
                            display=f"> {suggestion}",
                            display_meta=f"🔧 {meta}"
                        )
                    return

                if field == 'order':
                    for opt, meta in [('asc', 'Ascending'), ('desc', 'Descending')]:
                        suggestion = f"sort order {opt}"
                        yield Completion(
                            text=suggestion,
                            start_position=-len(word),
                            display=f"> {suggestion}",
                            display_meta=f"🔧 {meta}"
                        )
                    return

        # Also provide regular command completion without '/'
        elif word:
            search_text = word.lower()
            for cmd in self.commands:
                if search_text in cmd.name.lower():
                    # Use safe ">" prefix in main display
                    display_text = f"> {cmd.name}"

                    # Put emoji in description (display_meta) for visual indication
                    display_meta = f"{cmd.icon} {cmd.description}"

                    yield Completion(
                        text=cmd.name,
                        start_position=-len(word),
                        display=display_text,
                        display_meta=display_meta
                    )


def create_command_completer(state: AppState) -> CommandCompleter:
    """
    Create a completer instance with current state.
    This replaces the old questionary-based menu system.
    """
    return CommandCompleter(state)


# Keep these helper functions for backward compatibility
def get_command_by_name(name: str) -> CommandDefinition:
    """Get command definition by name"""
    for cmd in COMMANDS:
        if cmd.name == name:
            return cmd
    return None


def get_available_tags(state: AppState) -> List[str]:
    """Get list of all tags currently in use (leverages tag index)."""
    # Use O(1) tag index via state API to include all tags (not just legacy first tag)
    return sorted(list(state.get_all_tags_with_stats().keys()))
