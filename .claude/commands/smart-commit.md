# Smart Commit - Review → Confirm → Execute Workflow

**CRITICAL: This is a TWO-PHASE workflow. Do NOT execute ANY changes in Phase 1!**

## 🔍 PHASE 1: COMPREHENSIVE REVIEW & PLANNING (Read-Only)

**DO NOT make any changes yet - only read and analyze!**

### Step 1: Review Code Changes
1. Run `git status` - see what changed
2. Run `git diff --stat` - understand scope of changes
3. Identify the type of work done (feat/fix/refactor/perf/docs/test/chore)

### Step 2: Comprehensive Documentation Review
Check EVERY documentation file for needed updates:

**Active Documentation (`docs/`):**
- `docs/status/STATUS.md` - Does it need latest commit added to Recent Changes?
- `docs/status/e2e-status.md` - Did test status change?
- `docs/tasks/` - Are there completed tasks that should be archived to `docs/tasks-archive/`?
- `docs/architecture/` - Do architectural changes need documentation?
- `docs/testing/` - Were testing patterns or rules updated?
- `docs/guides/` - Do workflow guides need updates?
- `docs/summaries/` - Does a significant feature need a summary document?

**Root Documentation:**
- `CLAUDE.md` - Did development rules or commands change?
- `README.md` - Do setup instructions need updates?

### Step 3: Check for Cleanup
Look for temporary/debug files to remove:
- `CON` (Windows reserved name - causes git errors)
- `.DS_Store`, `Thumbs.db`
- `*.log` files (unless intentional)
- `temp-*` files
- Any other debug artifacts

### Step 4: Draft Comprehensive Plan

Create a detailed plan with:

**A. Tasks to Archive**
- List specific task files: `docs/tasks/task-xxx.md` → `docs/tasks-archive/`
- Note any monitoring items to add to STATUS.md

**B. STATUS.md Updates**
- Add commit hash and description to Recent Changes table
- Update relevant sections (Build Status, Test Coverage, Performance, etc.)
- Mark completed items with ✅
- Update "Last Updated" date

**C. Feature Summary** (if applicable)
- For significant features, draft `docs/summaries/summary-<feature>.md`
- Include: problem solved, implementation, technical details

**D. Other Documentation Updates**
- List any architecture, testing, or guide updates needed

**E. Cleanup Actions**
- List files to delete

**F. Commit Message**
Draft comprehensive commit following CLAUDE.md format:
```
<type>: <concise description>

- <Category 1>:
  - <specific change>
  - <specific change>

- <Category 2>:
  - <specific change>

- Documentation:
  - <doc updates>
```

Types: `feat` | `fix` | `refactor` | `perf` | `docs` | `test` | `chore`

**IMPORTANT:** Do NOT include Claude Code attribution or co-author lines in commit messages.

### Step 5: Present Plan & WAIT FOR APPROVAL

Use the `ExitPlanMode` tool to present the complete plan.

**⏸️ STOP HERE AND WAIT FOR USER APPROVAL!**

Do NOT proceed to Phase 2 until the user explicitly approves.

---

## ✅ PHASE 2: EXECUTION (Only After User Confirms)

**Only proceed when user has reviewed and approved the plan!**

### Execute in Order:

1. **Archive Tasks**
   - Move completed task files to `docs/tasks-archive/`
   - Add monitoring notes to STATUS.md if needed

2. **Update STATUS.md**
   - Add commit to Recent Changes
   - Update relevant status sections
   - Mark completed items
   - Update last modified date

3. **Create Feature Summary** (if planned)
   - Write `docs/summaries/summary-<feature>.md`

4. **Update Other Docs** (if planned)
   - Architecture, testing, guides as identified

5. **Cleanup**
   - Remove temporary/debug files identified in plan

6. **Git Operations**
   - Stage all changes: `git add .`
   - Verify staged files: `git status`
   - Create commit with drafted message (use HEREDOC for formatting)
   - Show final `git status` to confirm

7. **Summary**
   - Display commit hash
   - List files committed
   - Note any follow-up actions needed

## Additional Context

$ARGUMENTS

---

**Remember**: The key to this workflow is the TWO-PHASE approach - thorough review FIRST, then execute ONLY after approval!
