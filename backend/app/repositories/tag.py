from typing import List, Optional, Dict
from datetime import datetime
from ..models.tag import Tag
from ..models.document import Document
from ..schemas.tag import TagCreate, TagUpdate
from .base import BaseRepository

class TagRepository(BaseRepository[Tag, TagCreate, TagUpdate]):
    """Repository for tag operations."""
    
    def __init__(self):
        super().__init__(Tag)
    
    async def get_by_name(self, name: str) -> Optional[Tag]:
        """Get a tag by name."""
        return await self.get_by_query({"name": name.lower()})
    
    async def get_or_create(self, name: str, description: Optional[str] = None) -> Tag:
        """
        Get an existing tag or create a new one.
        
        Args:
            name: Tag name
            description: Optional tag description
            
        Returns:
            Existing or newly created tag
        """
        async with self.transaction():
            tag = await self.get_by_name(name)
            if tag:
                return tag
            
            tag = Tag(
                name=name.lower(),
                description=description,
                created_at=datetime.now(datetime.timezone.utc)
            )
            await tag.insert()
            return tag
    
    async def get_or_create_many(
        self,
        names: List[str]
    ) -> List[Tag]:
        """
        Get or create multiple tags by name.
        
        Args:
            names: List of tag names
            
        Returns:
            List of existing or newly created tags
        """
        async with self.transaction():
            tags = []
            for name in names:
                tag = await self.get_or_create(name)
                tags.append(tag)
            return tags
    
    async def search_tags(
        self,
        query: str = None,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Tag], int]:
        """
        Search tags by name or description.
        
        Args:
            query: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (tags, total_count)
        """
        search_query = {}
        if query:
            search_query = {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}}
                ]
            }
        
        tags = await self.list(
            query=search_query,
            skip=skip,
            limit=limit,
            sort=[("name", 1)]
        )
        
        total = await self.count(search_query)
        
        return tags, total
    
    async def merge_tags(self, source_tag: Tag, target_tag: Tag) -> Tag:
        """
        Merge source tag into target tag.
        Updates all documents using the source tag to use the target tag instead.
        
        Args:
            source_tag: Tag to merge from
            target_tag: Tag to merge into
            
        Returns:
            Updated target tag
        """
        async with self.transaction():
            # Update all documents using the source tag
            await Document.find(
                {"tags": source_tag.id}
            ).update_many({
                "$set": {"updated_at": datetime.now(datetime.timezone.utc)},
                "$pull": {"tags": source_tag.id},
                "$addToSet": {"tags": target_tag.id}
            })
            
            # Delete the source tag
            await source_tag.delete()
            
            return target_tag
    
    async def get_tag_usage_stats(self) -> List[Dict]:
        """
        Get usage statistics for all tags.
        
        Returns:
            List of dicts containing tag stats
        """
        pipeline = [
            {
                "$lookup": {
                    "from": Document._get_collection_name(),
                    "localField": "_id",
                    "foreignField": "tags",
                    "as": "documents"
                }
            },
            {
                "$project": {
                    "name": 1,
                    "description": 1,
                    "document_count": {"$size": "$documents"}
                }
            },
            {"$sort": {"document_count": -1}}
        ]
        
        return await self.aggregate(pipeline)
    
    async def get_unused_tags(self) -> List[Tag]:
        """
        Get tags that aren't used by any documents.
        
        Returns:
            List of unused tags
        """
        pipeline = [
            {
                "$lookup": {
                    "from": Document._get_collection_name(),
                    "localField": "_id",
                    "foreignField": "tags",
                    "as": "documents"
                }
            },
            {
                "$match": {
                    "documents": {"$size": 0}
                }
            }
        ]
        
        return await self.model.aggregate(pipeline).to_list()
    
    async def cleanup_unused_tags(self) -> int:
        """
        Delete all tags that aren't used by any documents.
        
        Returns:
            Number of tags deleted
        """
        unused_tags = await self.get_unused_tags()
        if not unused_tags:
            return 0
        
        async with self.transaction():
            for tag in unused_tags:
                await tag.delete()
            
            return len(unused_tags)

# Global instance
tag_repository = TagRepository() 