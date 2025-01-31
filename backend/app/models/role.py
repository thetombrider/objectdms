from datetime import datetime
from typing import List, Optional
from beanie import Document, Link
from pydantic import BaseModel
from .user import User

class Permission(BaseModel):
    """Permission model for role-based access control."""
    resource: str  # e.g., "document", "tag"
    action: str    # e.g., "create", "read", "update", "delete"
    conditions: Optional[dict] = None  # Additional conditions (e.g., ownership)

class Role(Document):
    """Role model for access control."""
    name: str
    description: Optional[str] = None
    permissions: List[Permission]
    is_system_role: bool = False  # True for built-in roles like "admin", "user"
    created_at: datetime = datetime.now(datetime.timezone.utc)
    updated_at: datetime = datetime.now(datetime.timezone.utc)
    
    class Settings:
        name = "roles"
        indexes = [
            "name",
            ("name", {"unique": True})
        ]

class UserRole(Document):
    """User-Role association model."""
    user: Link[User]
    role: Link[Role]
    assigned_at: datetime = datetime.now(datetime.timezone.utc)
    assigned_by: Optional[Link[User]] = None
    
    class Settings:
        name = "user_roles"
        indexes = [
            "user",
            "role",
            ("user", "role", {"unique": True})
        ] 