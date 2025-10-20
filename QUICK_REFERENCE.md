# ⚡ Todo CLI - Quick Reference Guide

**Updated:** 2025-10-20

---

## 🚀 New Features Summary

### **1. Command Shortcuts** (60% faster!)
```bash
d <id>     # done <id>
u <id>     # undone <id>
r <id>     # remove <id>
e <id>     # edit <id>
s <id>     # show <id>
n          # next page
p          # prev page
t          # tags
h          # help
x          # exit
```

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

### **Task Management**
| Command | Shortcut | Usage | Example |
|---------|----------|-------|---------|
| add | - | `add` | Opens interactive form |
| edit | `e` | `edit <id>` | `e 5` or `edit 5` |
| done | `d` | `done <id> [ids...]` | `d 3` or `done 1-5` |
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
| sort | - | `sort <field>` | `sort priority` |
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

### **Information & AI**
| Command | Usage | Description |
|---------|-------|-------------|
| insights | `insights` | Comprehensive task analysis (local AI) |
| suggest | `suggest` | Smart recommendations (local AI) |
| help | `h` or `help` | Show full help |
| ? | `?` | Ask GPT (requires API key) |

### **System**
| Command | Shortcut | Usage | Description |
|---------|----------|-------|-------------|
| save | - | `save` | Save tasks to file |
| cls | - | `cls`, `clear`, or `c` | Clear and refresh |
| exit | `x` | `exit`, `quit`, or `x` | Save and exit |

---

## 💡 Pro Tips

### **Speed Up Your Workflow**
```bash
# Old way (slow)
❯ done 5
❯ done 6
❯ done 7

# New way (fast)
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

### **Shortcuts not working?**
Make sure you're typing the letter and the command together:
```bash
✅ Correct: d 5
❌ Wrong: d5 (no space)
```

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

## 🎯 Common Workflows

### **Morning Routine**
```bash
❯ insights          # Check task overview
❯ f undone          # Filter to incomplete
❯ sort priority     # Sort by priority
# Start working on top tasks
```

### **End of Day**
```bash
❯ d 10-15          # Mark completed tasks
❯ save             # Save progress
❯ insights         # Review progress
❯ x                # Exit
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
