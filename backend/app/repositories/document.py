from typing import List, Optional, Dict, Any
from datetime import datetime
from beanie.operators import Or, Text
from ..models.document import Document
from ..models.user import User
from ..schemas.document import DocumentCreate, DocumentUpdate
from .base import BaseRepository
from ..core.storage import storage

class DocumentRepository(BaseRepository[Document, DocumentCreate, DocumentUpdate]):
    """Repository for document operations."""
    
    def __init__(self):
        super().__init__(Document)
    
    async def create_with_file(
        self,
        owner: User,
        file_data: Dict[str, Any],
        document_data: DocumentCreate
    ) -> Document:
        """
        Create a document with associated file.
        Uses transaction to ensure consistency between storage and database.
        
        Args:
            owner: Document owner
            file_data: File information (file object, content type)
            document_data: Document metadata
            
        Returns:
            Created document
        """
        async with self.transaction():
            # Upload file to storage
            file_path = await storage.upload_file(
                str(owner.id),
                file_data["file"],
                file_data["content_type"]
            )
            
            # Create document record
            document = Document(
                **document_data.model_dump(),
                file_path=file_path,
                owner=owner
            )
            await document.insert()
            
            return document
    
    async def delete_with_file(self, document: Document) -> bool:
        """
        Delete a document and its associated file.
        Uses transaction to ensure consistency.
        
        Args:
            document: Document to delete
            
        Returns:
            True if successful
        """
        async with self.transaction():
            # Delete file from storage
            if document.file_path:
                await storage.delete_file(document.file_path)
            if document.thumbnail_path:
                await storage.delete_file(document.thumbnail_path)
            
            # Delete document record
            await document.delete()
            return True
    
    async def batch_create_with_files(
        self,
        owner: User,
        documents_data: List[Dict[str, Any]]
    ) -> List[Document]:
        """
        Create multiple documents with their files.
        Uses transaction to ensure consistency.
        
        Args:
            owner: Document owner
            documents_data: List of document data including files
            
        Returns:
            List of created documents
        """
        created_documents = []
        file_paths = []
        
        async with self.transaction():
            try:
                for data in documents_data:
                    # Upload file
                    file_path = await storage.upload_file(
                        str(owner.id),
                        data["file"],
                        data["content_type"]
                    )
                    file_paths.append(file_path)
                    
                    # Create document
                    document = Document(
                        **data["metadata"].model_dump(),
                        file_path=file_path,
                        owner=owner
                    )
                    await document.insert()
                    created_documents.append(document)
                
                return created_documents
                
            except Exception as e:
                # Clean up any uploaded files
                for file_path in file_paths:
                    await storage.delete_file(file_path)
                raise e
    
    async def batch_delete_with_files(
        self,
        owner: User,
        document_ids: List[str],
        permanent: bool = False
    ) -> int:
        """
        Delete multiple documents and their files.
        Uses transaction to ensure consistency.
        
        Args:
            owner: Document owner
            document_ids: List of document IDs
            permanent: Whether to permanently delete
            
        Returns:
            Number of documents deleted
        """
        query = {
            "_id": {"$in": document_ids},
            "owner.id": owner.id
        }
        
        if permanent:
            documents = await self.list(query=query)
            async with self.transaction():
                # Delete files from storage
                for doc in documents:
                    if doc.file_path:
                        await storage.delete_file(doc.file_path)
                    if doc.thumbnail_path:
                        await storage.delete_file(doc.thumbnail_path)
                
                # Delete document records
                return await self.bulk_delete(query)
        else:
            # Soft delete
            update_data = {
                "is_deleted": True,
                "updated_at": datetime.now(datetime.timezone.utc)
            }
            return await self.bulk_update(query, update_data)
    
    async def search_documents(
        self,
        owner: User,
        query: str = None,
        tags: List[str] = None,
        mime_types: List[str] = None,
        skip: int = 0,
        limit: int = 10,
        include_deleted: bool = False
    ) -> tuple[List[Document], int]:
        """
        Search documents with various filters.
        
        Args:
            owner: Document owner
            query: Full-text search query
            tags: Filter by tags
            mime_types: Filter by MIME types
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted documents
            
        Returns:
            Tuple of (documents, total_count)
        """
        criteria = [{"owner.id": owner.id}]
        
        if not include_deleted:
            criteria.append({"is_deleted": False})
        
        if query:
            criteria.append(
                Or(
                    Text(query, path="title"),
                    Text(query, path="description"),
                    Text(query, path="metadata.preview")
                )
            )
        
        if tags:
            criteria.append({"tags": {"$in": tags}})
        
        if mime_types:
            criteria.append({"mime_type": {"$in": mime_types}})
        
        find_query = {"$and": criteria}
        
        # Get documents with pagination
        documents = await self.list(
            query=find_query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        # Get total count
        total = await self.count(find_query)
        
        return documents, total
    
    async def batch_update_tags(
        self,
        owner: User,
        document_ids: List[str],
        add_tags: List[str] = None,
        remove_tags: List[str] = None
    ) -> List[Document]:
        """
        Update tags for multiple documents.
        
        Args:
            owner: Document owner
            document_ids: List of document IDs
            add_tags: Tags to add
            remove_tags: Tags to remove
            
        Returns:
            List of updated documents
        """
        query = {
            "_id": {"$in": document_ids},
            "owner.id": owner.id
        }
        
        documents = await self.list(query=query)
        updated_docs = []
        
        for doc in documents:
            current_tags = set(doc.tags)
            if add_tags:
                current_tags.update(add_tags)
            if remove_tags:
                current_tags.difference_update(remove_tags)
            
            doc.tags = list(current_tags)
            doc.updated_at = datetime.now(datetime.timezone.utc)
            await doc.save()
            updated_docs.append(doc)
        
        return updated_docs
    
    async def batch_soft_delete(
        self,
        owner: User,
        document_ids: List[str]
    ) -> int:
        """
        Soft delete multiple documents.
        
        Args:
            owner: Document owner
            document_ids: List of document IDs
            
        Returns:
            Number of documents deleted
        """
        query = {
            "_id": {"$in": document_ids},
            "owner.id": owner.id
        }
        
        update_data = {
            "is_deleted": True,
            "updated_at": datetime.now(datetime.timezone.utc)
        }
        
        return await self.bulk_update(query, update_data)
    
    async def batch_restore(
        self,
        owner: User,
        document_ids: List[str]
    ) -> int:
        """
        Restore soft-deleted documents.
        
        Args:
            owner: Document owner
            document_ids: List of document IDs
            
        Returns:
            Number of documents restored
        """
        query = {
            "_id": {"$in": document_ids},
            "owner.id": owner.id,
            "is_deleted": True
        }
        
        update_data = {
            "is_deleted": False,
            "updated_at": datetime.now(datetime.timezone.utc)
        }
        
        return await self.bulk_update(query, update_data)
    
    async def get_user_documents(
        self,
        owner: User,
        skip: int = 0,
        limit: int = 10,
        include_deleted: bool = False
    ) -> tuple[List[Document], int]:
        """
        Get user's documents with pagination.
        
        Args:
            owner: Document owner
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted documents
            
        Returns:
            Tuple of (documents, total_count)
        """
        query = {"owner.id": owner.id}
        if not include_deleted:
            query["is_deleted"] = False
        
        documents = await self.list(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        total = await self.count(query)
        
        return documents, total

# Global instance
document_repository = DocumentRepository() 