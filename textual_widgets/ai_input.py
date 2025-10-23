"""
AI Input Widget
Input field for AI prompts with history navigation
"""

from textual.app import ComposeResult
from textual.widgets import Input
from textual.message import Message
from typing import List
from debug_logger import debug_log


class AIInput(Input):
    """
    Input field for AI prompts

    Features:
    - History navigation (↑/↓)
    - Submit with Enter
    - Cancel with Esc
    - Placeholder text

    Note: No key bindings defined to allow normal input handling.
    Instructions are shown in the placeholder text.
    """

    class PromptSubmitted(Message):
        """Message sent when user submits an AI prompt"""

        bubble = True  # Allow message to bubble up to parent widgets (App)

        def __init__(self, prompt: str):
            super().__init__()  # MUST be called first (Textual requirement)
            self.prompt = prompt

    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Ask AI about your tasks... (Press Enter to send, Esc to cancel)",
            **kwargs
        )
        self.history: List[str] = []  # Command history
        self.history_index: int = -1  # Current position in history
        self.current_input: str = ""  # Temp storage for current input

        # Log initialization
        debug_log.debug(f"AIInput widget initialized with id: {kwargs.get('id', 'NO_ID')}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key - submit prompt"""
        prompt = event.value.strip()

        # LOG: Show what was entered
        debug_log.debug(f"[STEP 1] AI Input received: '{prompt[:50]}' (length: {len(prompt)})")

        if not prompt:
            debug_log.debug("[STEP 1] Empty prompt, returning")
            return

        # Validate input length (prevent API errors)
        if len(prompt) > 5000:
            debug_log.debug(f"[STEP 1] Prompt too long: {len(prompt)} chars")
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
        original_len = len(prompt)
        prompt = ''.join(char for char in prompt if char.isprintable() or char.isspace())

        if len(prompt) != original_len:
            debug_log.debug(f"[STEP 1] Sanitized prompt: {original_len} -> {len(prompt)} chars")

        # Validate again after sanitization (in case all chars were control chars)
        if not prompt.strip():
            debug_log.debug("[STEP 1] Prompt empty after sanitization")
            return

        # Add to history
        self.history.append(prompt)
        self.history_index = -1

        # LOG: Show message is being posted
        debug_log.debug(f"[STEP 2] Posting PromptSubmitted message to app")
        debug_log.debug(f"[STEP 2] Widget app reference: {self.app}")
        debug_log.debug(f"[STEP 2] Widget parent: {self.parent}")
        debug_log.debug(f"[STEP 2] Widget ID: {self.id}")

        # Send message to app
        try:
            debug_log.debug(f"[STEP 2] About to create PromptSubmitted message object...")
            message_obj = self.PromptSubmitted(prompt)
            debug_log.debug(f"[STEP 2] Message object created successfully")

            message_type = type(message_obj).__name__
            message_bubble = getattr(message_obj.__class__, 'bubble', 'NOT_SET')
            debug_log.debug(f"[STEP 2] Message type={message_type}, bubble={message_bubble}")

            debug_log.debug(f"[STEP 2] About to call post_message()...")
            result = self.post_message(message_obj)
            debug_log.debug(f"[STEP 2] post_message() returned: {result}")

            debug_log.debug(f"[STEP 2] Message posted successfully to message pump")

            # WORKAROUND: Manually call the handler since message routing is broken
            debug_log.debug(f"[STEP 2] WORKAROUND: Manually calling app handler...")
            if hasattr(self.app, 'on_ai_input_prompt_submitted'):
                self.app.on_ai_input_prompt_submitted(message_obj)
                debug_log.debug(f"[STEP 2] Manual handler call completed")
            else:
                debug_log.error(f"[STEP 2] Handler not found on app!")

        except Exception as e:
            debug_log.error(f"[STEP 2] EXCEPTION while posting message: {type(e).__name__}: {str(e)}", exception=e)
            # Re-raise to see the error in the UI
            raise

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
