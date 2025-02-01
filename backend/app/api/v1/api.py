from fastapi import APIRouter
from .endpoints import auth, documents, sharing

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

api_router.include_router(
    sharing.router,
    prefix="/documents",  # Sharing endpoints are under documents
    tags=["sharing"]
)
