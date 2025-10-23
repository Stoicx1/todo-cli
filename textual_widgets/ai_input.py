"""
AI Input Widget
Input field for AI prompts with history navigation
"""

from textual.app import ComposeResult
from textual.widgets import Input
from textual.message import Message
from typing import List


class AIInput(Input):
    """
    Input field for AI prompts

    Features:
    - History navigation (↑/↓)
    - Submit with Enter
    - Cancel with Esc
    - Placeholder text
    """

    class PromptSubmitted(Message):
        """Message sent when user submits an AI prompt"""

        def __init__(self, prompt: str):
            self.prompt = prompt
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Ask AI about your tasks... (Press Enter to send, Esc to cancel)",
            **kwargs
        )
        self.history: List[str] = []  # Command history
        self.history_index: int = -1  # Current position in history
        self.current_input: str = ""  # Temp storage for current input

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key - submit prompt"""
        prompt = event.value.strip()

        if not prompt:
            return

        # Validate input length (prevent API errors)
        if len(prompt) > 5000:
            # Notify user of validation error
            try:
                self.app.notify(
                    "Prompt too long (max 5000 characters)",
                    severity="warning",
                    timeout=5
                )
            except Exception:
                # Fallback if app not available
                pass
            return

        # Sanitize control characters (security)
        prompt = ''.join(char for char in prompt if char.isprintable() or char.isspace())

        # Validate again after sanitization (in case all chars were control chars)
        if not prompt.strip():
            return

        # Add to history
        self.history.append(prompt)
        self.history_index = -1

        # Send message to app
        self.post_message(self.PromptSubmitted(prompt))

        # Clear input
        self.value = ""

        # Prevent event from bubbling
        event.stop()
        event.prevent_default()

    def on_key(self, event) -> None:
        """Handle special keys"""
        if event.key == "escape":
            # Cancel/clear input
            self.value = ""
            self.history_index = -1
            event.prevent_default()

        elif event.key == "up":
            # Navigate history backward
            if self.history:
                if self.history_index == -1:
                    # Save current input before navigating
                    self.current_input = self.value

                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.value = self.history[-(self.history_index + 1)]

                event.prevent_default()

        elif event.key == "down":
            # Navigate history forward
            if self.history_index >= 0:
                self.history_index -= 1

                if self.history_index == -1:
                    # Restore original input
                    self.value = self.current_input
                else:
                    self.value = self.history[-(self.history_index + 1)]

                event.prevent_default()

    def clear_history(self):
        """Clear command history"""
        self.history = []
        self.history_index = -1

    def focus_and_clear(self):
        """Focus input and clear any existing text"""
        self.value = ""
        self.history_index = -1
        self.focus()
