"""
Conversation Memory Manager for AI Assistant

Provides persistent conversation history with automatic summarization:
- Saves conversations to JSON file
- Auto-summarizes old messages to save tokens
- Token-aware memory management
- Cross-session persistence
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from core.file_safety import SafeFileManager
from config import ai as ai_config
from debug_logger import debug_log


class ConversationMemoryManager:
    """
    Manages persistent conversation history with automatic summarization.

    Features:
    - Stores conversations in JSON format
    - Auto-summarizes old messages when token limit reached
    - Token tracking and management
    - Safe file I/O with locking and backups
    """

    def __init__(
        self,
        memory_file: Optional[Path] = None,
        max_token_limit: int = 2000,
        max_messages: int = 50
    ):
        """
        Initialize conversation memory manager.

        Args:
            memory_file: Path to JSON file for storage (default: from config)
            max_token_limit: Max tokens to keep in memory (older messages summarized)
            max_messages: Max message count before forced summarization
        """
        self.memory_file = memory_file or ai_config.CHAT_HISTORY_FILE
        self.max_token_limit = max_token_limit
        self.max_messages = max_messages

        debug_log.info(f"[AI_MEMORY] Initializing ConversationMemoryManager - file: {self.memory_file}")
        debug_log.debug(f"[AI_MEMORY] Limits - tokens: {max_token_limit}, messages: {max_messages}")

        # In-memory state
        self.messages: List[Dict[str, str]] = []
        self.summary: str = ""
        self.total_exchanges: int = 0
        self.last_updated: str = ""

        # Load existing memory from disk
        self.load_from_disk()

    def load_from_disk(self) -> None:
        """
        Load conversation history from JSON file.

        File format:
        {
            "messages": [{"role": "user"|"assistant", "content": "..."}],
            "summary": "...",
            "metadata": {"total_exchanges": N, "last_updated": "ISO timestamp"}
        }
        """
        debug_log.debug(f"[AI_MEMORY] Loading from disk - {self.memory_file}")

        try:
            if not Path(self.memory_file).exists():
                debug_log.info(f"[AI_MEMORY] No existing file found - starting fresh")
                # Initialize empty memory
                self.messages = []
                self.summary = ""
                self.total_exchanges = 0
                self.last_updated = datetime.utcnow().isoformat()
                return

            # Load from file using SafeFileManager
            manager = SafeFileManager(str(self.memory_file))
            data = manager.load_json_with_lock()

            # Handle backward compatibility with old format (list of messages)
            if isinstance(data, list):
                debug_log.info(f"[AI_MEMORY] Migrating old format (list) to new format (dict)")
                # Old format: list of message dicts with role/content/timestamp
                # Convert to new format
                old_messages = data
                self.messages = [
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                    for msg in old_messages
                    if "role" in msg and "content" in msg
                ]
                self.summary = ""
                self.total_exchanges = len(self.messages) // 2  # Estimate exchanges
                self.last_updated = datetime.utcnow().isoformat()

                # Save in new format immediately
                debug_log.info(f"[AI_MEMORY] Saving migrated data in new format")
                self.save_to_disk()
            else:
                # New format: dict with messages, summary, metadata
                self.messages = data.get("messages", [])
                self.summary = data.get("summary", "")

                metadata = data.get("metadata", {})
                self.total_exchanges = metadata.get("total_exchanges", 0)
                self.last_updated = metadata.get("last_updated", "")

            debug_log.info(f"[AI_MEMORY] Loaded successfully - {len(self.messages)} messages, {self.total_exchanges} total exchanges")

        except Exception as e:
            # If loading fails, start fresh but log the error
            debug_log.error(f"[AI_MEMORY] Load failed: {str(e)}", exception=e)
            print(f"Warning: Failed to load conversation memory: {e}")
            self.messages = []
            self.summary = ""
            self.total_exchanges = 0

    def save_to_disk(self) -> None:
        """
        Save conversation history to JSON file.

        Uses SafeFileManager for atomic writes with backups.
        """
        debug_log.debug(f"[AI_MEMORY] Saving to disk - {len(self.messages)} messages")

        try:
            data = {
                "messages": self.messages,
                "summary": self.summary,
                "metadata": {
                    "total_exchanges": self.total_exchanges,
                    "last_updated": self.last_updated
                }
            }

            manager = SafeFileManager(str(self.memory_file))
            manager.save_json_with_lock(data, indent=2)
            debug_log.info(f"[AI_MEMORY] Saved successfully - {self.total_exchanges} exchanges")

        except Exception as e:
            debug_log.error(f"[AI_MEMORY] Save failed: {str(e)}", exception=e)
            print(f"Warning: Failed to save conversation memory: {e}")

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        """
        Add a user-assistant exchange to memory.

        Args:
            user_message: User's question or prompt
            assistant_message: AI assistant's response

        This automatically:
        - Appends messages to history
        - Checks token limits and summarizes if needed
        - Saves to disk
        """
        debug_log.debug(f"[AI_MEMORY] Adding exchange - user: {len(user_message)} chars, assistant: {len(assistant_message)} chars")

        # Add messages
        self.messages.append({"role": "user", "content": user_message})
        self.messages.append({"role": "assistant", "content": assistant_message})

        # Update metadata
        self.total_exchanges += 1
        self.last_updated = datetime.utcnow().isoformat()

        debug_log.debug(f"[AI_MEMORY] Exchange added - total exchanges: {self.total_exchanges}, messages: {len(self.messages)}")

        # Check if we need to summarize
        if self._should_summarize():
            debug_log.info(f"[AI_MEMORY] Triggering auto-summarization - {len(self.messages)} messages, ~{self._estimate_tokens()} tokens")
            self._auto_summarize()

        # Save to disk
        self.save_to_disk()

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history in LangChain message format.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        return self.messages.copy()

    def get_summary(self) -> str:
        """
        Get conversation summary (if exists).

        Returns:
            Summary string or empty string if no summary
        """
        return self.summary

    def clear(self) -> None:
        """
        Clear all conversation history and summary.

        This is a fresh start - all memory is wiped.
        """
        debug_log.info(f"[AI_MEMORY] Clearing all conversation history - was {len(self.messages)} messages")
        self.messages = []
        self.summary = ""
        self.total_exchanges = 0
        self.last_updated = datetime.utcnow().isoformat()
        self.save_to_disk()
        debug_log.info("[AI_MEMORY] Conversation cleared successfully")

    def get_stats(self) -> Dict[str, any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with:
            - messages: Number of messages in memory
            - exchanges: Total exchanges (user + assistant pairs)
            - tokens: Estimated token count
            - has_summary: Whether summary exists
            - last_updated: ISO timestamp
        """
        estimated_tokens = self._estimate_tokens()

        return {
            "messages": len(self.messages),
            "exchanges": self.total_exchanges,
            "tokens": estimated_tokens,
            "has_summary": bool(self.summary),
            "last_updated": self.last_updated
        }

    def export_to_markdown(self, filename: str) -> None:
        """
        Export conversation to markdown file.

        Args:
            filename: Output markdown file path

        Format:
        # AI Conversation History

        ## Summary
        <summary if exists>

        ## Conversation
        **User**: question
        **Assistant**: response
        ...
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# AI Conversation History\n\n")
            f.write(f"*Exported: {datetime.utcnow().isoformat()}*\n\n")
            f.write(f"*Total Exchanges: {self.total_exchanges}*\n\n")

            if self.summary:
                f.write("## Summary\n\n")
                f.write(f"{self.summary}\n\n")

            f.write("## Conversation\n\n")

            for msg in self.messages:
                role = "**User**" if msg["role"] == "user" else "**Assistant**"
                f.write(f"{role}: {msg['content']}\n\n")

    def _should_summarize(self) -> bool:
        """
        Check if we should auto-summarize old messages.

        Triggers when:
        - Token count exceeds limit, OR
        - Message count exceeds limit
        """
        token_count = self._estimate_tokens()
        message_count = len(self.messages)

        return (
            token_count > self.max_token_limit or
            message_count > self.max_messages
        )

    def _estimate_tokens(self) -> int:
        """
        Estimate token count of current messages.

        Uses rough heuristic: 1 token ≈ 4 characters
        """
        total_chars = sum(len(msg["content"]) for msg in self.messages)
        if self.summary:
            total_chars += len(self.summary)

        return total_chars // 4

    def _auto_summarize(self) -> None:
        """
        Auto-summarize old messages to save tokens.

        Strategy:
        - Keep last 10 messages verbatim (recent context)
        - Summarize older messages into summary string
        - Update summary with new compressed history
        """
        debug_log.debug(f"[AI_MEMORY] _auto_summarize() called - {len(self.messages)} messages")

        if len(self.messages) <= 10:
            # Not enough messages to summarize
            debug_log.debug("[AI_MEMORY] Not enough messages to summarize (≤10)")
            return

        # Split into old (to summarize) and recent (to keep)
        messages_to_summarize = self.messages[:-10]
        recent_messages = self.messages[-10:]

        debug_log.debug(f"[AI_MEMORY] Summarizing {len(messages_to_summarize)} old messages, keeping {len(recent_messages)} recent")

        # Build summary text from old messages
        summary_parts = []
        if self.summary:
            summary_parts.append(f"Previous context: {self.summary}")

        # Compress old messages into brief summary
        user_questions = []
        assistant_topics = []

        for msg in messages_to_summarize:
            if msg["role"] == "user":
                # Extract key topics from user questions
                content = msg["content"][:100]  # First 100 chars
                user_questions.append(content)
            else:
                # Extract brief summary of assistant responses
                content = msg["content"][:100]
                assistant_topics.append(content)

        if user_questions:
            summary_parts.append(
                f"User asked about: {', '.join(user_questions[:5])}"
            )

        # Update summary and keep only recent messages
        self.summary = " | ".join(summary_parts)
        self.messages = recent_messages

        debug_log.info(f"[AI_MEMORY] Summarization complete - summary: {len(self.summary)} chars, kept {len(recent_messages)} messages")

    def get_context_for_agent(self) -> Dict[str, any]:
        """
        Get formatted context for LangChain agent.

        Returns:
            Dictionary with:
            - chat_history: List of message dicts
            - summary: Summary string (if exists)
        """
        return {
            "chat_history": self.get_history(),
            "summary": self.summary if self.summary else "No previous context"
        }
