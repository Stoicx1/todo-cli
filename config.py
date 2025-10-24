"""
Application Configuration & Constants
All magic numbers and hardcoded values centralized here
"""

from dataclasses import dataclass
from pathlib import Path
import sys


# ============================================================================
# FILE PATHS
# ============================================================================

DEFAULT_TASKS_FILE = "tasks.json"
DEFAULT_HISTORY_FILE = Path.home() / ".todo_cli_history"
DEFAULT_AUTH_FILE = Path.home() / ".todo_auth"
DEFAULT_SETTINGS_FILE = Path.home() / ".todo_cli_settings.json"
DEFAULT_AI_CONVERSATION_FILE = Path.home() / ".todo_cli_ai_history.json"


# ============================================================================
# UI CONFIGURATION
# ============================================================================

@dataclass
class UIConfig:
    """UI/UX configuration constants"""

    # Pagination
    COMPACT_PAGE_SIZE: int = 20
    DETAIL_PAGE_SIZE: int = 10

    # Command Palette
    MENU_RESERVE_LINES: int = 12
    MENU_MAX_VISIBLE: int = 8

    # Visual Feedback
    SUCCESS_PANEL_DURATION: float = 2.0
    INFO_PANEL_DURATION: float = 1.5
    SPINNER_REFRESH_RATE: int = 10

    # Confirmation Dialogs
    BULK_DELETE_THRESHOLD: int = 3  # Show confirmation if deleting > 3 tasks


# ============================================================================
# DATA VALIDATION
# ============================================================================

@dataclass
class ValidationConfig:
    """Input validation limits"""

    # Text Field Limits
    MAX_TASK_NAME_LENGTH: int = 200
    MIN_TASK_NAME_LENGTH: int = 1
    MAX_COMMENT_LENGTH: int = 500
    MAX_DESCRIPTION_LENGTH: int = 2000

    # Tag Limits
    MAX_TAGS_PER_TASK: int = 3
    MAX_TAG_LENGTH: int = 50
    MIN_TAG_LENGTH: int = 1

    # Priority Range
    MIN_PRIORITY: int = 1
    MAX_PRIORITY: int = 3
    DEFAULT_PRIORITY: int = 2

    # ID Limits
    MAX_TASK_ID: int = 999999  # Sanity check


# ============================================================================
# ANALYSIS & SUGGESTIONS
# ============================================================================

@dataclass
class AnalysisConfig:
    """LocalSuggestions thresholds"""

    HIGH_PRIORITY_WARNING_THRESHOLD: int = 5
    LOW_COMPLETION_RATE_THRESHOLD: float = 20.0
    HIGH_COMPLETION_RATE_THRESHOLD: float = 80.0
    LARGE_TASK_LIST_THRESHOLD: int = 20
    RECOMMENDED_TASKS_COUNT: int = 3


# ============================================================================
# PERFORMANCE
# ============================================================================

@dataclass
class PerformanceConfig:
    """Performance tuning settings"""

    # Task Index
    USE_TASK_INDEX: bool = True  # Enable O(1) task lookups

    # JSON Formatting
    # ---------------
    # indent=4: Human-readable, but 2-3x larger files and slower saves
    #   - Use for: Development, debugging, manual file editing
    #   - 1000 tasks: ~250KB file, 45ms save time
    #
    # indent=None: Compact JSON, faster saves, smaller files
    #   - Use for: Production, large datasets (10K+ tasks)
    #   - 1000 tasks: ~85KB file, 15ms save time (66% smaller, 67% faster)
    #
    # Recommendation: None for production, 4 for development
    JSON_INDENT: int | None = None  # Changed from 4 to None for production
    JSON_ENSURE_ASCII: bool = False  # Allow Unicode in JSON

    # Cache Settings
    ENABLE_TAG_CACHE: bool = True
    TAG_CACHE_TTL: int = 60  # seconds


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

ui = UIConfig()
validation = ValidationConfig()
analysis = AnalysisConfig()
performance = PerformanceConfig()


# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

try:
    # Prefer centralized detection to avoid mojibake on Windows terminals
    from utils.emoji import SUPPORTS_UNICODE as USE_UNICODE  # type: ignore
except Exception:
    # Fallback heuristic
    USE_UNICODE = (
        sys.stdout.encoding and (
            'utf' in sys.stdout.encoding.lower() or sys.stdout.encoding.lower() == 'cp65001'
        )
    )

# Debug flags
DEBUG_PARSER = False  # When True, prints parsed command parts in UI

# Platform detection
IS_WINDOWS = sys.platform.startswith('win')
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')


# ============================================================================
# AI ASSISTANT CONFIGURATION (LangChain Agent System)
# ============================================================================

@dataclass
class AIConfig:
    """AI Assistant & LangChain Agent Settings"""

    # OpenAI Model Settings
    MODEL: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1500
    STREAMING: bool = True

    # Conversation Memory Settings
    CHAT_HISTORY_FILE: Path = DEFAULT_AI_CONVERSATION_FILE
    MEMORY_MAX_TOKENS: int = 2000  # Keep ~2000 tokens in memory
    MEMORY_MAX_MESSAGES: int = 50  # Max messages before forced summarization

    # Agent Settings
    AGENT_VERBOSE: bool = False  # Set True to see reasoning steps (debugging)
    AGENT_MAX_ITERATIONS: int = 5  # Prevent infinite loops
    AGENT_HANDLE_PARSING_ERRORS: bool = True  # Graceful error recovery

    # Tool Execution Settings
    TOOL_SEARCH_LIMIT: int = 10  # Max tasks returned by search_tasks tool
    TOOL_REQUIRE_CONFIRMATION: bool = False  # Set True for destructive operations


# Global AI config instance
ai = AIConfig()
