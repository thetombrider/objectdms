"""Test configuration and fixtures."""

import os
import pytest
import asyncio
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.tag import Tag
from app.models.role import Role, UserRole, Permission
from app.models.audit import AuditLog

# Test database name
TEST_DB_NAME = "test_objectdms"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create a MongoDB client for testing."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    yield client
    client.close()

@pytest.fixture(scope="session")
async def init_test_db(mongodb_client: AsyncIOMotorClient) -> AsyncGenerator[None, None]:
    """Initialize the test database with required models."""
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
    
    # Clean up any existing data
    await cleanup_test_db(mongodb_client)
    
    yield
    
    # Clean up after tests
    await cleanup_test_db(mongodb_client)

async def cleanup_test_db(client: AsyncIOMotorClient) -> None:
    """Clean up the test database by dropping all collections."""
    db = client[TEST_DB_NAME]
    collections = await db.list_collection_names()
    for collection in collections:
        await db.drop_collection(collection)

@pytest.fixture(autouse=True)
async def setup_test_db(init_test_db) -> AsyncGenerator[None, None]:
    """Fixture to ensure database is initialized for each test."""
    yield

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