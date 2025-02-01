from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import EmailStr, Field, field_validator
from .base import BaseModel

class User(Document, BaseModel):
    email: str = Indexed(EmailStr, unique=True)
    username: str = Indexed(str, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    last_login: Optional[datetime] = None
    
    @field_validator('username')
    def username_must_be_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()
    
    class Settings:
        name = "users"
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
