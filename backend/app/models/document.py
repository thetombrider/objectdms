from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document as BeanieDocument, Indexed, Link
from pydantic import Field
from .base import BaseModel
from .user import User
from .tag import Tag

class SharePermission(BaseModel):
    """Document sharing permission model."""
    can_read: bool = True
    can_write: bool = False
    can_share: bool = False
    can_delete: bool = False

class DocumentShare(BaseModel):
    """Document sharing model."""
    user: Link[User]
    permissions: SharePermission
    shared_at: datetime = datetime.now(datetime.timezone.utc)
    shared_by: Link[User]

class Document(BeanieDocument, BaseModel):
    title: str = Indexed(str)
    description: Optional[str] = None
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    owner: Link[User]
    tags: List[Link[Tag]] = Field(default_factory=list)
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    last_accessed: Optional[datetime] = None
    is_deleted: bool = False
    version: int = 1
    thumbnail_path: Optional[str] = None
    shared_with: List[DocumentShare] = []
    deleted_at: Optional[datetime] = None
    
    class Settings:
        name = "documents"
        indexes = [
            "title",
            "owner",
            "tags",
            "mime_type",
            "created_at",
            "updated_at",
            "is_deleted",
            "shared_with.user",
            [
                ("title", "text"),
                ("description", "text"),
                ("metadata.preview", "text"),
            ],
            [
                ("owner", 1),
                ("is_deleted", 1),
                ("created_at", -1),
            ],
            [
                ("owner", 1),
                ("tags", 1),
                ("created_at", -1),
            ],
            [
                ("owner", 1),
                ("mime_type", 1),
                ("created_at", -1),
            ],
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Important Document",
                "description": "Contains important information",
                "file_path": "documents/2024/01/document.pdf",
                "file_name": "document.pdf",
                "file_size": 1024576,
                "mime_type": "application/pdf",
                "metadata": {
                    "author": "John Doe",
                    "created": "2024-01-31",
                    "pages": 10,
                    "preview": "Document content preview..."
                }
            }
        }

    async def share_with_user(
        self,
        user: User,
        shared_by: User,
        permissions: Optional[SharePermission] = None
    ) -> None:
        """Share document with a user."""
        # Remove existing share if any
        self.shared_with = [s for s in self.shared_with if s.user.id != user.id]
        
        # Add new share
        self.shared_with.append(
            DocumentShare(
                user=user,
                permissions=permissions or SharePermission(),
                shared_by=shared_by
            )
        )
        await self.save()
    
    async def remove_share(self, user: User) -> None:
        """Remove document share for a user."""
        self.shared_with = [s for s in self.shared_with if s.user.id != user.id]
        await self.save()
    
    async def get_user_permissions(self, user: User) -> Optional[SharePermission]:
        """Get user's permissions for this document."""
        if user.id == self.owner.id:
            return SharePermission(
                can_read=True,
                can_write=True,
                can_share=True,
                can_delete=True
            )
        
        for share in self.shared_with:
            if share.user.id == user.id:
                return share.permissions
        
        return None
    
    async def soft_delete(self) -> None:
        """Soft delete the document."""
        self.is_deleted = True
        self.deleted_at = datetime.now(datetime.timezone.utc)
        await self.save()
    
    async def restore(self) -> None:
        """Restore a soft-deleted document."""
        self.is_deleted = False
        self.deleted_at = None
        await self.save()
