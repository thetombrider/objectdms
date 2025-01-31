import pytest
from datetime import datetime, timezone
from bson import ObjectId
from app.models.document import Document, SharePermission, DocumentShare
from app.models.user import User

@pytest.mark.asyncio
class TestDocumentModel:
    """Test suite for Document model functionality."""

    async def test_document_creation(self):
        """Test basic document creation with required fields."""
        owner = User(
            id=ObjectId(),
            email="test@example.com",
            username="testuser",
            hashed_password="dummy_hash"
        )
        
        doc = Document(
            title="Test Document",
            file_path="/path/to/file.pdf",
            file_name="file.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=owner
        )
        
        assert doc.title == "Test Document"
        assert doc.file_path == "/path/to/file.pdf"
        assert doc.file_size == 1024
        assert doc.mime_type == "application/pdf"
        assert doc.owner == owner
        assert not doc.is_deleted
        assert doc.version == 1
        assert isinstance(doc.created_at, datetime)
        assert doc.created_at.tzinfo == timezone.utc
    
    async def test_document_sharing(self):
        """Test document sharing functionality."""
        owner = User(id=ObjectId(), username="owner")
        user = User(id=ObjectId(), username="user")
        
        doc = Document(
            title="Shared Doc",
            file_path="/test.pdf",
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=owner
        )
        
        # Test sharing with default permissions
        await doc.share_with_user(user, owner)
        assert len(doc.shared_with) == 1
        share = doc.shared_with[0]
        assert share.user == user
        assert share.shared_by == owner
        assert share.permissions.can_read
        assert not share.permissions.can_write
        assert not share.permissions.can_share
        assert not share.permissions.can_delete
        
        # Test sharing with custom permissions
        custom_perms = SharePermission(
            can_read=True,
            can_write=True,
            can_share=True,
            can_delete=False
        )
        await doc.share_with_user(user, owner, custom_perms)
        assert len(doc.shared_with) == 1  # Should update existing share
        share = doc.shared_with[0]
        assert share.permissions.can_write
        assert share.permissions.can_share
        assert not share.permissions.can_delete
    
    async def test_remove_share(self):
        """Test removing document share."""
        owner = User(id=ObjectId(), username="owner")
        user1 = User(id=ObjectId(), username="user1")
        user2 = User(id=ObjectId(), username="user2")
        
        doc = Document(
            title="Shared Doc",
            file_path="/test.pdf",
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=owner
        )
        
        # Share with two users
        await doc.share_with_user(user1, owner)
        await doc.share_with_user(user2, owner)
        assert len(doc.shared_with) == 2
        
        # Remove share for user1
        await doc.remove_share(user1)
        assert len(doc.shared_with) == 1
        assert doc.shared_with[0].user == user2
    
    async def test_get_user_permissions(self):
        """Test retrieving user permissions for a document."""
        owner = User(id=ObjectId(), username="owner")
        user = User(id=ObjectId(), username="user")
        other_user = User(id=ObjectId(), username="other")
        
        doc = Document(
            title="Test Doc",
            file_path="/test.pdf",
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=owner
        )
        
        # Test owner permissions
        owner_perms = await doc.get_user_permissions(owner)
        assert owner_perms is not None
        assert all([
            owner_perms.can_read,
            owner_perms.can_write,
            owner_perms.can_share,
            owner_perms.can_delete
        ])
        
        # Test shared user permissions
        custom_perms = SharePermission(
            can_read=True,
            can_write=True,
            can_share=False,
            can_delete=False
        )
        await doc.share_with_user(user, owner, custom_perms)
        user_perms = await doc.get_user_permissions(user)
        assert user_perms is not None
        assert user_perms.can_read
        assert user_perms.can_write
        assert not user_perms.can_share
        assert not user_perms.can_delete
        
        # Test non-shared user permissions
        other_perms = await doc.get_user_permissions(other_user)
        assert other_perms is None
    
    async def test_soft_delete_restore(self):
        """Test document soft deletion and restoration."""
        owner = User(id=ObjectId(), username="owner")
        doc = Document(
            title="Test Doc",
            file_path="/test.pdf",
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=owner
        )
        
        # Test soft delete
        assert not doc.is_deleted
        assert doc.deleted_at is None
        
        await doc.soft_delete()
        assert doc.is_deleted
        assert isinstance(doc.deleted_at, datetime)
        assert doc.deleted_at.tzinfo == timezone.utc
        
        # Test restore
        await doc.restore()
        assert not doc.is_deleted
        assert doc.deleted_at is None 