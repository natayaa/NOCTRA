# app/core/config.py
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator, root_validator
from functools import lru_cache
import secrets
from enum import Enum

# ==================== ENUM CLASSES ====================

class Environment(str, Enum):
    """Application environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

# ==================== SETTINGS CLASS ====================

class Settings(BaseSettings):
    """
    Core application settings.
    All settings can be overridden by environment variables.
    """
    
    # ==================== BASE APPLICATION ====================
    APP_NAME: str = "NOKTRA Autoworks Core"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Core Application for NOKTRA Autoworks Dashboard"
    APP_ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT,
        env="APP_ENVIRONMENT"
    )
    DEBUG: bool = Field(False, env="DEBUG")
    
    # ==================== SECURITY ====================
    SECRET_KEY: str = Field(..., env="SECRET_KEY", min_length=32)
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    JWT_RESET_TOKEN_EXPIRE_MINUTES: int = Field(30, env="JWT_RESET_TOKEN_EXPIRE_MINUTES")
    JWT_VERIFICATION_TOKEN_EXPIRE_HOURS: int = Field(24, env="JWT_VERIFICATION_TOKEN_EXPIRE_HOURS")
    
    PASSWORD_HASH_ROUNDS: int = Field(12, env="PASSWORD_HASH_ROUNDS")
    
    # ==================== SERVER ====================
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    WORKERS: int = Field(4, env="WORKERS")
    RELOAD: bool = Field(False, env="RELOAD")
    BACKLOG: int = Field(2048, env="BACKLOG")
    TIMEOUT_KEEP_ALIVE: int = Field(5, env="TIMEOUT_KEEP_ALIVE")
    MAX_REQUESTS: int = Field(1000, env="MAX_REQUESTS")
    MAX_REQUESTS_JITTER: int = Field(100, env="MAX_REQUESTS_JITTER")
    
    # ==================== DATABASE ====================
    # PostgreSQL
    DB_HOST: str = Field("localhost", env="DB_HOST")
    DB_PORT: int = Field(5432, env="DB_PORT")
    DB_NAME: str = Field("noktra_core", env="DB_NAME")
    DB_USER: str = Field("postgres", env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DB_DRIVER: str = Field("postgresql+asyncpg", env="DB_DRIVER")
    
    # Connection Pool
    DB_POOL_SIZE: int = Field(20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(40, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(3600, env="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(True, env="DB_POOL_PRE_PING")
    DB_ECHO: bool = Field(False, env="DB_ECHO")
    DB_ECHO_POOL: bool = Field(False, env="DB_ECHO_POOL")
    
    # ==================== CACHE (Redis) ====================
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_SSL: bool = Field(False, env="REDIS_SSL")
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = Field(20, env="REDIS_MAX_CONNECTIONS")
    REDIS_SOCKET_TIMEOUT: int = Field(5, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    REDIS_RETRY_ON_TIMEOUT: bool = Field(True, env="REDIS_RETRY_ON_TIMEOUT")
    
    # Cache defaults
    CACHE_DEFAULT_TTL: int = Field(300, env="CACHE_DEFAULT_TTL")  # 5 minutes
    CACHE_ENABLED: bool = Field(True, env="CACHE_ENABLED")
    
    # ==================== CORS ====================
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ],
        env="CORS_ALLOWED_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: List[str] = Field(
        ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        env="CORS_ALLOW_METHODS"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        [
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Request-ID",
            "X-API-Key",
            "X-API-Version",
        ],
        env="CORS_ALLOW_HEADERS"
    )
    CORS_EXPOSE_HEADERS: List[str] = Field(
        [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Response-Time",
        ],
        env="CORS_EXPOSE_HEADERS"
    )
    CORS_MAX_AGE: int = Field(3600, env="CORS_MAX_AGE")
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_ENABLED: bool = Field(True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_DEFAULT_REQUESTS: int = Field(100, env="RATE_LIMIT_DEFAULT_REQUESTS")
    RATE_LIMIT_DEFAULT_PERIOD: int = Field(60, env="RATE_LIMIT_DEFAULT_PERIOD")  # seconds
    RATE_LIMIT_AUTH_REQUESTS: int = Field(10, env="RATE_LIMIT_AUTH_REQUESTS")
    RATE_LIMIT_AUTH_PERIOD: int = Field(300, env="RATE_LIMIT_AUTH_PERIOD")  # 5 minutes
    RATE_LIMIT_API_REQUESTS: int = Field(1000, env="RATE_LIMIT_API_REQUESTS")
    RATE_LIMIT_API_PERIOD: int = Field(3600, env="RATE_LIMIT_API_PERIOD")  # 1 hour
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field("logs/app.log", env="LOG_FILE")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    LOG_DATE_FORMAT: str = Field(
        "%Y-%m-%d %H:%M:%S",
        env="LOG_DATE_FORMAT"
    )
    LOG_MAX_SIZE: int = Field(10 * 1024 * 1024, env="LOG_MAX_SIZE")  # 10MB
    LOG_BACKUP_COUNT: int = Field(5, env="LOG_BACKUP_COUNT")
    LOG_JSON_FORMAT: bool = Field(False, env="LOG_JSON_FORMAT")
    LOG_INCLUDE_SOURCE: bool = Field(True, env="LOG_INCLUDE_SOURCE")
    
    # ==================== EMAIL ====================
    SMTP_HOST: str = Field("smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USER: str = Field(..., env="SMTP_USER")
    SMTP_PASSWORD: str = Field(..., env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = Field("noreply@noktra.com", env="SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = Field("NOKTRA Autoworks", env="SMTP_FROM_NAME")
    SMTP_USE_TLS: bool = Field(True, env="SMTP_USE_TLS")
    SMTP_USE_SSL: bool = Field(False, env="SMTP_USE_SSL")
    SMTP_TIMEOUT: int = Field(30, env="SMTP_TIMEOUT")
    
    # Email templates path
    EMAIL_TEMPLATES_DIR: str = Field("templates/email", env="EMAIL_TEMPLATES_DIR")
    
    # ==================== FILE STORAGE ====================
    STORAGE_TYPE: str = Field("local", env="STORAGE_TYPE")  # local, s3, minio, gcs
    STORAGE_ROOT: str = Field("storage", env="STORAGE_ROOT")
    STORAGE_BASE_URL: Optional[str] = Field(None, env="STORAGE_BASE_URL")
    
    # Local storage
    LOCAL_STORAGE_PATH: str = Field("storage/local", env="LOCAL_STORAGE_PATH")
    LOCAL_STORAGE_PUBLIC_URL: Optional[str] = Field(None, env="LOCAL_STORAGE_PUBLIC_URL")
    
    # S3/MinIO storage
    S3_ENDPOINT: Optional[str] = Field(None, env="S3_ENDPOINT")
    S3_ACCESS_KEY: Optional[str] = Field(None, env="S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = Field(None, env="S3_SECRET_KEY")
    S3_BUCKET: Optional[str] = Field(None, env="S3_BUCKET")
    S3_REGION: str = Field("ap-southeast-1", env="S3_REGION")
    S3_USE_SSL: bool = Field(True, env="S3_USE_SSL")
    S3_CDN_URL: Optional[str] = Field(None, env="S3_CDN_URL")
    
    # File upload restrictions
    MAX_UPLOAD_SIZE: int = Field(10 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = Field(
        [".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".doc", ".docx", ".xlsx"],
        env="ALLOWED_UPLOAD_EXTENSIONS"
    )
    IMAGE_ALLOWED_EXTENSIONS: List[str] = Field(
        [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        env="IMAGE_ALLOWED_EXTENSIONS"
    )
    DOCUMENT_ALLOWED_EXTENSIONS: List[str] = Field(
        [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"],
        env="DOCUMENT_ALLOWED_EXTENSIONS"
    )
    
    # ==================== I18N ====================
    DEFAULT_LANGUAGE: str = Field("id", env="DEFAULT_LANGUAGE")
    SUPPORTED_LANGUAGES: List[str] = Field(
        ["id", "en"],
        env="SUPPORTED_LANGUAGES"
    )
    LOCALE_PATH: str = Field("locales", env="LOCALE_PATH")
    TIMEZONE: str = Field("Asia/Jakarta", env="TIMEZONE")
    
    # ==================== API ====================
    API_V1_PREFIX: str = "/api/v1"
    API_V2_PREFIX: str = "/api/v2"
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    API_OPENAPI_URL: str = "/openapi.json"
    API_TITLE: str = "NOKTRA Autoworks Core API"
    API_DESCRIPTION: str = "Core API for NOKTRA Autoworks Dashboard"
    API_VERSION: str = "1.0.0"
    API_CONTACT_NAME: str = "NOKTRA Autoworks"
    API_CONTACT_EMAIL: str = "support@noktra.com"
    API_LICENSE_NAME: str = "Proprietary"
    
    # ==================== EXTERNAL SERVICES ====================
    EXTERNAL_SERVICES_TIMEOUT: int = Field(30, env="EXTERNAL_SERVICES_TIMEOUT")
    EXTERNAL_SERVICES_RETRY_ATTEMPTS: int = Field(3, env="EXTERNAL_SERVICES_RETRY_ATTEMPTS")
    EXTERNAL_SERVICES_RETRY_DELAY: int = Field(1, env="EXTERNAL_SERVICES_RETRY_DELAY")  # seconds
    
    # Example: Payment gateway (to be extended by payment module)
    PAYMENT_SERVICE_ENABLED: bool = Field(False, env="PAYMENT_SERVICE_ENABLED")
    PAYMENT_SERVICE_URL: Optional[str] = Field(None, env="PAYMENT_SERVICE_URL")
    
    # Example: Notification service
    NOTIFICATION_SERVICE_ENABLED: bool = Field(True, env="NOTIFICATION_SERVICE_ENABLED")
    NOTIFICATION_SERVICE_URL: Optional[str] = Field(None, env="NOTIFICATION_SERVICE_URL")
    
    # ==================== FEATURE FLAGS ====================
    FEATURE_AUTH_ENABLED: bool = Field(True, env="FEATURE_AUTH_ENABLED")
    FEATURE_CACHE_ENABLED: bool = Field(True, env="FEATURE_CACHE_ENABLED")
    FEATURE_ASYNC_ENABLED: bool = Field(True, env="FEATURE_ASYNC_ENABLED")
    FEATURE_AUDIT_LOG_ENABLED: bool = Field(True, env="FEATURE_AUDIT_LOG_ENABLED")
    FEATURE_BULK_OPERATIONS: bool = Field(True, env="FEATURE_BULK_OPERATIONS")
    FEATURE_EXPORT_ENABLED: bool = Field(True, env="FEATURE_EXPORT_ENABLED")
    FEATURE_IMPORT_ENABLED: bool = Field(True, env="FEATURE_IMPORT_ENABLED")
    FEATURE_NOTIFICATIONS: bool = Field(True, env="FEATURE_NOTIFICATIONS")
    FEATURE_WEBSOCKET: bool = Field(False, env="FEATURE_WEBSOCKET")
    FEATURE_BACKGROUND_TASKS: bool = Field(True, env="FEATURE_BACKGROUND_TASKS")
    FEATURE_SCHEDULER: bool = Field(False, env="FEATURE_SCHEDULER")
    
    # ==================== SECURITY HEADERS ====================
    SECURE_SSL_REDIRECT: bool = Field(False, env="SECURE_SSL_REDIRECT")
    SECURE_HSTS_SECONDS: int = Field(31536000, env="SECURE_HSTS_SECONDS")
    SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = Field(True, env="SECURE_HSTS_INCLUDE_SUBDOMAINS")
    SECURE_FRAME_DENY: bool = Field(True, env="SECURE_FRAME_DENY")
    SECURE_CONTENT_TYPE_NOSNIFF: bool = Field(True, env="SECURE_CONTENT_TYPE_NOSNIFF")
    SECURE_XSS_PROTECTION: bool = Field(True, env="SECURE_XSS_PROTECTION")
    SECURE_REFERRER_POLICY: str = Field(
        "strict-origin-when-cross-origin",
        env="SECURE_REFERRER_POLICY"
    )
    SECURE_CSP: Optional[str] = Field(None, env="SECURE_CSP")
    
    # ==================== SESSION ====================
    SESSION_ENABLED: bool = Field(False, env="SESSION_ENABLED")
    SESSION_SECRET_KEY: Optional[str] = Field(None, env="SESSION_SECRET_KEY")
    SESSION_COOKIE_NAME: str = Field("session", env="SESSION_COOKIE_NAME")
    SESSION_COOKIE_SECURE: bool = Field(False, env="SESSION_COOKIE_SECURE")
    SESSION_COOKIE_HTTPONLY: bool = Field(True, env="SESSION_COOKIE_HTTPONLY")
    SESSION_COOKIE_SAMESITE: str = Field("lax", env="SESSION_COOKIE_SAMESITE")
    SESSION_MAX_AGE: int = Field(86400, env="SESSION_MAX_AGE")  # 24 hours
    SESSION_CACHE_TTL: int = Field(3600, env="SESSION_CACHE_TTL")
    
    # ==================== CELERY / BACKGROUND TASKS ====================
    CELERY_BROKER_URL: Optional[str] = Field(None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(None, env="CELERY_RESULT_BACKEND")
    CELERY_TASK_ALWAYS_EAGER: bool = Field(True, env="CELERY_TASK_ALWAYS_EAGER")
    CELERY_TASK_TIME_LIMIT: int = Field(300, env="CELERY_TASK_TIME_LIMIT")  # 5 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(240, env="CELERY_TASK_SOFT_TIME_LIMIT")  # 4 minutes
    CELERY_TASK_MAX_RETRIES: int = Field(3, env="CELERY_TASK_MAX_RETRIES")
    
    # ==================== HEALTH CHECK ====================
    HEALTH_CHECK_PATH: str = "/health"
    HEALTH_CHECK_ENABLED: bool = Field(True, env="HEALTH_CHECK_ENABLED")
    HEALTH_CHECK_TIMEOUT: int = Field(10, env="HEALTH_CHECK_TIMEOUT")  # seconds
    HEALTH_CHECK_INTERVAL: int = Field(30, env="HEALTH_CHECK_INTERVAL")  # seconds
    
    # ==================== GRACEFUL SHUTDOWN ====================
    GRACEFUL_SHUTDOWN_TIMEOUT: int = Field(30, env="GRACEFUL_SHUTDOWN_TIMEOUT")  # seconds
    
    # ==================== DEBUG TOOLS ====================
    DEBUG_TOOLBAR_ENABLED: bool = Field(False, env="DEBUG_TOOLBAR_ENABLED")
    SQL_DEBUG_ENABLED: bool = Field(False, env="SQL_DEBUG_ENABLED")
    PROFILE_ENABLED: bool = Field(False, env="PROFILE_ENABLED")
    TRACE_ENABLED: bool = Field(False, env="TRACE_ENABLED")
    
    # ==================== VALIDATORS ====================
    
    @validator("SECRET_KEY", "JWT_SECRET_KEY")
    def validate_secret_keys(cls, v, field):
        """Ensure secret keys are long enough"""
        if len(v) < 32:
            raise ValueError(f"{field.name} must be at least 32 characters")
        # Check if using default/placeholder
        if v in ["change_this_in_production", "your-secret-key-here"]:
            raise ValueError(f"{field.name} must be set properly in production")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @validator("CORS_ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_UPLOAD_EXTENSIONS", "IMAGE_ALLOWED_EXTENSIONS", "DOCUMENT_ALLOWED_EXTENSIONS", pre=True)
    def parse_extensions(cls, v):
        """Parse extensions from string or list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @root_validator
    def validate_environment(cls, values):
        """Validate environment-specific settings"""
        env = values.get("APP_ENVIRONMENT")
        debug = values.get("DEBUG")
        
        # Production validation
        if env == Environment.PRODUCTION and debug:
            raise ValueError("DEBUG must be False in production")
        
        if env == Environment.PRODUCTION:
            # Additional production validations
            if values.get("SECRET_KEY") in ["change_this_in_production", "your-secret-key-here"]:
                raise ValueError("SECRET_KEY must be changed in production")
            if values.get("JWT_SECRET_KEY") in ["change_this_in_production", "your-jwt-secret-key-here"]:
                raise ValueError("JWT_SECRET_KEY must be changed in production")
        
        return values
    
    @root_validator
    def build_redis_url(cls, values):
        """Build Redis URL if not provided"""
        if values.get("REDIS_URL"):
            return values
        
        host = values.get("REDIS_HOST", "localhost")
        port = values.get("REDIS_PORT", 6379)
        password = values.get("REDIS_PASSWORD")
        db = values.get("REDIS_DB", 0)
        ssl = values.get("REDIS_SSL", False)
        
        if password:
            values["REDIS_URL"] = f"redis://:{password}@{host}:{port}/{db}"
        else:
            values["REDIS_URL"] = f"redis://{host}:{port}/{db}"
        
        if ssl:
            values["REDIS_URL"] += "?ssl=True"
        
        return values
    
    # ==================== PROPERTIES ====================
    
    @property
    def DATABASE_URL(self) -> str:
        """Build database connection URL"""
        return f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build synchronous database connection URL"""
        driver = self.DB_DRIVER.replace("+asyncpg", "")
        return f"{driver}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.APP_ENVIRONMENT == Environment.STAGING
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.APP_ENVIRONMENT == Environment.TESTING
    
    @property
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return self.DEBUG
    
    # ==================== CONFIG CLASS ====================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        use_enum_values = True
        extra = "ignore"  # Ignore extra environment variables

# ==================== SINGLETON INSTANCE ====================

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to avoid reading .env file multiple times.
    """
    return Settings()

# ==================== EXPORTS ====================

settings = get_settings()

__all__ = [
    "settings",
    "get_settings",
    "Settings",
    "Environment",
]