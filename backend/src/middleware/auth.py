"""JWT authentication middleware and RBAC dependency injection."""
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import User
from src.services.auth_service import decode_token, has_permission, UserRole

log = structlog.get_logger()
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates JWT and returns the authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
        # Only access tokens may authenticate API calls. Refresh tokens also
        # carry a `sub`, so without this check a long-lived refresh token would
        # be accepted as an access token on every protected route.
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except ValueError:
        raise credentials_exception

    result = await db.execute(
        select(User)
        .where(User.id == user_id, User.is_active == True)
        .options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception

    return user


def require_permission(permission: str):
    """Factory: returns a dependency that enforces a specific RBAC permission."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' does not have permission: {permission}",
            )
        return current_user
    return _check
