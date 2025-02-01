from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.core.logging import app_logger
from app.core.monitoring import setup_monitoring
from app.core.middleware.audit import setup_audit_middleware
from app.api.v1.endpoints import router as api_router
from app.models.user import User
from app.models.document import Document
from app.models.tag import Tag
from app.models.role import Role, UserRole
from app.models.audit import AuditLog

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup monitoring and audit logging
setup_monitoring(app)
setup_audit_middleware(app)

@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup."""
    try:
        app_logger.info("Starting application...")
        
        # Initialize MongoDB connection
        app_logger.info("Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        await init_beanie(
            database=client[settings.MONGODB_DB],
            document_models=[
                User,
                Document,
                Tag,
                Role,
                UserRole,
                AuditLog
            ]
        )
        app_logger.info("MongoDB connection established")
        
        # Include API router
        app.include_router(api_router, prefix=settings.API_V1_STR)
        app_logger.info("API router initialized")
        
        app_logger.info("Application startup complete")
        
    except Exception as e:
        app_logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application services on shutdown."""
    try:
        app_logger.info("Shutting down application...")
        
        # Close MongoDB connection
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        client.close()
        app_logger.info("MongoDB connection closed")
        
        app_logger.info("Application shutdown complete")
        
    except Exception as e:
        app_logger.error(f"Error during shutdown: {str(e)}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}