"""
StatusBar Widget - Displays task statistics and pagination info
"""

from textual.widgets import Static
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
        """Initialize status bar with placeholder"""
        super().__init__("Loading status...", **kwargs)

    def update_from_state(self, state: AppState) -> None:
        """
        Update status bar content from app state

        Args:
            state: Application state
        """
        from debug_logger import debug_log
        debug_log.debug(f"StatusBar.update_from_state() called with {len(state.tasks)} tasks")

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

        # Build status text as markup string (Textual supports Rich markup)
        order_arrow = "↑" if state.sort_order == "asc" else "↓"

        # Line 1: Navigation and context
        line1 = (
            f"Page [cyan bold]{current_page}[/cyan bold][dim]/{total_pages}[/dim]  •  "
            f"[bold]{shown}[/bold][dim]/{total_filtered}[/dim] showing  •  "
            f"[magenta]{state.view_mode}[/magenta]  •  "
            f"[blue]{order_arrow} {state.sort}[/blue] [dim]({state.sort_order})[/dim]"
        )

        # Line 2: Task statistics
        line2 = (
            f"[cyan bold]{total}[/cyan bold] tasks  •  "
            f"[green bold]{completed}[/green bold] done  •  "
            f"[yellow bold]{incomplete}[/yellow bold] todo"
        )

        # Add filter info if active
        if state.filter != "none":
            line2 += f"  •  Filter: [yellow]{state.filter}[/yellow]"

        # Combine lines
        status_markup = f"{line1}\n{line2}"

        debug_log.debug(f"StatusBar content: {status_markup[:100]}")

        # Update widget content
        self.update(status_markup)
        self.refresh(layout=True)
