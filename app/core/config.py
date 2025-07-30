"""
Application configuration management using Pydantic Settings.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "SlideGenie"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "SlideGenie API"
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # JWT Settings
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "slidegenie-api"
    
    # Session Settings
    SESSION_TTL_SECONDS: int = 86400  # 24 hours
    
    # Redis Settings
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "slidegenie"
    DATABASE_URL: Optional[PostgresDsn] = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[RedisDsn] = None
    
    # MinIO (S3-compatible storage)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "slidegenie"
    MINIO_USE_SSL: bool = False
    
    # AI Services
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL_PRIMARY: str = "claude-3-5-sonnet-20241022"
    AI_MODEL_FALLBACK: str = "gpt-4o-mini"
    AI_MAX_RETRIES: int = 3
    AI_TIMEOUT_SECONDS: int = 120
    
    # AI Budget Limits (monthly in USD)
    AI_BUDGET_ANTHROPIC: float = 1000.0
    AI_BUDGET_OPENAI: float = 500.0
    
    # AI Cache Settings
    AI_CACHE_TTL_DAYS: int = 7
    AI_CACHE_ENABLED: bool = True
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@slidegenie.com"
    SMTP_FROM_NAME: str = "SlideGenie"
    SMTP_TLS: bool = True
    
    # OAuth Settings
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    
    # OAuth General Settings
    OAUTH_AUTO_CREATE_USERS: bool = True
    OAUTH_REDIRECT_TO_FRONTEND: bool = True
    OAUTH_STATE_TTL_SECONDS: int = 600  # 10 minutes
    
    # URLs
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".tex", ".docx"]
    
    # Generation Limits
    FREE_TIER_PRESENTATIONS_PER_MONTH: int = 5
    FREE_TIER_STORAGE_MB: int = 100
    GENERATION_TIMEOUT_SECONDS: int = 300
    MAX_SLIDES_PER_PRESENTATION: int = 100
    
    # Feature Flags
    ENABLE_LATEX_EXPORT: bool = True
    ENABLE_COLLABORATION: bool = True
    ENABLE_AI_SUGGESTIONS: bool = True
    ENABLE_ANALYTICS: bool = True
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if v:
            return v
        values = info.data
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        host = values.get("POSTGRES_HOST", "localhost")
        port = values.get("POSTGRES_PORT", 5432)
        db = values.get("POSTGRES_DB", "slidegenie")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    
    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info) -> str:
        if v:
            return v
        values = info.data
        host = values.get("REDIS_HOST", "localhost")
        port = values.get("REDIS_PORT", 6379)
        db = values.get("REDIS_DB", 0)
        password = values.get("REDIS_PASSWORD")
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Calculate max upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI service configuration."""
        return {
            "primary_model": self.AI_MODEL_PRIMARY,
            "fallback_model": self.AI_MODEL_FALLBACK,
            "max_retries": self.AI_MAX_RETRIES,
            "timeout": self.AI_TIMEOUT_SECONDS,
            "has_anthropic": bool(self.ANTHROPIC_API_KEY),
            "has_openai": bool(self.OPENAI_API_KEY),
        }


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()


# Create a settings instance for easy import
settings = get_settings()