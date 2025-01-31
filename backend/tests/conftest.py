import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from fastapi import FastAPI
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from ..app.models.user import User
from ..app.models.document import Document
from ..app.models.tag import Tag
from ..app.core.config import settings
from ..app.repositories.user import user_repository
from ..app.repositories.document import document_repository
from ..app.repositories.tag import tag_repository
from ..app.api.v1.api import api_router
from ..app.core.security import get_password_hash

# Test database name
TEST_DB_NAME = "test_objectdms"

def get_test_app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI(title=settings.PROJECT_NAME)
    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app

@pytest_asyncio.fixture
async def db() -> AsyncGenerator:
    """Create test database and collections."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    # Drop test database if it exists
    await client.drop_database(TEST_DB_NAME)
    
    # Initialize Beanie with test database
    await init_beanie(
        database=client[TEST_DB_NAME],
        document_models=[User, Document, Tag]
    )
    
    yield client[TEST_DB_NAME]
    
    # Cleanup
    await client.drop_database(TEST_DB_NAME)
    await client.close()

@pytest_asyncio.fixture
async def app(db) -> FastAPI:
    """Create test app with database."""
    return get_test_app()

@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator:
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def test_user(db) -> User:
    """Create test user."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User"
    }
    user = await user_repository.create_with_password(user_data)
    return user

@pytest_asyncio.fixture
async def test_superuser(db) -> User:
    """Create test superuser."""
    user_data = {
        "email": "admin@example.com",
        "username": "admin",
        "password": "admin123",
        "full_name": "Admin User",
        "is_superuser": True
    }
    user = await user_repository.create_with_password(user_data)
    return user

@pytest_asyncio.fixture
async def test_tag(db, test_user) -> Tag:
    """Create test tag."""
    tag = await tag_repository.get_or_create("test-tag", "Test Tag")
    return tag

@pytest_asyncio.fixture
async def test_document(db, test_user, test_tag) -> Document:
    """Create test document."""
    doc_data = {
        "title": "Test Document",
        "description": "Test Description",
        "file_name": "test.txt",
        "file_size": 1024,
        "mime_type": "text/plain",
        "file_path": "/test/path/test.txt",
        "tags": [str(test_tag.id)],
        "metadata": {"test": "data"},
        "owner": test_user
    }
    doc = Document(**doc_data)
    await doc.insert()
    return doc

@pytest.fixture
def test_file() -> Generator:
    """Create test file."""
    content = b"Test file content"
    file_path = "test_file.txt"
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    yield file_path
    
    if os.path.exists(file_path):
        os.remove(file_path) 