import pytest
from datetime import datetime, timedelta
from ...app.repositories.user import user_repository
from ...app.models.user import User
from ...app.core.security import verify_password

pytestmark = pytest.mark.asyncio

async def test_create_with_password(db):
    """Test user creation with password."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    user = await user_repository.create_with_password(user_data)
    
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert user.full_name == user_data["full_name"]
    assert verify_password(user_data["password"], user.hashed_password)
    assert user.is_active
    assert not user.is_superuser

async def test_create_duplicate_email(db, test_user):
    """Test creating user with duplicate email."""
    user_data = {
        "email": test_user.email,
        "username": "different",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    with pytest.raises(ValueError, match="Email already registered"):
        await user_repository.create_with_password(user_data)

async def test_create_duplicate_username(db, test_user):
    """Test creating user with duplicate username."""
    user_data = {
        "email": "different@example.com",
        "username": test_user.username,
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    with pytest.raises(ValueError, match="Username already taken"):
        await user_repository.create_with_password(user_data)

async def test_authenticate_success(db, test_user):
    """Test successful authentication."""
    user = await user_repository.authenticate("testuser", "testpass123")
    assert user is not None
    assert user.id == test_user.id

async def test_authenticate_wrong_password(db, test_user):
    """Test authentication with wrong password."""
    user = await user_repository.authenticate("testuser", "wrongpass")
    assert user is None

async def test_authenticate_wrong_username(db, test_user):
    """Test authentication with wrong username."""
    user = await user_repository.authenticate("wronguser", "testpass123")
    assert user is None

async def test_get_by_email(db, test_user):
    """Test getting user by email."""
    user = await user_repository.get_by_email(test_user.email)
    assert user is not None
    assert user.id == test_user.id

async def test_get_by_username(db, test_user):
    """Test getting user by username."""
    user = await user_repository.get_by_username(test_user.username)
    assert user is not None
    assert user.id == test_user.id

async def test_update_password(db, test_user):
    """Test password update."""
    new_password = "newpass123"
    success = await user_repository.update_password(
        test_user,
        "testpass123",
        new_password
    )
    assert success
    
    # Verify new password works
    user = await user_repository.authenticate(test_user.username, new_password)
    assert user is not None

async def test_update_password_wrong_current(db, test_user):
    """Test password update with wrong current password."""
    success = await user_repository.update_password(
        test_user,
        "wrongpass",
        "newpass123"
    )
    assert not success

async def test_reset_password(db, test_user):
    """Test password reset."""
    new_password = "newpass123"
    user = await user_repository.reset_password(test_user, new_password)
    assert user is not None
    
    # Verify new password works
    user = await user_repository.authenticate(test_user.username, new_password)
    assert user is not None

async def test_update_last_login(db, test_user):
    """Test updating last login time."""
    old_login = test_user.last_login
    user = await user_repository.update_last_login(test_user)
    assert user.last_login > old_login

async def test_get_inactive_users(db, test_user):
    """Test getting inactive users."""
    # Set last login to 31 days ago
    test_user.last_login = datetime.now(datetime.timezone.utc) - timedelta(days=31)
    await test_user.save()
    
    inactive_users = await user_repository.get_inactive_users(30)
    assert len(inactive_users) == 1
    assert inactive_users[0].id == test_user.id

async def test_get_user_stats(db, test_user, test_superuser):
    """Test getting user statistics."""
    stats = await user_repository.get_user_stats()
    assert stats["total_users"] == 2
    assert stats["active_users"] == 2
    assert stats["superusers"] == 1 