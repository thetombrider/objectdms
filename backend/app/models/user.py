"""User model."""

from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo
from beanie import Document, Indexed
from pydantic import EmailStr, Field, field_validator
from app.models.base import BaseDocument

class User(BaseDocument):
    """User document model."""
    
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    last_login: Optional[datetime] = Field(default=None)
    
    @field_validator('username')
    def username_must_be_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()
    
    async def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.now(ZoneInfo("UTC"))
        await self.save()
    
    class Settings:
        """Document settings."""
        name = "users"
        use_revision = True
        validate_on_save = True
        indexes = [
            "email",
            "username",
            [
                ("email", 1),
                ("username", 1),
            ],
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
            }
        }
