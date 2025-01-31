import magic
from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from ....core.config import settings
from ....core.storage import storage
from ....core.metadata import metadata_extractor
from ....models.document import Document
from ....models.user import User
from ....models.tag import Tag
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
    
    uploaded_documents = []
    file_paths = []
    
    try:
        # Process each file in the batch
        for i, file in enumerate(files):
            # Validate and upload file
            content_type = validate_file(file)
            file_path = await storage.upload_file(str(current_user.id), file, content_type)
            file_paths.append(file_path)
            
            # Extract metadata
            metadata = await metadata_extractor.extract_metadata(file, content_type)
            
            # Create document record
            document = Document(
                title=titles[i],
                description=descriptions[i] if descriptions else None,
                file_path=file_path,
                file_name=file.filename,
                file_size=file.size,
                mime_type=content_type,
                owner=current_user,
                tags=tags or [],
                metadata=metadata
            )
            await document.insert()
            uploaded_documents.append(document)
        
        return uploaded_documents
        
    except Exception as e:
        # Rollback: delete any uploaded files if operation fails
        for file_path in file_paths:
            await storage.delete_file(file_path)
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
    content_type = validate_file(file)
    
    try:
        file_path = await storage.upload_file(str(current_user.id), file, content_type)
        metadata = await metadata_extractor.extract_metadata(file, content_type)
        
        document = Document(
            title=title,
            description=description,
            file_path=file_path,
            file_name=file.filename,
            file_size=file.size,
            mime_type=content_type,
            owner=current_user,
            tags=tags or [],
            metadata=metadata
        )
        await document.insert()
        
        return document
        
    except Exception as e:
        if 'file_path' in locals():
            await storage.delete_file(file_path)
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
    documents = await Document.find(
        {"_id": {"$in": document_ids}, "owner.id": current_user.id}
    ).to_list()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found"
        )
    
    if permanent:
        # Physically delete files and records
        for doc in documents:
            await storage.delete_file(doc.file_path)
            if doc.thumbnail_path:
                await storage.delete_file(doc.thumbnail_path)
            await doc.delete()
    else:
        # Soft delete
        for doc in documents:
            doc.is_deleted = True
            doc.updated_at = datetime.now(datetime.timezone.utc)
            await doc.save()
    
    return {"message": f"Successfully deleted {len(documents)} documents"}

@router.post("/batch/restore")
async def batch_restore_documents(
    document_ids: List[str],
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Restore soft-deleted documents.
    """
    documents = await Document.find(
        {
            "_id": {"$in": document_ids},
            "owner.id": current_user.id,
            "is_deleted": True
        }
    ).to_list()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deleted documents found"
        )
    
    for doc in documents:
        doc.is_deleted = False
        doc.updated_at = datetime.now(datetime.timezone.utc)
        await doc.save()
    
    return {"message": f"Successfully restored {len(documents)} documents"}

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
    
    documents = await Document.find(
        {"_id": {"$in": document_ids}, "owner.id": current_user.id}
    ).to_list()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found"
        )
    
    for doc in documents:
        current_tags = set(doc.tags)
        if add_tags:
            current_tags.update(add_tags)
        if remove_tags:
            current_tags.difference_update(remove_tags)
        
        doc.tags = list(current_tags)
        doc.updated_at = datetime.now(datetime.timezone.utc)
        await doc.save()
    
    return {"message": f"Successfully updated tags for {len(documents)} documents"}

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
    # Build search criteria
    criteria = [
        {"owner.id": current_user.id},
        {"is_deleted": False}
    ]
    
    # Add text search if query provided
    if query:
        criteria.append(
            Or(
                Text(query, path="title"),
                Text(query, path="description"),
                Text(query, path="metadata.preview")
            )
        )
    
    # Add tag filter if provided
    if tags:
        criteria.append({"tags": {"$in": tags}})
    
    # Add mime type filter if provided
    if mime_types:
        criteria.append({"mime_type": {"$in": mime_types}})
    
    # Execute search
    documents = await Document.find(
        {"$and": criteria}
    ).sort(
        [("created_at", -1)]  # Sort by creation date, newest first
    ).skip(
        skip
    ).limit(
        limit
    ).to_list()
    
    # Get total count for pagination
    total = await Document.find({"$and": criteria}).count()
    
    return {
        "total": total,
        "documents": documents,
        "skip": skip,
        "limit": limit
    }

@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a document by ID.
    """
    document = await Document.get(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check ownership
    if document.owner.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return document

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a presigned URL to download the document.
    """
    document = await Document.get(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check ownership
    if document.owner.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Generate presigned URL
    url = await storage.get_presigned_url(
        document.file_path,
        expires_in=3600  # URL valid for 1 hour
    )
    
    return {"url": url} 