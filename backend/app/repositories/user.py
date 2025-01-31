from typing import Optional, List
from datetime import datetime, timedelta
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from ..core.security import get_password_hash, verify_password
from .base import BaseRepository

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for user operations."""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        return await self.get_by_query({"email": email.lower()})
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return await self.get_by_query({"username": username.lower()})
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user.
        
        Args:
            username: Username or email
            password: Plain password
            
        Returns:
            User if authentication successful, None otherwise
        """
        # Try username
        user = await self.get_by_username(username)
        if not user:
            # Try email
            user = await self.get_by_email(username)
        
        if not user or not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def create_with_password(self, data: UserCreate) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            data: User creation data including plain password
            
        Returns:
            Created user
        """
        async with self.transaction():
            # Check if email or username already exists
            if await self.get_by_email(data.email):
                raise ValueError("Email already registered")
            if await self.get_by_username(data.username):
                raise ValueError("Username already taken")
            
            user_dict = data.model_dump()
            user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
            user_dict["email"] = user_dict["email"].lower()
            user_dict["username"] = user_dict["username"].lower()
            
            user = User(**user_dict)
            await user.insert()
            return user
    
    async def update_last_login(self, user: User) -> User:
        """
        Update user's last login timestamp.
        
        Args:
            user: User to update
            
        Returns:
            Updated user
        """
        user.last_login = datetime.now(datetime.timezone.utc)
        await user.save()
        return user
    
    async def update_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Update user's password with verification.
        
        Args:
            user: User to update
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            True if password was updated
        """
        if not verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = get_password_hash(new_password)
        await user.save()
        return True
    
    async def reset_password(self, user: User, new_password: str) -> User:
        """
        Reset user's password without verification.
        For use with password reset functionality.
        
        Args:
            user: User to update
            new_password: New password
            
        Returns:
            Updated user
        """
        user.hashed_password = get_password_hash(new_password)
        await user.save()
        return user
    
    async def toggle_active_status(self, user: User, is_active: bool) -> User:
        """
        Toggle user's active status.
        
        Args:
            user: User to update
            is_active: New active status
            
        Returns:
            Updated user
        """
        user.is_active = is_active
        await user.save()
        return user
    
    async def get_inactive_users(self, days: int) -> List[User]:
        """
        Get users who haven't logged in for a specified number of days.
        
        Args:
            days: Number of days of inactivity
            
        Returns:
            List of inactive users
        """
        cutoff_date = datetime.now(datetime.timezone.utc) - timedelta(days=days)
        query = {
            "last_login": {"$lt": cutoff_date},
            "is_active": True
        }
        return await self.list(query=query)
    
    async def get_user_stats(self) -> dict:
        """
        Get user statistics.
        
        Returns:
            Dict containing user statistics
        """
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_users": {"$sum": 1},
                    "active_users": {
                        "$sum": {"$cond": ["$is_active", 1, 0]}
                    },
                    "superusers": {
                        "$sum": {"$cond": ["$is_superuser", 1, 0]}
                    }
                }
            }
        ]
        
        results = await self.aggregate(pipeline)
        if not results:
            return {
                "total_users": 0,
                "active_users": 0,
                "superusers": 0
            }
        
        stats = results[0]
        stats.pop("_id")
        return stats

# Global instance
user_repository = UserRepository() 