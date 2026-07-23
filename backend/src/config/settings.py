"""
Application settings with environment variable support.
All secrets loaded from environment — never hardcoded.
"""
import json
from functools import lru_cache
from typing import Annotated, List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    # NoDecode: skip pydantic-settings' built-in JSON parsing so the validator
    # below can accept EITHER a JSON array (["a","b"]) OR a plain comma-separated
    # string (a,b) from the environment — the latter is far easier to set in
    # hosting dashboards (Render, Railway) that mangle quotes.
    ALLOWED_HOSTS: Annotated[List[str], NoDecode] = ["*"]
    CORS_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000", "http://localhost:5173"]

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

    @field_validator("ALLOWED_HOSTS", "CORS_ORIGINS", mode="before")
    @classmethod
    def _split_list(cls, v):
        """Accept a JSON array, a comma-separated string, or an actual list."""
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):
                return json.loads(s)
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

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
