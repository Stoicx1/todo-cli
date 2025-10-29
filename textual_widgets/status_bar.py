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
        from debug_logger import debug_log
        super().__init__("Loading status...", **kwargs)
        debug_log.info("[STATUSBAR] Widget initialized with placeholder text")

    def update_from_state(self, state: AppState) -> None:
        """
        Update status bar content from app state

        Args:
            state: Application state
        """
        from debug_logger import debug_log
        debug_log.info(f"[STATUSBAR] Starting update_from_state with {len(state.tasks)} tasks")

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
            f"Page [cyan bold]{current_page}[/cyan bold]/{total_pages}  •  "
            f"[bold]{shown}[/bold]/{total_filtered} showing  •  "
            f"mode=[magenta]{getattr(state, 'entity_mode', 'tasks')}[/magenta]  •  "
            f"view=[magenta]{state.view_mode}[/magenta]  •  "
            f"[blue]{order_arrow} {state.sort}[/blue] ({state.sort_order})"
        )
        # If in notes mode, append selected note title when available
        try:
            if getattr(state, 'entity_mode', 'tasks') == 'notes':
                from textual_widgets.note_table import NoteTable  # type: ignore
                tbl = self.app.query_one(NoteTable)
                nid = tbl.get_selected_note_id()
                if nid:
                    # Find title via state
                    note = next((n for n in getattr(state, 'notes', []) if n.id.startswith(nid)), None)
                    if note and getattr(note, 'title', ''):
                        title = (note.title or '')
                        if len(title) > 30:
                            title = title[:30] + '…'
                        line1 += f"  •  note: {title}"
        except Exception:
            pass

        # Append current focus target
        try:
            focused = self.app.focused
            focus_id = getattr(focused, 'id', '') or focused.__class__.__name__
            # Reduce verbosity for known ids
            friendly = (
                'tasks' if focus_id in ('task_table',) else
                'notes' if focus_id in ('note_table',) else
                'ai chat' if focus_id in ('ai_chat_panel',) else
                'ai input' if focus_id in ('ai_input',) else
                'command' if focus_id in ('command_input',) else
                focus_id
            )
            if friendly:
                line1 += f"  •  focus: {friendly}"
        except Exception:
            pass

        # Line 2: Task/Notes statistics
        if getattr(state, 'entity_mode', 'tasks') == 'notes':
            line2 = f"[cyan bold]{len(getattr(state, 'notes', []))}[/cyan bold] notes"
            tid_filter = getattr(state, 'notes_task_id_filter', None)
            q = getattr(state, 'notes_query', '') or ''
            if tid_filter is not None:
                line2 += f"  •  filter: task=#{tid_filter}"
            if q.strip():
                line2 += f"  •  search: [yellow]{q.strip()}[/yellow]"
        else:
            line2 = (
                f"[cyan bold]{total}[/cyan bold] tasks  •  "
                f"[green bold]{completed}[/green bold] done  •  "
                f"[yellow bold]{incomplete}[/yellow bold] todo"
            )
            if state.filter != "none":
                line2 += f"  •  Filter: [yellow]{state.filter}[/yellow]"

        # Combine lines
        status_markup = f"{line1}\n{line2}"

        # Log content details
        debug_log.info(f"[STATUSBAR] Generated content ({len(status_markup)} chars): {status_markup[:150]}...")

        # Log widget state before update
        try:
            debug_log.info(f"[STATUSBAR] Widget before update: visible={self.visible}, display={self.display}, size={self.size}")
            debug_log.info(f"[STATUSBAR] Content region: {self.content_region}, content_size={self.content_size}")
        except Exception as e:
            debug_log.warning(f"[STATUSBAR] Could not log widget state: {e}")

        # Update widget content
        debug_log.info(f"[STATUSBAR] Calling self.update() with {len(status_markup)} chars")
        self.update(status_markup)

        # Log widget state after update
        try:
            debug_log.info(f"[STATUSBAR] Widget after update: renderable type={type(self.renderable).__name__}")
            debug_log.info(f"[STATUSBAR] Renderable preview: {str(self.renderable)[:100]}...")
        except Exception as e:
            debug_log.warning(f"[STATUSBAR] Could not log post-update state: {e}")

        debug_log.info("[STATUSBAR] update_from_state() completed successfully")
