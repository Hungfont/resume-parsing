"""Embedding service for multilingual (vi/en) text embeddings.

Wraps sentence-transformers with proper batching, error handling, and caching.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

import numpy as np

# Try to import torch and sentence-transformers, but provide fallback
try:
    import torch
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError as e:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Torch/sentence-transformers not available: {e}. Embeddings will use placeholder values.")
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None

from tenacity import retry, stop_after_attempt, wait_exponential

from be.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding computation fails."""
    pass


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer | None:
    """Load and cache the sentence transformer model.
    
    Returns:
        Initialized SentenceTransformer model or None if unavailable
        
    Raises:
        EmbeddingError: If model loading fails
    """
    if not EMBEDDINGS_AVAILABLE:
        logger.warning("Embeddings not available - using placeholder values")
        return None
        
    try:
        logger.info(
            f"Loading embedding model: {settings.embeddings.model_name} "
            f"on device: {settings.embeddings.device}"
        )
        model = SentenceTransformer(
            settings.embeddings.model_name,
            device=settings.embeddings.device,
        )
        logger.info(f"Model loaded successfully. Embedding dim: {settings.embeddings.dim}")
        return model
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise EmbeddingError(f"Model loading failed: {e}") from e


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def embed_texts(texts: list[str] | Iterable[str]) -> list[list[float]]:
    """Compute embeddings for a batch of texts with retry logic.
    
    Args:
        texts: List or iterable of text strings to embed
        
    Returns:
        List of embedding vectors (each is a list of floats)
        
    Raises:
        EmbeddingError: If embedding computation fails after retries
        ValueError: If texts is empty or contains invalid data
    """
    if not texts:
        logger.warning("Empty text list provided to embed_texts")
        return []

    text_list = list(texts)
    if not all(isinstance(t, str) for t in text_list):
        raise ValueError("All items in texts must be strings")

    # Filter out empty strings
    valid_texts = [t for t in text_list if t.strip()]
    if not valid_texts:
        logger.warning("All texts are empty after filtering")
        return [[0.0] * settings.embeddings.dim] * len(text_list)

    try:
        model = _load_model()
        
        # If model not available, return placeholder embeddings
        if model is None:
            logger.warning(f"Model unavailable - returning placeholder embeddings for {len(valid_texts)} texts")
            return [[0.0] * settings.embeddings.dim for _ in valid_texts]
            
        logger.debug(f"Encoding {len(valid_texts)} texts")
        
        embeddings = model.encode(
            valid_texts,
            batch_size=settings.embeddings.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=settings.embeddings.normalize_embeddings,
        )
        
        # Convert to list of lists for JSON serialization
        result = embeddings.tolist()
        logger.debug(f"Successfully encoded {len(result)} embeddings")
        return result
        
    except Exception as e:
        logger.error(f"Embedding computation failed: {e}")
        raise EmbeddingError(f"Failed to compute embeddings: {e}") from e


def embed_single(text: str) -> list[float]:
    """Convenience function to embed a single text.
    
    Args:
        text: Single text string to embed
        
    Returns:
        Single embedding vector as list of floats
    """
    if not text or not text.strip():
        return [0.0] * settings.embeddings.dim
    
    embeddings = embed_texts([text])
    return embeddings[0]


def get_model_info() -> dict[str, str | int]:
    """Get information about the loaded model.
    
    Returns:
        Dictionary with model metadata
    """
    model = _load_model()
    return {
        "model_name": settings.embeddings.model_name,
        "dimension": settings.embeddings.dim,
        "device": str(model.device),
        "max_seq_length": model.max_seq_length,
    }
