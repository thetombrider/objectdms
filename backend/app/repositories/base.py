from typing import Generic, TypeVar, List, Optional, Type, Any, AsyncContextManager
from contextlib import asynccontextmanager
from beanie import Document, PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from ..core.config import settings

ModelType = TypeVar("ModelType", bound=Document)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository providing common CRUD operations.
    
    Generic Types:
        ModelType: The Beanie document model type
        CreateSchemaType: The Pydantic model for creation operations
        UpdateSchemaType: The Pydantic model for update operations
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    @asynccontextmanager
    async def transaction(self) -> AsyncContextManager[None]:
        """
        Start a transaction session.
        
        Usage:
            async with repository.transaction():
                # Operations within transaction
        """
        session = await self.model.get_motor_collection().database.client.start_session()
        try:
            async with session.start_transaction():
                yield
                await session.commit_transaction()
        except Exception as e:
            await session.abort_transaction()
            raise e
        finally:
            session.end_session()
    
    async def get(self, id: str | PydanticObjectId) -> Optional[ModelType]:
        """Get a single record by ID."""
        if isinstance(id, str):
            try:
                id = PydanticObjectId(id)
            except Exception:
                return None
        return await self.model.get(id)
    
    async def get_by_query(self, query: dict) -> Optional[ModelType]:
        """Get a single record by query."""
        return await self.model.find_one(query)
    
    async def list(
        self,
        query: dict = None,
        skip: int = 0,
        limit: int = 100,
        sort: List[tuple] = None
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and sorting.
        
        Args:
            query: MongoDB query dict
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort: List of (field, direction) tuples for sorting
        """
        find_query = self.model.find(query) if query else self.model.find_all()
        
        if sort:
            find_query = find_query.sort(sort)
        
        return await find_query.skip(skip).limit(limit).to_list()
    
    async def count(self, query: dict = None) -> int:
        """Count records matching the query."""
        if query:
            return await self.model.find(query).count()
        return await self.model.find_all().count()
    
    async def create(self, data: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj = self.model(**data.model_dump())
        await obj.insert()
        return obj
    
    async def update(
        self,
        id: str | PydanticObjectId,
        data: UpdateSchemaType | dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Update a record by ID.
        
        Args:
            id: Record ID
            data: Update data (Pydantic model or dict)
        """
        obj = await self.get(id)
        if not obj:
            return None
            
        update_data = data.model_dump() if hasattr(data, 'model_dump') else data
        
        for field, value in update_data.items():
            setattr(obj, field, value)
        
        await obj.save()
        return obj
    
    async def delete(self, id: str | PydanticObjectId) -> bool:
        """Delete a record by ID."""
        obj = await self.get(id)
        if not obj:
            return False
        await obj.delete()
        return True
    
    async def bulk_create(self, items: List[CreateSchemaType]) -> List[ModelType]:
        """Create multiple records."""
        objects = [self.model(**item.model_dump()) for item in items]
        await self.model.insert_many(objects)
        return objects
    
    async def bulk_update(
        self,
        query: dict,
        update_data: dict
    ) -> int:
        """
        Update multiple records matching the query.
        Returns number of updated records.
        """
        result = await self.model.find(query).update_many({"$set": update_data})
        return result.modified_count
    
    async def bulk_delete(self, query: dict) -> int:
        """
        Delete multiple records matching the query.
        Returns number of deleted records.
        """
        result = await self.model.find(query).delete_many()
        return result.deleted_count
    
    async def exists(self, query: dict) -> bool:
        """Check if any record matches the query."""
        return await self.model.find_one(query) is not None
    
    async def aggregate(self, pipeline: List[dict]) -> List[dict]:
        """
        Execute an aggregation pipeline.
        
        Args:
            pipeline: MongoDB aggregation pipeline
            
        Returns:
            List of aggregation results
        """
        return await self.model.aggregate(pipeline).to_list(None) 