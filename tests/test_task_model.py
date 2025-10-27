"""
Tests for models/task.py - Task dataclass
"""

import pytest
from datetime import datetime
from models.task import Task


class TestTaskCreation:
    """Test Task creation and initialization"""

    def test_create_task_with_all_fields(self):
        """Test creating a task with all fields specified"""
        task = Task(
            id=1,
            name="Test Task",
            comment="Test Comment",
            description="Test Description",
            priority=1,
            tag="work",
            done=False,
            tags=["work", "urgent"],
        )

        assert task.id == 1
        assert task.name == "Test Task"
        assert task.comment == "Test Comment"
        assert task.description == "Test Description"
        assert task.priority == 1
        assert task.tag == "work"
        assert task.done is False
        assert task.tags == ["work", "urgent"]
        assert task.created_at != ""
        assert task.updated_at != ""

    def test_create_task_minimal_fields(self):
        """Test creating a task with minimal required fields"""
        task = Task(
            id=1,
            name="Minimal Task",
            comment="",
            description="",
            priority=2,
            tag="",
        )

        assert task.id == 1
        assert task.name == "Minimal Task"
        assert task.done is False
        assert task.tags == []
        assert task.created_at != ""

    def test_auto_timestamp_on_creation(self):
        """Test that created_at and updated_at are auto-set"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="",
        )

        # Check timestamps are ISO format
        assert task.created_at != ""
        assert task.updated_at != ""
        # Both should be set to same value on creation
        assert task.created_at == task.updated_at

        # Validate ISO format
        datetime.fromisoformat(task.created_at)
        datetime.fromisoformat(task.updated_at)


class TestTagMigration:
    """Test tag migration from single tag to tags list"""

    def test_migrate_single_tag_to_tags_list(self):
        """Test migration from legacy tag field to tags list"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=[],  # Empty tags list
        )

        # Should migrate tag to tags list
        assert task.tags == ["work"]
        assert task.tag == "work"

    def test_sync_tags_list_to_tag_field(self):
        """Test syncing tags list to legacy tag field"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="",  # Empty tag
            tags=["work", "urgent"],
        )

        # Should sync first tag from tags list
        assert task.tag == "work"
        assert task.tags == ["work", "urgent"]

    def test_tags_normalized_to_lowercase(self):
        """Test that tags are normalized to lowercase"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="WORK",
            tags=["URGENT", "Personal"],
        )

        # Tags list is normalized, but when both tag and tags are provided,
        # tag field remains unchanged and tags list gets normalized
        assert task.tags == ["urgent", "personal"]
        assert task.tag == "WORK"  # Original value preserved when tags list provided

    def test_tags_trimmed_of_whitespace(self):
        """Test that tags are trimmed of whitespace"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="  work  ",
            tags=["  urgent  ", " personal "],
        )

        # Tags list is trimmed and normalized
        assert task.tags == ["urgent", "personal"]
        assert task.tag == "  work  "  # Original value when tags list provided

    def test_empty_tags_filtered_out(self):
        """Test that empty tags are filtered out"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work", "", "  ", "urgent"],
        )

        # Empty strings and whitespace-only should be removed
        assert task.tags == ["work", "urgent"]

    def test_tags_limited_to_three(self):
        """Test that tags are limited to maximum 3"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work", "urgent", "personal", "project", "extra"],
        )

        # Should only keep first 3 tags
        assert len(task.tags) == 3
        assert task.tags == ["work", "urgent", "personal"]


class TestTagOperations:
    """Test tag manipulation methods"""

    def test_add_tag_success(self):
        """Test adding a tag successfully"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work"],
        )

        result = task.add_tag("urgent")
        assert result is True
        assert task.tags == ["work", "urgent"]
        assert task.tag == "work"  # Legacy field stays synced

    def test_add_tag_normalizes_case(self):
        """Test that adding a tag normalizes to lowercase"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="",
            tags=[],
        )

        result = task.add_tag("URGENT")
        assert result is True
        assert task.tags == ["urgent"]

    def test_add_tag_duplicate(self):
        """Test adding a duplicate tag"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work"],
        )

        result = task.add_tag("work")
        assert result is False
        assert task.tags == ["work"]

    def test_add_tag_max_limit(self):
        """Test adding a tag when at maximum limit"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work", "urgent", "personal"],
        )

        result = task.add_tag("extra")
        assert result is False
        assert len(task.tags) == 3

    def test_add_tag_empty_string(self):
        """Test adding an empty tag"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="",
            tags=[],
        )

        result = task.add_tag("   ")
        assert result is False
        assert task.tags == []

    def test_remove_tag_success(self):
        """Test removing a tag successfully"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work", "urgent"],
        )

        result = task.remove_tag("urgent")
        assert result is True
        assert task.tags == ["work"]
        assert task.tag == "work"

    def test_remove_tag_not_found(self):
        """Test removing a tag that doesn't exist"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work"],
        )

        result = task.remove_tag("urgent")
        assert result is False
        assert task.tags == ["work"]

    def test_remove_last_tag_clears_legacy_field(self):
        """Test that removing last tag clears legacy tag field"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work"],
        )

        result = task.remove_tag("work")
        assert result is True
        assert task.tags == []
        assert task.tag == ""


class TestTagDisplay:
    """Test tag display formatting"""

    def test_get_tags_display_multiple(self):
        """Test displaying multiple tags"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work", "urgent", "personal"],
        )

        display = task.get_tags_display()
        assert display == "work, urgent, personal"

    def test_get_tags_display_single(self):
        """Test displaying single tag"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            tags=["work"],
        )

        display = task.get_tags_display()
        assert display == "work"

    def test_get_tags_display_empty(self):
        """Test displaying no tags"""
        task = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="",
            tags=[],
        )

        display = task.get_tags_display()
        assert display == ""


class TestTaskEquality:
    """Test task comparison and equality"""

    def test_tasks_equal_by_id(self):
        """Test that tasks with same data are equal"""
        task1 = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            created_at="2024-01-01T00:00:00",
        )

        task2 = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            created_at="2024-01-01T00:00:00",
        )

        # Dataclasses with same values are equal
        assert task1 == task2

    def test_tasks_not_equal_different_id(self):
        """Test that tasks with different IDs are not equal"""
        task1 = Task(
            id=1,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            created_at="2024-01-01T00:00:00",
        )

        task2 = Task(
            id=2,
            name="Task",
            comment="",
            description="",
            priority=2,
            tag="work",
            created_at="2024-01-01T00:00:00",
        )

        assert task1 != task2
