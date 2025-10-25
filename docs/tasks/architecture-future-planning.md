# 🏗️ Ultra-Deep Scalable Architecture for Todo-CLI Evolution

**Version:** 1.0
**Date:** October 23, 2025
**Status:** Planning Document
**Author:** Architecture Planning Session

---

## 📋 Executive Summary

Transform todo-cli from a local JSON-based application into an **offline-first collaborative multi-platform system** with LangChain AI capabilities, while maintaining full backward compatibility.

### Key Requirements
- ✅ **Offline-first**: Must work without internet connection
- ✅ **Collaboration**: Multi-user from day 1 with permissions
- ✅ **Gradual migration**: No breaking changes for existing users
- ✅ **Multi-platform**: CLI, Web App, Mobile App, API
- ✅ **LangChain integration**: AI tools for task manipulation
- ✅ **Real-time sync**: Changes propagate across devices/users

### Architecture Philosophy
> **"Local-first, cloud-enhanced"** - Every operation works offline instantly, syncs when online, and handles conflicts intelligently.

---

## 🎯 Architectural Principles

### 1. **Hexagonal Architecture (Ports & Adapters)**

```
┌─────────────────────────────────────┐
│     Core Domain Logic (Pure)        │
│  - Task, Workspace, User models     │
│  - Business rules & validation      │
└─────────────┬───────────────────────┘
              │
        [Repository Interface]  ← Abstract boundary
              │
    ┌─────────┴─────────┐
    │                   │
[JSON Adapter]    [SQLite Adapter]    [Supabase Adapter]
    │                   │                     │
  tasks.json      local.db              Cloud Postgres
```

**Benefits:**
- Core logic never depends on infrastructure
- Swap storage implementations without changing business logic
- Easy to test with in-memory implementations
- Future-proof for new storage backends

### 2. **Local-First with Eventual Consistency**

```
┌─────────────────┐         ┌─────────────────┐
│  Local SQLite   │ ←────→  │  Sync Engine    │ ←────→ ┌─────────────────┐
│  (Embedded)     │         │  (Background)   │        │ Supabase Cloud  │
└────────┬────────┘         └─────────────────┘        └────────┬────────┘
         │                                                        │
    Instant Response                                      When Online +
    Works Offline                                         Realtime Updates
```

**Core Principles:**
- All operations write to local DB first (instant response)
- Sync engine reconciles in background when online
- Conflict resolution using hybrid CRDTs + Last-Write-Wins
- Vector clocks track causality
- Optimistic UI updates with rollback on failure

### 3. **Service Layer Abstraction**

```
┌───────────────────────────────────────────────────┐
│        Presentation Layer (Platform-specific)      │
│   CLI (Textual)  │  Web (Next.js)  │  Mobile (RN) │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│              Service Layer (Shared)                │
│  - TaskService                                     │
│  - WorkspaceService    ← LangChain tools call here │
│  - AIService                                       │
│  - SyncService                                     │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│         Repository Interface (Abstract)            │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│      Storage Adapters (Implementations)            │
│  JSON  │  SQLite  │  Supabase  │  Hybrid          │
└───────────────────────────────────────────────────┘
```

**Why Service Layer?**
- Business logic lives in ONE place
- All platforms share the same code
- LangChain tools are thin wrappers around services
- Easy to add new platforms without duplicating logic

---

## 📦 Detailed Layer Architecture (Bottom-Up)

### **Layer 1: Domain Models** (Pure Python, Zero Dependencies)

**Location:** `models/`

#### Enhanced Task Model
```python
# models/task.py (enhanced for distributed systems)
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import uuid

@dataclass
class Task:
    # Identity (UUID for distributed systems, not auto-increment int!)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str = ""  # Multi-workspace support

    # Core fields (existing)
    name: str = ""
    comment: str = ""
    description: str = ""
    priority: int = 2  # 1=high, 2=medium, 3=low
    done: bool = False
    tags: List[str] = field(default_factory=list)

    # Collaboration fields (NEW)
    created_by: str = ""  # User ID
    assigned_to: List[str] = field(default_factory=list)  # User IDs

    # Sync metadata (NEW - critical for offline-first)
    version: int = 1  # Incremented on each change (conflict detection)
    last_modified: str = ""  # ISO timestamp
    device_id: str = ""  # Which device made the last change
    deleted: bool = False  # Soft delete (hard deletes can't sync reliably)

    # Timestamps
    created_at: str = ""  # ISO timestamp
    completed_at: str = ""  # ISO timestamp when marked done

    def __post_init__(self):
        """Initialize timestamps and normalize data"""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.last_modified:
            self.last_modified = self.created_at

        # Normalize tags (lowercase, trim)
        self.tags = [t.strip().lower() for t in self.tags if t.strip()]

    def mark_done(self, user_id: str, device_id: str):
        """Mark task as complete (updates metadata)"""
        self.done = True
        self.completed_at = datetime.utcnow().isoformat()
        self.last_modified = self.completed_at
        self.version += 1
        self.device_id = device_id

    def add_tag(self, tag: str) -> bool:
        """Add tag (max 3), returns True if added"""
        tag = tag.strip().lower()
        if tag and tag not in self.tags and len(self.tags) < 3:
            self.tags.append(tag)
            return True
        return False
```

#### Workspace Model (NEW)
```python
# models/workspace.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class WorkspaceMember:
    user_id: str
    role: str  # 'owner', 'admin', 'member', 'viewer'
    joined_at: str

@dataclass
class Workspace:
    id: str
    name: str
    owner_id: str
    members: List[WorkspaceMember] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def can_user_write(self, user_id: str) -> bool:
        """Check if user has write permission"""
        for member in self.members:
            if member.user_id == user_id:
                return member.role in ('owner', 'admin', 'member')
        return False

    def can_user_admin(self, user_id: str) -> bool:
        """Check if user has admin permission"""
        for member in self.members:
            if member.user_id == user_id:
                return member.role in ('owner', 'admin')
        return False
```

#### User Model (NEW)
```python
# models/user.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: str = ""

    # Local user for offline mode
    @staticmethod
    def local_user():
        """Create local user for offline-only usage"""
        return User(
            id="local",
            email="local@localhost",
            name="Local User"
        )
```

#### Sync Log Entry (NEW)
```python
# models/sync_log.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SyncLogEntry:
    """Track pending changes for sync"""
    id: str
    entity_type: str  # 'task', 'workspace', etc.
    entity_id: str
    operation: str  # 'create', 'update', 'delete'
    data: dict  # JSON of the entity
    created_at: str = ""
    synced: bool = False
    attempts: int = 0
    last_error: str = ""
```

**Key Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| **UUIDs not integers** | Distributed ID generation without coordination |
| **Soft deletes** | Sync can propagate deletions reliably |
| **Version numbers** | Simple conflict detection (higher wins) |
| **device_id** | Track change origin for debugging |
| **Workspace isolation** | Multi-tenancy, data segregation |
| **ISO timestamps** | Portable, parseable, timezone-aware |

---

### **Layer 2: Repository Interface** (Abstract Contracts)

**Location:** `repositories/interfaces.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from models.task import Task
from models.workspace import Workspace
from models.user import User

class ITaskRepository(ABC):
    """
    Abstract interface for task storage
    All storage adapters must implement these methods
    """

    @abstractmethod
    async def get_all(self, workspace_id: str, include_deleted: bool = False) -> List[Task]:
        """Get all tasks in workspace"""
        pass

    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """Get single task by ID"""
        pass

    @abstractmethod
    async def save(self, task: Task) -> Task:
        """Create or update task (upsert)"""
        pass

    @abstractmethod
    async def delete(self, task_id: str, hard_delete: bool = False) -> bool:
        """
        Delete task
        hard_delete=False: soft delete (set deleted=True)
        hard_delete=True: permanent removal (use carefully!)
        """
        pass

    @abstractmethod
    async def get_changes_since(self, workspace_id: str, since_version: int) -> List[Task]:
        """
        Get all tasks modified after given version
        Critical for sync engine
        """
        pass

    @abstractmethod
    async def search(self, workspace_id: str, query: str, filters: dict = {}) -> List[Task]:
        """
        Full-text search with filters
        filters example: {'priority': 1, 'done': False, 'tags': ['urgent']}
        """
        pass

    @abstractmethod
    async def bulk_upsert(self, tasks: List[Task]) -> int:
        """
        Efficient bulk insert/update for sync
        Returns number of tasks affected
        """
        pass

class IWorkspaceRepository(ABC):
    """Abstract interface for workspace storage"""

    @abstractmethod
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        pass

    @abstractmethod
    async def get_user_workspaces(self, user_id: str) -> List[Workspace]:
        """Get all workspaces user has access to"""
        pass

    @abstractmethod
    async def save(self, workspace: Workspace) -> Workspace:
        pass

    @abstractmethod
    async def add_member(self, workspace_id: str, user_id: str, role: str) -> bool:
        pass

    @abstractmethod
    async def remove_member(self, workspace_id: str, user_id: str) -> bool:
        pass

class IUserRepository(ABC):
    """Abstract interface for user storage"""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        pass

class ISyncLogRepository(ABC):
    """Track pending sync operations"""

    @abstractmethod
    async def add_pending(self, entry: SyncLogEntry) -> None:
        """Add operation to sync queue"""
        pass

    @abstractmethod
    async def get_pending(self, limit: int = 100) -> List[SyncLogEntry]:
        """Get operations waiting to sync"""
        pass

    @abstractmethod
    async def mark_synced(self, entry_id: str) -> None:
        """Mark operation as successfully synced"""
        pass

    @abstractmethod
    async def mark_failed(self, entry_id: str, error: str) -> None:
        """Mark sync as failed (will retry)"""
        pass
```

**Benefits of Repository Pattern:**
- **Testability**: Mock implementations for unit tests
- **Flexibility**: Swap storage without changing business logic
- **Clear contracts**: Interface documents exactly what storage must do
- **Migration path**: Old and new implementations can coexist

---

### **Layer 3: Storage Adapters** (Concrete Implementations)

**Location:** `repositories/adapters/`

#### **A. LocalJsonRepository** (Backward Compatibility - Phase 1)

```python
# repositories/adapters/json_adapter.py
import json
from pathlib import Path
from typing import List, Optional
from repositories.interfaces import ITaskRepository
from models.task import Task

class LocalJsonRepository(ITaskRepository):
    """
    Maintains backward compatibility with existing tasks.json
    Used during gradual migration period

    Limitations:
    - No sync metadata
    - No workspace isolation
    - No efficient search
    """

    def __init__(self, filepath: str = "tasks.json"):
        self.filepath = Path(filepath)

    async def get_all(self, workspace_id: str, include_deleted: bool = False) -> List[Task]:
        """Load all tasks from JSON file"""
        if not self.filepath.exists():
            return []

        with open(self.filepath, 'r') as f:
            data = json.load(f)

        tasks = [Task(**item) for item in data]

        # Filter by workspace if specified
        if workspace_id:
            tasks = [t for t in tasks if t.workspace_id == workspace_id]

        # Filter deleted unless requested
        if not include_deleted:
            tasks = [t for t in tasks if not t.deleted]

        return tasks

    async def save(self, task: Task) -> Task:
        """Save task to JSON file"""
        tasks = await self.get_all(workspace_id="", include_deleted=True)

        # Update or append
        found = False
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                found = True
                break

        if not found:
            tasks.append(task)

        # Write back to file
        with open(self.filepath, 'w') as f:
            json.dump([t.__dict__ for t in tasks], f, indent=2)

        return task

    async def get_changes_since(self, workspace_id: str, since_version: int) -> List[Task]:
        """JSON adapter doesn't support versioning"""
        # Return all tasks (inefficient, but works)
        return await self.get_all(workspace_id)

    async def search(self, workspace_id: str, query: str, filters: dict = {}) -> List[Task]:
        """Simple search by name"""
        tasks = await self.get_all(workspace_id)

        # Simple text search
        if query:
            query_lower = query.lower()
            tasks = [t for t in tasks if query_lower in t.name.lower()]

        # Apply filters
        if 'done' in filters:
            tasks = [t for t in tasks if t.done == filters['done']]

        if 'priority' in filters:
            tasks = [t for t in tasks if t.priority == filters['priority']]

        return tasks
```

#### **B. LocalSQLiteRepository** (Offline Database - Phase 2)

```python
# repositories/adapters/sqlite_adapter.py
import sqlite3
import json
from typing import List, Optional
from repositories.interfaces import ITaskRepository
from models.task import Task

class LocalSQLiteRepository(ITaskRepository):
    """
    Local SQLite database for offline-first architecture

    Benefits:
    - Fast querying and indexing
    - Transactions (ACID guarantees)
    - Full-text search
    - Sync metadata tracking
    """

    def __init__(self, db_path: str = "local.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                comment TEXT,
                description TEXT,
                priority INTEGER DEFAULT 2,
                done BOOLEAN DEFAULT 0,
                tags TEXT,  -- JSON array
                created_by TEXT,
                assigned_to TEXT,  -- JSON array
                version INTEGER DEFAULT 1,
                last_modified TEXT,
                device_id TEXT,
                deleted BOOLEAN DEFAULT 0,
                created_at TEXT,
                completed_at TEXT,

                -- Indexes for performance
                INDEX idx_workspace (workspace_id),
                INDEX idx_version (workspace_id, version),
                INDEX idx_deleted (deleted)
            )
        """)

        # Full-text search virtual table
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                id, name, description, content='tasks', content_rowid='rowid'
            )
        """)

        conn.commit()
        conn.close()

    async def save(self, task: Task) -> Task:
        """Upsert task"""
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
            INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                comment=excluded.comment,
                description=excluded.description,
                priority=excluded.priority,
                done=excluded.done,
                tags=excluded.tags,
                assigned_to=excluded.assigned_to,
                version=excluded.version,
                last_modified=excluded.last_modified,
                device_id=excluded.device_id,
                deleted=excluded.deleted,
                completed_at=excluded.completed_at
        """, (
            task.id, task.workspace_id, task.name, task.comment,
            task.description, task.priority, task.done,
            json.dumps(task.tags), task.created_by,
            json.dumps(task.assigned_to), task.version,
            task.last_modified, task.device_id, task.deleted,
            task.created_at, task.completed_at
        ))

        # Update FTS index
        conn.execute("""
            INSERT INTO tasks_fts(id, name, description)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description
        """, (task.id, task.name, task.description))

        conn.commit()
        conn.close()

        return task

    async def get_changes_since(self, workspace_id: str, since_version: int) -> List[Task]:
        """Get tasks modified after given version (for sync)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT * FROM tasks
            WHERE workspace_id = ? AND version > ?
            ORDER BY version ASC
        """, (workspace_id, since_version))

        tasks = [self._row_to_task(row) for row in cursor.fetchall()]
        conn.close()

        return tasks

    async def search(self, workspace_id: str, query: str, filters: dict = {}) -> List[Task]:
        """Full-text search with filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Build query
        sql = "SELECT t.* FROM tasks t"
        params = []
        conditions = ["workspace_id = ?", "deleted = 0"]
        params.append(workspace_id)

        # Add FTS search
        if query:
            sql += " INNER JOIN tasks_fts fts ON t.id = fts.id"
            conditions.append("tasks_fts MATCH ?")
            params.append(query)

        # Add filters
        if 'done' in filters:
            conditions.append("done = ?")
            params.append(1 if filters['done'] else 0)

        if 'priority' in filters:
            conditions.append("priority = ?")
            params.append(filters['priority'])

        # Combine
        sql += " WHERE " + " AND ".join(conditions)

        cursor = conn.execute(sql, params)
        tasks = [self._row_to_task(row) for row in cursor.fetchall()]
        conn.close()

        return tasks

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert SQLite row to Task object"""
        return Task(
            id=row['id'],
            workspace_id=row['workspace_id'],
            name=row['name'],
            comment=row['comment'] or "",
            description=row['description'] or "",
            priority=row['priority'],
            done=bool(row['done']),
            tags=json.loads(row['tags']) if row['tags'] else [],
            created_by=row['created_by'] or "",
            assigned_to=json.loads(row['assigned_to']) if row['assigned_to'] else [],
            version=row['version'],
            last_modified=row['last_modified'],
            device_id=row['device_id'] or "",
            deleted=bool(row['deleted']),
            created_at=row['created_at'],
            completed_at=row['completed_at'] or ""
        )
```

#### **C. SupabaseRepository** (Cloud Storage - Phase 4)

```python
# repositories/adapters/supabase_adapter.py
from supabase import create_client, Client
from typing import List, Optional
from repositories.interfaces import ITaskRepository
from models.task import Task

class SupabaseRepository(ITaskRepository):
    """
    Supabase Postgres cloud storage

    Benefits:
    - Auth built-in (RLS for security)
    - Realtime subscriptions
    - REST API auto-generated
    - Scales horizontally
    """

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
        self.table = self.client.table('tasks')

    async def save(self, task: Task) -> Task:
        """Upsert task to Supabase"""
        data = {
            'id': task.id,
            'workspace_id': task.workspace_id,
            'name': task.name,
            'comment': task.comment,
            'description': task.description,
            'priority': task.priority,
            'done': task.done,
            'tags': task.tags,
            'created_by': task.created_by,
            'assigned_to': task.assigned_to,
            'version': task.version,
            'last_modified': task.last_modified,
            'device_id': task.device_id,
            'deleted': task.deleted,
            'created_at': task.created_at,
            'completed_at': task.completed_at
        }

        # Upsert (insert or update on conflict)
        result = self.table.upsert(data).execute()

        return task

    async def get_all(self, workspace_id: str, include_deleted: bool = False) -> List[Task]:
        """Get all tasks from Supabase"""
        query = self.table.select("*").eq('workspace_id', workspace_id)

        if not include_deleted:
            query = query.eq('deleted', False)

        result = query.execute()

        return [Task(**item) for item in result.data]

    async def get_changes_since(self, workspace_id: str, since_version: int) -> List[Task]:
        """Get changes for sync"""
        result = (self.table
                 .select("*")
                 .eq('workspace_id', workspace_id)
                 .gt('version', since_version)
                 .order('version')
                 .execute())

        return [Task(**item) for item in result.data]

    async def search(self, workspace_id: str, query: str, filters: dict = {}) -> List[Task]:
        """Search using Supabase full-text search"""
        # Use Supabase text search
        q = (self.table
             .select("*")
             .eq('workspace_id', workspace_id)
             .eq('deleted', False))

        if query:
            q = q.text_search('name', query)

        if 'done' in filters:
            q = q.eq('done', filters['done'])

        if 'priority' in filters:
            q = q.eq('priority', filters['priority'])

        result = q.execute()
        return [Task(**item) for item in result.data]

    def subscribe_to_changes(self, workspace_id: str, callback):
        """
        Subscribe to realtime changes
        Callback receives: {'event': 'INSERT'|'UPDATE'|'DELETE', 'data': {...}}
        """
        channel = self.client.channel(f'workspace-{workspace_id}')

        channel.on_postgres_changes(
            event='*',
            schema='public',
            table='tasks',
            filter=f'workspace_id=eq.{workspace_id}',
            callback=callback
        ).subscribe()

        return channel
```

#### **D. HybridRepository** (Sync Coordinator - Phase 5)

```python
# repositories/adapters/hybrid_adapter.py
from typing import List, Optional
from repositories.interfaces import ITaskRepository
from repositories.adapters.sqlite_adapter import LocalSQLiteRepository
from repositories.adapters.supabase_adapter import SupabaseRepository
from services.sync_service import SyncEngine
from models.task import Task

class HybridRepository(ITaskRepository):
    """
    Coordinates local and remote storage
    - Write to local immediately (instant response)
    - Queue for background sync to cloud
    - Handle conflicts on sync
    """

    def __init__(self,
                 local: LocalSQLiteRepository,
                 remote: SupabaseRepository,
                 sync_engine: SyncEngine):
        self.local = local
        self.remote = remote
        self.sync = sync_engine

    async def save(self, task: Task) -> Task:
        """
        Save to local first (instant), queue for remote sync
        """
        # Increment version for this change
        task.version += 1

        # Write to local DB (instant)
        await self.local.save(task)

        # Queue for background sync to cloud
        await self.sync.queue_task_upload(task)

        return task

    async def get_all(self, workspace_id: str, include_deleted: bool = False) -> List[Task]:
        """Read from local (fast)"""
        return await self.local.get_all(workspace_id, include_deleted)

    async def get_by_id(self, task_id: str) -> Optional[Task]:
        """Read from local (fast)"""
        return await self.local.get_by_id(task_id)

    async def search(self, workspace_id: str, query: str, filters: dict = {}) -> List[Task]:
        """Search local first (instant results)"""
        return await self.local.search(workspace_id, query, filters)

    async def sync_now(self, workspace_id: str):
        """
        Manually trigger sync (called on app start, or when user requests)
        """
        await self.sync.sync_workspace(workspace_id)
```

---

### **Layer 4: Service Layer** (Business Logic)

**Location:** `services/`

#### **TaskService** (Core Business Logic)

```python
# services/task_service.py
from typing import List, Optional
from repositories.interfaces import ITaskRepository
from services.auth_service import AuthService
from models.task import Task
from datetime import datetime
import uuid

class TaskService:
    """
    High-level task operations
    All platforms use this service (CLI, API, Web, Mobile)
    """

    def __init__(self,
                 repo: ITaskRepository,
                 auth: AuthService):
        self.repo = repo
        self.auth = auth

    async def create_task(self,
                         workspace_id: str,
                         name: str,
                         priority: int = 2,
                         tags: List[str] = [],
                         user_id: str = "",
                         comment: str = "",
                         description: str = "") -> Task:
        """
        Create new task with validation and permissions

        Raises:
            PermissionError: User can't write to workspace
            ValueError: Invalid input
        """
        # Validate permission
        if not await self.auth.can_write(user_id, workspace_id):
            raise PermissionError(f"User {user_id} can't write to workspace")

        # Validate inputs
        if not name.strip():
            raise ValueError("Task name cannot be empty")

        if priority not in [1, 2, 3]:
            raise ValueError("Priority must be 1, 2, or 3")

        if len(tags) > 3:
            raise ValueError("Maximum 3 tags allowed")

        # Create task
        task = Task(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            name=name.strip(),
            comment=comment.strip(),
            description=description.strip(),
            priority=priority,
            tags=[t.strip().lower() for t in tags if t.strip()],
            created_by=user_id,
            version=1,
            last_modified=datetime.utcnow().isoformat(),
            device_id=self._get_device_id(),
            created_at=datetime.utcnow().isoformat()
        )

        # Save to repository
        return await self.repo.save(task)

    async def update_task(self,
                         task_id: str,
                         updates: dict,
                         user_id: str) -> Task:
        """
        Update existing task

        Args:
            task_id: Task ID to update
            updates: Dictionary of fields to update
            user_id: User making the change

        Raises:
            ValueError: Task not found
            PermissionError: User can't edit task
        """
        # Get existing task
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Check permission
        if not await self.auth.can_write(user_id, task.workspace_id):
            raise PermissionError("User can't edit this task")

        # Apply updates
        if 'name' in updates:
            task.name = updates['name'].strip()
        if 'priority' in updates:
            task.priority = updates['priority']
        if 'tags' in updates:
            task.tags = [t.strip().lower() for t in updates['tags'] if t.strip()][:3]
        if 'comment' in updates:
            task.comment = updates['comment'].strip()
        if 'description' in updates:
            task.description = updates['description'].strip()

        # Update metadata
        task.version += 1
        task.last_modified = datetime.utcnow().isoformat()
        task.device_id = self._get_device_id()

        # Save
        return await self.repo.save(task)

    async def mark_done(self, task_id: str, user_id: str) -> Task:
        """Mark task as complete"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if not await self.auth.can_write(user_id, task.workspace_id):
            raise PermissionError("User can't modify this task")

        task.mark_done(user_id, self._get_device_id())
        return await self.repo.save(task)

    async def search_tasks(self,
                          workspace_id: str,
                          query: str = "",
                          filters: dict = {},
                          user_id: str = "") -> List[Task]:
        """
        Search tasks with full-text and filters

        filters examples:
            {'done': False, 'priority': 1}
            {'tags': ['urgent'], 'assigned_to': 'user123'}
        """
        # Check permission
        if not await self.auth.can_read(user_id, workspace_id):
            raise PermissionError("User can't access this workspace")

        return await self.repo.search(workspace_id, query, filters)

    async def get_task_summary(self, workspace_id: str, user_id: str) -> dict:
        """
        Get workspace summary (for AI insights or dashboard)

        Returns:
            {
                'total': 50,
                'done': 20,
                'pending': 30,
                'by_priority': {1: 5, 2: 15, 3: 10},
                'by_tag': {'urgent': 8, 'backend': 12, ...}
            }
        """
        if not await self.auth.can_read(user_id, workspace_id):
            raise PermissionError("User can't access workspace")

        tasks = await self.repo.get_all(workspace_id)

        summary = {
            'total': len(tasks),
            'done': sum(1 for t in tasks if t.done),
            'pending': sum(1 for t in tasks if not t.done),
            'by_priority': {},
            'by_tag': {}
        }

        # Count by priority
        for task in tasks:
            if not task.done:
                summary['by_priority'][task.priority] = \
                    summary['by_priority'].get(task.priority, 0) + 1

        # Count by tag
        for task in tasks:
            for tag in task.tags:
                summary['by_tag'][tag] = summary['by_tag'].get(tag, 0) + 1

        return summary

    def _get_device_id(self) -> str:
        """Get unique device identifier"""
        import platform
        import hashlib

        # Hash hostname for privacy
        hostname = platform.node()
        return hashlib.md5(hostname.encode()).hexdigest()[:12]
```

#### **AIService** (LangChain Integration)

```python
# services/ai_service.py
from typing import List, Dict, Any
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from services.task_service import TaskService
from services.workspace_service import WorkspaceService
from models.task import Task

class AddTaskInput(BaseModel):
    """Schema for add_task tool"""
    name: str = Field(..., description="Task name (required)")
    priority: int = Field(2, description="Priority: 1=high, 2=medium, 3=low")
    tags: List[str] = Field(default_factory=list, description="Tags (max 3)")
    comment: str = Field("", description="Short comment")

class SearchTasksInput(BaseModel):
    """Schema for search_tasks tool"""
    query: str = Field("", description="Search query for task name/description")
    done: bool = Field(None, description="Filter by completion status")
    priority: int = Field(None, description="Filter by priority")

class AIService:
    """
    LangChain-powered AI assistant with tool calling
    Tools wrap service layer methods
    """

    def __init__(self,
                 task_service: TaskService,
                 workspace_service: WorkspaceService,
                 llm_model: str = "gpt-4o"):
        self.task_service = task_service
        self.workspace_service = workspace_service
        self.llm = ChatOpenAI(model=llm_model, temperature=0)

    def create_agent_for_workspace(self, workspace_id: str, user_id: str) -> AgentExecutor:
        """
        Create workspace-specific AI agent with tools

        Returns:
            AgentExecutor that can be used for Q&A
        """
        # Create tools with context bound
        tools = self._create_tools(workspace_id, user_id)

        # Create agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=tools,
            prompt=self._get_agent_prompt()
        )

        return AgentExecutor(agent=agent, tools=tools, verbose=False)

    def _create_tools(self, workspace_id: str, user_id: str) -> List[StructuredTool]:
        """Create LangChain tools that wrap service methods"""

        async def add_task_tool(name: str, priority: int = 2, tags: List[str] = [], comment: str = ""):
            """Add a new task to the workspace"""
            task = await self.task_service.create_task(
                workspace_id=workspace_id,
                name=name,
                priority=priority,
                tags=tags,
                user_id=user_id,
                comment=comment
            )
            return f"✅ Created task: {task.name} (ID: {task.id}, Priority: {task.priority})"

        async def search_tasks_tool(query: str = "", done: bool = None, priority: int = None):
            """Search tasks in the workspace"""
            filters = {}
            if done is not None:
                filters['done'] = done
            if priority is not None:
                filters['priority'] = priority

            tasks = await self.task_service.search_tasks(
                workspace_id=workspace_id,
                query=query,
                filters=filters,
                user_id=user_id
            )

            return self._format_tasks_for_llm(tasks)

        async def mark_done_tool(task_id: str):
            """Mark a task as complete"""
            task = await self.task_service.mark_done(task_id, user_id)
            return f"✅ Marked as done: {task.name}"

        async def get_summary_tool():
            """Get workspace task summary"""
            summary = await self.task_service.get_task_summary(workspace_id, user_id)
            return (
                f"📊 Workspace Summary:\n"
                f"Total: {summary['total']} | "
                f"Done: {summary['done']} | "
                f"Pending: {summary['pending']}\n"
                f"By Priority: {summary['by_priority']}\n"
                f"By Tag: {summary['by_tag']}"
            )

        # Build tool list
        tools = [
            StructuredTool.from_function(
                func=add_task_tool,
                name="add_task",
                description="Create a new task in the workspace",
                args_schema=AddTaskInput
            ),
            StructuredTool.from_function(
                func=search_tasks_tool,
                name="search_tasks",
                description="Search tasks by keywords or filters (done, priority)",
                args_schema=SearchTasksInput
            ),
            StructuredTool.from_function(
                func=mark_done_tool,
                name="mark_done",
                description="Mark a task as complete by its ID"
            ),
            StructuredTool.from_function(
                func=get_summary_tool,
                name="get_summary",
                description="Get overview of workspace tasks"
            )
        ]

        return tools

    def _format_tasks_for_llm(self, tasks: List[Task]) -> str:
        """Format tasks for LLM consumption"""
        if not tasks:
            return "No tasks found."

        output = f"Found {len(tasks)} tasks:\n\n"
        for task in tasks:
            status = "✅" if task.done else "❌"
            priority_icons = {1: "🔴", 2: "🟡", 3: "🟢"}
            priority = priority_icons.get(task.priority, "⚪")
            tags = ", ".join(task.tags) if task.tags else "no tags"

            output += f"{status} {priority} [{task.id[:8]}] {task.name}\n"
            output += f"   Tags: {tags} | Priority: {task.priority}\n"
            if task.comment:
                output += f"   Comment: {task.comment}\n"
            output += "\n"

        return output

    def _get_agent_prompt(self) -> str:
        """System prompt for the agent"""
        return """You are a helpful task management assistant.

You have access to tools to:
- Add tasks
- Search tasks
- Mark tasks as done
- Get workspace summaries

When the user asks to create a task, extract:
- Name (required)
- Priority (1=high, 2=medium, 3=low, default=2)
- Tags (optional, up to 3)
- Comment (optional)

When searching, use appropriate filters based on user intent.

Be concise and helpful. Use emojis for visual clarity."""
```

#### **SyncService** (Offline Sync Engine - Phase 5)

```python
# services/sync_service.py
import asyncio
from typing import List
from repositories.interfaces import ITaskRepository, ISyncLogRepository
from models.task import Task
from models.sync_log import SyncLogEntry
from datetime import datetime

class ConflictResolver:
    """Resolve conflicts when local and remote differ"""

    def resolve(self, local: Task, remote: Task) -> Task:
        """
        Resolve conflict between local and remote versions

        Strategy:
        1. Compare versions (higher wins for most fields)
        2. Merge mergeable fields (tags = union)
        3. Use timestamps for tie-breaking
        """
        if remote.version > local.version:
            # Remote is newer
            if not local.is_modified_locally():
                return remote  # Remote wins
            else:
                # Both modified, do field-level merge
                return self._field_merge(local, remote)

        # Local is newer or equal
        return local

    def _field_merge(self, local: Task, remote: Task) -> Task:
        """Merge fields intelligently"""
        merged = Task(id=local.id)

        # Name: last-write-wins by timestamp
        if local.last_modified >= remote.last_modified:
            merged.name = local.name
        else:
            merged.name = remote.name

        # Priority: last-write-wins
        if local.last_modified >= remote.last_modified:
            merged.priority = local.priority
        else:
            merged.priority = remote.priority

        # Tags: union (set CRDT - both edits preserved)
        merged.tags = list(set(local.tags) | set(remote.tags))[:3]

        # Done: if either marked done, consider done
        merged.done = local.done or remote.done
        if merged.done:
            # Use most recent completion time
            merged.completed_at = max(
                local.completed_at or "",
                remote.completed_at or ""
            )

        # Comments/description: prefer local if modified
        merged.comment = local.comment if local.comment else remote.comment
        merged.description = local.description if local.description else remote.description

        # Metadata
        merged.version = max(local.version, remote.version) + 1
        merged.last_modified = datetime.utcnow().isoformat()

        return merged

class SyncEngine:
    """
    Orchestrate bi-directional sync between local and remote

    Flow:
    1. Pull remote changes since last sync
    2. Apply to local with conflict resolution
    3. Push local changes to remote
    4. Update sync markers
    """

    def __init__(self,
                 local_repo: ITaskRepository,
                 remote_repo: ITaskRepository,
                 sync_log_repo: ISyncLogRepository):
        self.local = local_repo
        self.remote = remote_repo
        self.sync_log = sync_log_repo
        self.resolver = ConflictResolver()
        self._sync_in_progress = False

    async def sync_workspace(self, workspace_id: str, last_sync_version: int = 0):
        """
        Sync workspace bi-directionally

        Args:
            workspace_id: Workspace to sync
            last_sync_version: Version number of last sync (0 = full sync)
        """
        if self._sync_in_progress:
            print("Sync already in progress, skipping")
            return

        self._sync_in_progress = True

        try:
            # Phase 1: Pull remote changes
            print(f"📥 Pulling changes since version {last_sync_version}...")
            remote_changes = await self.remote.get_changes_since(
                workspace_id,
                last_sync_version
            )

            print(f"   Found {len(remote_changes)} remote changes")

            # Phase 2: Apply remote changes with conflict resolution
            conflicts_resolved = 0
            for remote_task in remote_changes:
                local_task = await self.local.get_by_id(remote_task.id)

                if local_task:
                    # Both exist, check for conflict
                    if local_task.version != remote_task.version:
                        # Conflict! Resolve it
                        merged = self.resolver.resolve(local_task, remote_task)
                        await self.local.save(merged)
                        conflicts_resolved += 1
                    else:
                        # No conflict, apply remote
                        await self.local.save(remote_task)
                else:
                    # New task from remote
                    await self.local.save(remote_task)

            if conflicts_resolved > 0:
                print(f"   ⚠️  Resolved {conflicts_resolved} conflicts")

            # Phase 3: Push local changes
            print(f"📤 Pushing local changes...")
            pending = await self.sync_log.get_pending(limit=100)

            pushed = 0
            for entry in pending:
                try:
                    # Get current state
                    task = await self.local.get_by_id(entry.entity_id)
                    if task:
                        # Push to remote
                        await self.remote.save(task)

                        # Mark as synced
                        await self.sync_log.mark_synced(entry.id)
                        pushed += 1
                except Exception as e:
                    # Mark failed (will retry later)
                    await self.sync_log.mark_failed(entry.id, str(e))

            print(f"   Pushed {pushed} changes")

            # Phase 4: Update sync marker
            # (Store last_sync_version in local settings)
            max_version = max([t.version for t in remote_changes] + [last_sync_version])
            # TODO: Save max_version to settings

            print(f"✅ Sync complete (new version: {max_version})")

        finally:
            self._sync_in_progress = False

    async def queue_task_upload(self, task: Task):
        """Queue task for upload on next sync"""
        entry = SyncLogEntry(
            id=str(uuid.uuid4()),
            entity_type='task',
            entity_id=task.id,
            operation='upsert',
            data=task.__dict__,
            created_at=datetime.utcnow().isoformat()
        )

        await self.sync_log.add_pending(entry)

    async def start_background_sync(self, workspace_id: str, interval_seconds: int = 60):
        """
        Start background sync loop
        Runs every `interval_seconds` when online
        """
        last_version = 0  # TODO: Load from settings

        while True:
            try:
                await asyncio.sleep(interval_seconds)

                # Check if online (ping Supabase)
                is_online = await self._check_online()

                if is_online:
                    await self.sync_workspace(workspace_id, last_version)
                    # Update last_version after successful sync

            except Exception as e:
                print(f"Background sync error: {e}")

    async def _check_online(self) -> bool:
        """Check if we can reach remote server"""
        try:
            # Simple health check to Supabase
            await self.remote.get_by_id("health_check_dummy_id")
            return True
        except:
            return False
```

---

## 🗄️ Database Schema (Supabase Postgres)

**Complete Schema with Indexes and RLS**

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =======================
-- WORKSPACES
-- =======================
CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  owner_id UUID REFERENCES auth.users(id) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  settings JSONB DEFAULT '{}'::jsonb,
  deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_deleted ON workspaces(deleted);

-- =======================
-- WORKSPACE MEMBERS
-- =======================
CREATE TABLE workspace_members (
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX idx_members_user ON workspace_members(user_id);

-- =======================
-- TASKS
-- =======================
CREATE TABLE tasks (
  -- Identity
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,

  -- Core fields
  name TEXT NOT NULL,
  comment TEXT,
  description TEXT,
  priority INT NOT NULL DEFAULT 2 CHECK (priority IN (1, 2, 3)),
  done BOOLEAN DEFAULT FALSE,
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],

  -- Collaboration
  created_by UUID REFERENCES auth.users(id),
  assigned_to UUID[] DEFAULT ARRAY[]::UUID[],

  -- Sync metadata
  version INT NOT NULL DEFAULT 1,
  last_modified TIMESTAMPTZ DEFAULT NOW(),
  device_id TEXT,
  deleted BOOLEAN DEFAULT FALSE,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Performance indexes
CREATE INDEX idx_tasks_workspace ON tasks(workspace_id, deleted);
CREATE INDEX idx_tasks_version ON tasks(workspace_id, version);
CREATE INDEX idx_tasks_done ON tasks(done);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);
CREATE INDEX idx_tasks_created_by ON tasks(created_by);

-- Full-text search
CREATE INDEX idx_tasks_name_fts ON tasks USING GIN(to_tsvector('english', name));
CREATE INDEX idx_tasks_desc_fts ON tasks USING GIN(to_tsvector('english', description));

-- =======================
-- AI CONVERSATIONS
-- =======================
CREATE TABLE ai_conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_workspace ON ai_conversations(workspace_id);
CREATE INDEX idx_conversations_user ON ai_conversations(user_id);

-- =======================
-- ROW LEVEL SECURITY (RLS)
-- =======================

-- Enable RLS on all tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;

-- WORKSPACES: Users can see workspaces they're members of
CREATE POLICY "Users can view member workspaces"
  ON workspaces FOR SELECT
  USING (
    id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
    )
  );

-- WORKSPACES: Only owners can create workspaces
CREATE POLICY "Users can create workspaces"
  ON workspaces FOR INSERT
  WITH CHECK (owner_id = auth.uid());

-- WORKSPACES: Owners and admins can update
CREATE POLICY "Owners and admins can update workspaces"
  ON workspaces FOR UPDATE
  USING (
    id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin')
    )
  );

-- TASKS: Users can view tasks in their workspaces
CREATE POLICY "Users can view workspace tasks"
  ON tasks FOR SELECT
  USING (
    workspace_id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
    )
  );

-- TASKS: Members can insert tasks
CREATE POLICY "Members can insert tasks"
  ON tasks FOR INSERT
  WITH CHECK (
    workspace_id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin', 'member')
    )
  );

-- TASKS: Members can update tasks
CREATE POLICY "Members can update tasks"
  ON tasks FOR UPDATE
  USING (
    workspace_id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin', 'member')
    )
  );

-- TASKS: Only owners and admins can delete
CREATE POLICY "Admins can delete tasks"
  ON tasks FOR DELETE
  USING (
    workspace_id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin')
    )
  );

-- =======================
-- FUNCTIONS & TRIGGERS
-- =======================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER workspaces_updated_at
  BEFORE UPDATE ON workspaces
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Auto-increment version on task update
CREATE OR REPLACE FUNCTION increment_task_version()
RETURNS TRIGGER AS $$
BEGIN
  NEW.version = OLD.version + 1;
  NEW.last_modified = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tasks_version_increment
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION increment_task_version();

-- =======================
-- REALTIME PUBLICATION
-- =======================

-- Enable realtime for all tables
ALTER PUBLICATION supabase_realtime ADD TABLE workspaces;
ALTER PUBLICATION supabase_realtime ADD TABLE workspace_members;
ALTER PUBLICATION supabase_realtime ADD TABLE tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE ai_conversations;
```

---

## 📅 Implementation Roadmap (Gradual Migration)

### **Phase 1: Repository Pattern Foundation** (2-3 weeks)
**Goal**: Abstract storage layer without changing user experience

**Tasks:**
1. Create `repositories/interfaces.py` with abstract interfaces
2. Implement `LocalJsonRepository` (wraps existing `AppState` logic)
3. Refactor `AppState` to use `ITaskRepository`
4. Add unit tests for repository pattern
5. Verify zero functionality changes

**Files Created:**
- `repositories/__init__.py`
- `repositories/interfaces.py`
- `repositories/adapters/json_adapter.py`
- `tests/test_repositories.py`

**User Impact:** None (fully backward compatible)

**Success Criteria:**
- [ ] All existing tests pass
- [ ] No performance regression
- [ ] `tasks.json` format unchanged

---

### **Phase 2: Service Layer + Local SQLite** (3-4 weeks)
**Goal**: Business logic abstraction and offline database

**Tasks:**
1. Create `TaskService` with core business logic
2. Implement `LocalSQLiteRepository` with full-text search
3. Create migration script: `tasks.json` → `local.db`
4. Add config flag: `STORAGE_BACKEND = "json" | "sqlite"`
5. Performance benchmarks (100, 1k, 10k tasks)

**Files Created:**
- `services/task_service.py`
- `services/auth_service.py` (stub for now)
- `repositories/adapters/sqlite_adapter.py`
- `migrations/json_to_sqlite.py`
- `config.py` (add STORAGE_BACKEND setting)

**User Impact:**
- Optional upgrade to SQLite (faster for 100+ tasks)
- Full-text search enabled

**Success Criteria:**
- [ ] SQLite 10x faster than JSON for 1000+ tasks
- [ ] Migration script handles all existing data
- [ ] Users can switch backends without data loss

---

### **Phase 3: LangChain Tools Integration** (2-3 weeks)
**Goal**: Enhance AI with tool calling capabilities

**Tasks:**
1. Create `AIService` with LangChain agent
2. Implement tools: `add_task`, `search_tasks`, `mark_done`, `summarize`
3. Replace simple GPT calls with agent execution
4. Add tool schemas (Pydantic models)
5. Update CLI to use new AI service

**Files Created:**
- `services/ai_service.py`
- `services/langchain_tools.py`
- Update: `textual_app.py`, `assistant.py`

**User Impact:**
- Much smarter AI (can actually manipulate tasks)
- Natural language commands: "Add a high priority task to fix login bug"
- AI can search and summarize workspace

**Success Criteria:**
- [ ] AI can add tasks via natural language
- [ ] AI can search and filter tasks
- [ ] AI provides accurate summaries
- [ ] Response time <2 seconds

---

### **Phase 4: Supabase + Authentication** (4-5 weeks)
**Goal**: Cloud storage and multi-user support

**Tasks:**
1. Set up Supabase project (Postgres + Auth)
2. Implement database schema (tasks, workspaces, members)
3. Configure Row Level Security (RLS) policies
4. Implement `SupabaseRepository`
5. Create `WorkspaceService` and `AuthService`
6. Add login/signup UI (Textual screens + Web forms)
7. Workspace management (create, invite, leave)

**Files Created:**
- `repositories/adapters/supabase_adapter.py`
- `services/workspace_service.py`
- `services/auth_service.py` (full implementation)
- `textual_widgets/auth_screens.py`
- `supabase/schema.sql`
- `.env.example` (add SUPABASE_URL, SUPABASE_KEY)

**User Impact:**
- Can create account (email/password or OAuth)
- Create multiple workspaces
- Invite team members
- Access from any device (cloud sync)

**Success Criteria:**
- [ ] User registration and login work
- [ ] Workspaces isolate data correctly
- [ ] RLS prevents unauthorized access
- [ ] OAuth (Google, GitHub) works

---

### **Phase 5: Hybrid Sync Engine** (5-6 weeks)
**Goal**: Offline-first with automatic cloud sync

**Tasks:**
1. Implement `HybridRepository` (local + remote coordination)
2. Build `SyncEngine` with conflict resolution
3. Implement `ConflictResolver` (field-level merging)
4. Add background sync worker (runs every 60s when online)
5. Implement `ISyncLogRepository` for tracking pending changes
6. Add network detection (online/offline status)
7. Supabase Realtime subscriptions for live updates

**Files Created:**
- `repositories/adapters/hybrid_adapter.py`
- `services/sync_service.py`
- `services/conflict_resolver.py`
- `repositories/adapters/sync_log_adapter.py`

**User Impact:**
- **Works offline** (all operations instant)
- **Syncs automatically** when internet available
- **Conflicts resolved intelligently** (no "your changes will be lost")
- **Real-time updates** (see others' changes live)

**Success Criteria:**
- [ ] All operations work offline
- [ ] Sync completes within 5s for 100 changes
- [ ] Conflicts resolve without data loss
- [ ] Realtime updates <500ms latency

---

### **Phase 6: REST API Layer** (3-4 weeks)
**Goal**: Enable external clients (web, mobile)

**Tasks:**
1. Build FastAPI application (`api/main.py`)
2. Implement REST endpoints (CRUD for tasks, workspaces)
3. Add JWT authentication middleware
4. WebSocket support for realtime updates
5. Rate limiting (100 req/min per user)
6. API documentation (OpenAPI/Swagger)
7. CORS configuration for web client

**Files Created:**
- `api/main.py`
- `api/routes/tasks.py`
- `api/routes/workspaces.py`
- `api/routes/auth.py`
- `api/dependencies.py`
- `api/middleware/auth.py`
- `api/middleware/rate_limit.py`

**Endpoints:**
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/workspaces
GET    /api/v1/workspaces/{id}/tasks
POST   /api/v1/workspaces/{id}/tasks
PUT    /api/v1/tasks/{id}
DELETE /api/v1/tasks/{id}
WS     /api/v1/ws/workspaces/{id}
```

**User Impact:** None directly (enables future platforms)

**Success Criteria:**
- [ ] API documented in Swagger
- [ ] JWT auth works
- [ ] Rate limiting prevents abuse
- [ ] WebSocket realtime updates work

---

### **Phase 7: Web Application** (6-8 weeks)
**Goal**: Full-featured browser client

**Tech Stack:**
- Next.js 14 (App Router)
- React 18
- TanStack Query (data fetching)
- Zustand (state management)
- Supabase Auth (login)
- Tailwind CSS (styling)

**Tasks:**
1. Initialize Next.js project
2. Implement authentication (login, signup, OAuth)
3. Workspace selector and dashboard
4. Task list with filters and search
5. Task detail modal (view, edit, delete)
6. Real-time subscriptions (Supabase Realtime)
7. Offline support (Service Worker + IndexedDB)
8. Responsive design (mobile-first)

**Key Pages:**
- `/login` - Authentication
- `/workspaces` - Workspace selector
- `/workspaces/[id]` - Task dashboard
- `/workspaces/[id]/tasks/[taskId]` - Task detail

**User Impact:**
- Use in any browser (desktop, mobile)
- No installation required
- Same features as CLI
- Beautiful UI with drag-and-drop

**Success Criteria:**
- [ ] Login and workspace selection work
- [ ] All task operations work
- [ ] Real-time updates within 1s
- [ ] Lighthouse score >90

---

### **Phase 8: Mobile Application** (8-10 weeks)
**Goal**: Native mobile experience (iOS + Android)

**Tech Stack:**
- React Native + Expo
- WatermelonDB (local SQLite)
- React Navigation (routing)
- Supabase Auth
- Background fetch (sync)

**Tasks:**
1. Initialize Expo project
2. Implement authentication screens
3. Task list with pull-to-refresh
4. Task detail and edit screens
5. Offline storage (WatermelonDB)
6. Background sync (Expo Background Fetch)
7. Push notifications (task assignments)
8. App icons and splash screens
9. App Store / Play Store submission

**User Impact:**
- Native mobile app (iOS + Android)
- Works offline
- Push notifications for updates
- Camera integration (task attachments)

**Success Criteria:**
- [ ] App runs on iOS and Android
- [ ] Offline mode works
- [ ] Push notifications delivered
- [ ] Approved in both app stores

---

### **Phase 9: Collaboration Features** (4-5 weeks)
**Goal**: Full multi-user workflows

**Tasks:**
1. Task assignments (assign to team members)
2. Comments system (threaded discussions)
3. @mentions in comments (notify users)
4. Activity feed (who did what)
5. Permissions management (role-based access)
6. Task dependencies (blockers)
7. Workspace templates

**Files Created:**
- `models/comment.py`
- `models/activity.py`
- `services/comment_service.py`
- `services/activity_service.py`
- Database: `comments`, `activities` tables

**User Impact:**
- Assign tasks to team members
- Discuss tasks in comments
- See activity history
- Control who can do what

**Success Criteria:**
- [ ] Assignments notify users
- [ ] Comments appear in realtime
- [ ] @mentions send notifications
- [ ] Activity feed accurate

---

## 🛠️ Technology Stack Summary

| Layer | Technology | Why? | Alternatives Considered |
|-------|-----------|------|------------------------|
| **Local DB** | SQLite (sqlalchemy) | Embedded, fast, universal | None (best choice) |
| **Cloud DB** | Supabase (Postgres) | Auth + RLS + Realtime built-in | Firebase (less control), AWS RDS (more setup) |
| **Backend** | FastAPI | Async Python, fast, great docs | Django (heavier), Flask (older) |
| **CLI** | Python + Textual | Current stack, excellent | Maintain as-is |
| **Web** | Next.js 14 + React | SSR, App Router, best DX | SvelteKit (smaller ecosystem), Remix (newer) |
| **Mobile** | React Native + Expo | Cross-platform, share code with web | Flutter (different language), Native (2x work) |
| **AI** | LangChain + OpenAI | Tool calling, agent framework | LlamaIndex (docs focus), Anthropic Claude (more expensive) |
| **Sync** | Custom engine | Control over logic, optimize for use case | Replicache (complex), Firebase (vendor lock-in) |
| **Auth** | Supabase Auth | OAuth, MFA, RLS integration | Auth0 (expensive), Clerk (overkill) |
| **Realtime** | Supabase Realtime | Built-in, scales well | Pusher (expensive), Socket.io (manage yourself) |

---

## 🎯 Key Design Decisions & Rationale

### ✅ **Critical Decisions**

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **UUIDs not integers** | Distributed systems need decentralized ID generation | Slightly larger storage (16 bytes vs 4) |
| **Soft deletes** | Sync can propagate deletions reliably across devices | Database never shrinks (use archive jobs) |
| **Field-level merging** | Better UX than "your changes conflict" messages | More complex conflict resolution code |
| **Service layer** | Share logic across CLI, API, Web, Mobile | Extra layer of abstraction |
| **Repository pattern** | Swap storage without changing business logic | More boilerplate code |
| **Local-first** | Best UX (instant response, works offline) | Complex sync engine required |
| **Supabase** | Fast development (Auth + DB + Realtime) | Vendor lock-in (mitigated by repository pattern) |

### ⚠️ **Potential Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Sync conflicts lose data** | High | Extensive testing, field-level merging, backup system |
| **Supabase vendor lock-in** | Medium | Repository pattern allows swapping to Postgres + custom auth |
| **Mobile offline storage bugs** | Medium | WatermelonDB is battle-tested, thorough QA |
| **LangChain API costs** | Low | Rate limiting, local AI fallback for simple tasks |
| **Complexity overwhelms dev** | Medium | Phase by phase, each phase independently useful |

---

## 🚀 Getting Started with Phase 1

To implement Phase 1 (Repository Pattern), we would:

1. **Create directory structure:**
   ```
   repositories/
   ├── __init__.py
   ├── interfaces.py
   └── adapters/
       ├── __init__.py
       └── json_adapter.py
   ```

2. **Define interfaces** (`interfaces.py`)

3. **Implement JSON adapter** (`json_adapter.py`)

4. **Refactor `core/state.py`** to use repository

5. **Add unit tests** for repository pattern

6. **Verify backward compatibility** (all existing tests pass)

---

## 📚 Additional Resources

### Recommended Reading
- **Hexagonal Architecture**: https://alistair.cockburn.us/hexagonal-architecture/
- **Local-First Software**: https://www.inkandswitch.com/local-first/
- **CRDT Primer**: https://crdt.tech/
- **Supabase Docs**: https://supabase.com/docs
- **LangChain Agents**: https://python.langchain.com/docs/modules/agents/

### Example Projects
- **Linear** (local-first task management): https://linear.app/
- **Notion** (sync engine): https://www.notion.so/blog/how-notion-syncs
- **RxDB** (offline-first database): https://rxdb.info/

---

## 📝 Notes & Open Questions

### Open Questions
1. **Conflict resolution UX**: Should we show users when conflicts are resolved automatically?
2. **Pricing model**: Free tier limits? Paid plans?
3. **Data retention**: How long to keep deleted tasks in archive?
4. **Export format**: Support CSV, JSON, Markdown export?

### Future Enhancements (Post-MVP)
- File attachments (images, PDFs)
- Recurring tasks
- Gantt chart view
- Calendar integration (Google Cal, Outlook)
- Email integration (task from email)
- Slack/Discord integration
- Time tracking
- Reports and analytics

---

**Document Version**: 1.0
**Last Updated**: October 23, 2025
**Status**: Planning / Architecture Design
**Next Steps**: Review with stakeholders, begin Phase 1 implementation

---

*This is a living document. Update as architecture evolves.*
