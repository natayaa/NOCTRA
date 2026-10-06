from functools import lru_cache
from pathlib import Path
from typing import Literal, Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode

# Absolute path so .env is found regardless of CWD
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────
    APP_NAME: str = "NOCTRA Autoworks"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = Field(..., min_length=32)
    APP_BASE_URL: str = "http://localhost:8000"
    APP_TIMEZONE: str = "Asia/Jakarta"
    APP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    APP_LOG_FORMAT: Literal["json", "console"] = "console"

    # ── Database ────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "noctra"
    POSTGRES_PASSWORD: str = "noctra"
    POSTGRES_DB: str = "noctra"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ── Auth ────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "noctra-autoworks"
    BCRYPT_ROUNDS: int = 12

    # ── Session / CSRF ──────────────────────────────────
    SESSION_COOKIE_NAME: str = "noctra_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 8
    CSRF_COOKIE_NAME: str = "noctra_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_TOKEN_BYTES: int = 32

    # ── Rate limiting ───────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 300
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 60

    # ── CORS / Hosts ────────────────────────────────────
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []
    CORS_ALLOW_CREDENTIALS: bool = False
    TRUSTED_HOSTS: Annotated[list[str], NoDecode] = [
        "localhost", "127.0.0.1", "*.noctra.local"
    ]

    # ── Derived ─────────────────────────────────────────
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    # ── Validators (INSIDE the class) ───────────────────
    @field_validator("APP_SECRET_KEY")
    @classmethod
    def _validate_secret(cls, v: str) -> str:
        weak = {"change-me", "secret", "test", "dev", "changeme"}
        if v.lower() in weak:
            raise ValueError("APP_SECRET_KEY must be a strong random value")
        return v

    @field_validator("CORS_ORIGINS", "TRUSTED_HOSTS", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()