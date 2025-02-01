"""API endpoints package."""

from fastapi import APIRouter
from . import auth, documents, sharing

# Create main router
router = APIRouter()

# Include routers from endpoints
router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

router.include_router(
    sharing.router,
    prefix="/documents",  # Sharing endpoints are under documents
    tags=["sharing"]
) 