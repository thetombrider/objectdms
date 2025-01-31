from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from ....models.user import User
from ....models.document import Document, SharePermission
from ....core.security.access_control import access_control
from ....core.logging import app_logger
from ...deps import get_current_active_user

router = APIRouter()

@router.post("/{document_id}/share/{user_id}")
async def share_document(
    document_id: str,
    user_id: str,
    permissions: SharePermission,
    current_user: User = Depends(get_current_active_user)
) -> Document:
    """
    Share a document with another user.
    """
    # Get document
    document = await Document.get(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if user has permission to share
    await access_control.ensure_permission(
        current_user, "document", "share", document
    )
    
    # Get target user
    target_user = await User.get(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Share document
    try:
        await document.share_with_user(
            user=target_user,
            shared_by=current_user,
            permissions=permissions
        )
        app_logger.info(
            f"Document {document_id} shared with user {user_id} by {current_user.id}"
        )
        return document
    except Exception as e:
        app_logger.error(f"Error sharing document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sharing document"
        )

@router.delete("/{document_id}/share/{user_id}")
async def remove_share(
    document_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Document:
    """
    Remove document share from a user.
    """
    # Get document
    document = await Document.get(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if user has permission to manage shares
    await access_control.ensure_permission(
        current_user, "document", "share", document
    )
    
    # Get target user
    target_user = await User.get(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove share
    try:
        await document.remove_share(target_user)
        app_logger.info(
            f"Share removed for document {document_id} from user {user_id} by {current_user.id}"
        )
        return document
    except Exception as e:
        app_logger.error(f"Error removing share: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing share"
        )

@router.get("/{document_id}/shares")
async def get_document_shares(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> List[dict]:
    """
    Get list of users the document is shared with.
    """
    # Get document
    document = await Document.get(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if user has permission to view shares
    await access_control.ensure_permission(
        current_user, "document", "read", document
    )
    
    # Return shares
    return [
        {
            "user_id": str(share.user.id),
            "username": share.user.username,
            "permissions": share.permissions.dict(),
            "shared_at": share.shared_at,
            "shared_by": {
                "user_id": str(share.shared_by.id),
                "username": share.shared_by.username
            }
        }
        for share in document.shared_with
    ]

@router.get("/shared-with-me")
async def get_shared_documents(
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 10
) -> dict:
    """
    Get documents shared with the current user.
    """
    # Get documents shared with user
    query = {
        "shared_with.user": current_user.id,
        "is_deleted": False
    }
    
    documents = await Document.find(query).skip(skip).limit(limit).to_list()
    total = await Document.find(query).count()
    
    return {
        "total": total,
        "documents": documents,
        "skip": skip,
        "limit": limit
    } 