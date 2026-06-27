"""
Authentication service: JWT tokens, password hashing, RBAC.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.models.core import User, UserRole

log = structlog.get_logger()
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, organization_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# RBAC permission matrix
ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        "users:read", "users:write", "users:delete",
        "suppliers:read", "suppliers:write", "suppliers:delete",
        "risk:read", "risk:write",
        "alerts:read", "alerts:write", "alerts:delete",
        "graph:read", "graph:write",
        "simulator:run",
        "audit:read",
        "organization:manage",
    },
    UserRole.RISK_ANALYST: {
        "suppliers:read", "suppliers:write",
        "risk:read", "risk:write",
        "alerts:read", "alerts:write",
        "graph:read",
        "simulator:run",
    },
    UserRole.PROCUREMENT_MANAGER: {
        "suppliers:read", "suppliers:write",
        "risk:read",
        "alerts:read",
        "graph:read",
        "simulator:run",
    },
    UserRole.EXECUTIVE_VIEWER: {
        "suppliers:read",
        "risk:read",
        "alerts:read",
        "graph:read",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
