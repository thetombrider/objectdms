import magic
from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from ....core.config import settings
from ....core.storage import storage
from ....core.metadata import metadata_extractor
from ....models.document import Document
from ....models.user import User
from ....models.tag import Tag
from ....repositories.document import document_repository
from ....repositories.tag import tag_repository
from ....api.deps import get_current_active_user
from beanie.operators import Or, Text, In
from datetime import datetime

router = APIRouter()

def validate_file(file: UploadFile) -> str:
    """
    Validate uploaded file size and type.
    
    Args:
        file: The uploaded file to validate
        
    Returns:
        str: The detected MIME type if valid
        
    Raises:
        HTTPException: If file size exceeds limit or type is not allowed
    """
    # Check file size by seeking to end
    file.file.seek(0, 2)  # 2 means seek from end
    size = file.file.tell()
    file.file.seek(0)  # Reset position
    
    # Validate file size against configured limit
    if size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )
    
    # Detect MIME type from file header
    header = file.file.read(2048)
    file.file.seek(0)  # Reset position
    mime = magic.from_buffer(header, mime=True)
    
    # Validate against allowed file types
    if mime not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {mime} not allowed"
        )
    
    return mime

@router.post("/batch", response_model=List[Document], status_code=status.HTTP_201_CREATED)
async def batch_create_documents(
    files: List[UploadFile] = File(...),
    titles: List[str] = Form(...),
    descriptions: List[str] | None = Form(None),
    tags: List[str] | None = Form(None),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Upload multiple documents in a single request.
    
    This endpoint handles batch upload of documents with the following features:
    - Validates all files before processing
    - Extracts metadata from each file
    - Creates document records in the database
    - Handles rollback if any operation fails
    
    Args:
        files: List of files to upload
        titles: Corresponding titles for each file
        descriptions: Optional descriptions for each file
        tags: Optional list of tags to apply to all documents
        current_user: The authenticated user performing the upload
        
    Returns:
        List[Document]: List of created document records
        
    Raises:
        HTTPException: If validation fails or upload fails
    """
    # Validate input lengths match
    if len(files) != len(titles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of files and titles must match"
        )
    
    if descriptions and len(descriptions) != len(files):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of descriptions must match number of files"
        )
    
    # Process tags if provided
    tag_objects = []
    if tags:
        tag_objects = await tag_repository.get_or_create_many(tags)
    
    # Prepare document data
    documents_data = []
    for i, file in enumerate(files):
        # Validate file
        content_type = validate_file(file)
        
        # Extract metadata
        metadata = await metadata_extractor.extract_metadata(file, content_type)
        
        documents_data.append({
            "file": file,
            "content_type": content_type,
            "metadata": {
                "title": titles[i],
                "description": descriptions[i] if descriptions else None,
                "file_name": file.filename,
                "file_size": file.size,
                "mime_type": content_type,
                "tags": [str(tag.id) for tag in tag_objects],
                "metadata": metadata
            }
        })
    
    try:
        # Use repository for batch creation with transaction support
        return await document_repository.batch_create_with_files(
            owner=current_user,
            documents_data=documents_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/single", response_model=Document, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str,
    description: str | None = None,
    tags: List[str] | None = None,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Upload a single document.
    """
    try:
        # Validate file
        content_type = validate_file(file)
        
        # Process tags if provided
        tag_objects = []
        if tags:
            tag_objects = await tag_repository.get_or_create_many(tags)
        
        # Extract metadata
        metadata = await metadata_extractor.extract_metadata(file, content_type)
        
        # Create document using repository
        document = await document_repository.create_with_file(
            owner=current_user,
            file_data={
                "file": file,
                "content_type": content_type
            },
            document_data={
                "title": title,
                "description": description,
                "file_name": file.filename,
                "file_size": file.size,
                "mime_type": content_type,
                "tags": [str(tag.id) for tag in tag_objects],
                "metadata": metadata
            }
        )
        
        return document
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/batch/download")
async def batch_download_documents(
    document_ids: List[str],
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get presigned URLs for multiple documents.
    """
    documents = await Document.find(
        {"_id": {"$in": document_ids}, "owner.id": current_user.id}
    ).to_list()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found"
        )
    
    urls = []
    for doc in documents:
        url = await storage.get_presigned_url(
            doc.file_path,
            expires_in=3600
        )
        urls.append({"id": str(doc.id), "url": url})
    
    return urls

@router.put("/batch", response_model=List[Document])
async def batch_update_documents(
    updates: List[Dict] = Body(...),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update multiple documents at once.
    Body format:
    [
        {
            "id": "document_id",
            "title": "new title",
            "description": "new description",
            "tags": ["tag1", "tag2"]
        }
    ]
    """
    document_ids = [update["id"] for update in updates]
    documents = await Document.find(
        {"_id": {"$in": document_ids}, "owner.id": current_user.id}
    ).to_list()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found"
        )
    
    updated_docs = []
    for update in updates:
        doc = next((d for d in documents if str(d.id) == update["id"]), None)
        if doc:
            # Update only provided fields
            if "title" in update:
                doc.title = update["title"]
            if "description" in update:
                doc.description = update["description"]
            if "tags" in update:
                doc.tags = update["tags"]
            
            doc.updated_at = datetime.now(datetime.timezone.utc)
            await doc.save()
            updated_docs.append(doc)
    
    return updated_docs

@router.delete("/batch")
async def batch_delete_documents(
    document_ids: List[str],
    permanent: bool = False,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete multiple documents.
    If permanent=True, physically delete files and records.
    If permanent=False, soft delete (mark as deleted).
    """
    try:
        deleted_count = await document_repository.batch_delete_with_files(
            owner=current_user,
            document_ids=document_ids,
            permanent=permanent
        )
        return {"message": f"Successfully deleted {deleted_count} documents"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/batch/restore")
async def batch_restore_documents(
    document_ids: List[str],
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Restore soft-deleted documents.
    """
    try:
        restored_count = await document_repository.restore_documents(
            owner=current_user,
            document_ids=document_ids
        )
        return {"message": f"Successfully restored {restored_count} documents"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/batch/tags")
async def batch_update_tags(
    document_ids: List[str],
    add_tags: List[str] | None = None,
    remove_tags: List[str] | None = None,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Add or remove tags from multiple documents.
    """
    if not add_tags and not remove_tags:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either add_tags or remove_tags must be provided"
        )
    
    try:
        # Process tags to add
        add_tag_objects = []
        if add_tags:
            add_tag_objects = await tag_repository.get_or_create_many(add_tags)
        
        # Process tags to remove
        remove_tag_objects = []
        if remove_tags:
            remove_tag_objects = await tag_repository.get_or_create_many(remove_tags)
        
        # Update documents
        updated_count = await document_repository.update_document_tags(
            owner=current_user,
            document_ids=document_ids,
            add_tags=[str(tag.id) for tag in add_tag_objects],
            remove_tags=[str(tag.id) for tag in remove_tag_objects]
        )
        
        return {"message": f"Successfully updated tags for {updated_count} documents"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/search")
async def search_documents(
    query: str,
    tags: List[str] | None = None,
    mime_types: List[str] | None = None,
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 10
) -> Any:
    """
    Search documents by text, tags, and file types.
    """
    try:
        documents, total = await document_repository.search_documents(
            owner=current_user,
            query=query,
            tags=tags,
            mime_types=mime_types,
            skip=skip,
            limit=limit,
            include_deleted=False
        )
        
        return {
            "total": total,
            "documents": documents,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a document by ID.
    """
    try:
        document = await document_repository.get_document(
            document_id=document_id,
            owner=current_user
        )
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        return document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a presigned URL to download the document.
    """
    try:
        url = await document_repository.get_download_url(
            document_id=document_id,
            owner=current_user,
            expires_in=3600  # URL valid for 1 hour
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 