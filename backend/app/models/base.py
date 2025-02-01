"""Base model for all documents."""

from datetime import datetime
from zoneinfo import ZoneInfo
from beanie import Document
from pydantic import Field

class BaseDocument(Document):
    """Base document with common fields."""
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None)
    
    async def soft_delete(self) -> None:
        """Soft delete the document."""
        self.is_deleted = True
        self.deleted_at = datetime.now(ZoneInfo("UTC"))
        await self.save()
    
    async def restore(self) -> None:
        """Restore a soft-deleted document."""
        self.is_deleted = False
        self.deleted_at = None
        await self.save()
    
    class Settings:
        """Document settings."""
        use_revision = True
        validate_on_save = True

    async def save_document(self):
        """Save document with updated timestamp"""
        self.updated_at = datetime.now(ZoneInfo("UTC"))
        await self.save()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 