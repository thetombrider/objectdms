"""User schemas for request/response validation."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., description="Username")


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., description="User password")


class UserUpdate(UserBase):
    """Schema for user update."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """Schema for user response."""
    id: str = Field(..., description="User ID")
    is_active: bool = Field(True, description="Whether the user is active")
    is_superuser: bool = Field(False, description="Whether the user is a superuser")

    class Config:
        """Pydantic model configuration."""
        from_attributes = True
