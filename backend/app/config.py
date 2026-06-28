"""
ARGUS Platform Configuration
Centralized settings loaded from environment variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "ARGUS Risk Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Server ─────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'argus.db'}"

    # ── Google AI ──────────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_VISION_MODEL: str = "gemini-2.0-flash"
    GEMINI_FALLBACK_MODELS: List[str] = ["gemini-1.5-flash", "gemini-1.5-pro"]

    # ── Groq AI ─────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODELS: List[str] = ["llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]

    # ── Demo Mode (Mock AI responses without API calls) ─────────────────────────────
    DEMO_MODE: bool = False

    # ── File Upload ────────────────────────────────────────────────────────────
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    ALLOWED_DOCUMENT_TYPES: List[str] = ["application/pdf", "text/plain", "text/csv", "application/csv"]

    # ── CORS ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "*",
    ]

    # ── Reports ────────────────────────────────────────────────────────────────
    REPORTS_DIR: Path = BASE_DIR / "uploads" / "reports"

    # ── Search (optional) ──────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""  # Optional: for SearchMCP web search

    def get_upload_path(self, category: str) -> Path:
        """Return typed subdirectory for uploads."""
        path = self.UPLOAD_DIR / category
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
