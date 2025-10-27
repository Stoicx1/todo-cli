# ⚡ Todo CLI - Quick Reference Guide

**Updated:** 2025-10-23 (October 2025 Update)

---

## 🚀 New Features Summary

### **1. Command Shortcuts** (60% faster!) - Updated Oct 2025
```bash
# Task Operations (MODE-AWARE)
a          # add (tasks mode: task form | notes mode: note editor)
e <id>     # edit (tasks mode: edit task | notes mode: edit note)
x <id>     # done <id> (x OR d both work!)
d <id>     # done <id> (d OR x both work!)
u <id>     # undone <id>
r <id>     # remove <id> (changed from 'd' → 'r' for clarity)
s <id>     # show <id>

# Navigation
n          # next page
p          # prev page
v          # toggle view (compact/detail)

# Filtering & Info
f          # filter (use with expressions)
t          # tags
h          # help

# System
q          # quit/exit (changed from 'x' → 'q')
```

**Oct 2025 Changes:**
- ✅ Both `x` and `d` now mark tasks done
- ✅ Delete changed from `d` to `r` for clarity
- ✅ Exit/quit changed from `x` to `q`
- ✅ Added `a` shortcut for add

### **2. Bulk Operations**
```bash
done 1 2 3        # Mark multiple tasks
done 1-5          # Mark range
done 1,3,5-8      # Mixed format
undone 1-10       # Unmark range
remove 20-30      # Remove range
```

### **3. Multiple Tags** (up to 3)
```bash
# Tasks can now have up to 3 tags
Task: ✗ Implement API     Tags: backend, api, urgent
```

### **4. Better Visual Design**
- ✅ Status in task name: `✓ Task` or `✗ Task`
- 🔴 Priority icons: `🔴 HIGH`, `🟡 MED`, `🟢 LOW`
- 📋 Clean table (no heavy borders)
- 🎨 Subtle row shading (easier on eyes)

### **5. Manual Save**
```bash
save   # Save tasks without exiting
```

---

## 📖 Command Reference

### **Task Management** (Updated Oct 2025)
| Command | Shortcut | Usage | Example |
|---------|----------|-------|---------|
| add | `a` | `add` | **Mode-aware**: Opens task form or note editor |
| edit | `e` | `edit <id>` | **Mode-aware**: Edits task or note |
| done | `x` / `d` | `done <id> [ids...]` | `x 3` or `d 1-5` (both work!) |
| undone | `u` | `undone <id> [ids...]` | `u 3` or `undone 1 2 3` |
| remove | `r` | `remove <id> [ids...]` | `r 10` or `remove 1-5,8` |
| show | `s` | `show <id>` | `s 5` |

### **Navigation**
| Command | Shortcut | Usage |
|---------|----------|-------|
| next | `n` | Go to next page |
| prev | `p` | Go to previous page |
| view compact | - | Show 20 tasks/page |
| view detail | - | Show 10 tasks/page with details |

### **Filtering & Sorting**
| Command | Shortcut | Usage | Example |
|---------|----------|-------|---------|
| filter | `f` | `filter <type>` | `filter done` |
| sort | `so` | `sort <field> [asc|desc]` | `sort priority desc` |
| tags | `t` | List all tags | `t` or `tags` |

**Filter Types:**
- `done` - Show completed tasks
- `undone` - Show incomplete tasks
- `tag:<name>` - Filter by tag
- `none` - Clear filters

**Sort Fields:**
- `priority` - Sort by priority (1=high, 3=low)
- `id` - Sort by task ID
- `name` - Sort alphabetically
**Order:**
- `asc` — ascending (default)
- `desc` — descending
- Examples: `sort name desc`, `sort order asc`, `sort` (toggle)

### **Information & AI**
| Command | Usage | Description |
|---------|-------|-------------|
| insights | `insights` | Comprehensive task analysis (local AI) |
| suggest | `suggest` | Smart recommendations (local AI) |
| help | `h` or `help` | Show full help |
| ? | `?` | Ask GPT (requires API key) |

### **System** (Updated Oct 2025)
| Command | Shortcut | Usage | Description |
|---------|----------|-------|-------------|
| save | - | `save` | Save tasks to file |
| cls | `c` | `cls`, `clear`, or `c` | Clear and refresh |
| exit | `q` | `exit`, `quit`, or `q` | Save and exit |
| version | - | `python main.py --version` | Show CLI version |

### **Settings**
- Preferences saved to `~/.todo_cli_settings.json`
- Persisted: sort, sort_order, view_mode, filter

---

## 💡 Pro Tips

### **Speed Up Your Workflow** (Oct 2025)
```bash
# Old way (slow)
❯ done 5
❯ done 6
❯ done 7

# New way (fast) - use x or d
❯ x 5-7
# OR
❯ d 5-7
```

### **Batch Processing**
```bash
# Complete an entire sprint
❯ done 10-20

# Clean up old tasks
❯ remove 1,3,5,7,9,11

# Reopen tasks for review
❯ undone 15-18
```

### **Quick Navigation**
```bash
# Old way
❯ next
❯ next
❯ next

# New way
❯ n
❯ n
❯ n
```

### **Tag Multiple Items**
When adding tasks, separate tags with commas:
```bash
❯ add "Deploy to production" "" "" 1 "devops,backend,urgent"
```

Result:
```
5    ✗ Deploy to production    devops, backend, urgent    🔴 HIGH
```

---

## 🎨 Visual Guide

### **Table Layout (New)**
```
ID   Task                          Tags            Priority
──────────────────────────────────────────────────────────
3    ✓ PSDC FA090 PCBs            psdc, work      🔴 HIGH
5    ✗ Fix authentication          work, urgent    🔴 HIGH
12   ✗ Update docs                docs            🟡 MED
```

**Key:**
- `✓` = Done
- `✗` = Not done
- `🔴 HIGH` = Priority 1
- `🟡 MED` = Priority 2
- `🟢 LOW` = Priority 3

### **Compact vs Detail View**

**Compact (20/page):**
```
3    ✓ PSDC FA090 PCBs    psdc    🔴 HIGH
```

**Detail (10/page):**
```
3    ✓ PSDC FA090 PCBs          psdc    🔴 HIGH
       → Urgent: needs testing
         Full description here with more details
```

---

## 🐛 Troubleshooting

### **Emojis not showing?**
Your terminal uses CP1252 encoding. The app automatically falls back to ASCII:
- `✓` → `Y`
- `✗` → `N`
- `🔴 HIGH` → `! HIGH`
- `🟡 MED` → `· MED`
- `🟢 LOW` → `- LOW`

### **Shortcuts not working?** (Updated Oct 2025)
Make sure you're typing the letter and space, then the argument:
```bash
✅ Correct: x 5    (mark done)
✅ Correct: d 5    (mark done - both work!)
✅ Correct: r 5    (remove)
✅ Correct: q      (quit)
❌ Wrong: x5       (no space)
❌ Wrong: d5       (no space)
```

**Note:** Both `x` and `d` mark tasks as done. Use whichever you prefer!

### **Bulk operations failing?**
Check your syntax:
```bash
✅ Correct: done 1-5      (range with hyphen)
✅ Correct: done 1,3,5    (comma-separated)
✅ Correct: done 1 2 3    (space-separated)
❌ Wrong: done 1..5       (two dots)
❌ Wrong: done 1~5        (tilde)
```

---

## 📊 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Show command palette |
| `↑` / `↓` | Navigate history |
| `Tab` | Auto-complete |
| `Esc` | Clear input |
| `Ctrl+C` | Exit (will prompt to save) |

---

## 🔄 Mode-Aware Commands (Oct 2025)

The `add` and `edit` commands automatically adapt based on your current mode:

**Tasks Mode** (default):
- `a` or `add` → Opens task add form
- `e` or `edit 5` → Opens task edit form

**Notes Mode** (press `m` to switch):
- `a` or `add` → Opens note editor ("Create Note")
- `e` or `edit abc123` → Opens note editor ("Edit Note")

**Toggle modes:** Press `m` key or type `mode notes` / `mode tasks`

---

## 🎯 Common Workflows

### **Morning Routine**
```bash
❯ insights          # Check task overview
❯ f undone          # Filter to incomplete
❯ sort priority     # Sort by priority
❯ sort name desc    # Z→A
# Start working on top tasks
```

### **End of Day** (Updated Oct 2025)
```bash
❯ x 10-15          # Mark completed tasks (or use 'd')
❯ save             # Save progress
❯ insights         # Review progress
❯ q                # Exit (updated from 'x')
```

### **Sprint Planning**
```bash
❯ filter tag:sprint-5   # View sprint tasks
❯ insights              # Analyze sprint
❯ suggest               # Get recommendations
```

### **Bulk Cleanup**
```bash
❯ filter done           # Show completed
❯ remove 1-50           # Remove old completed tasks
❯ filter none           # Clear filter
```

---

## 📚 Resources

- **Full Documentation:** `readme.md`
- **Usage Guide:** `USAGE_GUIDE.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY.md`
- **In-App Help:** Type `help` or `h`
- **Command Palette:** Type `/`

---

**Need help?** Type `/` to see all available commands!

## Age
- Sort: sort age [asc|desc] (asc=youngest first)
- Filter: ge>=3d, ge<=2h, ge>=30m`n- Column: ID | Age | Priority | Tags | Task

---

## Notes (Offline)
Commands
```bash
mode notes                 # Switch to notes list
notes [task_id|query]      # Show notes for task or search; paged (next/prev)
notes clear                # Clear notes filters
note new --title "..." [--task 12] [--tag x]
note edit <note_id>        # Edit by id prefix
note link <note_id> <task> # Link to task / unlink
note unlink <note_id> <task>
note delete <note_id>      # Delete by id prefix
note duplicate <note_id> [--title "..."] [--task 12]
```

Shortcuts
- Textual: m toggle mode, Enter open, Ctrl+E edit, Shift+N quick, Ctrl+N new, Ctrl+L link, Ctrl+U unlink, Ctrl+D duplicate, Delete remove
- Rich: Ctrl+N new (selected task), Ctrl+O open latest (selected task)

---

## AI + Notes (Cheat Sheet)
Examples
```bash
? create a note "Design log" linked to task 12
? search notes "webasto" and link the first to task 3
? get note details abcd1234
? convert note abcd1234 into a task with priority 1 tags backend,api
? open note abcd1234 in editor
```
Tips
- Prefer notes for long text; use task comment for short context
- Edit tags with +tag to add and -tag to remove
