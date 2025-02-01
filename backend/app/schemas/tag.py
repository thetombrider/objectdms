"""Tag schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """Base tag schema."""
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")


class TagCreate(TagBase):
    """Schema for tag creation."""
    pass


class TagUpdate(TagBase):
    """Schema for tag update."""
    name: Optional[str] = None
    description: Optional[str] = None


class Tag(TagBase):
    """Schema for tag response."""
    id: str = Field(..., description="Tag ID")

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
