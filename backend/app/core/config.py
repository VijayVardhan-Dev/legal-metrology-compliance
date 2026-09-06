from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
    )

    # Application
    APP_NAME: str = "Legal Metrology Compliance API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security (placeholder for Phase 3+)
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/legal_metrology"

    # CORS — origins allowed to call this API
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Storage Phase 3
    STORAGE_PATH: str = "storage"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Optional NLP enrichment. Nutrition extraction never depends on Gemini.
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash-lite"



# Singleton instance used throughout the application
settings = Settings()
