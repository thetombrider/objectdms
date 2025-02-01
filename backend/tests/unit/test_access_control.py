"""Test suite for AccessControl service."""

import pytest
from bson import ObjectId
from fastapi import HTTPException
from app.core.security.access_control import AccessControl
from app.models.user import User
from app.models.document import Document, SharePermission
from app.models.role import Role, UserRole, Permission

@pytest.mark.asyncio
class TestAccessControl:
    """Test suite for AccessControl service."""
    
    async def test_superuser_permissions(self):
        """Test that superusers have all permissions."""
        superuser = User(
            id=ObjectId(),
            username="admin",
            email="admin@example.com",
            is_superuser=True
        )
        
        # Superuser should have all permissions
        assert await AccessControl.check_permission(
            superuser, "document", "create"
        )
        assert await AccessControl.check_permission(
            superuser, "document", "delete"
        )
        assert await AccessControl.check_permission(
            superuser, "user", "manage"
        )
    
    async def test_role_based_permissions(self):
        """Test role-based permission checks."""
        user = User(
            id=ObjectId(),
            username="user",
            email="user@example.com"
        )
        
        # Create a role with specific permissions
        role = Role(
            id=ObjectId(),
            name="document_manager",
            permissions=[
                Permission(resource="document", action="create"),
                Permission(resource="document", action="read"),
                Permission(resource="document", action="update"),
                Permission(
                    resource="document",
                    action="delete",
                    conditions={"owner": True}
                )
            ]
        )
        await role.insert()
        
        # Assign role to user
        user_role = UserRole(user=user, role=role)
        await user_role.insert()
        
        # Test permissions
        assert await AccessControl.check_permission(
            user, "document", "create"
        )
        assert await AccessControl.check_permission(
            user, "document", "read"
        )
        assert not await AccessControl.check_permission(
            user, "user", "manage"
        )
    
    async def test_conditional_permissions(self):
        """Test permissions with conditions."""
        user = User(
            id=ObjectId(),
            username="user",
            email="user@example.com"
        )
        other_user = User(
            id=ObjectId(),
            username="other",
            email="other@example.com"
        )
        
        # Create documents
        owned_doc = Document(
            title="Owned Doc",
            file_path="/owned.pdf",
            file_name="owned.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=user
        )
        
        other_doc = Document(
            title="Other Doc",
            file_path="/other.pdf",
            file_name="other.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=other_user
        )
        
        # Create role with ownership condition
        role = Role(
            id=ObjectId(),
            name="document_owner",
            permissions=[
                Permission(
                    resource="document",
                    action="delete",
                    conditions={"owner": True}
                ),
                Permission(
                    resource="document",
                    action="update",
                    conditions={"owner": True}
                )
            ]
        )
        await role.insert()
        
        # Assign role to user
        user_role = UserRole(user=user, role=role)
        await user_role.insert()
        
        # Test conditional permissions
        assert await AccessControl.check_permission(
            user, "document", "delete", owned_doc
        )
        assert not await AccessControl.check_permission(
            user, "document", "delete", other_doc
        )
    
    async def test_shared_document_permissions(self):
        """Test permissions for shared documents."""
        owner = User(
            id=ObjectId(),
            username="owner",
            email="owner@example.com"
        )
        user = User(
            id=ObjectId(),
            username="user",
            email="user@example.com"
        )
        
        # Create document
        doc = Document(
            title="Shared Doc",
            file_path="/shared.pdf",
            file_name="shared.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=owner
        )
        
        # Share document with user
        await doc.share_with_user(
            user,
            owner,
            SharePermission(
                can_read=True,
                can_write=True,
                can_share=False,
                can_delete=False
            )
        )
        
        # Create role with shared condition
        role = Role(
            id=ObjectId(),
            name="shared_docs",
            permissions=[
                Permission(
                    resource="document",
                    action="read",
                    conditions={"shared": True}
                ),
                Permission(
                    resource="document",
                    action="write",
                    conditions={"shared": True}
                )
            ]
        )
        await role.insert()
        
        # Assign role to user
        user_role = UserRole(user=user, role=role)
        await user_role.insert()
        
        # Test shared document permissions
        assert await AccessControl.check_permission(
            user, "document", "read", doc
        )
        assert await AccessControl.check_permission(
            user, "document", "write", doc
        )
        assert not await AccessControl.check_permission(
            user, "document", "delete", doc
        )
    
    async def test_ensure_permission(self):
        """Test permission enforcement with HTTP exceptions."""
        user = User(
            id=ObjectId(),
            username="user",
            email="user@example.com"
        )
        
        # Create role without permissions
        role = Role(
            id=ObjectId(),
            name="limited",
            permissions=[]
        )
        await role.insert()
        
        # Assign role to user
        user_role = UserRole(user=user, role=role)
        await user_role.insert()
        
        # Test permission enforcement
        with pytest.raises(HTTPException) as exc_info:
            await AccessControl.ensure_permission(
                user, "document", "create"
            )
        assert exc_info.value.status_code == 403
        
    async def test_get_accessible_resources(self):
        """Test retrieving accessible resource IDs."""
        user = User(
            id=ObjectId(),
            username="user",
            email="user@example.com"
        )
        
        # Create documents
        owned_doc = Document(
            title="Owned Doc",
            file_path="/owned.pdf",
            file_name="owned.pdf",
            file_size=1024,
            mime_type="application/pdf",
            owner=user
        )
        await owned_doc.insert()
        
        # Create role with read permission
        role = Role(
            id=ObjectId(),
            name="reader",
            permissions=[
                Permission(resource="document", action="read")
            ]
        )
        await role.insert()
        
        # Assign role to user
        user_role = UserRole(user=user, role=role)
        await user_role.insert()
        
        # Get accessible documents
        accessible_docs = await AccessControl.get_accessible_resources(
            user, "document", "read"
        )
        assert str(owned_doc.id) in accessible_docs 