"""Test suite for Tag model."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId
from app.models.tag import Tag
from app.models.user import User

@pytest.mark.asyncio
class TestTagModel:
    """Test suite for Tag model functionality."""

    async def test_tag_creation(self):
        """Test basic tag creation with required fields."""
        owner = User(
            id=ObjectId(),
            email="test@example.com",
            username="testuser",
            hashed_password="dummy_hash"
        )
        
        tag = Tag(
            name="Important",
            description="Important documents",
            owner=owner
        )
        
        assert tag.name == "Important"
        assert tag.description == "Important documents"
        assert tag.owner == owner
        assert not tag.is_deleted
        assert isinstance(tag.created_at, datetime)
        assert tag.created_at.tzinfo == ZoneInfo("UTC")

    async def test_tag_soft_delete_restore(self):
        """Test tag soft deletion and restoration."""
        owner = User(
            id=ObjectId(),
            email="test@example.com",
            username="testuser",
            hashed_password="dummy_hash"
        )
        
        tag = Tag(
            name="Important",
            description="Important documents",
            owner=owner
        )
        
        # Test soft delete
        assert not tag.is_deleted
        assert tag.deleted_at is None
        
        await tag.soft_delete()
        assert tag.is_deleted
        assert isinstance(tag.deleted_at, datetime)
        assert tag.deleted_at.tzinfo == ZoneInfo("UTC")
        
        # Test restore
        await tag.restore()
        assert not tag.is_deleted
        assert tag.deleted_at is None 