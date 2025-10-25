from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class Task:
    id: int
    name: str
    comment: str
    description: str
    priority: int
    tag: str  # Legacy single tag field (for backward compatibility)
    done: bool = False
    tags: List[str] = field(default_factory=list)  # New: up to 3 tags
    created_at: str = ""  # ISO timestamp
    completed_at: str = ""  # ISO timestamp when marked done
    updated_at: str = ""  # ISO timestamp when last modified

    def __post_init__(self):
        """
        Migrate old single tag to tags list if needed
        Limit tags to 3 maximum
        """
        # If tags list is empty but tag field has value, migrate it
        if not self.tags and self.tag:
            self.tags = [self.tag.strip().lower()]

        # If tags list has values but tag field is empty, sync first tag
        if self.tags and not self.tag:
            self.tag = self.tags[0]

        # Ensure all tags are lowercase and trimmed
        self.tags = [t.strip().lower() for t in self.tags if t.strip()]

        # Limit to 3 tags maximum
        self.tags = self.tags[:3]

        # Set created_at if not set
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
            # Initialize updated_at if missing
            if not self.updated_at:
                self.updated_at = self.created_at

    def get_tags_display(self) -> str:
        """Get comma-separated tags for display"""
        return ", ".join(self.tags) if self.tags else ""

    def add_tag(self, tag: str) -> bool:
        """Add a tag (up to 3 maximum). Returns True if added, False if limit reached."""
        tag = tag.strip().lower()
        if tag and tag not in self.tags and len(self.tags) < 3:
            self.tags.append(tag)
            self.tag = self.tags[0]  # Keep legacy field synced
            return True
        return False

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag. Returns True if removed, False if not found."""
        tag = tag.strip().lower()
        if tag in self.tags:
            self.tags.remove(tag)
            self.tag = self.tags[0] if self.tags else ""  # Keep legacy field synced
            return True
        return False
