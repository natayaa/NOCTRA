# core/config.py
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings."""

    # =========================================================================
    # Database
    # =========================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/workshop_db",
        description="Database connection URL"
    )
    DB_POOL_SIZE: int = Field(
        default=10, ge=1, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(
        default=20, ge=0, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(
        default=30, ge=1, description="Connection timeout in seconds")

    # =========================================================================
    # Application
    # =========================================================================
    APP_NAME: str = Field(default="Workshop Management API",
                          description="Application name")
    APP_VERSION: str = Field(
        default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=True, description="Debug mode")
    ENVIRONMENT: str = Field(
        default="development", description="Environment: development, staging, production")
    SECRET_KEY: str = Field(default="your-secret-key-here",
                            description="Secret key for JWT")

    # =========================================================================
    # API
    # =========================================================================
    API_PREFIX: str = Field(default="/api", description="API prefix")
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="CORS allowed origins (comma separated)"
    )

    # =========================================================================
    # Upload
    # =========================================================================
    UPLOAD_DIR: str = Field(default="./uploads",
                            description="Upload directory")
    MAX_UPLOAD_SIZE: int = Field(
        default=10_485_760, description="Max upload size in bytes")

    # =========================================================================
    # JWT / Auth
    # =========================================================================
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiry in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiry in days")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")

    # =========================================================================
    # External Services
    # =========================================================================
    WHATSAPP_API_URL: Optional[str] = Field(
        None, description="WhatsApp API URL")
    WHATSAPP_API_TOKEN: Optional[str] = Field(
        None, description="WhatsApp API token")
    EMAIL_HOST: Optional[str] = Field(None, description="Email host")
    EMAIL_PORT: Optional[int] = Field(None, description="Email port")
    EMAIL_USER: Optional[str] = Field(None, description="Email user")
    EMAIL_PASSWORD: Optional[str] = Field(None, description="Email password")

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> list:
        """Parse comma-separated origins into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# =============================================================================
# Singleton Settings Instance
# =============================================================================

settings = Settings()
