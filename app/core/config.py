from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.constants import AppEnv

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
    APP_ENV: AppEnv = AppEnv.DEV
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = Field(..., min_length=32)
    APP_BASE_URL: str = "http://localhost:8000"
    APP_TIMEZONE: str = "Asia/Jakarta"
    APP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    APP_LOG_FORMAT: Literal["json", "console"] = "console"

    # ── Database ────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(..., min_length=1)
    POSTGRES_DB: str = "NOCTRADB"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ── Auth ────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # Restrict to HMAC algorithms — blocks `alg=none` and RSA-confusion.
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    JWT_ISSUER: str = "noctra-autoworks"
    BCRYPT_ROUNDS: int = 12

    # ── Session / CSRF ──────────────────────────────────
    SESSION_COOKIE_NAME: str = "noctra_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7
    CSRF_COOKIE_NAME: str = "noctra_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_TOKEN_BYTES: int = 32

    # ── Rate limiting ───────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 300
    RATE_LIMIT_PUBLIC_PER_MINUTE: int = 60
    # Only enable behind a reverse proxy that STRIPS client-supplied
    # X-Forwarded-For and sets its own. Otherwise, leave False.
    TRUST_PROXY_HEADERS: bool = False

    # ── CORS / Hosts ────────────────────────────────────
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []
    CORS_ALLOW_CREDENTIALS: bool = False
    TRUSTED_HOSTS: Annotated[list[str], NoDecode] = [
        "localhost", "127.0.0.1", "*.noctra.local",
    ]

    # ── Email ───────────────────────────────────────────
    EMAIL_ENABLED: bool = False
    EMAIL_FROM_NAME: str = "NOCTRA Autoworks"
    EMAIL_FROM_ADDRESS: str = "hello@noctra.local"
    EMAIL_REPLY_TO: str | None = None

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_STARTTLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 30

    # ── Retry ───────────────────────────────────────────
    # Total attempts = 1 initial + SMTP_MAX_RETRIES retries.
    # Backoff: min(base × 2^attempt, max_delay) + up to 30% jitter.
    SMTP_MAX_RETRIES: int = 3
    SMTP_RETRY_BASE_DELAY: float = 1.0
    SMTP_RETRY_MAX_DELAY: float = 30.0

    # ── Public contact info ─────────────────────────────
    PUBLIC_PHONE: str = "+62 812 3456 7890"
    PUBLIC_EMAIL: str = "hello@noctra.local"
    PUBLIC_ADDRESS: str = "Jl. Contoh No. 123, Jakarta"
    PUBLIC_WHATSAPP: str | None = None

    # ── Media / Uploads ─────────────────────────────────
    MEDIA_ROOT: str = "media"

    # Internal media paths (uploads through this app) must start with one
    # of these prefixes. Prevents arbitrary local path references.
    MEDIA_URL_PREFIXES: Annotated[list[str], NoDecode] = ["/media/"]

    # External media hosts allowlisted for photo references (e.g. a CDN).
    # Empty = reject all external URLs — safe default for a self-hosted app.
    # Wildcard subdomains supported: "*.cdn.example.com".
    MEDIA_ALLOWED_HOSTS: Annotated[list[str], NoDecode] = []

    # ── Inquiry workflow ────────────────────────────────
    INQUIRY_TRACK_CONTACT_ON_TRANSITION: bool = True

    # ── Derived ─────────────────────────────────────────
    @property
    def database_url(self) -> str:
        # `quote_plus` would turn spaces into `+`, which SQLAlchemy's
        # URL parser treats as a literal `+` in userinfo — auth then fails
        # for any password containing a space. `quote` is correct here.
        user = quote(self.POSTGRES_USER, safe="")
        pwd = quote(self.POSTGRES_PASSWORD, safe="")
        return (
            f"postgresql+asyncpg://{user}:{pwd}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        user = quote(self.POSTGRES_USER, safe="")
        pwd = quote(self.POSTGRES_PASSWORD, safe="")
        return (
            f"postgresql://{user}:{pwd}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnv.PROD

    # ── Validators ──────────────────────────────────────
    @field_validator("APP_SECRET_KEY")
    @classmethod
    def _validate_secret(cls, v: str) -> str:
        weak = {"change-me", "secret", "test", "dev", "changeme"}
        if v.lower() in weak:
            raise ValueError("APP_SECRET_KEY must be a strong random value")
        return v

    @field_validator(
        "CORS_ORIGINS", "TRUSTED_HOSTS",
        "MEDIA_URL_PREFIXES", "MEDIA_ALLOWED_HOSTS",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("POSTGRES_PASSWORD")
    @classmethod
    def _validate_db_password(cls, v: str) -> str:
        bad = {"password", "postgres", "admin", "root", "1234"}
        if v.lower() in bad:
            raise ValueError(
                "POSTGRES_PASSWORD is too weak — use a strong random value"
            )
        return v

    @model_validator(mode="after")
    def _enforce_invariants(self) -> "Settings":
        if self.SESSION_COOKIE_SAMESITE == "none" and not self.SESSION_COOKIE_SECURE:
            raise ValueError(
                "SESSION_COOKIE_SAMESITE='none' requires SESSION_COOKIE_SECURE=True"
            )
        if self.is_production:
            if self.APP_DEBUG:
                raise ValueError("APP_DEBUG must be False in production")
            if not self.SESSION_COOKIE_SECURE:
                raise ValueError("SESSION_COOKIE_SECURE must be True in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()