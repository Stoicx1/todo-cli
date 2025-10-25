"""
AI Response Rendering with Streaming Markdown

Provides beautiful, formatted AI responses with:
- Streaming text display (word-by-word)
- Rich markdown rendering
- Tool execution indicators
- Cyan-themed panels
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from debug_logger import debug_log


class StreamingMarkdownCallback:
    """
    Callback handler for streaming AI responses.

    Displays responses in real-time with:
    - Live updating panel
    - Markdown formatting
    - Cyan border theme
    """

    def __init__(self, console: Console):
        """
        Initialize streaming callback.

        Args:
            console: Rich Console instance for rendering
        """
        self.console = console
        self.text = ""
        self.live = None

    def on_start(self):
        """Initialize live display when streaming starts"""
        debug_log.debug("[AI_RENDER] Streaming started - initializing live display")
        self.text = ""
        try:
            self.live = Live(
                Panel(
                    Spinner("dots", text="AI is thinking..."),
                    title="🤖 AI Assistant",
                    border_style="cyan"
                ),
                console=self.console,
                refresh_per_second=10
            )
            self.live.start()
            debug_log.debug("[AI_RENDER] Live display started")
        except Exception as e:
            debug_log.error(f"[AI_RENDER] Failed to start live display: {str(e)}", exception=e)

    def on_token(self, token: str):
        """
        Handle new token from stream.

        Args:
            token: Text chunk from AI response
        """
        if not self.live:
            self.on_start()

        self.text += token

        # Log every 50 chars to avoid spam
        if len(self.text) % 50 == 0:
            debug_log.debug(f"[AI_RENDER] Streaming progress - {len(self.text)} chars received")

        try:
            # Update display with markdown-rendered text
            self.live.update(
                Panel(
                    Markdown(self.text),
                    title="🤖 AI Assistant",
                    border_style="cyan",
                    padding=(1, 2)
                )
            )
        except Exception as e:
            debug_log.error(f"[AI_RENDER] Failed to update display: {str(e)}", exception=e)

    def on_end(self):
        """Stop live display when streaming completes"""
        debug_log.info(f"[AI_RENDER] Streaming completed - {len(self.text)} total chars")
        try:
            if self.live:
                self.live.stop()
                self.live = None
                debug_log.debug("[AI_RENDER] Live display stopped")
        except Exception as e:
            debug_log.error(f"[AI_RENDER] Failed to stop live display: {str(e)}", exception=e)

    def __call__(self, token: str):
        """Allow callback to be called directly with token"""
        self.on_token(token)


class AIResponsePanel:
    """
    Static panel for formatted AI responses.

    Use when not streaming, or for final display.
    """

    @staticmethod
    def render(content: str, title: str = "🤖 AI Assistant", console: Optional[Console] = None):
        """
        Render AI response in styled panel.

        Args:
            content: Response text (markdown supported)
            title: Panel title (default: "🤖 AI Assistant")
            console: Rich Console (optional, creates new if not provided)

        Returns:
            Panel instance (can be printed or returned)
        """
        panel = Panel(
            Markdown(content),
            title=title,
            border_style="cyan",
            padding=(1, 2)
        )

        if console:
            console.print(panel)

        return panel


class AIIndicators:
    """
    Helper functions for AI operation indicators.

    Provides consistent visual feedback for:
    - Thinking/loading states
    - Tool execution
    - Errors
    """

    @staticmethod
    def render_thinking(console: Console, message: str = "AI is thinking..."):
        """
        Show animated thinking indicator.

        Args:
            console: Rich Console
            message: Status message to display
        """
        console.print(
            Panel(
                Spinner("dots", text=message),
                title="🤖 AI Assistant",
                border_style="cyan"
            )
        )

    @staticmethod
    def render_tool_execution(tool_name: str, console: Console):
        """
        Show tool execution indicator.

        Args:
            tool_name: Name of the tool being executed
            console: Rich Console
        """
        console.print(f"[dim cyan]  Using tool: {tool_name}...[/dim cyan]")

    @staticmethod
    def render_error(error_msg: str, console: Console):
        """
        Render error message in red panel.

        Args:
            error_msg: Error message to display
            console: Rich Console
        """
        console.print(
            Panel(
                Text(error_msg, style="bold red"),
                title="❌ Error",
                border_style="red",
                padding=(1, 2)
            )
        )

    @staticmethod
    def render_success(message: str, console: Console):
        """
        Render success message in green panel.

        Args:
            message: Success message
            console: Rich Console
        """
        console.print(
            Panel(
                Text(message, style="bold green"),
                title="✅ Success",
                border_style="green",
                padding=(1, 2)
            )
        )

    @staticmethod
    def format_conversation_turn(turn: int, total: int) -> str:
        """
        Format conversation turn indicator.

        Args:
            turn: Current turn number
            total: Total turns in conversation

        Returns:
            Formatted string like "Turn 5/20"
        """
        return f"Turn {turn}/{total}"


# Convenience exports for common use cases
def render_ai_response(content: str, console: Console, streaming: bool = False):
    """
    Render AI response with appropriate method.

    Args:
        content: Response content (markdown supported)
        console: Rich Console
        streaming: If True, use streaming display; if False, use static panel

    Returns:
        StreamingMarkdownCallback if streaming, otherwise Panel
    """
    if streaming:
        callback = StreamingMarkdownCallback(console)
        callback.on_start()
        return callback
    else:
        return AIResponsePanel.render(content, console=console)


def create_streaming_callback(console: Console) -> StreamingMarkdownCallback:
    """
    Create a streaming callback for AI responses.

    Args:
        console: Rich Console instance

    Returns:
        StreamingMarkdownCallback instance ready to use

    Example:
        callback = create_streaming_callback(console)
        response = agent.ask("What tasks do I have?", streaming_callback=callback)
    """
    return StreamingMarkdownCallback(console)
