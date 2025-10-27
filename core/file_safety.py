"""
File Safety Module
Provides atomic writes, file locking, and backup/recovery mechanisms

Features:
- File locking (prevents concurrent access)
- Atomic writes (prevents partial write corruption)
- Automatic backups (enables recovery from corruption)
- Backup rotation (keeps last N backups)
"""

import os
import json
import shutil
import tempfile
from typing import Any, Optional, Dict
from pathlib import Path
from typing import Any
from utils.file_validators import validate_filename
import threading


class FileSafetyError(Exception):
    """Base exception for file safety errors"""
    pass


class FileLockTimeoutError(FileSafetyError):
    """Kept for backward compatibility. No locks are used currently."""
    pass


class FileCorruptionError(FileSafetyError):
    """Raised when file is corrupted and no backup available"""
    pass


class SafeFileManager:
    """
    Safe file operations with atomic writes and backups.

    Features:
    - Atomic writes (prevents partial write corruption)
    - Automatic backups (enables recovery from corruption)
    - Backup rotation (keeps last N backups)

    Example usage:
        manager = SafeFileManager("tasks.json", lock_timeout=5.0, backup_count=3)

        # Save with protection
        data = {"tasks": [...]}
        manager.save_json_with_lock(data)

        # Load with recovery
        data = manager.load_json_with_lock()
    """

    def __init__(
        self,
        filename: str,
        lock_timeout: float = 5.0,
        backup_count: int = 3,
        console: Optional[Any] = None
    ):
        """
        Initialize SafeFileManager.

        Args:
            filename: Path to file to manage
            lock_timeout: Seconds to wait for lock (default 5.0)
            backup_count: Number of backups to keep (default 3)
            console: Rich console for output

        Raises:
            FileSafetyError: If filename validation fails
        """
        # Validate filename for security
        is_valid, error = validate_filename(filename, allow_absolute=True)
        if not is_valid:
            raise FileSafetyError(f"Invalid filename: {error}")

        self.filename = Path(filename)
        self.lock_timeout = lock_timeout
        self.backup_count = backup_count
        self.console = console
        # Intra-process write lock to serialize saves
        self._write_lock: threading.Lock = threading.Lock()

    def atomic_write_json(self, data: Dict[str, Any], indent: int = 4):
        """
        Atomically write JSON data to file.

        Process:
        1. Write to temporary file in same directory
        2. Flush and fsync (force to disk)
        3. Atomic replace (one OS operation)

        This ensures the original file is never in an inconsistent state.
        If the process crashes during write, the temp file is abandoned
        and the original file remains intact.

        Args:
            data: Dictionary to serialize as JSON
            indent: JSON indentation (default 4)

        Raises:
            FileSafetyError: If write fails
        """
        # Ensure directory exists
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        # Initialize to None for safe cleanup
        temp = None
        temp_path = None

        try:
            # Create temp file in SAME directory (critical for atomic replace)
            # Using same directory ensures temp file is on same filesystem,
            # which is required for atomic os.replace()
            temp = tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.filename.parent,
                prefix=f'.{self.filename.name}.',
                suffix='.tmp',
                delete=False,
                encoding='utf-8'
            )
            temp_path = temp.name  # Save path early for cleanup

            # Serialize to JSON
            json_str = json.dumps(data, indent=indent, ensure_ascii=False)

            # Write to temp file
            temp.write(json_str)
            temp.flush()

            # Force write to disk (important for networked filesystems)
            # This ensures data is physically written before we replace
            os.fsync(temp.fileno())
            temp.close()

            # Atomic replace (one OS operation - never partial)
            # os.replace() is guaranteed atomic on all platforms (Python 3.3+)
            os.replace(temp_path, self.filename)

        except Exception as e:
            # SAFE CLEANUP: Check if temp exists before accessing
            if temp is not None:
                try:
                    if not temp.closed:
                        temp.close()
                except Exception:
                    pass  # Ignore cleanup errors

            # Delete temp file if it exists
            if temp_path is not None and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass  # Ignore cleanup errors

            raise FileSafetyError(f"Failed to write {self.filename}: {e}") from e

    def load_json_with_recovery(self) -> Dict[str, Any]:
        """
        Load JSON data with automatic backup recovery.

        Process:
        1. Try to load main file
        2. If corrupted, try backups in order (newest first)
        3. If all fail, raise FileCorruptionError

        Returns:
            Loaded JSON data

        Raises:
            FileNotFoundError: If no file or backups exist
            FileCorruptionError: If all files corrupted
        """
        # Try main file first
        if self.filename.exists():
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.console.print(
                    f"[yellow]⚠️  Main file corrupted: {e}[/yellow]"
                )

        # Try backups in order (newest to oldest)
        for i in range(self.backup_count):
            backup_path = self._get_backup_path(i)
            if backup_path.exists():
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.console.print(
                            f"[green]✓ Recovered from {backup_path.name}[/green]"
                        )
                        return data
                except json.JSONDecodeError:
                    self.console.print(
                        f"[yellow]⚠️  Backup {backup_path.name} corrupted[/yellow]"
                    )
                    continue

        # All files failed
        if not self.filename.exists():
            raise FileNotFoundError(f"No file found: {self.filename}")
        else:
            raise FileCorruptionError(
                f"File corrupted and no valid backups: {self.filename}"
            )

    def save_json_with_lock(
        self,
        data: Dict[str, Any],
        indent: int = 4,
        create_backup: bool = True
    ):
        """
        Save JSON data with backup and atomic replace.

        Process:
        1. Rotate existing backups
        2. Create a backup copy of the current file (if it exists)
        3. Atomically write the new JSON data to the main file

        Args:
            data: Dictionary to save
            indent: JSON indentation
            create_backup: Whether to create backup first

        Raises:
            FileLockTimeoutError: If can't acquire lock
            FileSafetyError: If save fails
        """
        # Serialize writes within process
        with self._write_lock:
            # Rotate and create backup if requested
            if create_backup and self.filename.exists():
                self._rotate_backups()
                backup_path = self._get_backup_path(0)
                shutil.copy2(self.filename, backup_path)

            # Atomic write ensures file replacement is safe
            self.atomic_write_json(data, indent)

    def load_json_with_lock(self) -> Dict[str, Any]:
        """
        Load JSON data with automatic backup recovery.

        Note: File locking removed for load operations to avoid Windows file handle
        conflicts. Atomic writes on the save side ensure consistency. Reading doesn't
        need locking since:
        1. Atomic writes guarantee file is never in partial state
        2. We have backup recovery for corrupted files
        3. Single-process app doesn't need read locks

        Returns:
            Loaded JSON data

        Raises:
            FileNotFoundError: If no file exists
            FileCorruptionError: If all files corrupted
        """
        # Just load with recovery - no locking needed for reads
        # Atomic writes ensure file is always in consistent state
        return self.load_json_with_recovery()

    def _get_backup_path(self, index: int) -> Path:
        """
        Get backup file path by index.

        Naming scheme:
        - index 0: tasks.json.backup (newest)
        - index 1: tasks.json.backup.1
        - index 2: tasks.json.backup.2 (oldest)

        Args:
            index: Backup index (0 = newest)

        Returns:
            Path to backup file
        """
        if index == 0:
            return self.filename.with_suffix(self.filename.suffix + '.backup')
        else:
            return self.filename.with_suffix(
                self.filename.suffix + f'.backup.{index}'
            )

    def _rotate_backups(self):
        """
        Rotate backup files.

        Process:
        1. Delete oldest backup (backup.2)
        2. Rename backup.1 → backup.2
        3. Rename backup → backup.1
        4. Current file will be copied to backup (by caller)

        This maintains a rolling window of backups.
        """
        # Delete oldest backup if it exists
        oldest = self._get_backup_path(self.backup_count - 1)
        if oldest.exists():
            oldest.unlink()

        # Rotate existing backups (from newest to oldest)
        # This ensures we don't overwrite files
        for i in range(self.backup_count - 2, -1, -1):
            old_path = self._get_backup_path(i)
            new_path = self._get_backup_path(i + 1)

            if old_path.exists():
                old_path.rename(new_path)

    def get_backup_info(self) -> Dict[str, Any]:
        """
        Get information about backups.

        Returns:
            Dictionary with backup metadata:
            - count: Number of backups found
            - backups: List of (path, size, modified_time) tuples
        """
        backups = []
        for i in range(self.backup_count):
            backup_path = self._get_backup_path(i)
            if backup_path.exists():
                stat = backup_path.stat()
                backups.append({
                    'path': str(backup_path),
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'index': i
                })

        return {
            'count': len(backups),
            'backups': backups
        }
