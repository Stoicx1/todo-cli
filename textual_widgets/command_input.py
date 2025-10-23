"""
CommandInput Widget - Command line input with autocomplete
"""

from textual.widgets import Input
from textual.message import Message
from textual.suggester import Suggester


class CommandSuggester(Suggester):
    """
    Autocomplete suggester for commands

    Provides suggestions based on command prefixes and common patterns
    """

    # Command completions with descriptions
    COMMANDS = {
        # Task Management
        "add": "Add a new task",
        "edit": "Edit an existing task",
        "done": "Mark task(s) as complete",
        "undone": "Mark task(s) as incomplete",
        "remove": "Delete task(s)",
        "show": "Show task details or filter",

        # Shortcuts
        "a": "Shortcut for add",
        "e": "Shortcut for edit",
        "x": "Shortcut for done",
        "u": "Shortcut for undone",
        "d": "Shortcut for delete",
        "s": "Shortcut for show",

        # Filtering & Sorting
        "filter": "Filter tasks by criteria",
        "f": "Shortcut for filter",
        "sort": "Sort tasks by field",
        "tags": "List all tags",
        "t": "Shortcut for tags",

        # Navigation
        "next": "Next page",
        "prev": "Previous page",
        "n": "Shortcut for next",
        "p": "Shortcut for prev",

        # View
        "view": "Change view mode",
        "v": "Shortcut for view",

        # AI & Help
        "insights": "Local AI insights",
        "suggest": "Smart suggestions",
        "?": "Ask GPT (requires API key)",
        "help": "Show help",
        "h": "Shortcut for help",

        # System
        "clear": "Clear screen",
        "cls": "Clear screen",
        "c": "Clear screen",
        "save": "Save tasks manually",
        "exit": "Save and quit",
        "quit": "Save and quit",
        "q": "Shortcut for quit",
    }

    # Common filter patterns
    FILTER_PATTERNS = [
        "status=done",
        "status=undone",
        "priority=1",
        "priority=2",
        "priority=3",
        "priority>=2",
        "tag=",
        "tag!=",
    ]

    # Common sort patterns
    SORT_PATTERNS = [
        "priority",
        "priority asc",
        "priority desc",
        "id",
        "id asc",
        "id desc",
        "name",
        "name asc",
        "name desc",
    ]

    async def get_suggestion(self, value: str) -> str | None:
        """
        Get autocomplete suggestion for current input

        Args:
            value: Current input value

        Returns:
            Suggested completion or None
        """
        if not value:
            return None

        value_lower = value.lower()

        # Check if it's a filter command
        if value_lower.startswith("filter ") or value_lower.startswith("f "):
            filter_part = value.split(" ", 1)[1] if " " in value else ""
            for pattern in self.FILTER_PATTERNS:
                if pattern.startswith(filter_part.lower()):
                    prefix = "filter " if value_lower.startswith("filter") else "f "
                    return prefix + pattern

        # Check if it's a sort command
        if value_lower.startswith("sort "):
            sort_part = value.split(" ", 1)[1] if " " in value else ""
            for pattern in self.SORT_PATTERNS:
                if pattern.startswith(sort_part.lower()):
                    return "sort " + pattern

        # Check if it's a view command
        if value_lower.startswith("view ") or value_lower.startswith("v "):
            for mode in ["compact", "detail"]:
                if mode.startswith(value.split(" ", 1)[1].lower() if " " in value else ""):
                    prefix = "view " if value_lower.startswith("view") else "v "
                    return prefix + mode

        # Check for command completions
        for cmd, desc in self.COMMANDS.items():
            if cmd.startswith(value_lower):
                return cmd

        return None


class CommandInput(Input):
    """
    Command input widget with autocomplete and history

    Features:
    - Autocomplete for commands
    - Command history (up/down arrows)
    - Syntax highlighting
    - Submit on Enter
    """

    class CommandSubmitted(Message):
        """Message sent when command is submitted"""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    def __init__(self, **kwargs) -> None:
        """Initialize command input with suggester"""
        super().__init__(
            placeholder="COMMANDS: type 'add', 'edit', 'filter'... or 'help' for all | Ctrl+K to toggle",
            suggester=CommandSuggester(),
            **kwargs
        )

        # Command history
        self.history: list[str] = []
        self.history_index: int = -1

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle command submission (Enter key)

        Args:
            event: Input submitted event
        """
        command = event.value.strip()

        if command:
            # Add to history (avoid duplicates)
            if not self.history or self.history[-1] != command:
                self.history.append(command)

            # Reset history index
            self.history_index = -1

            # Post message to parent
            self.post_message(self.CommandSubmitted(command))

            # Clear input
            self.value = ""

            # Prevent event from bubbling
            event.stop()
            event.prevent_default()

    async def _on_key(self, event) -> None:
        """
        Handle special keys (up/down for history)

        Args:
            event: Key event
        """
        # Up arrow - previous command in history
        if event.key == "up" and self.history:
            if self.history_index == -1:
                self.history_index = len(self.history) - 1
            elif self.history_index > 0:
                self.history_index -= 1

            if 0 <= self.history_index < len(self.history):
                self.value = self.history[self.history_index]
                event.prevent_default()

        # Down arrow - next command in history
        elif event.key == "down" and self.history:
            if self.history_index >= 0:
                self.history_index += 1

                if self.history_index >= len(self.history):
                    self.history_index = -1
                    self.value = ""
                else:
                    self.value = self.history[self.history_index]

                event.prevent_default()
