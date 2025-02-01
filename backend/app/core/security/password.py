"""Password hashing utilities."""
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The password to hash
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: The password to verify
        hashed_password: The hash to verify against
        
    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password) 