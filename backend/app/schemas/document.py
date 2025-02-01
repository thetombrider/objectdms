"""Document schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema."""
    title: str = Field(..., description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    file_path: str = Field(..., description="Path to the document file")
    mime_type: str = Field(..., description="MIME type of the document")
    tags: List[str] = Field(default_factory=list, description="List of tags")


class DocumentCreate(DocumentBase):
    """Schema for document creation."""
    owner_id: str = Field(..., description="ID of the document owner")


class DocumentUpdate(DocumentBase):
    """Schema for document update."""
    title: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None


class Document(DocumentBase):
    """Schema for document response."""
    id: str = Field(..., description="Document ID")
    owner_id: str = Field(..., description="ID of the document owner")
    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Document last update timestamp")
    is_deleted: bool = Field(False, description="Whether the document is deleted")

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
