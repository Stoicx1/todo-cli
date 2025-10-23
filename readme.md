# 📋 Todo CLI - Interactive Task Manager

A modern, feature-rich command-line task manager with dual UI support: **Textual** (modern reactive TUI with AI chat) and **Rich** (classic REPL interface).

## ✨ Features

### 🚀 Dual UI Support

**Textual UI (Default)** - Modern reactive TUI with AI chat sidebar:
- Zero flicker, smooth 5ms updates with virtual DOM diffing
- Persistent AI chat sidebar with conversation history
- Context-aware follow-up questions (remembers last 20 messages)
- Real-time streaming AI responses with thread-safe updates 🆕
- Split-screen layout: 70% tasks, 30% AI chat
- Keyboard shortcuts: `?` (Ask AI), `Ctrl+A` (Toggle AI), `i` (Insights)
- Perfect Windows compatibility, handles 1000+ tasks smoothly
- Performance-optimized filter caching (95%+ cache hit rate) 🆕
- Robust error handling with graceful degradation 🆕
- Command input visible by default (no more confusion!) 🆕

**Rich UI (Classic)** - Traditional REPL interface:
- Available with `--ui rich` flag
- Simpler, SSH-friendly interface
- One-time AI answer panels
- Same task management features
- Backward compatible with existing workflows

### 🎯 Interactive Command Palette
- Type `/` to open an interactive menu of all available commands
- Categorized commands with icons and descriptions
- Fuzzy search and arrow key navigation
- Context-aware parameter prompts

### 🤖 Local AI Suggestions (No API Required!)
- Type `insights` for comprehensive task analysis
- Type `suggest` for smart recommendations
- Priority distribution visualization
- Tag-based analytics
- Automatic task prioritization suggestions

### 💅 Claude Code-Style UI
- Enhanced prompt line showing current context (filter, sort, page, view)
- Beautiful color-coded task display
- Auto-completion for all commands
- Real-time status updates

### ⚡ Quick Actions
- Type `qa` or `quick` for rapid task completion
- Inline forms for adding and editing tasks
- Keyboard shortcuts for common operations

## 🚀 Getting Started

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd todo-cli

# Install dependencies
pip install -r requirements.txt

# Run the application (Textual UI - default)
python main.py

# Or explicitly choose UI framework
python main.py --ui textual  # Modern UI with AI chat
python main.py --ui rich     # Classic REPL UI
```

### Requirements
- Python 3.8+
- Dependencies listed in `requirements.txt`
- For AI features: OpenAI API key in `.env` file (optional - local insights work without it!)

### Quick Start

**Textual UI (Recommended):**
1. Run `python main.py`
2. Press `?` to ask AI a question
3. Press `Ctrl+K` to enter task commands
4. Press `i` for local insights (no API needed)
5. See footer for keyboard shortcuts

**Rich UI (Classic):**
1. Run `python main.py --ui rich`
2. Type `/` to open command palette
3. Type `?` for one-time AI answers
4. Type `help` for command list

## 📖 Usage Guide

### Opening the Command Palette
Simply type `/` at the prompt to see all available commands:

```
❯ Sort: priority (ASC) | Page: 1 | View: compact › /
```

This will show an interactive menu with categories:
- 📝 Task Management
- 👁️ View Controls
- 🧭 Navigation
- 🔧 Filters & Sort
- ℹ️ Information
- 🤖 AI Assistant
- ⚙️ System

### Using Local AI Insights

```bash
# Get comprehensive task analysis
insights

# Get quick suggestions
suggest
```

Example insights output:
```
📊 Task Insights
────────────────────────────────────────
Total Tasks:     31
Completed:       15 (48.4%)
Incomplete:      16

Priority Distribution (Incomplete Tasks):
  🔴 High   [ 3]: ███
  🟡 Medium [ 8]: ████████
  🟢 Low    [ 5]: █████

💡 Smart Suggestions:
  📊 Most active tag: 'psdc' (16 tasks)
  👍 Everything looks good! Keep up the great work.

⚡ Recommended Next Tasks:
  1. 🔴 [6] PSDC PAA1 – Merge Local HMIs into Central Interface
  2. 🔴 [7] PSDC – Complete HMI Translations
  3. 🟡 [9] PSDC FA040 – Conditional Unload Measurement
```

### Core Commands

#### Task Management
```bash
add                    # Open inline form to add a task
edit <id>              # Edit an existing task
done <id>              # Mark task as complete
undone <id>            # Mark task as incomplete
remove <id>            # Delete a task
show <id>              # Show full task details
```

#### View Controls
```bash
view compact           # Show 20 tasks per page
view detail            # Show 10 tasks per page with details
next                   # Go to next page
prev                   # Go to previous page
```

#### Filtering & Sorting
```bash
filter done            # Show only completed tasks
filter undone          # Show only incomplete tasks
filter tag:<name>      # Filter by specific tag
filter none            # Clear filters

sort priority [asc|desc]   # Sort by priority (1→3 asc, 3→1 desc)
sort id [asc|desc]         # Sort by task ID (asc = oldest first)
sort name [asc|desc]       # Sort alphabetically (asc = A→Z)
sort order [asc|desc]      # Set sort order without changing field
sort                       # Quick toggle (flip asc↔desc)
```

#### Information
```bash
tags                   # List all unique tags
insights               # Show comprehensive task analysis
suggest                # Get smart recommendations
help                   # Show full command list
```

#### System Commands
```bash
cls                    # Clear screen and refresh dashboard
clear                  # Same as cls
c                      # Shortcut for cls
exit                   # Save and exit
quit                   # Same as exit
/                      # Open command palette
```

## 🎨 UI Features

### Two-Line Status Display

The interface shows status in two clean lines:

**Line 1** (Navigation & Context):
```
📄 Page 1/2 | 👁️ 20/29 showing | 🎨 compact | ⬆️ priority (asc)
```

**Line 2** (Statistics):
```
📊 29 tasks | ✅ 15 done | ⏳ 14 todo
```

**Prompt Line** (where you type):
```
❯ Type / for commands ›
```

### Auto-completion
Start typing any command and press `Tab` to auto-complete:
```
❯ fi<Tab>  →  filter
```

### Color Coding
- 🔴 High Priority (1)
- 🟡 Medium Priority (2)
- 🟢 Low Priority (3)
- ✅ Completed tasks (green checkmark)
- ❌ Incomplete tasks (red X)

## 🔧 Configuration

### Task JSON Structure
Tasks are stored in `tasks.json`:

```json
{
  "id": 1,
  "name": "Task Name",
  "comment": "Short comment",
  "description": "Detailed description",
  "priority": 1,
  "tag": "project-name",
  "done": false
}
```

### OpenAI Integration (Optional)
To use the GPT assistant feature (`?` command), create a `.env` file:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

**Note:** The local AI insights (`insights` and `suggest` commands) work without any API key!

## 📊 Local AI Features

The local AI system provides intelligent insights without requiring any external API:

### Task Analysis
- Completion rate tracking
- Priority distribution visualization
- Tag-based organization
- Workload assessment

### Smart Suggestions
- Priority-based recommendations
- Workload balancing tips
- Tag utilization insights
- Next task recommendations

### Quick Stats
View at-a-glance statistics in the dashboard footer.

## 💬 Textual AI Chat (New!)

The Textual UI includes a persistent AI chat sidebar with advanced features:

### Conversation Sidebar
- **Persistent History**: All conversations saved across sessions
- **Context-Aware**: AI remembers last 20 messages for follow-up questions
- **Real-time Streaming**: Watch AI type responses progressively
- **Scrollable Panel**: Access full conversation history
- **Timestamps**: Every message includes time stamp

### How to Use
```bash
# Ask AI a question
? <enter your question>

# Example conversation:
? "What are my high priority tasks?"
<AI lists priority 1 tasks>

? "Show details for task 6"
<AI remembers context from previous question>

# Toggle AI panel visibility
Ctrl+A

# Clear conversation history
Ctrl+Shift+C

# Navigate previous questions
↑ / ↓ in AI input field
```

### Keyboard Shortcuts
- `?` - Focus AI input, ask a question
- `Ctrl+A` - Toggle AI panel visibility
- `Ctrl+Shift+C` - Clear conversation history
- `i` - Local insights (no API required)
- `Esc` - Clear current input
- `↑` / `↓` - Navigate command history

### Chat Features
- **Follow-up Questions**: "Tell me more about task 5"
- **Task Summaries**: "Summarize my completed tasks this week"
- **Prioritization Help**: "What should I focus on today?"
- **Filtering Advice**: "Show me all PSDC tasks"
- **Formatting Requests**: "Display my tasks as a timeline"

### Conversation Storage
- **Location**: `~/.todo_cli_ai_history.json`
- **Format**: JSON with role, content, timestamp, token count
- **Persistence**: Survives app restarts
- **Safety**: Uses `SafeFileManager` (atomic writes, backups, file locking)
- **Management**: Clear with `Ctrl+Shift+C` or delete file manually

### Performance
- **First Token**: ~500ms (network + model warmup)
- **Streaming**: ~50ms per token (~20 tokens/sec)
- **Context Size**: Last 20 messages (~2,000-4,000 tokens)
- **UI Updates**: 2-5ms per chunk (smooth animation)
- **File Save**: 15-25ms (atomic write with locking)

## 🎯 Tips & Tricks

### Textual UI (Modern)
1. **AI Follow-ups** - Press `?` and ask follow-up questions; AI remembers context
2. **Quick Insights** - Press `i` for local AI insights (no API required)
3. **Toggle AI Panel** - Press `Ctrl+A` to hide AI sidebar for more task space
4. **Clear AI History** - Press `Ctrl+Shift+C` to start fresh conversation
5. **Command History** - Use `↑`/`↓` in AI input to recall previous questions
6. **Keyboard First** - Check footer for all keyboard shortcuts
7. **Split Screen** - View tasks and AI chat simultaneously

### Rich UI (Classic)
1. **Use `/` for discovery** - If you forget a command, just type `/`
2. **Clear with ESC** - Press ESC to clear current input instantly
3. **Quick refresh** - Type `cls` or `c` to clear and refresh the screen
4. **Auto-completion** - Press `Tab` while typing commands

### Both UIs
1. **Filter by tag** - Organize work by project: `filter tag:project-name`
2. **Advanced filters** - Use operators: `f priority=1 status=undone`
3. **Command shortcuts** - Use single letters: `a` (add), `e` (edit), `x` (done)
4. **Regular insights** - Run `insights` or `i` daily to stay on track
5. **Inline editing** - Type `edit 5` to quickly modify task #5
6. **Multi-tag filters** - Use `+` for AND: `f tag=psdc+webasto`

## 💾 Settings & Preferences

The app remembers your view and sorting preferences between runs.

- Stored at: `~/.todo_cli_settings.json`
- Persisted keys:
  - `sort` (`priority` | `id` | `name`)
  - `sort_order` (`asc` | `desc`)
  - `view_mode` (`compact` | `detail`)
  - `filter` (e.g., `none`, `done`, `undone`, `tag:psdc`)

Notes:
- Saved automatically on save/exit; loaded on startup.
- Best-effort: errors are ignored to avoid disrupting usage.
- Safe to delete; a fresh file is created next run.

## 🐛 Troubleshooting

### Textual UI Issues

**Textual UI not starting:**
- Run: `pip install textual`
- Or reinstall: `pip install -r requirements.txt`
- Fallback: Use Rich UI with `python main.py --ui rich`

**AI chat not working:**
- Check `.env` file has `OPENAI_API_KEY=your_key_here`
- Verify API key is valid
- Check internet connection
- Use local insights instead: Press `i` (no API required)

**Conversation not persisting:**
- Check file exists: `~/.todo_cli_ai_history.json`
- Check file permissions: Should be readable/writable
- Look for error messages in console output

**Layout issues (AI panel too wide/narrow):**
- Terminal must be at least 100 columns wide
- Check: `tput cols` (should show ≥100)
- Adjust in `styles/app.tcss`: `#task_container { width: 60%; }`

**Windows rendering issues:**
- Use Windows Terminal (not CMD.exe)
- Update Windows Terminal to latest version
- Enable UTF-8 support in terminal settings

### General Issues

**Command not found:**
- Type `/` to see all available commands (Rich UI)
- Type `help` for the full command list
- Use `Tab` for auto-completion

**Tasks not saving:**
- Ensure you have write permissions in the directory
- Check that `tasks.json` is not locked by another program
- The app auto-saves on exit

**No insights showing:**
- Add some tasks first with `add` or `/`
- Insights require at least one task to analyze

**Performance issues:**
- Textual UI: Handles 1000+ tasks smoothly
- Rich UI: Use `filter` to reduce visible tasks
- Clear old AI conversations: `Ctrl+Shift+C` (Textual) or delete `~/.todo_cli_ai_history.json`

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📝 License

[Your License Here]

---

**Built with:**
- [Textual](https://github.com/Textualize/textual) - Modern reactive TUI framework
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Interactive prompts and completion
- [OpenAI API](https://openai.com/) - Optional GPT integration
- [Questionary](https://github.com/tmbo/questionary) - Interactive forms

**Recent Improvements:**

**v2.1.0 - October 2025 - Stability & Performance Update** 🆕
- ✅ **FIXED**: Command prompt visibility (now visible by default - no more confusion!)
- ✅ **FIXED**: Detail view task selection (edit/delete now targets correct task)
- ✅ **FIXED**: Event bubbling (commands execute exactly once)
- ✅ **FIXED**: AI streaming crashes (thread-safe worker pattern)
- ✅ **FIXED**: AI chat panel crashes on multiple messages
- ✅ **NEW**: Filter caching optimization (95%+ cache hit rate, 50-100ms → <1ms)
- ✅ **NEW**: Comprehensive error handling with logging and user notifications
- ✅ **NEW**: AI input validation (5000 char limit, control character sanitization)
- ✅ **NEW**: Command aliases consolidation (single source of truth)
- ✅ **NEW**: Textual console integration (cleaner architecture)
- 📄 **See:** `BUGFIX_COMPREHENSIVE_TEXTUAL_2025.md` for complete technical details

**v2.0.0 - Textual UI Launch:**
- ✅ Textual UI as default with AI chat sidebar
- ✅ Persistent conversation history with context-aware AI
- ✅ Real-time streaming AI responses
- ✅ Split-screen layout (70% tasks, 30% AI)
- ✅ Keyboard shortcuts: `?`, `Ctrl+A`, `Ctrl+Shift+C`, `i`
- ✅ Zero flicker, 10x faster rendering (5ms vs 58ms)
- ✅ Perfect Windows compatibility
- ✅ Dual UI support: `--ui textual` or `--ui rich`
- ✅ Advanced filtering with operators (`=`, `!=`, `>=`, `<=`)
- ✅ Command shortcuts (single-letter aliases: `a`, `e`, `x`/`d`, `u`, `r`, `q`)
- ✅ Professional bordered status panel
- ✅ Crash-proof commands with helpful error messages
- ✅ ESC key to clear input instantly
- ✅ Windows CP1252 encoding support

**Documentation:**
- `BUGFIX_COMPREHENSIVE_TEXTUAL_2025.md` - Complete bugfix documentation (Oct 2025) 🆕
- `MIGRATION_GUIDE.md` - Switching from Rich to Textual UI
- `TEXTUAL_AI_CHAT.md` - Technical AI chat documentation
- `TEXTUAL_TROUBLESHOOTING.md` - Textual CSS caching and resolved issues
- `TEXTUAL_QUICKSTART.md` - Quick start guide for Textual UI
- `USAGE_GUIDE.md` - Complete command reference
- `QUICK_REFERENCE.md` - One-page cheat sheet
- `CLAUDE.md` - Developer/architecture documentation 
