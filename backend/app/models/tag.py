from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field
from .base import BaseModel

class Tag(Document, BaseModel):
    name: str = Indexed(str, unique=True)
    description: Optional[str] = None
    color: Optional[str] = "#808080"  # Default gray color
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    
    class Settings:
        name = "tags"
        indexes = [
            "name",
            [
                ("name", "text"),
                ("description", "text"),
            ],
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "invoice",
                "description": "Financial documents and invoices",
                "color": "#FF0000"
            }
        }
