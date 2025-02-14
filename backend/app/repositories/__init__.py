"""
Repository layer for data access.

This module provides repositories that encapsulate data access logic
and provide a clean interface for working with the application's models.
"""

from .document import DocumentRepository, document_repository
from .user import UserRepository, user_repository
from .tag import TagRepository, tag_repository

__all__ = [
    "DocumentRepository",
    "UserRepository",
    "TagRepository",
    "document_repository",
    "user_repository",
    "tag_repository",
]
