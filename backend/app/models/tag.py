"""Tag model."""

from beanie import Indexed, Link
from pydantic import Field

from app.models.base import BaseDocument
from app.models.user import User

class Tag(BaseDocument):
    """Tag document model."""
    
    name: Indexed(str, unique=True)
    description: str | None = None
    owner: Link[User] = Field(...)
    
    class Settings:
        """Document settings."""
        name = "tags"
        use_revision = True
        validate_on_save = True
