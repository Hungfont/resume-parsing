"""Text normalization utilities for vi/en mixed content.

Handles lowercasing, whitespace, punctuation, and Vietnamese diacritics.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Callable

logger = logging.getLogger(__name__)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces, remove leading/trailing."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_punctuation(text: str) -> str:
    """Normalize common punctuation variations."""
    # Replace smart quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    
    # Normalize dashes
    text = text.replace('–', '-').replace('—', '-')
    
    # Remove excessive punctuation
    text = re.sub(r'([!?.]){2,}', r'\1', text)
    
    return text


def remove_urls(text: str) -> str:
    """Remove URLs from text."""
    url_pattern = r'https?://\S+|www\.\S+'
    return re.sub(url_pattern, '', text)


def remove_emails(text: str) -> str:
    """Remove email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.sub(email_pattern, '', text)


def normalize_vietnamese_text(text: str, preserve_diacritics: bool = True) -> str:
    """Normalize Vietnamese text carefully.
    
    Args:
        text: Input Vietnamese text
        preserve_diacritics: If True, keep Vietnamese diacritics (recommended)
        
    Returns:
        Normalized text
    """
    # Normalize Unicode to composed form (important for Vietnamese)
    text = unicodedata.normalize('NFC', text)
    
    if not preserve_diacritics:
        # Only remove diacritics if explicitly requested (not recommended)
        # This can change meaning in Vietnamese
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = unicodedata.normalize('NFC', text)
    
    return text


def clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    html_pattern = re.compile(r'<[^>]+>')
    return html_pattern.sub('', text)


def normalize_text(
    text: str,
    *,
    lowercase: bool = True,
    remove_extra_whitespace: bool = True,
    clean_urls: bool = True,
    clean_emails: bool = False,
    clean_html_tags: bool = True,
    preserve_vietnamese_diacritics: bool = True,
) -> str:
    """Comprehensive text normalization for JD/resume text.
    
    Args:
        text: Input text to normalize
        lowercase: Convert to lowercase
        remove_extra_whitespace: Collapse and trim whitespace
        clean_urls: Remove URLs
        clean_emails: Remove email addresses
        clean_html_tags: Remove HTML tags
        preserve_vietnamese_diacritics: Keep Vietnamese diacritics (recommended)
        
    Returns:
        Normalized text
    """
    if not text or not text.strip():
        return ""
    
    # Clean HTML first if present
    if clean_html_tags:
        text = clean_html(text)
    
    # Remove URLs and emails if requested
    if clean_urls:
        text = remove_urls(text)
    if clean_emails:
        text = remove_emails(text)
    
    # Normalize Vietnamese
    text = normalize_vietnamese_text(text, preserve_diacritics=preserve_vietnamese_diacritics)
    
    # Normalize punctuation
    text = normalize_punctuation(text)
    
    # Lowercase if requested
    if lowercase:
        text = text.lower()
    
    # Normalize whitespace
    if remove_extra_whitespace:
        text = normalize_whitespace(text)
    
    return text


def extract_sections(text: str) -> dict[str, str]:
    """Extract common resume sections (basic heuristic).
    
    Returns:
        Dictionary with section names and their content
    """
    sections = {}
    
    # Common section headers (vi/en)
    patterns = {
        'education': r'(?:education|học vấn|bằng cấp)',
        'experience': r'(?:experience|kinh nghiệm|công việc)',
        'skills': r'(?:skills|kỹ năng|technical skills)',
        'summary': r'(?:summary|objective|tóm tắt|mục tiêu)',
    }
    
    text_lower = text.lower()
    
    for section_name, pattern in patterns.items():
        match = re.search(f'({pattern})[:\\s]*(.{{0,500}}?)(?=(?:{"|".join(patterns.values())})|$)', text_lower, re.IGNORECASE | re.DOTALL)
        if match:
            sections[section_name] = match.group(2).strip()
    
    return sections
