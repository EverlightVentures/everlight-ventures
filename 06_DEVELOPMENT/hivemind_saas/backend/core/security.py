"""
JWT auth helpers and API key encryption.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    """Create a signed JWT for a user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_fernet() -> Fernet:
    """Return a Fernet cipher for encrypting tenant API keys."""
    if not settings.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY not set in environment")
    return Fernet(settings.encryption_key.encode())


def encrypt_credential(plaintext: str) -> str:
    """Encrypt a user's API key before storing in the database."""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    """Decrypt a stored API key for use in a hive session."""
    return get_fernet().decrypt(ciphertext.encode()).decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
