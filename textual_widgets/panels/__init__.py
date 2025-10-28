"""
Panel widgets for vim-style inline editing
Replaces modal-based UI with persistent panels
"""

from .task_detail_panel import TaskDetailPanel
from .task_edit_panel import TaskEditPanel
from .note_detail_panel import NoteDetailPanel
from .note_edit_panel import NoteEditPanel
from .left_panel_container import LeftPanelContainer

__all__ = [
    "TaskDetailPanel",
    "TaskEditPanel",
    "NoteDetailPanel",
    "NoteEditPanel",
    "LeftPanelContainer",
]
