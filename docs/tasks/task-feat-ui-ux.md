# Task: feat/ui-ux Branch - UI/UX Enhancements

**Branch:** `feat/ui-ux`
**Created:** 2025-10-28
**Status:** In Progress
**Priority:** High

## Overview

Major UI/UX improvements for the Textual interface, focusing on:
1. Panel-based editing system (replacing modals)
2. AI chat status indicators
3. Theme switching and CSS stability fixes
4. Enhanced user experience during AI interactions

## Completed Work

### Phase 1: Panel System Migration ✅
- Implemented `LeftPanelContainer` for dynamic panel switching
- Created panel modes: LIST_TASKS, DETAIL_TASK, EDIT_TASK, LIST_NOTES, DETAIL_NOTE, EDIT_NOTE
- Migrated from modal-based editing to in-place panel editing
- Vim-style editing experience in task/note areas

**Files Modified:**
- `textual_widgets/panels/left_panel_container.py` (new)
- `textual_widgets/panels/task_detail_panel.py`
- `textual_widgets/panels/task_edit_panel.py`
- `textual_widgets/panels/note_detail_panel.py`
- `textual_widgets/panels/note_edit_panel.py`
- `core/state.py` - Added `LeftPanelMode` enum

### Phase 2A: AI Chat Status Indicators ✅
**Commit:** `9240290` - feat(ai-chat): add status indicators during AI response delays

Eliminated 2-5 second "blank screen" during AI thinking/tool execution.

**Implementation:**
- Extended `AIMessage` model with `is_status: bool` field
- Added status methods to `AIChatPanel`:
  - `add_status_message(text)` - Create temporary status bubble
  - `remove_status_messages()` - Clean up all status messages
  - `update_status_message(text)` - Replace current status
- Updated `MessageBubble` to style status messages (dim, italic, no timestamp)
- Integrated 3-stage status progression into `stream_ai_response()`:
  1. "🤔 Thinking..." (worker start)
  2. "🧠 Loading AI agent..." (assistant init)
  3. "⚡ Processing request..." (before agent call)
- Status messages auto-remove on first chunk or error

**Files Modified:**
- `models/ai_message.py` (+8 lines)
- `textual_widgets/ai_chat_panel.py` (+88 lines)
- `textual_app.py` (+28 lines)

**User Benefit:**
- No more "blank screen" confusion
- Progressive feedback during AI processing
- Smooth visual transition to streaming

### Phase 2B: LangChain Save Tool ✅
**Commit:** `feat: add save_all_changes LangChain tool`

Added explicit save tool for AI agent with file name display.

**Implementation:**
- Created `save_all_changes()` tool in `core/ai_tools.py`
- Shows file name, task count, and note count
- Tool registry now has 21 total tools

**User Benefit:**
- AI can explicitly save when user asks
- Clear confirmation of what was saved

### Theme CSS Switching & Fixes 🔧
**Status:** In Progress

Fixed CSS parsing issues and implemented theme switching system.

**Problem:**
- CSS parsing errors causing app crashes
- Need for theme switching capability (dark/light modes)
- Textual CSS caching issues (per CLAUDE.md guidelines)

**Implementation:**
- Created `styles/theme-dark.tcss` - Dark theme variant
- Created `styles/theme-light.tcss` - Light theme variant
- Created `styles/theme-default-safe.tcss` - Safe fallback theme
- Backup of broken CSS: `styles/app_broken_backup.tcss`
- Following CLAUDE.md pattern: inline CSS only, no external CSS_PATH

**Files:**
- `styles/theme-dark.tcss` (5192 bytes)
- `styles/theme-light.tcss` (5351 bytes)
- `styles/theme-default-safe.tcss` (2590 bytes)
- `styles/app_broken_backup.tcss` (broken version backup)

**Next Steps:**
- [ ] Integrate theme switching into main app
- [ ] Add theme toggle command/keybinding
- [ ] Test all themes for visual consistency
- [ ] Document theme switching in user guide
- [ ] Consider adding theme preference to settings.json

**User Benefit:**
- Multiple theme options (dark/light)
- Stable CSS without parsing errors
- Better visual customization

## In Progress

### Theme CSS Integration
Integrate theme switching functionality into main application.

**Current State:**
- Theme files created (dark, light, default-safe)
- Need to wire up theme switching logic
- Need to add user-facing commands

**Tasks:**
- [ ] Add theme loading logic to `textual_app.py`
- [ ] Create theme toggle command (e.g., `theme dark`, `theme light`)
- [ ] Add keybinding for quick theme switching (e.g., Ctrl+T)
- [ ] Save theme preference to `~/.todo_cli_settings.json`
- [ ] Test theme switching without app restart

### Phase 2B: Tool Execution Indicators
Show real-time tool usage during AI operations.

**Plan:**
- Parse LangChain agent logs during execution
- Show "🔧 Using tool: add_task" status messages
- Update status dynamically during tool execution
- Handle multi-tool scenarios

**Estimated Time:** 45 minutes

**Files to Modify:**
- `textual_app.py` - Enhanced streaming callback
- `core/ai_agent.py` - Tool event callbacks

## Planned Work

### Phase 2C: Polish & Animations
**Estimated Time:** 15 minutes

- CSS fade transitions for status messages
- Pulsing dot animation for "Thinking..."
- Visual polish for smooth UX

**Files to Modify:**
- `textual_app.py` - CSS additions
- `textual_widgets/ai_chat_panel.py` - Animation classes

### Phase 3: Additional UX Enhancements (TBD)
- Keyboard shortcut improvements
- Better focus management
- Enhanced error messages
- Loading states for long operations

## Testing Requirements

### Manual Testing
- [ ] Test status indicators with AI queries
- [ ] Verify status messages disappear on streaming start
- [ ] Test status messages on error scenarios
- [ ] Verify panel switching in all modes
- [ ] Test task/note editing in panels
- [ ] Test save_all_changes tool via AI
- [ ] Test theme switching (dark/light/default)
- [ ] Verify theme persists across app restarts
- [ ] Test CSS rendering in all themes
- [ ] Verify no CSS parsing errors on theme load

### Automated Testing
- [ ] Add tests for AIMessage.is_status field
- [ ] Add tests for status message methods
- [ ] Add tests for panel mode switching
- [ ] Integration tests for streaming callbacks
- [ ] Add tests for theme loading/switching
- [ ] Add tests for theme preference persistence

## Documentation Updates Needed

- [ ] Update USAGE_GUIDE.md with panel editing workflow
- [ ] Document AI status indicators in TEXTUAL_AI_CHAT.md
- [ ] Add theme switching documentation to USAGE_GUIDE.md
- [ ] Document theme files in TEXTUAL_TROUBLESHOOTING.md
- [ ] Update CHANGELOG.md for release
- [ ] Add screenshots/GIFs of new UX (including themes)

## Related Issues

- Fixes blank screen during AI thinking (reported by user)
- Improves panel-based editing UX
- Enhances AI transparency and feedback
- Fixes CSS parsing errors causing app crashes
- Adds theme customization for better user experience

## Notes

- Status messages are ephemeral (`is_status=True`) and don't persist to history
- All UI updates from worker thread use `call_from_thread()` for thread safety
- Panel system eliminates modal-related issues on certain terminals
- Follow CLAUDE.md patterns for Textual reserved attributes
- **CSS Pattern:** Use inline CSS in `textual_app.py` only, avoid external `.tcss` files (per CLAUDE.md)
- Theme files stored in `styles/` for reference/backup but loaded inline
- Theme preference should persist in `~/.todo_cli_settings.json`

## Merge Strategy

1. Complete Theme CSS Integration
2. Complete Phase 2B (Tool Execution Indicators) and 2C (Polish & Animations)
3. Run full test suite (including theme tests)
4. Manual testing session (all features + theme switching)
5. Update documentation (USAGE_GUIDE.md, CHANGELOG.md)
6. Create PR to main branch
7. Squash commits if needed (or keep detailed history)

## References

- `CLAUDE.md` - Project patterns and conventions
- `docs/technical/TEXTUAL_AI_CHAT.md` - AI chat implementation
- `docs/technical/TEXTUAL_TROUBLESHOOTING.md` - Common issues
- Previous feature branch: `task-feature-notes`
