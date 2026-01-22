"""
Configuration management using Pydantic Settings.

This module defines the Settings class that loads configuration from
environment variables and .env files.
"""

from typing import Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = Field(default="Smart Agriculture", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")

    # Database (PostgreSQL)
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/smartag",
        description="PostgreSQL database URL",
    )

    # Redis (Celery broker)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for Celery broker",
    )

    # OpenAI API (for LangChain)
    openai_api_key: str = Field(
        default="", description="OpenAI API key for LLM operations"
    )

    # ChromaDB (Vector database)
    chroma_host: str = Field(default="chroma", description="ChromaDB host")
    chroma_port: int = Field(default=8000, description="ChromaDB port")

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0", description="Celery result backend"
    )

    # MinIO (Object storage)
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO endpoint")
    minio_access_key: str = Field(default="", description="MinIO access key")
    minio_secret_key: str = Field(default="", description="MinIO secret key")
    minio_bucket_name: str = Field(default="smart-agriculture", description="MinIO bucket name")
    minio_secure: bool = Field(default=False, description="Use HTTPS for MinIO")

    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        description="CORS allowed origins",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get the global Settings instance.

    Returns:
        Settings: The application settings

    Raises:
        ValidationError: If environment variables are invalid
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
