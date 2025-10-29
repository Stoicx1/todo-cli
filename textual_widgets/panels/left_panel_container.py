"""
LeftPanelContainer - Dynamic container for panel switching

Manages the left side of the UI, switching between different panel modes:
- Task List (TaskTable)
- Task Detail (TaskDetailPanel)
- Task Edit (TaskEditPanel)
- Note List (NoteTable)
- Note Detail (NoteDetailPanel)
- Note Edit (NoteEditPanel)

Uses reactive attributes for automatic UI updates when mode changes.
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widget import Widget

from core.state import LeftPanelMode
from textual_widgets.panels.task_detail_panel import TaskDetailPanel
from textual_widgets.panels.task_edit_panel import TaskEditPanel
from textual_widgets.panels.note_detail_panel import NoteDetailPanel
from textual_widgets.panels.note_edit_panel import NoteEditPanel
from debug_logger import debug_log


class LeftPanelContainer(Container):
    """
    Dynamic container that switches between panel widgets based on app state

    Features:
        - Automatic panel switching via reactive attributes
        - Clean mount/unmount of panels
        - Preserves existing table widgets (TaskTable, NoteTable)
        - Handles panel creation with current state data

    Reactivity:
        Watches app.state.left_panel_mode and switches panels automatically
    """

    DEFAULT_CSS = """
    LeftPanelContainer {
        width: 70%;
        height: 1fr;
        layout: vertical;
        background: $surface;
        border: solid #404040;
    }

    LeftPanelContainer:focus-within {
        border: solid #ffdb7a;
    }
    """

    # Reactive - triggers panel switching
    current_mode = reactive(LeftPanelMode.LIST_TASKS)

    def __init__(self, **kwargs):
        super().__init__(**kwargs, id="left_panel_container")
        self._current_panel: Widget | None = None

        # Set initial border title
        self.border_title = "Tasks"

    def compose(self) -> ComposeResult:
        """
        Initial composition - starts empty

        Panels are dynamically mounted based on mode changes
        Table widgets (TaskTable, NoteTable) will be injected by the app
        """
        # Container starts empty - panels mounted dynamically
        return []

    def watch_current_mode(self, old_mode: LeftPanelMode, new_mode: LeftPanelMode) -> None:
        """
        Reactive watcher - automatically called when current_mode changes

        Args:
            old_mode: Previous panel mode
            new_mode: New panel mode to display
        """
        debug_log.info(f"[LEFT_PANEL] ──────────────────────────────────────")
        debug_log.info(f"[LEFT_PANEL] Mode change: {old_mode} → {new_mode}")
        debug_log.info(f"[LEFT_PANEL] ──────────────────────────────────────")
        self._switch_to_mode(new_mode)

    def _switch_to_mode(self, mode: LeftPanelMode) -> None:
        """
        Switch the visible panel based on mode

        Args:
            mode: Target panel mode

        Process:
            1. Update border title based on mode
            2. Remove current panel (if any)
            3. Create and mount appropriate panel
            4. Focus new panel
        """
        import time
        start_time = time.time()

        # Update border title based on mode
        mode_titles = {
            LeftPanelMode.LIST_TASKS: "Tasks",
            LeftPanelMode.DETAIL_TASK: "Task Detail",
            LeftPanelMode.EDIT_TASK: "Edit Task",
            LeftPanelMode.LIST_NOTES: "Notes",
            LeftPanelMode.DETAIL_NOTE: "Note Detail",
            LeftPanelMode.EDIT_NOTE: "Edit Note",
        }
        self.border_title = mode_titles.get(mode, "Panel")

        debug_log.debug(f"[LEFT_PANEL] _switch_to_mode called with mode: {mode}")
        debug_log.debug(f"[LEFT_PANEL] Current panel: {type(self._current_panel).__name__ if self._current_panel else 'None'}")
        debug_log.debug(f"[LEFT_PANEL] Container children count: {len(list(self.children))}")

        # Remove current panel
        self._clear_current_panel()

        # Mount appropriate panel based on mode
        debug_log.debug(f"[LEFT_PANEL] Mounting panel for mode: {mode}")

        if mode == LeftPanelMode.LIST_TASKS:
            self._mount_task_list()

        elif mode == LeftPanelMode.DETAIL_TASK:
            self._mount_task_detail()

        elif mode == LeftPanelMode.EDIT_TASK:
            self._mount_task_edit()

        elif mode == LeftPanelMode.LIST_NOTES:
            self._mount_note_list()

        elif mode == LeftPanelMode.DETAIL_NOTE:
            self._mount_note_detail()

        elif mode == LeftPanelMode.EDIT_NOTE:
            self._mount_note_edit()

        elapsed = (time.time() - start_time) * 1000
        debug_log.info(f"[LEFT_PANEL] Mode switch completed in {elapsed:.2f}ms")
        debug_log.debug(f"[LEFT_PANEL] New panel: {type(self._current_panel).__name__ if self._current_panel else 'None'}")
        debug_log.debug(f"[LEFT_PANEL] New children count: {len(list(self.children))}")

    def _clear_current_panel(self) -> None:
        """Remove current panel from container"""
        debug_log.debug(f"[LEFT_PANEL] Clearing current panel...")

        if self._current_panel:
            panel_name = type(self._current_panel).__name__
            debug_log.debug(f"[LEFT_PANEL] Removing current panel: {panel_name}")
            try:
                self._current_panel.remove()
                debug_log.debug(f"[LEFT_PANEL] Panel {panel_name} removed successfully")
            except Exception as e:
                debug_log.warning(f"[LEFT_PANEL] Failed to remove panel {panel_name}: {e}")
            self._current_panel = None

        # Remove all children to ensure clean slate
        children_count = len(list(self.children))
        if children_count > 0:
            debug_log.debug(f"[LEFT_PANEL] Removing {children_count} remaining children...")
            for child in list(self.children):
                try:
                    child.remove()
                except Exception as e:
                    debug_log.warning(f"[LEFT_PANEL] Failed to remove child {type(child).__name__}: {e}")
            debug_log.debug(f"[LEFT_PANEL] All children removed")

    def _mount_task_list(self) -> None:
        """Mount TaskTable for LIST_TASKS mode"""
        from textual_widgets.task_table import TaskTable

        debug_log.debug(f"[LEFT_PANEL] _mount_task_list called")

        # Check if TaskTable already exists in app
        try:
            task_table = self.app.query_one(TaskTable)
            debug_log.debug(f"[LEFT_PANEL] Found existing TaskTable, reparenting...")
            # Reparent to this container
            self.mount(task_table)
            self._current_panel = task_table
            task_table.focus()
            debug_log.debug(f"[LEFT_PANEL] TaskTable reparented and focused")
        except Exception as e:
            # Create new if not found
            debug_log.debug(f"[LEFT_PANEL] No existing TaskTable found ({e}), creating new...")
            task_table = TaskTable(id="task_table")
            self.mount(task_table)
            self._current_panel = task_table
            task_table.focus()
            debug_log.debug(f"[LEFT_PANEL] New TaskTable created and focused")

            # Update table from state
            debug_log.debug(f"[LEFT_PANEL] Refreshing table from state...")
            self.app.refresh_table()
            debug_log.debug(f"[LEFT_PANEL] Table refresh completed")

    def _mount_task_detail(self) -> None:
        """Mount TaskDetailPanel for DETAIL_TASK mode"""
        # Get selected task
        task_id = self.app.state.selected_task_id
        if task_id is None:
            # No task selected - return to list
            self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
            return

        task = self.app.state.get_task_by_id(task_id)
        if task is None:
            # Task not found - return to list
            self.app.notify(f"Task #{task_id} not found", severity="warning")
            self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
            return

        # Create and mount detail panel
        panel = TaskDetailPanel(task_data=task)
        self.mount(panel)
        self._current_panel = panel

    def _mount_task_edit(self) -> None:
        """Mount TaskEditPanel for EDIT_TASK mode"""
        is_new = self.app.state.edit_mode_is_new
        task_data = None

        if not is_new:
            # Editing existing task
            task_id = self.app.state.selected_task_id
            if task_id is None:
                # No task selected - return to list
                self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
                return

            task_data = self.app.state.get_task_by_id(task_id)
            if task_data is None:
                # Task not found - return to list
                self.app.notify(f"Task #{task_id} not found", severity="warning")
                self.app.state.left_panel_mode = LeftPanelMode.LIST_TASKS
                return

        # Get existing tags for suggestions
        existing_tags = list(self.app.state._tag_index.keys()) if self.app.state._tag_index else []

        # Create and mount edit panel
        panel = TaskEditPanel(
            task_data=task_data,
            is_new=is_new,
            existing_tags=existing_tags
        )
        self.mount(panel)
        self._current_panel = panel

    def _mount_note_list(self) -> None:
        """Mount NoteTable for LIST_NOTES mode"""
        from textual_widgets.note_table import NoteTable

        # Check if NoteTable already exists in app
        try:
            note_table = self.app.query_one(NoteTable)
            # Reparent to this container
            self.mount(note_table)
            self._current_panel = note_table
            note_table.focus()
        except Exception:
            # Create new if not found
            note_table = NoteTable(id="note_table")
            self.mount(note_table)
            self._current_panel = note_table
            note_table.focus()

            # Update table from state
            if hasattr(self.app, 'refresh_note_table'):
                self.app.refresh_note_table()

    def _mount_note_detail(self) -> None:
        """Mount NoteDetailPanel for DETAIL_NOTE mode"""
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR

        # Get selected note
        note_id = self.app.state.selected_note_id
        if note_id is None:
            # No note selected - return to list
            self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
            return

        # Load note from repository
        repo = FileNoteRepository(DEFAULT_NOTES_DIR)
        note = repo.get(note_id)

        if note is None:
            # Note not found - return to list
            self.app.notify(f"Note not found", severity="warning")
            self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
            return

        # Create and mount detail panel
        panel = NoteDetailPanel(note_data=note)
        self.mount(panel)
        self._current_panel = panel

    def _mount_note_edit(self) -> None:
        """Mount NoteEditPanel for EDIT_NOTE mode"""
        from services.notes import FileNoteRepository
        from config import DEFAULT_NOTES_DIR

        is_new = self.app.state.edit_mode_is_new
        note_data = None

        if not is_new:
            # Editing existing note
            note_id = self.app.state.selected_note_id
            if note_id is None:
                # No note selected - return to list
                self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
                return

            # Load note from repository
            repo = FileNoteRepository(DEFAULT_NOTES_DIR)
            note_data = repo.get(note_id)

            if note_data is None:
                # Note not found - return to list
                self.app.notify(f"Note not found", severity="warning")
                self.app.state.left_panel_mode = LeftPanelMode.LIST_NOTES
                return

        # Create and mount edit panel
        panel = NoteEditPanel(
            note_data=note_data,
            is_new=is_new
        )
        self.mount(panel)
        self._current_panel = panel

    def sync_with_app_state(self) -> None:
        """
        Manually sync with app state (called after state changes)

        This ensures the container reflects the current app state mode
        """
        if hasattr(self.app, 'state') and hasattr(self.app.state, 'left_panel_mode'):
            self.current_mode = self.app.state.left_panel_mode
