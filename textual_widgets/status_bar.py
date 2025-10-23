"""
StatusBar Widget - Displays task statistics and pagination info
"""

from textual.widgets import Static
from rich.text import Text

from core.state import AppState


class StatusBar(Static):
    """
    Status bar widget showing task statistics

    Displays:
    - Page navigation (Page X/Y)
    - Task counts (total, done, todo)
    - Active filter
    - View mode
    - Sort order
    """

    def __init__(self, **kwargs):
        """Initialize status bar"""
        super().__init__("", **kwargs)

    def update_from_state(self, state: AppState) -> None:
        """
        Update status bar content from app state

        Args:
            state: Application state
        """
        # Calculate stats
        total = len(state.tasks)
        completed = sum(1 for t in state.tasks if t.done)
        incomplete = total - completed

        # Calculate pagination
        filtered_tasks = state.get_filter_tasks(state.tasks)
        total_filtered = len(filtered_tasks)
        total_pages = (total_filtered + state.page_size - 1) // state.page_size if total_filtered > 0 else 1
        current_page = state.page + 1
        shown = len(state.get_current_page_tasks())

        # Build status text
        status_text = Text()

        # Line 1: Navigation and context
        status_text.append(f"Page ", style="white")
        status_text.append(f"{current_page}", style="cyan bold")
        status_text.append(f"/{total_pages}", style="dim")
        status_text.append("  •  ", style="dim")

        status_text.append(f"{shown}", style="white bold")
        status_text.append(f"/{total_filtered}", style="dim")
        status_text.append(" showing", style="white")
        status_text.append("  •  ", style="dim")

        status_text.append(f"{state.view_mode}", style="magenta")
        status_text.append("  •  ", style="dim")

        # Sort indicator
        order_arrow = "↑" if state.sort_order == "asc" else "↓"
        status_text.append(f"{order_arrow} ", style="blue")
        status_text.append(f"{state.sort}", style="blue")
        status_text.append(f" ({state.sort_order})", style="dim")

        status_text.append("\n")

        # Line 2: Task statistics
        status_text.append(f"{total}", style="cyan bold")
        status_text.append(" tasks", style="dim")
        status_text.append("  •  ", style="dim")

        status_text.append(f"{completed}", style="green bold")
        status_text.append(" done", style="dim")
        status_text.append("  •  ", style="dim")

        status_text.append(f"{incomplete}", style="yellow bold")
        status_text.append(" todo", style="dim")

        # Add filter info if active
        if state.filter != "none":
            status_text.append("  •  ", style="dim")
            status_text.append("Filter: ", style="white")
            status_text.append(f"{state.filter}", style="yellow")

        # Update widget content
        self.update(status_text)
