from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document as BeanieDocument, Indexed, Link
from pydantic import Field
from .base import BaseModel
from .user import User
from .tag import Tag

class SharePermission(BaseModel):
    """Document sharing permission model.
    
    This class defines the granular permissions that can be assigned when sharing a document.
    Each permission is a boolean flag that controls specific access rights.
    
    Attributes:
        can_read (bool): Permission to view the document content. Defaults to True.
        can_write (bool): Permission to modify the document. Defaults to False.
        can_share (bool): Permission to share the document with other users. Defaults to False.
        can_delete (bool): Permission to delete the document. Defaults to False.
    """
    can_read: bool = True
    can_write: bool = False
    can_share: bool = False
    can_delete: bool = False

class DocumentShare(BaseModel):
    """Document sharing model.
    
    This class represents a document share instance, tracking who has access to a document
    and what permissions they have.
    
    Attributes:
        user (Link[User]): The user who has been granted access to the document.
        permissions (SharePermission): The specific permissions granted to the user.
        shared_at (datetime): Timestamp when the document was shared. Defaults to current UTC time.
        shared_by (Link[User]): The user who initiated the share.
    """
    user: Link[User]
    permissions: SharePermission
    shared_at: datetime = datetime.now(datetime.timezone.utc)
    shared_by: Link[User]

class Document(BeanieDocument, BaseModel):
    """Document model representing a file in the system.
    
    This is the core model for document management, handling metadata, sharing,
    versioning, and soft deletion capabilities.
    
    Attributes:
        title (str): Document title, indexed for quick search.
        description (Optional[str]): Optional document description.
        file_path (str): Path to the stored file in the storage system.
        file_name (str): Original name of the file.
        file_size (int): Size of the file in bytes.
        mime_type (str): MIME type of the file.
        owner (Link[User]): Reference to the document owner.
        tags (List[Link[Tag]]): List of tags associated with the document.
        metadata (Dict[str, Any]): Additional metadata extracted from the document.
        created_at (datetime): Timestamp of document creation.
        updated_at (datetime): Timestamp of last update.
        last_accessed (Optional[datetime]): Timestamp of last access.
        is_deleted (bool): Soft deletion flag.
        version (int): Document version number.
        thumbnail_path (Optional[str]): Path to document thumbnail if available.
        shared_with (List[DocumentShare]): List of users the document is shared with.
        deleted_at (Optional[datetime]): Timestamp when document was soft deleted.
    """
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
        """Beanie ODM settings for the Document model.
        
        Defines collection name and indexes for optimized queries.
        The indexes are designed to support:
        - Full-text search on title, description, and metadata
        - Efficient filtering by owner, tags, and mime type
        - Quick access to shared documents
        - Optimized listing with various sorting options
        """
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
            # Text index for full-text search
            [
                ("title", "text"),
                ("description", "text"),
                ("metadata.preview", "text"),
            ],
            # Compound index for listing user's documents
            [
                ("owner", 1),
                ("is_deleted", 1),
                ("created_at", -1),
            ],
            # Compound index for filtering by tags
            [
                ("owner", 1),
                ("tags", 1),
                ("created_at", -1),
            ],
            # Compound index for filtering by mime type
            [
                ("owner", 1),
                ("mime_type", 1),
                ("created_at", -1),
            ],
        ]
    
    class Config:
        """Pydantic model configuration with example data."""
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
        """Share the document with another user.
        
        Args:
            user (User): The user to share the document with.
            shared_by (User): The user initiating the share.
            permissions (Optional[SharePermission]): Custom permissions for the share.
                If not provided, default read-only permissions are used.
        """
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
        """Remove document share from a user.
        
        Args:
            user (User): The user whose share should be removed.
        """
        self.shared_with = [s for s in self.shared_with if s.user.id != user.id]
        await self.save()
    
    async def get_user_permissions(self, user: User) -> Optional[SharePermission]:
        """Get a user's permissions for this document.
        
        Args:
            user (User): The user to check permissions for.
            
        Returns:
            Optional[SharePermission]: The user's permissions, or None if no access.
            Document owners automatically get full permissions.
        """
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
        """Soft delete the document.
        
        Marks the document as deleted without physically removing it from the database.
        Sets the deleted_at timestamp to track when the deletion occurred.
        """
        self.is_deleted = True
        self.deleted_at = datetime.now(datetime.timezone.utc)
        await self.save()
    
    async def restore(self) -> None:
        """Restore a soft-deleted document.
        
        Removes the deletion mark and clears the deleted_at timestamp,
        making the document accessible again.
        """
        self.is_deleted = False
        self.deleted_at = None
        await self.save()
