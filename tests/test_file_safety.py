"""
Tests for core/file_safety.py - File safety operations
"""

import pytest
import json
import tempfile
from pathlib import Path
from io import StringIO

from core.file_safety import (
    SafeFileManager,
    FileSafetyError,
    FileLockTimeoutError,
    FileCorruptionError,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file path"""
    return temp_dir / "test.json"


# Use shared `console` fixture from tests/conftest.py


@pytest.fixture
def manager(temp_file, console):
    """Create a SafeFileManager instance"""
    return SafeFileManager(str(temp_file), lock_timeout=5.0, backup_count=3, console=console)


class TestSafeFileManagerInitialization:
    """Test SafeFileManager initialization"""

    def test_init_with_valid_path(self, temp_file, console):
        """Test initialization with valid file path"""
        manager = SafeFileManager(str(temp_file), console=console)

        assert manager.filename == temp_file
        assert manager.lock_timeout == 5.0
        assert manager.backup_count == 3
        assert manager.console is not None

    def test_init_with_custom_timeout(self, temp_file, console):
        """Test initialization with custom timeout"""
        manager = SafeFileManager(str(temp_file), lock_timeout=10.0, console=console)

        assert manager.lock_timeout == 10.0

    def test_init_with_custom_backup_count(self, temp_file, console):
        """Test initialization with custom backup count"""
        manager = SafeFileManager(str(temp_file), backup_count=5, console=console)

        assert manager.backup_count == 5


class TestAtomicWrite:
    """Test atomic write operations"""

    def test_atomic_write_creates_file(self, manager, temp_file):
        """Test that atomic write creates a new file"""
        data = {"test": "data", "number": 123}

        manager.atomic_write_json(data)

        assert temp_file.exists()

    def test_atomic_write_valid_json(self, manager, temp_file):
        """Test that atomic write creates valid JSON"""
        data = {"test": "data", "items": [1, 2, 3]}

        manager.atomic_write_json(data)

        # Read and parse the JSON
        loaded = json.loads(temp_file.read_text())
        assert loaded == data

    def test_atomic_write_overwrites_existing(self, manager, temp_file):
        """Test that atomic write overwrites existing file"""
        # Write initial data
        temp_file.write_text(json.dumps({"old": "data"}))

        # Overwrite with new data
        new_data = {"new": "data"}
        manager.atomic_write_json(new_data)

        # Verify new data
        loaded = json.loads(temp_file.read_text())
        assert loaded == new_data
        assert "old" not in loaded

    def test_atomic_write_with_indentation(self, manager, temp_file):
        """Test atomic write with custom indentation"""
        data = {"test": "data"}

        manager.atomic_write_json(data, indent=2)

        content = temp_file.read_text()
        # Indented JSON should have newlines
        assert "\n" in content

    def test_atomic_write_unicode(self, manager, temp_file):
        """Test atomic write with unicode characters"""
        data = {"text": "Hello 世界", "emoji": "🎉"}

        manager.atomic_write_json(data)

        loaded = json.loads(temp_file.read_text(encoding="utf-8"))
        assert loaded["text"] == "Hello 世界"
        assert loaded["emoji"] == "🎉"

    def test_atomic_write_creates_parent_dir(self, temp_dir, console):
        """Test that atomic write creates parent directory if needed"""
        nested_file = temp_dir / "subdir" / "nested.json"
        manager = SafeFileManager(str(nested_file), console=console)

        manager.atomic_write_json({"test": "data"})

        assert nested_file.exists()
        assert nested_file.parent.exists()


class TestLoadWithRecovery:
    """Test loading with backup recovery"""

    def test_load_valid_file(self, manager, temp_file):
        """Test loading a valid JSON file"""
        data = {"test": "data", "number": 123}
        temp_file.write_text(json.dumps(data))

        loaded = manager.load_json_with_recovery()

        assert loaded == data

    def test_load_nonexistent_file(self, manager):
        """Test loading a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            manager.load_json_with_recovery()

    def test_load_corrupted_file_with_backup(self, manager, temp_file):
        """Test loading corrupted file recovers from backup"""
        # Create corrupted main file
        temp_file.write_text("{ invalid json }")

        # Create valid backup
        backup_path = manager._get_backup_path(0)
        backup_data = {"backup": "data"}
        backup_path.write_text(json.dumps(backup_data))

        # Should recover from backup
        loaded = manager.load_json_with_recovery()

        assert loaded == backup_data

    def test_load_all_files_corrupted(self, manager, temp_file):
        """Test loading when all files are corrupted"""
        # Create corrupted main file
        temp_file.write_text("{ invalid }")

        # Create corrupted backups
        for i in range(3):
            backup_path = manager._get_backup_path(i)
            backup_path.write_text("{ also invalid }")

        with pytest.raises(FileCorruptionError):
            manager.load_json_with_recovery()

    def test_load_tries_backups_in_order(self, manager, temp_file):
        """Test that loading tries backups in order (newest first)"""
        # Corrupted main file
        temp_file.write_text("{ invalid }")

        # Corrupted first backup
        backup0 = manager._get_backup_path(0)
        backup0.write_text("{ invalid }")

        # Valid second backup
        backup1 = manager._get_backup_path(1)
        backup1_data = {"backup1": "data"}
        backup1.write_text(json.dumps(backup1_data))

        # Should skip backup0 and use backup1
        loaded = manager.load_json_with_recovery()
        assert loaded == backup1_data


class TestSaveWithBackup:
    """Test save operations with backups"""

    def test_save_creates_file(self, manager, temp_file):
        """Test that save creates the file"""
        data = {"test": "data"}

        manager.save_json_with_lock(data)

        assert temp_file.exists()

    def test_save_creates_backup(self, manager, temp_file):
        """Test that save creates a backup of existing file"""
        # Create initial file
        initial_data = {"initial": "data"}
        temp_file.write_text(json.dumps(initial_data))

        # Save new data
        new_data = {"new": "data"}
        manager.save_json_with_lock(new_data)

        # Check backup was created
        backup_path = manager._get_backup_path(0)
        assert backup_path.exists()

        # Verify backup contains old data
        backup_data = json.loads(backup_path.read_text())
        assert backup_data == initial_data

    def test_save_no_backup_for_new_file(self, manager, temp_file):
        """Test that no backup is created for new file"""
        data = {"test": "data"}

        manager.save_json_with_lock(data)

        # No backup should exist
        backup_path = manager._get_backup_path(0)
        assert not backup_path.exists()

    def test_save_without_backup(self, manager, temp_file):
        """Test saving without creating backup"""
        # Create initial file
        temp_file.write_text(json.dumps({"initial": "data"}))

        # Save without backup
        manager.save_json_with_lock({"new": "data"}, create_backup=False)

        # No backup should be created
        backup_path = manager._get_backup_path(0)
        assert not backup_path.exists()


class TestLoadWithLock:
    """Test load operations with file locking"""

    def test_load_valid_file(self, manager, temp_file):
        """Test loading a valid file"""
        data = {"test": "data"}
        temp_file.write_text(json.dumps(data))

        loaded = manager.load_json_with_lock()

        assert loaded == data

    def test_load_nonexistent_file(self, manager):
        """Test loading nonexistent file"""
        with pytest.raises(FileNotFoundError):
            manager.load_json_with_lock()

    def test_load_corrupted_with_recovery(self, manager, temp_file):
        """Test loading corrupted file with automatic recovery"""
        # Corrupted main file
        temp_file.write_text("{ invalid }")

        # Valid backup
        backup_path = manager._get_backup_path(0)
        backup_data = {"backup": "data"}
        backup_path.write_text(json.dumps(backup_data))

        # Should recover from backup
        loaded = manager.load_json_with_lock()
        assert loaded == backup_data


class TestBackupRotation:
    """Test backup rotation functionality"""

    def test_get_backup_path(self, manager):
        """Test getting backup file paths"""
        backup0 = manager._get_backup_path(0)
        backup1 = manager._get_backup_path(1)
        backup2 = manager._get_backup_path(2)

        assert backup0.name.endswith(".backup")
        assert backup1.name.endswith(".backup.1")
        assert backup2.name.endswith(".backup.2")

    def test_rotate_backups_basic(self, manager, temp_file):
        """Test basic backup rotation"""
        # Create backups
        backup0 = manager._get_backup_path(0)
        backup1 = manager._get_backup_path(1)

        backup0.write_text("backup0")
        backup1.write_text("backup1")

        # Rotate
        manager._rotate_backups()

        # backup0 should move to backup1
        # backup1 should move to backup2
        assert not backup0.exists()
        assert backup1.read_text() == "backup0"
        assert manager._get_backup_path(2).read_text() == "backup1"

    def test_rotate_backups_deletes_oldest(self, manager):
        """Test that rotation deletes the oldest backup"""
        # Create all backups (0, 1, 2)
        for i in range(3):
            backup = manager._get_backup_path(i)
            backup.write_text(f"backup{i}")

        # Rotate (should delete backup.2)
        manager._rotate_backups()

        # backup.2 should no longer exist
        backup2 = manager._get_backup_path(2)

        # After rotation:
        # old backup.0 → backup.1
        # old backup.1 → backup.2
        # backup.0 slot is now empty
        assert manager._get_backup_path(1).read_text() == "backup0"
        assert manager._get_backup_path(2).read_text() == "backup1"

    def test_multiple_saves_rotate_backups(self, manager, temp_file):
        """Test that multiple saves properly rotate backups"""
        # First save
        manager.save_json_with_lock({"version": 1})

        # Second save (creates backup.0)
        manager.save_json_with_lock({"version": 2})
        backup0 = manager._get_backup_path(0)
        assert backup0.exists()
        assert json.loads(backup0.read_text())["version"] == 1

        # Third save (rotates to backup.1)
        manager.save_json_with_lock({"version": 3})
        backup1 = manager._get_backup_path(1)
        assert backup1.exists()
        assert json.loads(backup1.read_text())["version"] == 1


class TestBackupInfo:
    """Test backup information retrieval"""

    def test_get_backup_info_no_backups(self, manager):
        """Test getting backup info when no backups exist"""
        info = manager.get_backup_info()

        assert info["count"] == 0
        assert info["backups"] == []

    def test_get_backup_info_with_backups(self, manager):
        """Test getting backup info with existing backups"""
        # Create some backups
        backup0 = manager._get_backup_path(0)
        backup1 = manager._get_backup_path(1)

        backup0.write_text(json.dumps({"test": "data"}))
        backup1.write_text(json.dumps({"test": "data2"}))

        info = manager.get_backup_info()

        assert info["count"] == 2
        assert len(info["backups"]) == 2
        assert info["backups"][0]["index"] == 0
        assert info["backups"][1]["index"] == 1


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_json_on_write(self, manager):
        """Test error handling for un-serializable data"""
        # Objects that can't be serialized to JSON
        class CustomClass:
            pass

        with pytest.raises(FileSafetyError):
            manager.atomic_write_json({"obj": CustomClass()})

    def test_corrupted_json_on_load(self, manager, temp_file):
        """Test error handling for corrupted JSON"""
        temp_file.write_text("{ not valid json }")

        # Should raise FileCorruptionError if no backups
        with pytest.raises((FileCorruptionError, FileNotFoundError)):
            manager.load_json_with_lock()

    def test_permission_error_handling(self, temp_dir, console):
        """Test handling of permission errors"""
        # This test is platform-specific and may not work on all systems
        # Skip if we can't create the scenario
        try:
            readonly_file = temp_dir / "readonly.json"
            readonly_file.write_text("{}")
            readonly_file.chmod(0o444)  # Read-only

            manager = SafeFileManager(str(readonly_file), console=console)

            # Should raise FileSafetyError
            with pytest.raises(FileSafetyError):
                manager.atomic_write_json({"test": "data"})

        except Exception:
            # Skip test if we can't set permissions
            pytest.skip("Cannot test permission errors on this platform")


class TestThreadSafety:
    """Test thread safety of file operations"""

    def test_write_lock_serializes_saves(self, manager, temp_file):
        """Test that write lock serializes concurrent saves"""
        import threading
        import time

        results = []
        errors = []

        def save_data(value):
            try:
                time.sleep(0.01)  # Small delay to increase chance of collision
                manager.save_json_with_lock({"value": value})
                results.append(value)
            except Exception as e:
                errors.append(e)

        # Start multiple threads trying to save
        threads = [threading.Thread(target=save_data, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All saves should succeed
        assert len(results) == 5
        assert len(errors) == 0

        # Final file should contain valid data
        assert temp_file.exists()
        data = json.loads(temp_file.read_text())
        assert "value" in data
