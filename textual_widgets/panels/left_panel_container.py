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
    }
    """

    # Reactive - triggers panel switching
    current_mode = reactive(LeftPanelMode.LIST_TASKS)

    def __init__(self, **kwargs):
        super().__init__(**kwargs, id="left_panel_container")
        self._current_panel: Widget | None = None

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
        self._switch_to_mode(new_mode)

    def _switch_to_mode(self, mode: LeftPanelMode) -> None:
        """
        Switch the visible panel based on mode

        Args:
            mode: Target panel mode

        Process:
            1. Remove current panel (if any)
            2. Create and mount appropriate panel
            3. Focus new panel
        """
        # Remove current panel
        self._clear_current_panel()

        # Mount appropriate panel based on mode
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

    def _clear_current_panel(self) -> None:
        """Remove current panel from container"""
        if self._current_panel:
            try:
                self._current_panel.remove()
            except Exception:
                pass
            self._current_panel = None

        # Remove all children to ensure clean slate
        for child in list(self.children):
            try:
                child.remove()
            except Exception:
                pass

    def _mount_task_list(self) -> None:
        """Mount TaskTable for LIST_TASKS mode"""
        from textual_widgets.task_table import TaskTable

        # Check if TaskTable already exists in app
        try:
            task_table = self.app.query_one(TaskTable)
            # Reparent to this container
            self.mount(task_table)
            self._current_panel = task_table
            task_table.focus()
        except Exception:
            # Create new if not found
            task_table = TaskTable(id="task_table")
            self.mount(task_table)
            self._current_panel = task_table
            task_table.focus()

            # Update table from state
            self.app.refresh_table()

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
