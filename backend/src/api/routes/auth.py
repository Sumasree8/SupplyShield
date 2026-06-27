"""Authentication API routes."""
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import User, Organization, AuditLog, UserRole
from src.services.auth_service import (
    authenticate_user, create_access_token, create_refresh_token,
    hash_password, decode_token
)
from src.api.schemas.auth import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse
)
from src.middleware.auth import get_current_user

log = structlog.get_logger()
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        organization_id=user.organization_id,
        action="login",
        resource_type="session",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))

    access_token = create_access_token(str(user.id), str(user.organization_id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    log.info("auth.login_success", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new organization and admin user."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create organization
    org = Organization(name=payload.organization_name, industry=payload.industry)
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        organization_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()
    # created_at is a DB server_default — refresh so the response carries the
    # real value rather than None (the default isn't loaded by flush alone).
    await db.refresh(user)

    log.info("auth.register", user_id=str(user.id), org_id=str(org.id))

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        organization_id=str(org.id),
        organization_name=org.name,
        created_at=user.created_at,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        result = await db.execute(select(User).where(User.id == payload["sub"], User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        access_token = create_access_token(str(user.id), str(user.organization_id), user.role.value)
        new_refresh = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=3600,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        organization_id=str(current_user.organization_id),
        organization_name=current_user.organization.name if current_user.organization else "",
        created_at=current_user.created_at,
    )
