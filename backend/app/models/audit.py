from datetime import datetime
from typing import Optional, Dict, Any
from beanie import Document, Link
from pydantic import BaseModel
from .user import User

class AuditLog(Document):
    """Audit log model for tracking system events."""
    timestamp: datetime = datetime.now(datetime.timezone.utc)
    user: Optional[Link[User]] = None
    action: str  # e.g., "create", "read", "update", "delete", "share"
    resource_type: str  # e.g., "document", "user", "tag"
    resource_id: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"  # "success" or "failure"
    error_message: Optional[str] = None
    
    class Settings:
        name = "audit_logs"
        indexes = [
            "timestamp",
            "user",
            "action",
            "resource_type",
            "resource_id",
            "status"
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