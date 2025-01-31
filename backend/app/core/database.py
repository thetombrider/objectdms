from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from ..core.config import settings
from ..models.user import User
from ..models.document import Document
from ..models.tag import Tag


class Database:
    client: Optional[AsyncIOMotorClient] = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB database"""
        if cls.client is None:
            try:
                cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
                # Initialize Beanie with the document models
                await init_beanie(
                    database=cls.client[settings.MONGODB_DB_NAME],
                    document_models=[
                        User,
                        Document,
                        Tag,
                    ]
                )
            except Exception as e:
                print(f"Error connecting to the MongoDB database: {e}")
                raise e

    @classmethod
    async def close_db(cls):
        """Close database connection"""
        if cls.client is not None:
            cls.client.close()
            cls.client = None

    @classmethod
    async def get_db(cls):
        """Get database instance"""
        if cls.client is None:
            await cls.connect_db()
        return cls.client[settings.MONGODB_DB_NAME] 