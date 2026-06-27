"""Authentication API routes."""
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.config.settings import get_settings
from src.models.core import User, Organization, AuditLog, UserRole
from src.services.auth_service import (
    authenticate_user, create_access_token, create_refresh_token,
    hash_password, decode_token
)
from src.api.schemas.auth import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse
)
from src.middleware.auth import get_current_user
from src.middleware.rate_limit import login_rate_limiter, register_rate_limiter

log = structlog.get_logger()
settings = get_settings()
router = APIRouter()

# The refresh token is stored in an httpOnly cookie (never exposed to JS) and
# scoped to the auth routes so it isn't sent on every API call.
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",  # requires HTTPS in prod
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(login_rate_limiter),
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

    # Refresh token goes into an httpOnly cookie — not the JSON body — so it is
    # not reachable by JavaScript (XSS-resistant). Only the short-lived access
    # token is returned to the client.
    _set_refresh_cookie(response, refresh_token)

    log.info("auth.login_success", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(register_rate_limiter),
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
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Rotate the session: read the refresh token from the httpOnly cookie,
    issue a new access token, and rotate the refresh cookie."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
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
        _set_refresh_cookie(response, new_refresh)  # rotate

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(response: Response):
    """Clear the refresh-token cookie. The client also discards its access token."""
    _clear_refresh_cookie(response)
    return {"detail": "Logged out"}


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
