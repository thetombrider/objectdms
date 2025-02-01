"""Access control service for managing permissions."""

from typing import Optional, Any, List
from fastapi import HTTPException, status
from ...models.user import User
from ...models.role import Role, UserRole, Permission
from ...models.document import Document
from ..logging import app_logger

class AccessControl:
    """Service for managing access control and permissions."""
    
    @staticmethod
    async def check_permission(
        user: User,
        resource: str,
        action: str,
        target: Optional[Any] = None
    ) -> bool:
        """
        Check if a user has permission to perform an action on a resource.
        
        Args:
            user: The user to check permissions for
            resource: The type of resource (e.g., "document", "user")
            action: The action to perform (e.g., "create", "read", "update", "delete")
            target: Optional target resource instance to check conditions against
            
        Returns:
            bool: Whether the user has permission
        """
        # Superusers have all permissions
        if user.is_superuser:
            return True
        
        # Get user's roles
        user_roles = await UserRole.find({"user.id": user.id}).to_list()
        roles = await Role.find({"_id": {"$in": [ur.role.id for ur in user_roles]}}).to_list()
        
        # Check each role's permissions
        for role in roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    # If no conditions, permission is granted
                    if not permission.conditions:
                        return True
                    
                    # Check conditions
                    if target:
                        if await AccessControl._check_conditions(
                            user, permission.conditions, target
                        ):
                            return True
        
        return False
    
    @staticmethod
    async def ensure_permission(
        user: User,
        resource: str,
        action: str,
        target: Optional[Any] = None
    ) -> None:
        """
        Ensure a user has permission or raise an HTTPException.
        
        Args:
            user: The user to check permissions for
            resource: The type of resource
            action: The action to perform
            target: Optional target resource instance
            
        Raises:
            HTTPException: If the user doesn't have permission
        """
        if not await AccessControl.check_permission(user, resource, action, target):
            app_logger.warning(
                f"Access denied: User {user.id} attempted {action} on {resource}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    @staticmethod
    async def _check_conditions(
        user: User,
        conditions: dict,
        target: Any
    ) -> bool:
        """
        Check if conditions are met for a target resource.
        
        Args:
            user: The user to check conditions for
            conditions: The conditions to check
            target: The target resource instance
            
        Returns:
            bool: Whether all conditions are met
        """
        for condition, value in conditions.items():
            if condition == "owner" and value:
                if not hasattr(target, "owner"):
                    return False
                if target.owner.id != user.id:
                    return False
            
            elif condition == "shared" and value:
                if not isinstance(target, Document):
                    return False
                # Check if document is shared with user
                for share in target.shared_with:
                    if share.user.id == user.id:
                        return True
                return False
        
        return True
    
    @staticmethod
    async def get_accessible_resources(
        user: User,
        resource: str,
        action: str
    ) -> List[str]:
        """
        Get IDs of resources the user has access to.
        
        Args:
            user: The user to check access for
            resource: The type of resource
            action: The action to check
            
        Returns:
            List of resource IDs the user has access to
        """
        # Superusers have access to everything
        if user.is_superuser:
            return []  # Return empty list to indicate no filtering needed
        
        # Get user's roles and permissions
        user_roles = await UserRole.find({"user.id": user.id}).to_list()
        roles = await Role.find({"_id": {"$in": [ur.role.id for ur in user_roles]}}).to_list()
        
        # Collect conditions from all matching permissions
        conditions = []
        for role in roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    if permission.conditions:
                        conditions.append(permission.conditions)
                    else:
                        return []  # No conditions means access to all
        
        if not conditions:
            return ["none"]  # No matching permissions
        
        # Build query based on conditions
        query = {"$or": []}
        for condition in conditions:
            if "owner" in condition and condition["owner"]:
                query["$or"].append({"owner.id": user.id})
            if "shared" in condition and condition["shared"]:
                query["$or"].append({"shared_with.user.id": user.id})
        
        return query["$or"] if query["$or"] else ["none"]

# Global instance for convenient access
access_control = AccessControl() 