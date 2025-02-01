"""JWT token handling utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status
from ...core.config import settings

ALGORITHM = "HS256"

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional token expiration time
        additional_claims: Optional additional claims to include in the token
        
    Returns:
        str: The encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        Optional[str]: The subject (user ID) if valid, None otherwise
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        return str(payload.get("sub"))
    except JWTError:
        return None 