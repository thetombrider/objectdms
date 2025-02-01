from datetime import datetime, timezone
from typing import Optional, Dict, Any
from beanie import Document, Link
from pydantic import Field
from .user import User

class AuditLog(Document):
    """Audit log model for tracking system events."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str  # e.g., "document.create", "user.login"
    user: Optional[Link[User]]  # The user who performed the action
    resource_type: str  # e.g., "document", "user"
    resource_id: Optional[str]  # ID of the affected resource
    action: str  # e.g., "create", "update", "delete"
    details: Dict[str, Any] = {}  # Additional event details
    ip_address: Optional[str]  # IP address of the user
    user_agent: Optional[str]  # User agent string

    class Settings:
        """Beanie ODM settings."""
        name = "audit_logs"
        indexes = [
            "timestamp",
            "event_type",
            "user",
            "resource_type",
            "resource_id",
            "action",
            [("timestamp", -1)],  # Index for time-based queries
            [("user", 1), ("timestamp", -1)],  # Index for user activity queries
            [("resource_type", 1), ("resource_id", 1), ("timestamp", -1)]  # Index for resource history
        ]
    
    @classmethod
    async def log_event(
        cls,
        *,
        user: Optional[User] = None,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> "AuditLog":
        """Create and save an audit log entry."""
        log = cls(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        await log.insert()
        return log 