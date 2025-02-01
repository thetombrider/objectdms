"""Configuration settings for the ObjectDMS application."""

from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings.
    
    These settings can be overridden by environment variables.
    """
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ObjectDMS"
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # MongoDB settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "objectdms"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Storage settings
    STORAGE_PATH: str = "storage"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    class Config:
        """Pydantic model configuration."""
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
