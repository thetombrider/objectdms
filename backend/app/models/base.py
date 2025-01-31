from datetime import datetime
from typing import Optional
from beanie import Document as BeanieDocument
from pydantic import BaseModel, Field


class BaseDocument(BeanieDocument):
    """Base document with common fields for all collections"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    class Settings:
        use_revision: bool = True  # Enable document versioning
        validate_on_save: bool = True  # Validate documents before saving

    async def save_document(self):
        """Save document with updated timestamp"""
        self.updated_at = datetime.utcnow()
        await self.save()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 