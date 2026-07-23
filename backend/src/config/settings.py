"""
Application settings with environment variable support.
All secrets loaded from environment — never hardcoded.
"""
import json
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "SupplyShield AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    # When true, seed demo data on startup IF the database is empty (never
    # drops). Safe to leave on; used for one-shot seeding on hosted deploys.
    SEED_ON_STARTUP: bool = False
    SECRET_KEY: str  # Required — must be set in environment
    # Stored as raw strings and exposed as parsed lists via the properties
    # below. Typed as `str` (not List) so pydantic-settings does NOT try to
    # JSON-decode the env value — that lets us accept EITHER a JSON array
    # (["a","b"]) OR a plain comma-separated string (a,b), the latter being far
    # easier to set in hosting dashboards (Render, Railway) that mangle quotes.
    ALLOWED_HOSTS_RAW: str = Field(default="*", alias="ALLOWED_HOSTS")
    CORS_ORIGINS_RAW: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    # Database (PostgreSQL)
    DATABASE_URL: str  # Required — postgresql+asyncpg://user:pass@host:port/dbname
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Graph Database (Neo4j)
    NEO4J_URI: Optional[str] = None
    NEO4J_USERNAME: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    NEO4J_DATABASE: str = "neo4j"

    # JWT Authentication
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis (for caching and Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # External APIs
    OPENWEATHER_API_KEY: Optional[str] = None
    NOAA_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    GDELT_BASE_URL: str = "https://api.gdeltproject.org"

    # Email (alerts)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "alerts@supplychield.ai"

    # Slack (alerts)
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Observability
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @staticmethod
    def _parse_list(value: str) -> List[str]:
        """Accept a JSON array (["a","b"]) or a comma-separated string (a,b)."""
        s = (value or "").strip()
        if not s:
            return []
        if s.startswith("["):
            return json.loads(s)
        return [item.strip() for item in s.split(",") if item.strip()]

    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        return self._parse_list(self.ALLOWED_HOSTS_RAW)

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return self._parse_list(self.CORS_ORIGINS_RAW)

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """Fail fast on insecure production configuration."""
        if self.ENVIRONMENT == "production":
            weak = {"", "changeme", "secret", "CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32"}
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY in weak:
                raise ValueError(
                    "SECRET_KEY must be a strong random value (>=32 chars) in production. "
                    "Generate one with: openssl rand -hex 32"
                )
            if self.ALLOWED_HOSTS == ["*"]:
                raise ValueError(
                    "ALLOWED_HOSTS must be restricted to known hostnames in production "
                    "(wildcard '*' disables host-header protection)."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
