"""
AI Message Model
Represents a single message in the AI conversation history
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class AIMessage:
    """
    A message in the AI conversation

    Attributes:
        role: "user" or "assistant"
        content: The message text
        timestamp: When the message was created
        token_count: Estimated tokens used (for API cost tracking)
        is_status: Whether this is a temporary status message (e.g., "Thinking...")
    """
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = ""  # ISO format timestamp
    token_count: int = 0  # Estimated tokens (rough: len(content) // 4)
    is_status: bool = False  # True for temporary status indicators

    def __post_init__(self):
        """Set timestamp if not provided"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

        # Estimate token count if not provided
        if self.token_count == 0:
            # Rough estimate: 1 token ≈ 4 characters for English text
            self.token_count = len(self.content) // 4

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "token_count": self.token_count,
            "is_status": self.is_status
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AIMessage":
        """Create AIMessage from dictionary (JSON deserialization)"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", ""),
            token_count=data.get("token_count", 0),
            is_status=data.get("is_status", False)
        )

    def format_for_display(self, max_width: int = 80) -> str:
        """
        Format message for terminal display

        Args:
            max_width: Maximum line width before wrapping

        Returns:
            Formatted string with role indicator and wrapped content
        """
        role_icon = "🧑" if self.role == "user" else "🤖"
        role_label = "You" if self.role == "user" else "AI"

        # Format timestamp (show time only, not full date)
        dt = datetime.fromisoformat(self.timestamp)
        time_str = dt.strftime("%H:%M:%S")

        # Header line
        header = f"{role_icon} {role_label} ({time_str})"

        # Content (simple wrapping)
        lines = [header, "─" * min(len(header), max_width)]

        # Split content into lines respecting max_width
        words = self.content.split()
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_width:
                current_line += (" " + word) if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return "\n".join(lines)

    def get_openai_format(self) -> dict:
        """
        Convert to OpenAI API format

        Returns:
            Dictionary with {"role": "user"|"assistant", "content": "..."}
        """
        return {
            "role": self.role,
            "content": self.content
        }
