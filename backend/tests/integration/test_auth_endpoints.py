import pytest
from httpx import AsyncClient
from app.core.config import settings

pytestmark = pytest.mark.asyncio

async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "testpass123",
        "full_name": "New User"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=user_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["full_name"] == user_data["full_name"]
    assert "password" not in data
    assert "hashed_password" not in data

async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test registration with duplicate email."""
    user_data = {
        "email": test_user.email,
        "username": "different",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=user_data
    )
    
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"].lower()

async def test_register_duplicate_username(client: AsyncClient, test_user):
    """Test registration with duplicate username."""
    user_data = {
        "email": "different@example.com",
        "username": test_user.username,
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json=user_data
    )
    
    assert response.status_code == 400
    assert "username already taken" in response.json()["detail"].lower()

async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    form_data = {
        "username": test_user.username,
        "password": "testpass123"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=form_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password."""
    form_data = {
        "username": test_user.username,
        "password": "wrongpass"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=form_data
    )
    
    assert response.status_code == 401
    assert "incorrect username or password" in response.json()["detail"].lower()

async def test_login_wrong_username(client: AsyncClient):
    """Test login with wrong username."""
    form_data = {
        "username": "nonexistent",
        "password": "testpass123"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=form_data
    )
    
    assert response.status_code == 401
    assert "incorrect username or password" in response.json()["detail"].lower()

async def test_login_inactive_user(client: AsyncClient, test_user):
    """Test login with inactive user."""
    # Make user inactive
    test_user.is_active = False
    await test_user.save()
    
    form_data = {
        "username": test_user.username,
        "password": "testpass123"
    }
    
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=form_data
    )
    
    assert response.status_code == 400
    assert "inactive user" in response.json()["detail"].lower()

async def test_rate_limit_register(client: AsyncClient):
    """Test rate limiting for register endpoint."""
    user_data = {
        "email": "test@example.com",
        "username": "test",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    # Make 6 requests (limit is 5 per minute)
    for i in range(6):
        user_data["email"] = f"test{i}@example.com"
        user_data["username"] = f"test{i}"
        response = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json=user_data
        )
        if i < 5:
            assert response.status_code in [201, 400]  # Success or duplicate error
        else:
            assert response.status_code == 429  # Too many requests

async def test_rate_limit_login(client: AsyncClient):
    """Test rate limiting for login endpoint."""
    form_data = {
        "username": "test",
        "password": "testpass123"
    }
    
    # Make 6 requests (limit is 5 per minute)
    for i in range(6):
        response = await client.post(
            f"{settings.API_V1_STR}/auth/login",
            data=form_data
        )
        if i < 5:
            assert response.status_code == 401  # Wrong credentials
        else:
            assert response.status_code == 429  # Too many requests 