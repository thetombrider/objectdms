"""Role and permission models."""

from typing import List, Dict, Any
from beanie import Indexed, Link
from pydantic import Field

from app.models.base import BaseDocument
from app.models.user import User

class Permission:
    """Permission model."""
    
    def __init__(
        self,
        resource: str,
        action: str,
        conditions: Dict[str, Any] | None = None
    ):
        self.resource = resource
        self.action = action
        self.conditions = conditions or {}

class Role(BaseDocument):
    """Role document model."""
    
    name: Indexed(str, unique=True)
    description: str | None = None
    permissions: List[Permission] = Field(default_factory=list)
    
    class Settings:
        """Document settings."""
        name = "roles"
        use_revision = True
        validate_on_save = True

class UserRole(BaseDocument):
    """User role assignment model."""
    
    user: Link[User] = Field(...)
    role: Link[Role] = Field(...)
    
    class Settings:
        """Document settings."""
        name = "user_roles"
        use_revision = True
        validate_on_save = True 