"""
ARGUS Platform — Auth Routes
JWT-based register, login, profile, and token refresh.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DBSession
from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database.models import User, UserRole
from app.database.schemas import TokenResponse, UserLogin, UserRegister, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: DBSession) -> User:
    """Register a new user account."""
    # Check for existing email / username
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.ANALYST,
    )
    db.add(user)
    db.flush()
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: DBSession) -> dict:
    """Authenticate and receive a JWT access token."""
    user = db.query(User).filter(
        (User.username == body.username) | (User.email == body.username)
    ).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.flush()

    token = create_access_token(subject=user.username, role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: CurrentUser) -> User:
    """Return the currently authenticated user's profile."""
    return current_user
