from typing import List, Optional, Any
from fastapi import HTTPException, status
from ...models.role import Role, UserRole, Permission
from ...models.user import User
from ...models.document import Document
from ..logging import app_logger

class AccessControl:
    """Access control service implementing Role-Based Access Control (RBAC).
    
    This service provides methods to check and enforce permissions based on user roles
    and specific conditions. It supports:
    - Role-based permission checks
    - Resource-specific access control
    - Conditional permissions (e.g., ownership-based access)
    - Permission enforcement with HTTP exception handling
    """
    
    @staticmethod
    async def check_permission(
        user: User,
        resource: str,
        action: str,
        target: Any = None
    ) -> bool:
        """Check if a user has permission to perform an action on a resource.
        
        This method implements the core RBAC logic, checking:
        1. Superuser status (automatic access)
        2. User roles and their associated permissions
        3. Permission conditions (e.g., ownership)
        
        Args:
            user: The user to check permissions for
            resource: Resource type (e.g., "document", "tag")
            action: Action to perform (e.g., "create", "read", "update", "delete")
            target: Optional target object to check conditions against
            
        Returns:
            bool: True if user has permission, False otherwise
            
        Example:
            >>> has_access = await AccessControl.check_permission(
            ...     user, "document", "read", document
            ... )
        """
        # Superusers have all permissions
        if user.is_superuser:
            return True
        
        # Get user roles
        user_roles = await UserRole.find({"user": user.id}).to_list()
        if not user_roles:
            return False
        
        # Get role permissions
        roles = await Role.find({"_id": {"$in": [ur.role.id for ur in user_roles]}}).to_list()
        
        # Check permissions
        for role in roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    # If no conditions, permission is granted
                    if not permission.conditions:
                        return True
                    
                    # Check conditions
                    if target and await AccessControl._check_conditions(
                        user, permission.conditions, target
                    ):
                        return True
        
        return False
    
    @staticmethod
    async def _check_conditions(user: User, conditions: dict, target: Any) -> bool:
        """Check permission conditions against a target object.
        
        Evaluates specific conditions that may be required for permission grant.
        Currently supports:
        - Ownership check: User must own the resource
        - Shared check: Resource must be shared with the user
        
        Args:
            user: The user to check conditions for
            conditions: Dictionary of condition names and values
            target: The object to check conditions against
            
        Returns:
            bool: True if all conditions are met, False otherwise
        """
        for condition, value in conditions.items():
            if condition == "owner":
                # Check if user is the owner
                if hasattr(target, "owner"):
                    return target.owner.id == user.id
            elif condition == "shared":
                # Check if document is shared with user
                if isinstance(target, Document):
                    return user.id in [share.user.id for share in target.shared_with]
        return False
    
    @staticmethod
    async def ensure_permission(
        user: User,
        resource: str,
        action: str,
        target: Any = None
    ) -> None:
        """Ensure user has permission or raise an HTTP exception.
        
        This is a convenience method that combines permission checking with
        HTTP exception handling. It's designed for use in API endpoints.
        
        Args:
            user: The user to check permissions for
            resource: Resource type (e.g., "document", "tag")
            action: Action to perform (e.g., "create", "read", "update", "delete")
            target: Optional target object to check conditions against
            
        Raises:
            HTTPException: With 403 status code if permission is denied
            
        Example:
            >>> await AccessControl.ensure_permission(
            ...     user, "document", "update", document
            ... )
        """
        has_permission = await AccessControl.check_permission(
            user, resource, action, target
        )
        if not has_permission:
            app_logger.warning(
                f"Access denied: User {user.id} attempted {action} on {resource}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    @staticmethod
    async def get_accessible_resources(
        user: User,
        resource: str,
        action: str
    ) -> List[str]:
        """Get list of resource IDs that user has permission to access.
        
        This method is useful for filtering queries to only show resources
        the user has access to. It considers:
        - User's roles and permissions
        - Resource ownership
        - Shared resources
        
        Args:
            user: The user to check permissions for
            resource: Resource type (e.g., "document", "tag")
            action: Action to perform (e.g., "read", "update")
            
        Returns:
            List[str]: List of accessible resource IDs.
                      Empty list means no restrictions (full access).
                      
        Example:
            >>> accessible_docs = await AccessControl.get_accessible_resources(
            ...     user, "document", "read"
            ... )
        """
        # Superusers can access everything
        if user.is_superuser:
            return []  # Empty list means no restrictions
        
        accessible_ids = set()
        
        # Get user roles and their permissions
        user_roles = await UserRole.find({"user": user.id}).to_list()
        roles = await Role.find({"_id": {"$in": [ur.role.id for ur in user_roles]}}).to_list()
        
        # Check each role's permissions
        for role in roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    if not permission.conditions:
                        return []  # No restrictions
                    
                    # Handle ownership condition
                    if permission.conditions.get("owner"):
                        if resource == "document":
                            docs = await Document.find({"owner": user.id}).to_list()
                            accessible_ids.update(str(doc.id) for doc in docs)
                    
                    # Handle shared condition
                    if permission.conditions.get("shared"):
                        if resource == "document":
                            docs = await Document.find(
                                {"shared_with.user": user.id}
                            ).to_list()
                            accessible_ids.update(str(doc.id) for doc in docs)
        
        return list(accessible_ids)

# Global instance for convenient access
access_control = AccessControl() 