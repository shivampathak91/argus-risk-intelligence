"""
ARGUS Platform — FastAPI Dependencies
Reusable dependency injections for auth, DB, and role checks.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.models import User, UserRole
from app.database.session import get_db_session


bearer_scheme = HTTPBearer(auto_error=False)


def get_db(db: Session = Depends(get_db_session)) -> Session:
    """Inject a database session."""
    return db


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the Bearer JWT token and return the active User.
    Raises 401 if token is missing, invalid, or user is inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == payload["sub"]).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to have the ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to have ANALYST or ADMIN role."""
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or Admin access required",
        )
    return current_user


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
AnalystUser = Annotated[User, Depends(require_analyst)]
DBSession = Annotated[Session, Depends(get_db)]
