from datetime import datetime, timezone
from typing import List, Optional
from beanie import Document, Link
from pydantic import Field
from .base import BaseModel
from .user import User

class Permission(BaseModel):
    """Permission model for role-based access control."""
    resource: str  # e.g., "document", "tag"
    action: str    # e.g., "create", "read", "update", "delete"
    conditions: dict = {}

class Role(Document):
    """Role model for user permissions."""
    name: str
    description: Optional[str] = None
    permissions: List[Permission] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "roles"
        indexes = [
            "name",
            [("name", 1)],  # Unique index on name
        ]

class UserRole(Document):
    """User-Role association model."""
    user: Link[User]
    role: Link[Role]
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_by: Optional[Link[User]] = None
    
    class Settings:
        name = "user_roles"
        indexes = [
            [("user", 1), ("role", 1)],  # Compound index for quick lookups
        ] 