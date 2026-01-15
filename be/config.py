"""Central configuration for the Job → Candidates matching MVP.

This module uses Pydantic Settings for validation and env management.
"""
from __future__ import annotations

import logging
from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class OCRBackend(str, Enum):
    """OCR backend type."""
    TESSERACT = "tesseract"
    HUGGINGFACE = "hf"


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/resume_matching",
        description="Async database connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=50)
    max_overflow: int = Field(default=10, ge=0, le=100)
    echo: bool = Field(default=False)


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""
    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", extra="ignore")

    model_name: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="Hugging Face model name for embeddings",
    )
    dim: int = Field(default=384, ge=128, le=1536, description="Embedding dimension")
    batch_size: int = Field(default=32, ge=1, le=256, description="Batch size for encoding")
    device: Literal["cpu", "cuda", "mps"] = Field(default="cpu")
    normalize_embeddings: bool = Field(default=True)


class MatchingSettings(BaseSettings):
    """Matching pipeline configuration."""
    model_config = SettingsConfigDict(env_prefix="MATCHING_", extra="ignore")

    top_k: int = Field(default=500, ge=10, le=5000, description="Initial retrieval candidates")
    top_n: int = Field(default=50, ge=1, le=500, description="Final shortlist size")
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)
    rules_version: str = Field(default="v1.0.0")
    taxonomy_version: str = Field(default="taxo-v1")


class OCRSettings(BaseSettings):
    """OCR configuration."""
    model_config = SettingsConfigDict(env_prefix="OCR_", extra="ignore")

    backend: OCRBackend = Field(default=OCRBackend.TESSERACT)
    hf_model_name: str = Field(default="microsoft/trocr-base-printed")
    tesseract_lang: str = Field(default="eng+vie", description="Tesseract language codes")
    dpi: int = Field(default=300, ge=150, le=600)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class SkillExtractionSettings(BaseSettings):
    """Skill extraction configuration."""
    model_config = SettingsConfigDict(env_prefix="SKILL_", extra="ignore")

    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    max_skills_per_doc: int = Field(default=50, ge=5, le=200)
    fuzzy_threshold: int = Field(default=80, ge=0, le=100, description="Rapidfuzz score threshold")


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    model_config = SettingsConfigDict(env_prefix="LOG_", extra="ignore")

    level: str = Field(default="INFO")
    format: str = Field(default="json")
    file: str | None = Field(default=None)


class Settings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    app_name: str = Field(default="Resume Matching MVP")
    version: str = Field(default="0.1.0")

    # Sub-configs
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    matching: MatchingSettings = Field(default_factory=MatchingSettings)
    ocr: OCRSettings = Field(default_factory=OCRSettings)
    skills: SkillExtractionSettings = Field(default_factory=SkillExtractionSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @field_validator("db", mode="before")
    @classmethod
    def validate_db(cls, v):
        return v if isinstance(v, DatabaseSettings) else DatabaseSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
