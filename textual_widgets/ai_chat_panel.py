"""
AI Chat Panel Widget
Displays conversation history in a scrollable sidebar
"""

from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Static, Label
from textual.reactive import reactive
from typing import List
from models.ai_message import AIMessage
from core.state import AppState


class MessageBubble(Static):
    """A single message bubble (user or assistant)"""

    def __init__(self, message: AIMessage, **kwargs):
        self.message = message
        super().__init__(**kwargs)
        self.update_content()

    def update_content(self):
        """Render message content"""
        role_icon = "🧑" if self.message.role == "user" else "🤖"
        role_label = "You" if self.message.role == "user" else "AI"

        # Format timestamp (time only)
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(self.message.timestamp)
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = ""

        # Build header
        header = f"{role_icon} {role_label}"
        if time_str:
            header += f" • {time_str}"

        # Add CSS classes for styling
        if self.message.role == "user":
            self.add_class("user-message")
        else:
            self.add_class("ai-message")

        # Update content
        self.update(f"{header}\n{self.message.content}")


class AIChatPanel(VerticalScroll):
    """
    Scrollable AI chat history panel (sidebar widget)

    Features:
    - Displays conversation history
    - Auto-scrolls to latest message
    - Shows streaming indicator
    - Collapsible sidebar
    """

    # Reactive attributes
    message_count = reactive(0)
    is_streaming = reactive(False)

    def __init__(self, state: AppState, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self.border_title = "💬 AI Chat"

    def compose(self) -> ComposeResult:
        """Compose initial layout"""
        yield Label("No conversation yet. Ask AI a question!", id="empty_message")

    def update_from_state(self):
        """Refresh chat panel from state conversation history"""
        # Clear existing messages
        self.remove_children()

        if not self.state.ai_conversation:
            # Show empty state
            empty_label = Label("No conversation yet.\nPress ? or Ctrl+Shift+A to ask AI!")
            empty_label.add_class("empty-state")
            self.mount(empty_label)
            self.message_count = 0
            return

        # Mount all messages
        for message in self.state.ai_conversation:
            bubble = MessageBubble(message)
            self.mount(bubble)

        # Update count
        self.message_count = len(self.state.ai_conversation)

        # Auto-scroll to bottom (latest message)
        self.scroll_end(animate=False)

    def add_message(self, message: AIMessage):
        """
        Add a new message to the panel

        Args:
            message: AIMessage to add
        """
        # Remove empty state if present
        try:
            empty = self.query_one("#empty_message", Label)
            empty.remove()
        except Exception:
            # Empty state already removed or doesn't exist
            pass

        # Mount new message
        bubble = MessageBubble(message)
        self.mount(bubble)

        # Update count
        self.message_count += 1

        # Scroll to bottom
        self.scroll_end(animate=True)

    def append_to_last_message(self, text_chunk: str):
        """
        Append text to the last message (for streaming)

        Args:
            text_chunk: Text chunk to append
        """
        if not self.state.ai_conversation:
            return

        # Get last message
        last_message = self.state.ai_conversation[-1]
        last_message.content += text_chunk

        # Find last bubble and update it
        bubbles = self.query(MessageBubble)
        if bubbles:
            last_bubble = bubbles[-1]
            last_bubble.update_content()

        # Keep scrolled to bottom during streaming
        self.scroll_end(animate=False)

    def clear_conversation(self):
        """Clear all messages"""
        self.remove_children()
        empty_label = Label("Conversation cleared.\nPress ? to start a new chat!")
        empty_label.add_class("empty-state")
        self.mount(empty_label)
        self.message_count = 0

    def show_streaming_indicator(self):
        """Show that AI is currently responding"""
        self.is_streaming = True
        self.border_title = "💬 AI Chat (streaming...)"

    def hide_streaming_indicator(self):
        """Hide streaming indicator"""
        self.is_streaming = False
        self.border_title = "💬 AI Chat"

    def get_stats(self) -> str:
        """Get conversation stats for display"""
        total_tokens = sum(msg.token_count for msg in self.state.ai_conversation)
        return f"{self.message_count} messages • ~{total_tokens} tokens"
