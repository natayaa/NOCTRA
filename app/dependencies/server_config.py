from pydantic import Field
from pydantic_settings import (BaseSettings, SettingsConfigDict)


class Settings(BaseSettings):
    """
    Application Configuration
    """
    # =====================
    # Environment
    # =====================
    STAGE: str = "development"
    # =====================
    # API
    # =====================

    HOSTNAME: str = "0.0.0.0"
    PORT: int = 8000

    API_NAME: str = "Noctra"
    API_DESCRIPTION: str = ""
    API_VERSION: str = "1.0.0"
    API_PREFIX_PATH: str = "/api"
    API_TOKEN_URL: str = "/auth/login"
    API_ENABLE_DOCS: bool = False

    # =====================
    # Authentication
    # =====================

    ACCESS_SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRES_DAYS: int = 7

    # =====================
    # CSRF
    # =====================

    CSRF_SECRET_KEY: str
    CSRF_SALT_KEY: str

    # =====================
    # Session
    # =====================

    SESSION_EXPIRES_MINUTES: int = 60

    HTTP_ONLY: bool = True

    SAME_SITE: str = "lax"

    TOKEN_MAX_AGE: int = 3600

    # =====================
    # Database
    # =====================

    DATABASE_URL: str

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    DB_POOL_TIMEOUT: int = 30

    DB_POOL_RECYCLE: int = 1800

    DB_ECHO: bool = False

    # =====================
    # Paths
    # =====================

    CONFIG_PATH: str = "./config"

    # =====================
    # Pydantic Settings
    # =====================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def docs_url(self) -> str | None:
        """
        Disable swagger in production.
        """

        if not self.API_ENABLE_DOCS:
            return None

        return "/docs"

    @property
    def redoc_url(self) -> str | None:
        """
        Disable redoc in production.
        """

        if not self.API_ENABLE_DOCS:
            return None

        return "/redoc"

    @property
    def is_production(self) -> bool:
        return self.STAGE.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.STAGE.lower() == "development"


settings = Settings()
