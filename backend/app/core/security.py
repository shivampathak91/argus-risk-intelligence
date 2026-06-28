"""
ARGUS Platform — Security Core
JWT token generation/validation and password hashing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    
    Design: Uses bcrypt with automatic salt generation for secure password storage.
    bcrypt is chosen because it's designed specifically for password hashing:
    - Slow by design (prevents brute force attacks)
    - Includes salt automatically (prevents rainbow table attacks)
    - Adaptive work factor (can be made slower as hardware improves)
    
    Implementation: Converts password to bytes, generates salt, hashes, returns string
    """
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    
    Behavior: Returns True if password matches hash, False otherwise.
    Security: Uses constant-time comparison to prevent timing attacks.
    Error handling: Returns False on any exception (defensive programming).
    
    Implementation: Converts both to bytes, uses bcrypt.checkpw for verification
    """
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    subject: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a signed JWT access token.
    
    Design: Uses JSON Web Tokens (JWT) for stateless authentication.
    JWTs are self-contained - no server-side session storage needed.
    
    Payload includes:
    - sub: Subject (username) - identifies the user
    - role: User role for authorization
    - exp: Expiration time - token becomes invalid after this
    - iat: Issued at time - for audit trails
    - type: Token type - distinguishes access from refresh tokens
    
    Security: Signed with SECRET_KEY using HS256 algorithm.
    Expiration: Default from settings (typically 30 minutes) or custom delta.
    
    Implementation: Creates payload, encodes with JWT, returns token string
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,       # username
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Behavior: Returns the payload dict if valid, None if invalid/expired.
    
    Validation checks:
    - Signature verification (using SECRET_KEY)
    - Expiration check (exp claim)
    - Token type check (must be "access")
    
    Security: Returns None on any error - never raises exceptions.
    This prevents information leakage about token validity.
    
    Implementation: Uses jwt.decode with signature verification,
    checks token type, returns payload or None
    
    Usage: Called by authentication middleware to validate requests
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
