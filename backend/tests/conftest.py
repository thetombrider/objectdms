"""Test configuration and fixtures."""

import os
import shutil
import pytest
import asyncio
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from httpx import AsyncClient
from fastapi import FastAPI

from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.tag import Tag
from app.models.role import Role, UserRole, Permission
from app.models.audit import AuditLog
from app.main import app

# Test database name
TEST_DB_NAME = "test_objectdms"

# Test monitoring directory
TEST_MONITORING_DIR = "test_monitoring"

@pytest.fixture(scope="session", autouse=True)
def setup_monitoring():
    """Set up monitoring directory for tests."""
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = TEST_MONITORING_DIR
    if os.path.exists(TEST_MONITORING_DIR):
        shutil.rmtree(TEST_MONITORING_DIR)
    os.makedirs(TEST_MONITORING_DIR)
    yield
    shutil.rmtree(TEST_MONITORING_DIR)

@pytest.fixture(scope="session")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create a MongoDB client for testing."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    yield client
    client.close()

@pytest.fixture(scope="session")
async def init_test_db(mongodb_client: AsyncIOMotorClient) -> AsyncGenerator[None, None]:
    """Initialize the test database with required models."""
    # Drop test database if it exists
    await mongodb_client.drop_database(TEST_DB_NAME)
    
    # Initialize Beanie with test database
    await init_beanie(
        database=mongodb_client[TEST_DB_NAME],
        document_models=[
            User,
            Document,
            Tag,
            Role,
            UserRole,
            AuditLog
        ]
    )
    
    yield
    
    # Clean up after tests
    await mongodb_client.drop_database(TEST_DB_NAME)

@pytest.fixture(autouse=True)
async def setup_test_db(init_test_db) -> AsyncGenerator[None, None]:
    """Fixture to ensure database is initialized for each test."""
    yield

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        app=app,
        base_url="http://test"
    ) as client:
        yield client

@pytest.fixture
async def test_user() -> User:
    """Create a test user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="dummy_hash"
    )
    await user.insert()
    return user

@pytest.fixture
async def test_superuser() -> User:
    """Create a test superuser for testing."""
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password="dummy_hash",
        is_superuser=True
    )
    await user.insert()
    return user

@pytest.fixture
async def test_document(test_user: User) -> Document:
    """Create a test document for testing."""
    doc = Document(
        title="Test Document",
        file_path="/test/document.pdf",
        file_name="document.pdf",
        file_size=1024,
        mime_type="application/pdf",
        owner=test_user
    )
    await doc.insert()
    return doc

@pytest.fixture
async def test_role() -> Role:
    """Create a test role for testing."""
    role = Role(
        name="test_role",
        description="Role for testing",
        permissions=[
            Permission(resource="document", action="read"),
            Permission(resource="document", action="create")
        ]
    )
    await role.insert()
    return role 