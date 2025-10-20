# 📋 Todo CLI - Interactive Task Manager

A modern, feature-rich command-line task manager with an interactive UI inspired by Claude Code.

## ✨ Features

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

# Run the application
python main.py
```

### Requirements
- Python 3.8+
- Dependencies listed in `requirements.txt`

## 📖 Usage Guide

### Opening the Command Palette
Simply type `/` at the prompt to see all available commands:

```
❯ Sort: priority | Page: 1 | View: compact › /
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

sort priority          # Sort by priority (default)
sort id                # Sort by task ID
sort name              # Sort alphabetically
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
📄 Page 1/2 | 👁️ 20/29 showing | 🎨 compact | ↕️ priority
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

## 🎯 Tips & Tricks

1. **Use `/` for discovery** - If you forget a command, just type `/`
2. **Clear with ESC** - Press ESC to clear current input instantly
3. **Quick refresh** - Type `cls` or `c` to clear and refresh the screen
4. **Filter by tag** - Organize work by project: `filter tag:project-name`
5. **Regular insights** - Run `insights` daily to stay on track
6. **Auto-completion** - Press `Tab` while typing commands
7. **Inline editing** - Type `edit 5` to quickly modify task #5

## 🐛 Troubleshooting

### Command not found
- Type `/` to see all available commands
- Use `Tab` for auto-completion
- Type `help` for the full command list

### Tasks not saving
- Ensure you have write permissions in the directory
- Check that `tasks.json` is not locked by another program
- The app auto-saves on exit

### No insights showing
- Add some tasks first with `add` or `/`
- Insights require at least one task to analyze

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📝 License

[Your License Here]

---

**Built with:**
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Interactive prompts and completion
- [OpenAI API](https://openai.com/) - Optional GPT integration

**Recent Improvements:**
- ✅ Crash-proof commands with helpful error messages
- ✅ ESC key to clear input instantly
- ✅ `cls` command for quick refresh
- ✅ Transparent dropdown background
- ✅ Reorganized two-line status display
- ✅ Windows CP1252 encoding support 
