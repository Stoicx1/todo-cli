# Task Sync Implementation Plan

## Overview

This document outlines the strategy for implementing login and sync functionality between local `tasks.json` and Supabase PostgreSQL database.

**Target Architecture**: Local-First with Cloud Backup
- **Use Case**: Hybrid (single user multi-device → future collaboration)
- **Offline Support**: Critical (must work fully offline)
- **Auth Model**: Start anonymous, upgrade to permanent account
- **Conflict Resolution**: Start simple (LWW), migrate to CRDT when collaboration needed

---

## Architecture Principles

### Source of Truth Strategy

**Local-First Approach:**
- `tasks.json` is the PRIMARY source of truth
- Supabase PostgreSQL is the SYNC backend (not the primary database)
- UI always reads/writes to local storage first
- Background sync engine handles cloud synchronization
- App works perfectly without internet connection

**Benefits:**
- Instant responsiveness (no network latency)
- Works offline indefinitely
- Reduced server load and costs
- User maintains data ownership
- Privacy-focused (data local by default)

---

## Research Summary

### Industry Best Practices (2025)

**Key Findings:**
1. **Local-first is trending**: Major shift from cloud-first to local-first architecture
2. **Delta sync is essential**: Only sync changes since last sync (timestamp/token-based)
3. **Conflict resolution matters**: LWW for simple cases, CRDT/OT for collaboration
4. **Offline queue required**: Store operations when offline, process when online
5. **PowerSync pattern**: Popular solution for Supabase offline-first apps

**Sources:**
- PowerSync + Supabase integration (reads PostgreSQL WAL)
- RxDB local-first patterns
- WatermelonDB + Supabase offline-first
- CRDT vs OT research for conflict resolution

### Conflict Resolution Options

**1. Last-Write-Wins (LWW)** ← Start here
- Simple: Compare timestamps, newest wins
- Works for 95% of single-user multi-device cases
- Low complexity, easy to implement and debug
- Limitation: Lost updates if simultaneous edits

**2. CRDTs (Conflict-free Replicated Data Types)** ← Future upgrade
- Mathematical guarantee: always mergeable
- No central coordinator needed
- Works peer-to-peer
- Libraries: Automerge, Yjs
- Complexity: High (data structure changes, larger payloads)
- Use when: Real collaboration needed

**3. Operational Transformation (OT)** ← Not recommended for us
- Requires central server coordination
- Complex transformation functions
- Good for: Real-time collaborative text editing
- Overkill for task management

**Recommendation**: Start LWW, add CRDT when users request collaboration features.

---

## Phase 1: Foundation

### 1.1 Supabase Database Schema

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tasks table
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,                    -- Keep existing task IDs from local
  user_id UUID REFERENCES auth.users,     -- Owner (anonymous or permanent)

  -- Task data
  name TEXT NOT NULL,
  comment TEXT,
  description TEXT,
  priority INTEGER,
  tag TEXT,
  status TEXT,                            -- "done" or "undone"

  -- Sync metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),   -- For LWW conflict resolution
  last_modified_device TEXT,              -- Track which device made last change
  version INTEGER DEFAULT 1,              -- Future-proof for CRDT migration
  is_deleted BOOLEAN DEFAULT FALSE,       -- Soft delete for sync

  -- Indexes
  CONSTRAINT tasks_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_tasks_user_updated ON tasks(user_id, updated_at DESC);
CREATE INDEX idx_tasks_user_deleted ON tasks(user_id, is_deleted) WHERE NOT is_deleted;

-- Sync metadata (tracks last sync per device)
CREATE TABLE sync_metadata (
  device_id TEXT PRIMARY KEY,
  user_id UUID REFERENCES auth.users,
  last_sync_at TIMESTAMPTZ,               -- Last successful full sync
  last_pull_at TIMESTAMPTZ,               -- Last time pulled from server
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security (RLS)
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_metadata ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own data
CREATE POLICY "Users can manage their own tasks"
  ON tasks FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own sync metadata"
  ON sync_metadata FOR ALL
  USING (auth.uid() = user_id);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

### 1.2 Authentication System

**Anonymous Sign-In Flow:**
```python
# On first run
1. Call supabase.auth.sign_in_anonymously()
2. Store JWT + refresh_token in ~/.todo_auth
3. Generate device_id (UUID)
4. Store device_id locally
5. Ready to use (no signup required)
```

**Upgrade to Permanent Account:**
```python
# When user runs 'login' command
1. Prompt for email/password
2. Link anonymous account to email (Supabase linkIdentity)
3. Update local auth file
4. User can now login from other devices
```

**Local Auth Storage** (`~/.todo_auth`):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "...",
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "anonymous_or_permanent_uuid",
  "is_anonymous": true
}
```

### 1.3 Task Model Changes

**Add to `models/task.py`:**
```python
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class Task:
    # Existing fields
    id: int
    name: str
    comment: str
    description: str
    priority: int
    tag: str
    status: str

    # NEW: Sync fields
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_modified_device: str = field(default_factory=lambda: get_device_id())
    version: int = 1
    is_deleted: bool = False

    def mark_modified(self):
        """Call whenever task is changed locally"""
        self.updated_at = datetime.utcnow().isoformat()
        self.last_modified_device = get_device_id()
        self.version += 1
```

---

## Phase 2: Sync Engine

### 2.1 Sync Strategy (Bidirectional Delta Sync)

**Sync Flow:**
```
1. PULL Phase
   - Fetch tasks WHERE updated_at > last_pull_at
   - Fetch deleted tasks WHERE is_deleted = true AND updated_at > last_pull_at
   - Merge remote changes into local (resolve conflicts)

2. PUSH Phase
   - Find local tasks modified since last_sync_at
   - POST/PATCH to Supabase
   - Handle failures → add to offline queue

3. COMMIT Phase
   - Update sync_metadata.last_sync_at
   - Update sync_metadata.last_pull_at
   - Clear processed items from offline queue
```

**Conflict Resolution (LWW):**
```python
def merge_task(local: Task, remote: Task) -> Task:
    """Last-Write-Wins with device tracking"""

    # Compare timestamps
    local_time = datetime.fromisoformat(local.updated_at)
    remote_time = datetime.fromisoformat(remote.updated_at)

    if remote_time > local_time:
        # Remote is newer
        return remote
    elif local_time > remote_time:
        # Local is newer (will push to server)
        return local
    else:
        # Same timestamp - use device_id as tiebreaker
        if remote.last_modified_device < local.last_modified_device:
            return remote
        else:
            return local
```

### 2.2 Offline Queue

**Purpose**: Store operations when offline, replay when online

**Structure** (`sync_queue.json`):
```json
[
  {
    "operation": "create|update|delete",
    "task_id": "123",
    "task_data": {...},
    "timestamp": "2025-10-20T10:30:00Z",
    "retry_count": 0
  }
]
```

**Implementation** (`core/sync_queue.py`):
```python
class SyncQueue:
    def add_operation(self, op_type: str, task: Task):
        """Add operation to queue"""

    def process_queue(self) -> List[str]:
        """Process all pending operations, return errors"""

    def clear_processed(self):
        """Remove successful operations"""
```

### 2.3 New Core Modules

**`core/auth.py`**:
```python
class SupabaseAuth:
    def __init__(self):
        self.supabase = create_client(url, key)
        self.auth_file = Path.home() / ".todo_auth"

    def sign_in_anonymously(self) -> bool:
        """Anonymous sign in, store credentials"""

    def upgrade_to_permanent(self, email: str, password: str) -> bool:
        """Link anonymous account to email"""

    def get_current_user(self) -> dict:
        """Get current user info"""

    def refresh_token(self):
        """Refresh JWT if expired"""

    def sign_out(self):
        """Sign out (keep local data)"""
```

**`core/sync_engine.py`**:
```python
class SyncEngine:
    def __init__(self, state: AppState, auth: SupabaseAuth):
        self.state = state
        self.auth = auth
        self.queue = SyncQueue()

    def sync(self) -> SyncResult:
        """Full bidirectional sync"""
        return self._pull_then_push()

    def _pull_from_server(self) -> List[Task]:
        """Fetch changes since last pull"""

    def _push_to_server(self) -> List[str]:
        """Push local changes, returns errors"""

    def _merge_conflicts(self, local: Task, remote: Task) -> Task:
        """LWW conflict resolution"""

    def auto_sync_loop(self, interval: int = 300):
        """Background sync every N seconds"""
```

---

## Phase 3: User Commands

### 3.1 New Commands

**Sync Commands:**
```bash
sync              # Manual sync now
sync auto on      # Enable auto-sync (every 5 min)
sync auto off     # Disable auto-sync
sync status       # Show sync info
```

**Auth Commands:**
```bash
login             # Upgrade anonymous → permanent account
logout            # Sign out (keep local data)
whoami            # Show current user info
```

**Command Output Examples:**
```
❯ sync
Syncing...
  ↓ Pulled 3 changes
  ↑ Pushed 5 changes
  ✓ Synced successfully (2.3s)

❯ sync status
Sync Status:
  Last sync: 2 minutes ago
  Pending changes: 0
  Auto-sync: Enabled (every 5 min)
  User: anonymous_user_abc123
  Device: desktop_550e8400

❯ login
Upgrade to permanent account to sync across devices.
Email: user@example.com
Password: ********
✓ Account linked! You can now login from other devices.
```

### 3.2 Integration with Existing Commands

**Hook task mutations to sync queue:**
```python
# In core/commands.py

def handle_add_command(state, parts):
    # ... existing add logic ...
    task = Task(...)
    state.tasks.append(task)

    # NEW: Add to sync queue if online
    if sync_engine.is_authenticated():
        sync_engine.queue.add_operation("create", task)

    return "Task added"

def handle_edit_command(state, parts):
    # ... existing edit logic ...
    task.mark_modified()  # Update timestamp

    # NEW: Add to sync queue
    if sync_engine.is_authenticated():
        sync_engine.queue.add_operation("update", task)

    return "Task updated"
```

---

## Phase 4: Future Enhancements

### 4.1 Migration to CRDT (When Collaboration Needed)

**When to migrate:**
- User requests shared task lists
- Multiple users need to collaborate
- Real-time sync becomes important

**Migration Path:**
```python
# Current: LWW with version counter
task.version += 1  # Unused in LWW

# Future: CRDT with Automerge
from automerge import Document

doc = Document()
doc.change(lambda d: d.tasks[task.id] = task.to_dict())
```

**Why version field helps:**
- CRDT libraries use version vectors
- Already tracking changes
- Smoother migration

### 4.2 Collaboration Features

**Shared Lists:**
```sql
CREATE TABLE task_lists (
  id UUID PRIMARY KEY,
  name TEXT,
  owner_id UUID REFERENCES auth.users,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE list_members (
  list_id UUID REFERENCES task_lists,
  user_id UUID REFERENCES auth.users,
  role TEXT, -- "owner", "editor", "viewer"
  PRIMARY KEY (list_id, user_id)
);

-- Update tasks table
ALTER TABLE tasks ADD COLUMN list_id UUID REFERENCES task_lists;
```

**Real-time Updates:**
```python
# Subscribe to Supabase Realtime
supabase.channel('tasks').on(
    'postgres_changes',
    event='*',
    schema='public',
    table='tasks',
    callback=on_task_change
).subscribe()
```

---

## Implementation Checklist

### Setup
- [ ] Create Supabase project
- [ ] Configure authentication (enable anonymous sign-in)
- [ ] Run database migrations (tables + RLS policies)
- [ ] Install dependencies: `supabase-py`, `python-dotenv`
- [ ] Add `.env` file with Supabase credentials

### Phase 1: Authentication
- [ ] Implement `core/auth.py` (SupabaseAuth class)
- [ ] Add auth commands: `login`, `logout`, `whoami`
- [ ] Test anonymous sign-in flow
- [ ] Test upgrade to permanent account

### Phase 2: Sync Engine
- [ ] Update `models/task.py` with sync fields
- [ ] Implement `core/sync_queue.py` (offline queue)
- [ ] Implement `core/sync_engine.py` (pull/push/merge)
- [ ] Add `sync` command
- [ ] Test offline → online sync
- [ ] Test conflict resolution (two devices editing same task)

### Phase 3: Integration
- [ ] Hook `add`/`edit`/`done`/`remove` to sync queue
- [ ] Add auto-sync background thread
- [ ] Add `sync status` command
- [ ] Update status display to show sync state
- [ ] Test full workflow (add → edit → sync → other device)

### Phase 4: Polish
- [ ] Error handling (network failures, auth errors)
- [ ] Progress indicators for sync operations
- [ ] Migration script (upgrade existing tasks.json)
- [ ] Documentation (user guide for sync)
- [ ] Performance testing (1000+ tasks)

---

## Environment Setup

**`.env` file:**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
SYNC_AUTO_ENABLED=false
SYNC_INTERVAL=300
```

**Dependencies** (`requirements.txt`):
```
rich>=13.0.0
prompt_toolkit>=3.0.0
supabase>=2.0.0
python-dotenv>=1.0.0
```

---

## Testing Strategy

### Test Scenarios

**1. Single Device Sync**
- [ ] Add tasks locally → sync → verify in Supabase
- [ ] Edit tasks in Supabase → sync → verify locally
- [ ] Delete task locally → sync → verify soft-deleted remotely

**2. Multi-Device Sync**
- [ ] Device A adds task → Device B syncs → verify received
- [ ] Both devices offline → both edit same task → both sync → verify LWW

**3. Offline Queue**
- [ ] Disconnect network → add 5 tasks → reconnect → sync → verify all pushed
- [ ] Fail to push (auth error) → verify queued → fix auth → sync → verify retry

**4. Conflict Resolution**
- [ ] Device A: edit task at 10:00 → Device B: edit task at 10:01 → sync → verify B wins
- [ ] Same timestamp → verify device_id tiebreaker

**5. Anonymous Upgrade**
- [ ] Use anonymously → add tasks → upgrade to permanent → verify tasks preserved
- [ ] Login from Device B with permanent account → verify tasks synced

---

## Rollout Plan

### Week 1: Foundation
- Setup Supabase + database schema
- Implement authentication layer
- Test anonymous + permanent sign-in

### Week 2: Core Sync
- Implement sync engine (pull/push)
- Add conflict resolution (LWW)
- Test basic sync flow

### Week 3: Integration
- Hook commands to sync queue
- Add offline queue
- Test offline scenarios

### Week 4: Polish
- Auto-sync background thread
- Error handling + retry logic
- User documentation

---

## Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Source of Truth** | Local-first | Offline-critical, instant responsiveness |
| **Conflict Resolution** | LWW → CRDT | Start simple, upgrade when collaboration needed |
| **Auth Strategy** | Anonymous → Permanent | Zero friction onboarding |
| **Sync Method** | Delta sync (timestamps) | Efficient bandwidth, scalable |
| **Offline Strategy** | Operation queue | Bulletproof offline support |
| **Database** | Supabase PostgreSQL | Built-in auth, RLS, Realtime, good DX |

---

## References

### Research Sources
- PowerSync + Supabase: https://www.powersync.com/blog/bringing-offline-first-to-supabase
- Local-First Software: https://www.inkandswitch.com/local-first/
- CRDT vs OT: https://thom.ee/blog/crdt-vs-operational-transformation/
- RxDB Replication: https://rxdb.info/replication.html
- Supabase Anonymous Auth: https://supabase.com/docs/guides/auth/auth-anonymous

### Libraries to Consider
- **Automerge**: CRDT library (when collaboration needed)
- **Yjs**: Alternative CRDT (more lightweight)
- **PowerSync**: Commercial offline-first sync (if DIY too complex)

---

## FAQ

**Q: Why not use PowerSync instead of building custom sync?**
A: PowerSync is excellent but adds dependency + complexity. For single-user multi-device, custom LWW sync is simpler and gives full control. Consider PowerSync if collaboration becomes critical.

**Q: Why LWW instead of CRDT from the start?**
A: CRDTs add significant complexity (data structure changes, larger payloads, learning curve). LWW handles 95% of single-user cases. Migrate when collaboration is actually needed.

**Q: What if two devices edit the same task simultaneously offline?**
A: LWW: Last to sync wins (other changes lost). Acceptable for single-user. For collaboration, upgrade to CRDT (no data loss).

**Q: Can users work offline indefinitely?**
A: Yes. Local storage is primary. Sync is just backup/multi-device access. Offline queue stores changes until online.

**Q: How to handle deleted tasks?**
A: Soft delete (`is_deleted=true`). Sync engine propagates deletes. Optionally: hard delete after 30 days.

**Q: What about large task descriptions/comments?**
A: JSON storage handles it. If size becomes issue, add file attachments to Supabase Storage later.

---

**Status**: Planning Complete
**Next Step**: Start with Phase 1 - Database Setup + Authentication
