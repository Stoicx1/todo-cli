# Task: SQLite Migration for Supabase Sync Preparation

**Status:** Planning
**Priority:** High
**Timeline:** 3-4 weeks
**Version Bump:** MAJOR (v0.2.0 → v1.0.0)
**Created:** 2025-10-29

## Executive Summary

Migrate the todo-cli application from JSON-based persistence to SQLite with a schema designed for future Supabase PostgreSQL synchronization. This is a **full migration** (no JSON backward compatibility) using a **direct implementation** approach.

### Key Drivers
- **Best practice:** SQLite is industry standard for local app persistence
- **Reliability:** ACID transactions, referential integrity, mature tooling
- **Future sync:** Schema designed to mirror Supabase PostgreSQL for seamless sync
- **Scalability:** Better performance for complex queries and large datasets

---

## Schema Design (Sync-Ready)

### Design Principles

1. **UUIDs for all primary keys** - PostgreSQL/Supabase standard, globally unique
2. **Soft deletes** - `deleted_at` columns for sync reconciliation
3. **Version tracking** - Optimistic locking for conflict resolution
4. **Comprehensive timestamps** - All tables have `created_at`, `updated_at`
5. **PostgreSQL compatibility** - Use standard SQL types that map cleanly

### Complete Schema

```sql
-- ============================================================================
-- TASKS TABLE
-- ============================================================================
CREATE TABLE tasks (
    -- Identity
    id TEXT PRIMARY KEY,                    -- UUID v7 (time-ordered)
    name TEXT NOT NULL,
    description TEXT DEFAULT '',

    -- Task properties
    priority INTEGER NOT NULL DEFAULT 2,
    done BOOLEAN NOT NULL DEFAULT 0,

    -- Legacy single tag (backward compat with old commands)
    tag TEXT DEFAULT '',

    -- Timestamps
    created_at TEXT NOT NULL,               -- ISO 8601 format
    updated_at TEXT NOT NULL,               -- ISO 8601 format
    completed_at TEXT DEFAULT '',           -- When marked done
    deleted_at TEXT DEFAULT '',             -- Soft delete

    -- Sync metadata (for future Supabase sync)
    version INTEGER NOT NULL DEFAULT 1,     -- Optimistic locking
    sync_status TEXT DEFAULT 'local',       -- local|synced|conflict|error
    last_synced_at TEXT DEFAULT '',         -- Last successful sync timestamp

    -- Constraints
    CHECK(priority >= 1 AND priority <= 3),
    CHECK(sync_status IN ('local', 'synced', 'conflict', 'error'))
);

-- ============================================================================
-- TAGS TABLE (Normalized, shared by tasks and notes)
-- ============================================================================
CREATE TABLE tags (
    id TEXT PRIMARY KEY,                    -- UUID
    name TEXT UNIQUE NOT NULL COLLATE NOCASE, -- Case-insensitive unique
    created_at TEXT NOT NULL,

    -- Sync metadata
    sync_status TEXT DEFAULT 'local',
    last_synced_at TEXT DEFAULT ''
);

-- ============================================================================
-- TASK-TAG JUNCTION TABLE (Many-to-Many)
-- ============================================================================
CREATE TABLE task_tags (
    task_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    created_at TEXT NOT NULL,               -- When tag was added to task

    PRIMARY KEY (task_id, tag_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- ============================================================================
-- NOTES TABLE (Migrated from notes/*.md files)
-- ============================================================================
CREATE TABLE notes (
    id TEXT PRIMARY KEY,                    -- UUID v7 (same as current)
    title TEXT NOT NULL,
    body_md TEXT DEFAULT '',                -- Full markdown content

    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT DEFAULT '',             -- Soft delete

    -- Sync metadata
    version INTEGER NOT NULL DEFAULT 1,
    sync_status TEXT DEFAULT 'local',
    last_synced_at TEXT DEFAULT ''
);

-- ============================================================================
-- NOTE-TAG JUNCTION TABLE
-- ============================================================================
CREATE TABLE note_tags (
    note_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    created_at TEXT NOT NULL,

    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- ============================================================================
-- TASK-NOTE LINKS (Many-to-Many)
-- ============================================================================
CREATE TABLE task_notes (
    task_id TEXT NOT NULL,
    note_id TEXT NOT NULL,
    created_at TEXT NOT NULL,               -- When link was created

    PRIMARY KEY (task_id, note_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);

-- ============================================================================
-- AI CONVERSATION HISTORY
-- ============================================================================
CREATE TABLE ai_messages (
    id TEXT PRIMARY KEY,                    -- UUID
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    is_status BOOLEAN NOT NULL DEFAULT 0,   -- Temporary status indicators

    CHECK(role IN ('user', 'assistant'))
);

-- ============================================================================
-- SETTINGS (Key-Value Store)
-- ============================================================================
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,                    -- JSON-encoded value
    updated_at TEXT NOT NULL
);

-- ============================================================================
-- PERFORMANCE INDICES
-- ============================================================================

-- Tasks
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_done ON tasks(done);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at DESC);
CREATE INDEX idx_tasks_deleted_at ON tasks(deleted_at);
CREATE INDEX idx_tasks_sync_status ON tasks(sync_status);

-- Tags
CREATE INDEX idx_tags_name ON tags(name);

-- Task-Tag junctions
CREATE INDEX idx_task_tags_task_id ON task_tags(task_id);
CREATE INDEX idx_task_tags_tag_id ON task_tags(tag_id);

-- Notes
CREATE INDEX idx_notes_created_at ON notes(created_at DESC);
CREATE INDEX idx_notes_updated_at ON notes(updated_at DESC);
CREATE INDEX idx_notes_deleted_at ON notes(deleted_at);
CREATE INDEX idx_notes_title ON notes(title);

-- Note-Tag junctions
CREATE INDEX idx_note_tags_note_id ON note_tags(note_id);
CREATE INDEX idx_note_tags_tag_id ON note_tags(tag_id);

-- Task-Note links
CREATE INDEX idx_task_notes_task_id ON task_notes(task_id);
CREATE INDEX idx_task_notes_note_id ON task_notes(note_id);

-- AI Messages
CREATE INDEX idx_ai_messages_timestamp ON ai_messages(timestamp DESC);
CREATE INDEX idx_ai_messages_role ON ai_messages(role);

-- Settings
-- Primary key index is sufficient
```

### Schema Rationale

**Why UUIDs for Tasks (Breaking Change)?**
- Current: INTEGER autoincrement (local only)
- New: UUID v7 (time-ordered, globally unique)
- Enables future multi-device sync without ID conflicts
- Compatible with PostgreSQL UUID type in Supabase

**Why Migrate Notes to Database?**
- Current: Individual `notes/*.md` files with YAML front matter
- New: `body_md TEXT` column in database
- Enables atomic sync operations with Supabase
- Simplifies backup/restore (single database file)
- Trade-off: Lose individual file access, but gain reliability

**Why Soft Deletes?**
- `deleted_at` column instead of hard deletes
- Enables sync conflict resolution (know what was deleted when)
- Can restore accidentally deleted items
- Required for proper sync with Supabase

**Why Version Column?**
- Optimistic locking for concurrent updates
- Detect conflicts when syncing with Supabase
- Increment on every update
- If local version ≠ remote version → conflict

---

## Week-by-Week Implementation Plan

### Week 1: Core Database Infrastructure

#### 1.1 Create Database Module (`core/database.py`)

**Purpose:** Central connection manager, schema initialization, migrations

**Key Functions:**
```python
class DatabaseManager:
    def __init__(self, db_path: str = "todo.db")
    def get_connection(self) -> sqlite3.Connection
    def initialize_schema(self) -> None
    def close(self) -> None

    # Transaction support
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]

    # Migration support
    def get_schema_version(self) -> int
    def run_migrations(self) -> None
```

**Features:**
- WAL mode for better concurrency: `PRAGMA journal_mode=WAL`
- Foreign key enforcement: `PRAGMA foreign_keys=ON`
- Connection pooling (though single-threaded app)
- Automatic schema initialization on first run

**Location:** `D:\MyProjects\todo-cli\core\database.py`

#### 1.2 Create Repository Package

**Structure:**
```
repositories/
├── __init__.py
├── base_repository.py       # Abstract base class
├── task_repository.py       # Task CRUD + tag management
├── note_repository.py       # Note CRUD + full-text search
├── settings_repository.py   # Key-value settings
└── ai_repository.py         # Conversation history
```

**Base Repository Pattern:**
```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @abstractmethod
    def create(self, entity: T) -> T:
        pass

    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        pass

    @abstractmethod
    def list_all(self) -> List[T]:
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        pass
```

#### 1.3 Implement TaskRepository

**Key Methods:**
```python
class TaskRepository(BaseRepository[Task]):
    def create(self, task: Task) -> Task
    def get(self, task_id: str) -> Optional[Task]
    def get_by_prefix(self, prefix: str) -> Optional[Task]  # For UUID prefix matching
    def list_all(self, include_deleted: bool = False) -> List[Task]
    def update(self, task: Task) -> Task
    def soft_delete(self, task_id: str) -> bool
    def hard_delete(self, task_id: str) -> bool

    # Tag management
    def add_tags(self, task_id: str, tag_names: List[str]) -> None
    def remove_tags(self, task_id: str, tag_names: List[str]) -> None
    def get_tags(self, task_id: str) -> List[str]
    def find_by_tags(self, tag_names: List[str], match_all: bool = False) -> List[Task]

    # Bulk operations
    def bulk_update_done(self, task_ids: List[str], done: bool) -> int
    def bulk_delete(self, task_ids: List[str]) -> int
```

**Tag Normalization:**
- Tags normalized to lowercase before insert
- Reuse existing tag IDs from `tags` table
- Handle tag creation in transaction with task

#### 1.4 Implement NoteRepository

**Key Methods:**
```python
class NoteRepository(BaseRepository[Note]):
    def create(self, note: Note) -> Note
    def get(self, note_id: str) -> Optional[Note]
    def get_by_prefix(self, prefix: str) -> Optional[Note]
    def list_all(self, include_deleted: bool = False) -> List[Note]
    def update(self, note: Note) -> Note
    def soft_delete(self, note_id: str) -> bool

    # Tag management
    def add_tags(self, note_id: str, tag_names: List[str]) -> None
    def remove_tags(self, note_id: str, tag_names: List[str]) -> None
    def get_tags(self, note_id: str) -> List[str]

    # Task links
    def link_task(self, note_id: str, task_id: str) -> bool
    def unlink_task(self, note_id: str, task_id: str) -> bool
    def get_linked_tasks(self, note_id: str) -> List[str]
    def get_notes_for_task(self, task_id: str) -> List[Note]

    # Search
    def search(self, query: str) -> List[Note]  # Full-text search in title + body
```

**Search Implementation:**
- Simple SQL `LIKE` for now: `WHERE title LIKE '%query%' OR body_md LIKE '%query%'`
- Future: SQLite FTS5 (Full-Text Search) for better performance

#### 1.5 Unit Tests (Week 1)

**Test Files:**
- `tests/unit/test_database.py` - Connection, schema initialization
- `tests/unit/test_task_repository.py` - All CRUD operations
- `tests/unit/test_note_repository.py` - All CRUD operations
- `tests/unit/test_settings_repository.py` - Key-value operations

**Use In-Memory SQLite:**
```python
@pytest.fixture
def db_manager():
    """In-memory database for fast testing"""
    db = DatabaseManager(":memory:")
    db.initialize_schema()
    yield db
    db.close()
```

**Deliverables Week 1:**
- ✅ Complete database layer with schema
- ✅ All repository classes implemented
- ✅ 30+ unit tests passing
- ✅ No integration with main app yet

---

### Week 2: Migration Tool + State Integration

#### 2.1 Create Migration Tool (`migrations/migrate_json_to_sqlite.py`)

**Purpose:** One-time migration of all existing JSON data to SQLite

**Key Functions:**
```python
def migrate(
    tasks_json: str = "tasks.json",
    notes_dir: str = "notes/",
    settings_json: str = None,  # ~/.todo_cli_settings.json
    ai_history_json: str = None,  # ~/.todo_cli_ai_history.json
    output_db: str = "todo.db",
    backup: bool = True,
    dry_run: bool = False
) -> MigrationReport

class MigrationReport:
    tasks_migrated: int
    notes_migrated: int
    tags_created: int
    settings_migrated: int
    ai_messages_migrated: int
    errors: List[str]
    id_mapping: Dict[int, str]  # old_task_id → new_uuid
```

**Migration Steps:**

1. **Backup Original Files**
   ```python
   shutil.copy("tasks.json", "tasks.json.pre_migration")
   shutil.copytree("notes/", "notes.pre_migration/")
   ```

2. **Generate UUID Mapping**
   ```python
   # Map old integer IDs to new UUIDs
   id_mapping = {}
   for old_task in tasks_json_data:
       new_uuid = generate_uuid_v7()
       id_mapping[old_task['id']] = new_uuid
   ```

3. **Migrate Tasks**
   ```python
   for old_task in tasks_json_data:
       new_task = Task(
           id=id_mapping[old_task['id']],
           name=old_task['name'],
           # ... map all fields ...
           created_at=old_task['created_at'],
           updated_at=old_task['updated_at'],
           version=1,
           sync_status='local'
       )
       task_repo.create(new_task)

       # Migrate tags
       if old_task.get('tags'):
           task_repo.add_tags(new_task.id, old_task['tags'])
   ```

4. **Migrate Notes**
   ```python
   for md_file in glob("notes/*.md"):
       # Parse YAML front matter + body
       front_matter, body = parse_markdown(md_file)

       note = Note(
           id=front_matter['id'],  # Keep existing UUID
           title=front_matter['title'],
           body_md=body,
           created_at=front_matter['created_at'],
           updated_at=front_matter['updated_at'],
           version=1
       )
       note_repo.create(note)

       # Migrate tags
       if front_matter.get('tags'):
           note_repo.add_tags(note.id, front_matter['tags'])

       # Migrate task links (update IDs!)
       if front_matter.get('task_ids'):
           for old_task_id in front_matter['task_ids']:
               new_task_id = id_mapping.get(old_task_id)
               if new_task_id:
                   note_repo.link_task(note.id, new_task_id)
   ```

5. **Verify Integrity**
   ```python
   # Row count validation
   assert len(tasks_json_data) == task_repo.count_all()

   # Tag integrity
   for task in task_repo.list_all():
       tags = task_repo.get_tags(task.id)
       assert all(tag_exists(tag) for tag in tags)

   # Note link validation
   for note in note_repo.list_all():
       linked_tasks = note_repo.get_linked_tasks(note.id)
       assert all(task_repo.get(tid) for tid in linked_tasks)
   ```

**CLI Interface:**
```bash
python -m migrations.migrate_json_to_sqlite --dry-run
python -m migrations.migrate_json_to_sqlite --backup --verbose
```

#### 2.2 Update Models

**File:** `models/task.py`

**Breaking Changes:**
```python
@dataclass
class Task:
    # BREAKING: Changed from int to str (UUID)
    id: str  # Was: id: int

    name: str
    comment: str
    description: str
    priority: int
    tag: str  # Legacy, kept for backward compat
    done: bool = False
    tags: List[str] = field(default_factory=list)

    # Timestamps (existing)
    created_at: str
    updated_at: str
    completed_at: str = ""

    # NEW: Sync metadata
    deleted_at: str = ""
    version: int = 1
    sync_status: str = "local"
    last_synced_at: str = ""
```

**File:** `models/note.py`

**Changes:**
```python
@dataclass
class Note:
    id: str  # Already UUID, no change
    title: str
    body_md: str = ""
    tags: List[str] = field(default_factory=list)
    task_ids: List[int] = field(default_factory=list)  # BREAKING: Will be List[str] with UUIDs

    created_at: str
    updated_at: str
    deleted_at: str = ""

    # NEW
    version: int = 1
    sync_status: str = "local"
    last_synced_at: str = ""
```

#### 2.3 Update AppState (`core/state.py`)

**Major Changes:**

1. **Replace `save_to_file()` / `load_from_file()`**

```python
# OLD (JSON-based)
def load_from_file(self, filename: str) -> None:
    data = SafeFileManager.load_json_with_lock(filename)
    self.tasks = [Task(**t) for t in data]
    self._rebuild_index()

def save_to_file(self, filename: str) -> None:
    data = [asdict(t) for t in self.tasks]
    SafeFileManager.save_json_with_lock(filename, data)

# NEW (SQLite-based)
def load_from_database(self) -> None:
    self.tasks = self.task_repo.list_all(include_deleted=False)
    self._rebuild_index()

    self.notes = self.note_repo.list_all(include_deleted=False)
    self._rebuild_note_index()

def save_to_database(self) -> None:
    # NOTE: With SQLite, saves happen immediately in repositories
    # This method might become a no-op or trigger sync
    pass
```

2. **Update Indices to Use UUID Keys**

```python
# OLD
_task_index: Dict[int, Task] = {}  # task_id → Task

# NEW
_task_index: Dict[str, Task] = {}  # uuid → Task

def _rebuild_index(self) -> None:
    self._task_index = {task.id: task for task in self.tasks}
```

3. **Add Repository References**

```python
class AppState:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.task_repo = TaskRepository(db_manager)
        self.note_repo = NoteRepository(db_manager)
        self.settings_repo = SettingsRepository(db_manager)
        self.ai_repo = AIMessageRepository(db_manager)

        # ... existing fields ...
```

4. **Update CRUD Methods to Use Repositories**

```python
# OLD
def add_task(self, name: str, priority: int, tags: List[str], ...) -> Task:
    task = Task(
        id=self._next_id(),
        name=name,
        # ...
    )
    self.tasks.append(task)
    self._rebuild_index()
    return task

# NEW
def add_task(self, name: str, priority: int, tags: List[str], ...) -> Task:
    task = Task(
        id=generate_uuid_v7(),
        name=name,
        # ...
        version=1,
        sync_status='local'
    )
    # Save to database immediately
    task = self.task_repo.create(task)

    # Add tags
    if tags:
        self.task_repo.add_tags(task.id, tags)

    # Update in-memory cache
    self.tasks.append(task)
    self._task_index[task.id] = task
    self._invalidate_filter_cache()

    return task
```

**Key Pattern:**
- **Write to database immediately** (no batching)
- **Update in-memory cache** for fast reads
- **Keep filter cache** for UI performance

#### 2.4 Auto-Migration on Startup

**File:** `main.py` or `textual_app.py`

```python
def check_and_migrate():
    """Auto-migrate JSON to SQLite on first run"""
    db_path = Path.home() / ".todo_cli.db"
    tasks_json = Path("tasks.json")

    if tasks_json.exists() and not db_path.exists():
        print("=" * 60)
        print("FIRST-TIME SETUP: Migrating to SQLite")
        print("=" * 60)
        print("Detected existing tasks.json file.")
        print("Migrating to SQLite database for better performance...")
        print()

        from migrations.migrate_json_to_sqlite import migrate

        try:
            report = migrate(
                tasks_json=str(tasks_json),
                notes_dir="notes/",
                output_db=str(db_path),
                backup=True
            )

            print(f"✅ Migration successful!")
            print(f"   Tasks migrated: {report.tasks_migrated}")
            print(f"   Notes migrated: {report.notes_migrated}")
            print(f"   Tags created: {report.tags_created}")
            print()
            print(f"Backup saved: tasks.json.pre_migration")
            print()

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("Please report this issue with the error message.")
            sys.exit(1)

# In main()
check_and_migrate()
app = TodoTextualApp(db_path=str(Path.home() / ".todo_cli.db"))
```

**Deliverables Week 2:**
- ✅ Complete migration tool with validation
- ✅ AppState updated to use repositories
- ✅ Auto-migration on first run
- ✅ ID mapping (old int → new UUID)
- ✅ All data migrated with zero loss

---

### Week 3: Update All Consumers

#### 3.1 Update Configuration (`config.py`)

```python
# NEW
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".todo_cli.db"
DEFAULT_DB_FILE = "todo.db"

# Keep for migration detection
DEFAULT_TASKS_FILE = "tasks.json"
DEFAULT_NOTES_DIR = "notes/"
```

#### 3.2 Update Task Table Widget (`textual_widgets/task_table.py`)

**UUID Display:**
```python
def populate_table(self, tasks: List[Task]) -> None:
    # Clear existing rows
    self.clear()

    for task in tasks:
        # Display first 8 chars of UUID
        task_id_display = task.id[:8]

        row_key = self.add_row(
            task_id_display,  # Was: str(task.id)
            task.name,
            # ... other columns ...
        )

        # Map row key to full UUID
        self._row_to_task_id[row_key] = task.id
```

**Task Selection:**
```python
def get_selected_task_id(self) -> Optional[str]:  # Was: Optional[int]
    """Get full UUID of selected task"""
    cursor_row = self.cursor_row
    if cursor_row is None:
        return None
    row_key = self.get_row_at(cursor_row)
    return self._row_to_task_id.get(row_key)
```

#### 3.3 Update Commands (`core/commands.py`)

**UUID Parsing:**
```python
def parse_task_id_or_prefix(arg: str, state: AppState) -> Optional[str]:
    """
    Parse task ID or prefix.

    Args:
        arg: Full UUID or prefix (min 8 chars)
        state: AppState for prefix matching

    Returns:
        Full UUID if found, None otherwise

    Examples:
        "019c4f2a-..." → "019c4f2a-1234-5678-90ab-cdef01234567"
        "019c4f2a" → "019c4f2a-1234-5678-90ab-cdef01234567"
    """
    # Try exact match first
    if state.get_task_by_id(arg):
        return arg

    # Try prefix match (min 8 chars)
    if len(arg) >= 8:
        matches = [
            task.id for task in state.tasks
            if task.id.startswith(arg)
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Ambiguous prefix '{arg}' matches {len(matches)} tasks")

    return None
```

**Update Done Command:**
```python
# OLD
def handle_done_command(task_id: int, state: AppState) -> None:
    task = state.get_task_by_id(task_id)
    # ...

# NEW
def handle_done_command(task_id_or_prefix: str, state: AppState) -> None:
    task_id = parse_task_id_or_prefix(task_id_or_prefix, state)
    if not task_id:
        raise ValueError(f"Task not found: {task_id_or_prefix}")

    task = state.get_task_by_id(task_id)
    # ...
```

**All Commands Affected:**
- `done` / `x` / `d`
- `undone` / `u`
- `remove` / `r`
- `edit` / `e`
- `show` / `s`
- `note link` (task ID argument)

#### 3.4 Update AI Tools (`core/ai_tools.py`)

**Tool Schemas:**
```python
# OLD
get_task_details_schema = {
    "type": "function",
    "function": {
        "name": "get_task_details",
        "parameters": {
            "task_id": {"type": "integer"}  # ❌ OLD
        }
    }
}

# NEW
get_task_details_schema = {
    "type": "function",
    "function": {
        "name": "get_task_details",
        "parameters": {
            "task_id": {"type": "string", "description": "Task UUID or prefix (min 8 chars)"}
        }
    }
}
```

**Tool Functions:**
```python
@tool
def mark_task_done(task_id: str) -> str:  # Was: task_id: int
    """Mark a task as done.

    Args:
        task_id: Task UUID or prefix (min 8 chars)
    """
    parsed_id = parse_task_id_or_prefix(task_id, state)
    if not parsed_id:
        return f"Error: Task '{task_id}' not found"

    # ... rest of logic ...
```

**All Tools Affected:**
- `get_task_details`
- `mark_task_done`
- `mark_task_undone`
- `update_task_priority`
- `add_tag_to_task`
- `link_note_to_task`

#### 3.5 Update Textual App (`textual_app.py`)

**Initialization:**
```python
# OLD
def __init__(self, tasks_file: str = "tasks.json"):
    super().__init__()
    self.state = AppState()
    self.tasks_file = tasks_file

# NEW
def __init__(self, db_path: str = None):
    super().__init__()
    if db_path is None:
        db_path = str(Path.home() / ".todo_cli.db")

    self.db_manager = DatabaseManager(db_path)
    self.state = AppState(self.db_manager)
```

**On Mount:**
```python
def on_mount(self) -> None:
    # OLD
    self.state.load_from_file(self.tasks_file)

    # NEW
    self.state.load_from_database()
```

**On Unmount:**
```python
def on_unmount(self) -> None:
    # OLD
    self.state.save_to_file(self.tasks_file)

    # NEW
    # No explicit save needed (repositories save immediately)
    self.db_manager.close()
```

#### 3.6 Update Rich UI (`ui/rich_ui.py`)

Similar changes to Textual UI:
- Accept `db_path` instead of `tasks_file`
- Use `load_from_database()` instead of `load_from_file()`
- Handle UUID display in tables

#### 3.7 Update Main Entry Point (`main.py`)

```python
# OLD
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", choices=["rich", "textual"], default="textual")
    parser.add_argument("--file", default="tasks.json")
    args = parser.parse_args()

    if args.ui == "rich":
        run_rich_ui(args.file)
    else:
        app = TodoTextualApp(tasks_file=args.file)
        app.run()

# NEW
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", choices=["rich", "textual"], default="textual")
    parser.add_argument("--db", default=None, help="Database path (default: ~/.todo_cli.db)")
    args = parser.parse_args()

    # Auto-migration check
    check_and_migrate()

    db_path = args.db or str(Path.home() / ".todo_cli.db")

    if args.ui == "rich":
        run_rich_ui(db_path)
    else:
        app = TodoTextualApp(db_path=db_path)
        app.run()
```

**Deliverables Week 3:**
- ✅ All widgets updated for UUID display
- ✅ All commands support UUID/prefix matching
- ✅ AI tools updated with UUID schemas
- ✅ Both UIs (Textual + Rich) working with SQLite
- ✅ Manual testing of core workflows

---

### Week 4: Testing + Cleanup

#### 4.1 Update Test Suite

**Fixtures (`conftest.py`):**

```python
# OLD
@pytest.fixture
def temp_tasks_file(tmp_path):
    """Temporary tasks.json file"""
    tasks_file = tmp_path / "test_tasks.json"
    yield str(tasks_file)

# NEW
@pytest.fixture
def temp_database(tmp_path):
    """Temporary SQLite database"""
    db_path = tmp_path / "test_todo.db"
    db_manager = DatabaseManager(str(db_path))
    db_manager.initialize_schema()
    yield db_manager
    db_manager.close()

@pytest.fixture
def in_memory_database():
    """In-memory SQLite for fast tests"""
    db_manager = DatabaseManager(":memory:")
    db_manager.initialize_schema()
    yield db_manager
    db_manager.close()
```

**Update All Test Files (~70 tests):**

Priority order:
1. `tests/test_state.py` - Core state management (20 tests)
2. `tests/test_commands.py` - Command parsing (15 tests)
3. `tests/integration/test_task_workflow.py` - Full workflow (10 tests)
4. `tests/test_ai_tools.py` - AI tool schemas (5 tests)
5. All remaining test files

**Example Test Update:**

```python
# OLD
def test_add_task(in_memory_state):
    state = in_memory_state
    task = state.add_task("Buy milk", priority=1, tags=["personal"])
    assert task.id == 1
    assert task.name == "Buy milk"

# NEW
def test_add_task(in_memory_database):
    state = AppState(in_memory_database)
    task = state.add_task("Buy milk", priority=1, tags=["personal"])

    # UUID assertions
    assert len(task.id) == 36  # Full UUID length
    assert task.id.count('-') == 4  # UUID format
    assert task.name == "Buy milk"

    # Verify persisted to DB
    loaded_task = state.task_repo.get(task.id)
    assert loaded_task.name == "Buy milk"
```

#### 4.2 Add Migration Tests

**File:** `tests/test_migration.py`

```python
def test_migrate_tasks_from_json(tmp_path):
    """Test migrating tasks from JSON to SQLite"""
    # Create test JSON file
    tasks_json = tmp_path / "tasks.json"
    tasks_data = [
        {
            "id": 1,
            "name": "Task 1",
            "priority": 1,
            "tags": ["work", "urgent"],
            "done": False,
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00"
        }
    ]
    tasks_json.write_text(json.dumps(tasks_data))

    # Migrate
    db_path = tmp_path / "test.db"
    report = migrate(
        tasks_json=str(tasks_json),
        output_db=str(db_path),
        backup=False
    )

    # Verify
    assert report.tasks_migrated == 1
    assert 1 in report.id_mapping  # Old ID

    # Verify in database
    db = DatabaseManager(str(db_path))
    repo = TaskRepository(db)
    tasks = repo.list_all()
    assert len(tasks) == 1
    assert tasks[0].name == "Task 1"
    assert set(repo.get_tags(tasks[0].id)) == {"work", "urgent"}

def test_migrate_notes_from_markdown(tmp_path):
    """Test migrating notes from .md files to SQLite"""
    # Create test note file
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    note_file = notes_dir / "019abc-test-note.md"
    note_content = """---
id: 019abc-1234-5678-90ab-cdef01234567
title: Test Note
tags: ["personal"]
task_ids: [1, 2]
created_at: "2025-01-01T10:00:00"
updated_at: "2025-01-01T10:00:00"
---
This is the note body."""
    note_file.write_text(note_content)

    # Migrate
    db_path = tmp_path / "test.db"
    report = migrate(
        notes_dir=str(notes_dir),
        output_db=str(db_path)
    )

    # Verify
    assert report.notes_migrated == 1
```

#### 4.3 Integration Testing

**Manual Test Scenarios:**

1. **Fresh Install (No JSON Files)**
   - Run app → should create empty database
   - Add tasks → verify saved to database
   - Restart app → verify tasks loaded

2. **Migration from JSON**
   - Copy production `tasks.json`
   - Run app → should auto-migrate
   - Verify all tasks present
   - Verify all tags preserved
   - Verify task links work

3. **Large Dataset Performance**
   - Create 1000 test tasks
   - Measure load time (target: <50ms)
   - Measure filter time (target: <20ms)
   - Compare with JSON baseline

4. **UUID Prefix Matching**
   - Create task → note UUID
   - Use prefix in commands: `done 019c4f2a`
   - Verify correct task marked done
   - Test ambiguous prefix (should error)

5. **Note Migration**
   - Create notes/*.md files
   - Run migration
   - Verify notes visible in app
   - Verify task links work

**Automated Integration Tests:**

```python
def test_full_task_lifecycle_with_database(tmp_path):
    """End-to-end test: create, update, delete task"""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    state = AppState(db)

    # Create
    task = state.add_task("Test task", priority=1, tags=["work"])
    task_id = task.id

    # Verify persisted
    db2 = DatabaseManager(str(db_path))
    state2 = AppState(db2)
    state2.load_from_database()
    assert len(state2.tasks) == 1
    assert state2.tasks[0].name == "Test task"

    # Update
    state.mark_done(task_id)
    state2.load_from_database()
    assert state2.tasks[0].done is True

    # Delete
    state.remove_task(task_id)
    state2.load_from_database()
    assert len(state2.tasks) == 0
```

#### 4.4 Performance Benchmarks

**File:** `tests/benchmark/test_performance.py`

```python
import pytest
import time

@pytest.mark.benchmark
def test_load_1000_tasks_performance(benchmark_database_1000_tasks):
    """Benchmark: Load 1000 tasks from database"""
    state = AppState(benchmark_database_1000_tasks)

    start = time.perf_counter()
    state.load_from_database()
    elapsed = time.perf_counter() - start

    assert elapsed < 0.050  # < 50ms
    assert len(state.tasks) == 1000

@pytest.mark.benchmark
def test_filter_performance(benchmark_database_1000_tasks):
    """Benchmark: Filter 1000 tasks"""
    state = AppState(benchmark_database_1000_tasks)
    state.load_from_database()

    start = time.perf_counter()
    state.filter = "priority=1"
    filtered = state.filtered_tasks
    elapsed = time.perf_counter() - start

    assert elapsed < 0.020  # < 20ms
```

#### 4.5 Remove Deprecated Code

**Delete Files:**
- `core/file_safety.py` (3-layer JSON safety system no longer needed)
- `services/notes.py` (file-based note repository)

**Remove from `core/state.py`:**
- `save_to_file()` method
- `load_from_file()` method
- `_save_preferences()` (move to SettingsRepository)
- `_load_preferences()` (move to SettingsRepository)
- All `SafeFileManager` imports

**Update `.gitignore`:**
```gitignore
# OLD
tasks.json
tasks.json.backup*

# NEW
todo.db
*.db
*.db-shm
*.db-wal

# Keep for migration detection
tasks.json.pre_migration
notes.pre_migration/
```

#### 4.6 Documentation Updates

**Update `CLAUDE.md`:**
- Replace JSON persistence section with SQLite section
- Update schema diagrams
- Document UUID usage
- Update file safety (SQLite ACID transactions)

**Update `readme.md`:**
- Migration notice for existing users
- New database location: `~/.todo_cli.db`
- Backup strategy (export command)

**Update `USAGE_GUIDE.md`:**
- UUID prefix matching in commands
- Database path flag: `--db`
- Export command for backups

**Create `MIGRATION_GUIDE_SQLITE.md`:**
```markdown
# Migrating to SQLite (v1.0.0)

## What Changed

Version 1.0.0 introduces SQLite as the persistence layer, replacing JSON files.

### Breaking Changes
- Task IDs changed from integers to UUIDs
- Notes moved from `notes/*.md` files to database
- Backup files (`.backup`) replaced with SQLite backups

### Migration Process

The migration happens **automatically** on first run:

1. App detects `tasks.json` and no `todo.db`
2. Migrates all data to SQLite
3. Creates backup: `tasks.json.pre_migration`
4. You can delete old JSON files after verifying

### UUID Usage

Tasks now use UUIDs instead of integers:
- **Full UUID:** `019c4f2a-1234-5678-90ab-cdef01234567`
- **Display:** `019c4f2a` (first 8 chars)
- **Commands:** Accept UUID prefix (min 8 chars)

Examples:
```bash
done 019c4f2a           # Mark task done
edit 019c4f2a           # Edit task
show 019c4f2a-1234      # Longer prefix also works
```

### Backup Strategy

**Export to JSON:**
```bash
export json my_backup.json
```

**SQLite Backup:**
```bash
cp ~/.todo_cli.db ~/.todo_cli.db.backup
```

### Rollback (Emergency)

If you need to rollback to v0.2.0:
1. `git checkout v0.2.0`
2. `pip install -r requirements.txt`
3. Restore: `cp tasks.json.pre_migration tasks.json`

### Supabase Sync (Future)

This migration prepares for Supabase sync in v1.1.0:
- UUIDs enable multi-device sync
- Schema mirrors PostgreSQL
- Version tracking for conflict resolution
```

**Deliverables Week 4:**
- ✅ All 70+ tests passing with SQLite
- ✅ Migration tests validate data integrity
- ✅ Performance benchmarks meet targets
- ✅ Deprecated JSON code removed
- ✅ Complete documentation updated

---

## Files to Create/Modify

### New Files (9)

| Path | Purpose | Lines |
|------|---------|-------|
| `core/database.py` | Connection manager, schema, migrations | ~300 |
| `repositories/__init__.py` | Package exports | ~20 |
| `repositories/base_repository.py` | Abstract base class | ~80 |
| `repositories/task_repository.py` | Task CRUD + tags | ~400 |
| `repositories/note_repository.py` | Note CRUD + search | ~300 |
| `repositories/settings_repository.py` | Key-value settings | ~100 |
| `repositories/ai_repository.py` | AI message history | ~150 |
| `migrations/migrate_json_to_sqlite.py` | One-time migration tool | ~600 |
| `docs/MIGRATION_GUIDE_SQLITE.md` | User migration guide | ~200 |

**Total New Code:** ~2,150 lines

### Modified Files (18+)

| Path | Changes | Impact |
|------|---------|--------|
| `models/task.py` | Add UUID, version, sync fields | High |
| `models/note.py` | Add version, sync fields | Medium |
| `core/state.py` | Replace JSON with repositories | High |
| `core/commands.py` | UUID parsing, all CRUD commands | High |
| `core/ai_tools.py` | UUID schemas, all tools | High |
| `config.py` | Add DB_PATH constants | Low |
| `main.py` | Auto-migration, db_path arg | Medium |
| `textual_app.py` | Init with db_path, UUID display | High |
| `ui/rich_ui.py` | Same as textual_app.py | High |
| `textual_widgets/task_table.py` | UUID display, selection | Medium |
| `textual_widgets/task_form.py` | UUID validation | Low |
| `textual_widgets/note_table.py` | UUID display | Medium |
| `conftest.py` | SQLite fixtures | Medium |
| `tests/test_state.py` | Update ~20 tests | High |
| `tests/test_commands.py` | Update ~15 tests | High |
| `tests/test_ai_tools.py` | Update ~5 tests | Medium |
| `tests/integration/*.py` | Update ~10 tests | High |
| All other test files | Update assertions | Medium |

**Total Modified Code:** ~3,000 lines changed

### Deleted Files (2)

- `core/file_safety.py` (~350 lines)
- `services/notes.py` (~270 lines)

**Net Code Change:** ~+1,550 lines (~+30% codebase)

---

## Data Migration Strategy

### Migration Flow

```
┌─────────────────────┐
│  Detect JSON Files  │
│  tasks.json exists  │
│  todo.db missing    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Create Backups     │
│  tasks.json.pre_    │
│  notes.pre_/        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Generate UUIDs     │
│  Map: old_id → uuid │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Migrate Tasks      │
│  + Tags             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Migrate Notes      │
│  Parse YAML + MD    │
│  Update task links  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Migrate Settings   │
│  + AI History       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Verify Integrity   │
│  Row counts         │
│  Tag refs           │
│  Note links         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Migration Complete │
│  App starts normally│
└─────────────────────┘
```

### Verification Checklist

**After migration, verify:**

✅ Task count matches: `SELECT COUNT(*) FROM tasks` == `len(tasks.json)`
✅ Note count matches: `SELECT COUNT(*) FROM notes` == `len(glob('notes/*.md'))`
✅ All tags exist: No orphaned references in `task_tags` or `note_tags`
✅ All note links valid: All `task_notes.task_id` exist in `tasks` table
✅ Timestamps valid: All ISO timestamps parse correctly
✅ UUIDs valid: All UUIDs match v7 format
✅ Backup created: `tasks.json.pre_migration` exists

### Rollback Procedure

**If migration fails:**

1. **Automatic Rollback:** Migration errors delete `todo.db`, keep JSON intact
2. **Manual Rollback:**
   ```bash
   rm ~/.todo_cli.db
   cp tasks.json.pre_migration tasks.json
   git checkout v0.2.0
   ```
3. **Report Issue:** Include migration error log

---

## Risks & Mitigations

### 🔴 Critical Risks

#### 1. Data Loss During Migration

**Risk:** Corruption or data loss when converting JSON → SQLite

**Likelihood:** Medium
**Impact:** CRITICAL

**Mitigations:**
- ✅ Create full backup before migration (`tasks.json.pre_migration`)
- ✅ Verification checksums after import (row counts, tag refs)
- ✅ Dry-run mode for testing (`--dry-run` flag)
- ✅ Atomic transaction (rollback on any error)
- ✅ Keep JSON files untouched (read-only)
- ✅ Comprehensive migration tests with real data

**Contingency:**
- If verification fails → delete `todo.db`, restore from backup
- User can retry migration or report issue

#### 2. UUID Display Confusion

**Risk:** Users confused by UUID format, can't reference tasks

**Likelihood:** High
**Impact:** HIGH

**Mitigations:**
- ✅ Display only first 8 chars in UI (`019c4f2a`)
- ✅ Support prefix matching (min 8 chars)
- ✅ Autocomplete with UUID prefix highlight
- ✅ Error message if prefix ambiguous
- ✅ Documentation with examples

**Contingency:**
- Add `--use-short-ids` flag to show sequential IDs (internal mapping)

### 🟡 Medium Risks

#### 3. Performance Regression

**Risk:** SQLite slower than JSON for small datasets

**Likelihood:** Low
**Impact:** MEDIUM

**Mitigations:**
- ✅ Keep in-memory caching (same as before)
- ✅ Add database indices on frequently queried columns
- ✅ Use prepared statements (cached query plans)
- ✅ WAL mode for better concurrency
- ✅ Benchmark before/after with real data

**Target Performance:**
- Load 100 tasks: <10ms
- Load 1000 tasks: <50ms
- Filter 1000 tasks: <20ms

**Contingency:**
- If slower than JSON → optimize queries, add more indices
- Profile with `EXPLAIN QUERY PLAN`

#### 4. Test Suite Overhaul Effort

**Risk:** Updating 70+ tests takes longer than expected

**Likelihood:** High
**Impact:** MEDIUM (delays release)

**Mitigations:**
- ✅ Create reusable SQLite fixtures in `conftest.py`
- ✅ Update tests incrementally (module by module)
- ✅ Keep backward compat tests for JSON import
- ✅ Use in-memory SQLite for faster tests (`:memory:`)

**Contingency:**
- Prioritize core tests (state, commands, integration)
- Ship with known test gaps, fix in v1.0.1

#### 5. Backup Strategy Complexity

**Risk:** Users lose human-readable backups (JSON → binary SQLite)

**Likelihood:** Medium
**Impact:** MEDIUM

**Mitigations:**
- ✅ Provide `export json` command for human-readable backups
- ✅ SQLite built-in backup API (`.backup()` command)
- ✅ Document backup strategy in README
- ✅ Auto-export on major operations (optional)

**Contingency:**
- Add periodic auto-export to JSON (weekly)

### 🟢 Low Risks

#### 6. Concurrency Issues

**Risk:** Multiple app instances corrupt database

**Likelihood:** Low (single-user app)
**Impact:** HIGH (data corruption)

**Mitigations:**
- ✅ SQLite WAL mode (better concurrency)
- ✅ Retry on `SQLITE_BUSY` errors (5 attempts)
- ✅ Transaction timeouts (5 seconds, like current file locks)
- ✅ Document: "Don't run multiple instances"

**Contingency:**
- Add file lock on database (like old `SafeFileManager`)

#### 7. Supabase Schema Mismatch (Future)

**Risk:** SQLite schema doesn't match PostgreSQL when adding sync

**Likelihood:** Low (planning ahead)
**Impact:** MEDIUM (schema migration needed)

**Mitigations:**
- ✅ Design SQLite schema to mirror PostgreSQL types
- ✅ Use TEXT for timestamps (ISO format, portable)
- ✅ Use standard SQLite types (TEXT, INTEGER, REAL)
- ✅ Test schema export to PostgreSQL before sync feature
- ✅ Add `sync_status` and `version` fields now

**Contingency:**
- If mismatch → write schema migration tool in v1.1.0

#### 8. External Tool Breakage

**Risk:** User scripts that parse `tasks.json` break

**Likelihood:** Low (unknown number)
**Impact:** MEDIUM (user frustration)

**Mitigations:**
- ✅ Provide `export json` command (same format as old `tasks.json`)
- ✅ Keep JSON export format identical
- ✅ Document migration with upgrade guide
- ✅ Add `--legacy-json` flag for emergency fallback (v1.0.1)

**Contingency:**
- Survey users about external scripts
- Provide JSON export in cron job

---

## Success Criteria

**Must Have (v1.0.0 Release Blockers):**

✅ All existing tasks migrated with **zero data loss**
✅ All existing notes migrated with **zero data loss**
✅ All 70+ tests passing with SQLite backend
✅ Migration completes in **<5 seconds** for typical datasets (<1000 tasks)
✅ Performance **equal or better** than JSON (load time <50ms)
✅ Schema ready for future Supabase sync (no breaking changes needed)
✅ Comprehensive migration guide for users
✅ Auto-migration on first run works flawlessly

**Should Have (v1.0.0):**

✅ UUID prefix matching in all commands
✅ Export to JSON command for backups
✅ Migration dry-run mode
✅ Performance benchmarks documented
✅ Integration tests with real data

**Nice to Have (v1.0.1+):**

- Auto-export to JSON on schedule
- Short ID aliases for UUIDs (like git short SHAs)
- Database vacuum/optimize command
- Database integrity check command
- Migration rollback command

---

## Version Bump Rationale

**MAJOR version bump: v0.2.0 → v1.0.0**

### Why MAJOR?

**Breaking Changes:**
1. **Task IDs change format:** INTEGER → UUID (breaks external scripts)
2. **Data location changes:** `tasks.json` → `~/.todo_cli.db`
3. **Notes storage changes:** `notes/*.md` → database table
4. **Backup strategy changes:** `.backup` files → SQLite backups
5. **CLI flag changes:** `--file` → `--db` (optional)

**Requires user action:**
- Migration process (automatic, but still a change)
- Update external scripts that parse `tasks.json`
- Learn UUID prefix matching

### Why v1.0.0 Specifically?

**Indicates production readiness:**
- Mature persistence layer (SQLite)
- Comprehensive test coverage
- Well-documented
- Battle-tested file safety → ACID transactions
- Ready for advanced features (Supabase sync)

**Semantic versioning:**
- v0.x = experimental, breaking changes expected
- v1.0 = stable API, backward compat maintained
- v1.x = only MINOR/PATCH changes (no more breaking changes)

---

## Supabase Sync Preparation

### Future Sync Architecture (v1.1.0+)

```
┌──────────────────┐         ┌──────────────────┐
│   Local SQLite   │ ◄─────► │ Supabase Postgres│
│   (todo.db)      │  Sync   │  (Cloud)         │
└──────────────────┘         └──────────────────┘
        │                             │
        │ Read/Write                  │ Read/Write
        ▼                             ▼
┌──────────────────┐         ┌──────────────────┐
│   Device A       │         │   Device B       │
│   (User's PC)    │         │   (User's Phone) │
└──────────────────┘         └──────────────────┘
```

### Sync-Ready Schema Features (Implemented in v1.0.0)

**1. UUIDs (Global Uniqueness)**
- No ID conflicts when merging devices
- Time-ordered (UUID v7) for efficient indexing

**2. Version Tracking (Optimistic Locking)**
- Detect conflicts: local version ≠ remote version
- Resolution strategies: last-write-wins, manual merge

**3. Soft Deletes**
- `deleted_at` timestamp instead of hard deletes
- Know what was deleted when (sync reconciliation)

**4. Comprehensive Timestamps**
- `created_at` - When created (never changes)
- `updated_at` - Last modification (conflict detection)
- `deleted_at` - When soft-deleted (sync reconciliation)
- `last_synced_at` - Last successful sync (future)

**5. Sync Status Tracking**
- `local` - Not yet synced to Supabase
- `synced` - In sync with Supabase
- `conflict` - Conflict detected, needs resolution
- `error` - Sync failed, retry later

### PostgreSQL Schema (Supabase Target)

**Same structure, PostgreSQL-specific types:**

```sql
-- tasks table (PostgreSQL)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- Native UUID
    name TEXT NOT NULL,
    -- ... same fields ...
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- Native timestamp
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,                         -- Nullable
    version INTEGER NOT NULL DEFAULT 1
);

-- Indices (same as SQLite)
CREATE INDEX idx_tasks_updated_at ON tasks(updated_at DESC);
```

**Migration Strategy (SQLite → PostgreSQL):**
- TEXT timestamps → TIMESTAMPTZ (parse ISO format)
- INTEGER → BIGINT (if needed)
- BOOLEAN → BOOLEAN (same)
- Foreign keys → Foreign keys (same)

**Sync Algorithm (v1.1.0):**

1. **Pull from Supabase:**
   ```sql
   SELECT * FROM tasks WHERE updated_at > :last_sync_time
   ```

2. **Compare versions:**
   - If remote version > local version → update local
   - If local version > remote version → push to remote
   - If equal → no change
   - If conflict (both changed) → mark as `conflict`

3. **Push to Supabase:**
   ```sql
   INSERT INTO tasks (...) VALUES (...)
   ON CONFLICT (id) DO UPDATE SET
     name = EXCLUDED.name,
     version = version + 1,
     updated_at = NOW()
   WHERE tasks.version = EXCLUDED.version - 1  -- Optimistic lock
   ```

4. **Conflict Resolution:**
   - Show user both versions
   - Let user pick: "Keep local" | "Keep remote" | "Merge"

---

## Timeline & Milestones

### Week 1: Database Layer (Oct 29 - Nov 5)
- [ ] Create `core/database.py` with schema
- [ ] Implement all repository classes
- [ ] Write 30+ unit tests
- [ ] **Milestone:** Repository layer complete, all tests passing

### Week 2: Migration Tool (Nov 6 - Nov 12)
- [ ] Create `migrations/migrate_json_to_sqlite.py`
- [ ] Update `models/` with UUID, version, sync fields
- [ ] Update `core/state.py` to use repositories
- [ ] Implement auto-migration on startup
- [ ] **Milestone:** Migration tool complete, verified with real data

### Week 3: Update Consumers (Nov 13 - Nov 19)
- [ ] Update all widgets (task_table, note_table, forms)
- [ ] Update all commands (UUID parsing)
- [ ] Update AI tools (UUID schemas)
- [ ] Update both UIs (Textual + Rich)
- [ ] **Milestone:** App fully functional with SQLite

### Week 4: Testing & Cleanup (Nov 20 - Nov 26)
- [ ] Update all 70+ tests
- [ ] Add migration tests
- [ ] Integration testing with real data
- [ ] Performance benchmarks
- [ ] Remove deprecated code
- [ ] Documentation updates
- [ ] **Milestone:** Ready for v1.0.0 release

### Release: v1.0.0 (Nov 27)
- [ ] Create release tag
- [ ] Update CHANGELOG.md
- [ ] Publish release notes
- [ ] Announce migration guide

---

## Open Questions

1. **UUID Display Length:**
   - Current plan: 8 chars (`019c4f2a`)
   - Alternative: 12 chars (`019c4f2a-1234`)
   - Decision: Start with 8, extend if collisions occur

2. **Short ID Aliases:**
   - Should we add sequential "short IDs" for easier reference?
   - Example: Task #1, #2, #3 (internal mapping to UUIDs)
   - Decision: Not in v1.0.0, consider for v1.0.1 based on user feedback

3. **Database Location:**
   - Current plan: `~/.todo_cli.db` (user home directory)
   - Alternative: `./.todo.db` (project directory, like git)
   - Decision: User home (portable, survives project deletions)

4. **Note File Cleanup:**
   - Should we auto-delete `notes/*.md` after migration?
   - Decision: Keep as backup, add note to delete manually

5. **Export Command Frequency:**
   - Should `export json` run automatically?
   - Decision: Manual only in v1.0.0, consider auto-export in v1.0.1

---

## Dependencies

**New Dependencies:**
- **sqlite3:** Built-in Python module (no install needed)
- **uuid:** Built-in Python module (no install needed)

**Optional (Consider):**
- **sqlite-utils:** CLI tool for database inspection (`pip install sqlite-utils`)
  - Useful for debugging, not required for app
- **pydantic:** Data validation (if we want strict schema validation)
  - Not needed initially, consider for sync feature

**No Breaking Changes to Dependencies!**

---

## Communication Plan

### User Announcement (Pre-Release)

**Subject:** Important: v1.0.0 Migration to SQLite

**Body:**
```
The upcoming v1.0.0 release introduces SQLite as the persistence layer,
replacing JSON files. This is a **breaking change** that requires migration.

What You Need to Know:
✅ Migration is automatic on first run
✅ Your data will be backed up (tasks.json.pre_migration)
✅ Performance improvements for large datasets
✅ Prepares for Supabase sync (coming in v1.1.0)

Action Required:
1. Update to v1.0.0: `git pull && pip install -r requirements.txt`
2. Run the app: `python main.py`
3. Migration happens automatically
4. Verify your tasks are present

Rollback:
If you encounter issues:
1. Report the issue (attach migration error log)
2. Rollback: `git checkout v0.2.0`
3. Restore: `cp tasks.json.pre_migration tasks.json`

Questions? See MIGRATION_GUIDE_SQLITE.md
```

### Post-Release (v1.0.0)

**Monitor for issues:**
- Migration failures (ask for error logs)
- Performance regressions (ask for benchmarks)
- UUID confusion (improve docs)

**Collect feedback:**
- Survey: "How was the migration experience?"
- Feature requests: "What would improve UUID usage?"

---

## Summary

This task file outlines a **3-4 week migration** from JSON to SQLite with:

✅ **Sync-ready schema** (UUIDs, versions, soft deletes)
✅ **Complete migration tool** with verification
✅ **Zero data loss guarantee** through comprehensive testing
✅ **Performance parity** with JSON baseline
✅ **Future-proof** for Supabase sync in v1.1.0

**Next Steps:**
1. Review and approve this plan
2. Create feature branch: `feat/sqlite-migration`
3. Start Week 1 implementation
4. Daily commits with incremental progress

**Questions?** Review this file and provide feedback before starting.

---

**End of Task File**
