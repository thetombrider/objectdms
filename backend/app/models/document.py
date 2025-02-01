from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from beanie import Indexed, Link
from pydantic import Field
from zoneinfo import ZoneInfo

from app.models.base import BaseDocument
from app.models.user import User
from app.models.tag import Tag

class SharePermission:
    """Document share permissions."""
    
    def __init__(
        self,
        can_read: bool = True,
        can_write: bool = False,
        can_share: bool = False,
        can_delete: bool = False
    ):
        self.can_read = can_read
        self.can_write = can_write
        self.can_share = can_share
        self.can_delete = can_delete

class DocumentShare:
    """Document share information."""
    
    def __init__(
        self,
        user: User,
        shared_by: User,
        permissions: SharePermission = SharePermission(),
        shared_at: datetime = None
    ):
        self.user = user
        self.shared_by = shared_by
        self.permissions = permissions
        self.shared_at = shared_at or datetime.now(ZoneInfo("UTC"))

class Document(BaseDocument):
    """Document model."""
    
    title: Indexed(str)
    description: Optional[str] = None
    file_path: str = Field(...)
    file_name: str = Field(...)
    file_size: int = Field(...)
    mime_type: str = Field(...)
    owner: Link[User] = Field(...)
    version: int = Field(default=1)
    thumbnail_path: Optional[str] = None
    shared_with: List[DocumentShare] = Field(default_factory=list)
    last_accessed: Optional[datetime] = None
    
    async def share_with_user(
        self,
        user: User,
        shared_by: User,
        permissions: SharePermission = SharePermission()
    ) -> None:
        """Share document with a user."""
        # Remove existing share if any
        self.shared_with = [share for share in self.shared_with if share.user.id != user.id]
        
        # Add new share
        share = DocumentShare(
            user=user,
            shared_by=shared_by,
            permissions=permissions
        )
        self.shared_with.append(share)
        await self.save()
    
    async def remove_share(self, user: User) -> None:
        """Remove document share for a user."""
        self.shared_with = [share for share in self.shared_with if share.user.id != user.id]
        await self.save()
    
    async def get_user_permissions(self, user: User) -> Optional[SharePermission]:
        """Get user permissions for the document."""
        # Owner has full permissions
        if user.id == self.owner.id:
            return SharePermission(
                can_read=True,
                can_write=True,
                can_share=True,
                can_delete=True
            )
        
        # Check shared permissions
        for share in self.shared_with:
            if share.user.id == user.id:
                return share.permissions
        
        return None
    
    async def update_last_accessed(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now(ZoneInfo("UTC"))
        await self.save()
    
    class Settings:
        """Document settings."""
        name = "documents"
        use_revision = True
        validate_on_save = True
        indexes = [
            "title",
            "owner",
            "mime_type",
            "created_at",
            "updated_at",
            "is_deleted",
            "shared_with.user",
            # Text index for full-text search
            [
                ("title", "text"),
                ("description", "text"),
            ],
            # Compound index for listing user's documents
            [
                ("owner", 1),
                ("is_deleted", 1),
                ("created_at", -1),
            ],
            # Compound index for filtering by mime type
            [
                ("owner", 1),
                ("mime_type", 1),
                ("created_at", -1),
            ],
        ]

    async def soft_delete(self) -> None:
        """Soft delete the document.
        
        Marks the document as deleted without physically removing it from the database.
        Sets the deleted_at timestamp to track when the deletion occurred.
        """
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        await self.save()
    
    async def restore(self) -> None:
        """Restore a soft-deleted document.
        
        Removes the deletion mark and clears the deleted_at timestamp,
        making the document accessible again.
        """
        self.is_deleted = False
        self.deleted_at = None
        await self.save()
