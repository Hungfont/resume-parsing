"""Complete pipeline orchestration for candidate processing.

Combines parsing, normalization, skill extraction, and embedding computation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from ai.embeddings import embed_single
from ai.skills import SkillExtractor
from be import models
from be.config import settings
from be.parsers import FileType, ParsedDocument, parse_file
from be.pipelines.normalization import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class ProcessedCandidate:
    """Result of complete candidate processing."""
    candidate_id: int
    full_name: str
    raw_text: str
    normalized_text: str
    skills: list[dict]
    embedding: list[float]
    metadata: dict


class CandidateProcessingError(Exception):
    """Raised when candidate processing fails."""
    pass


async def process_single_resume(
    session: AsyncSession,
    file_obj: BinaryIO,
    filename: str,
    *,
    full_name: str | None = None,
    metadata: dict | None = None,
) -> ProcessedCandidate:
    """Process a single resume file through the complete pipeline.
    
    Steps:
    1. Parse file (PDF/CSV/Excel)
    2. Normalize text
    3. Extract skills with evidence
    4. Compute embeddings
    5. Persist to database
    
    Args:
        session: Database session
        file_obj: Binary file object
        filename: Original filename
        full_name: Candidate name (if known)
        metadata: Additional metadata
        
    Returns:
        ProcessedCandidate with all computed features
        
    Raises:
        CandidateProcessingError: If processing fails
    """
    try:
        logger.info(f"Processing resume: {filename}")
        
        # Step 1: Parse file
        parsed = parse_file(file_obj, filename)
        
        if isinstance(parsed, ParsedDocument):
            # Single PDF resume
            raw_text = parsed.text
            file_metadata = parsed.metadata
            file_metadata.update(metadata or {})
        else:
            # CSV/Excel - take first record for now (batch handling should be separate)
            raise CandidateProcessingError(
                "Batch CSV/Excel upload should use batch processing endpoint"
            )
        
        # Extract name from text if not provided
        if not full_name:
            full_name = extract_name_heuristic(raw_text) or "Unknown"
        
        logger.debug(f"Extracted raw text: {len(raw_text)} characters")
        
        # Step 2: Normalize text
        normalized_text = normalize_text(
            raw_text,
            lowercase=True,
            clean_urls=True,
            clean_emails=False,  # Keep emails for contact info
            preserve_vietnamese_diacritics=True,
        )
        
        logger.debug(f"Normalized text: {len(normalized_text)} characters")
        
        # Step 3: Extract skills
        skill_extractor = SkillExtractor()
        extracted_skills = skill_extractor.extract(
            normalized_text,
            min_confidence=settings.skills.min_confidence,
        )
        
        logger.info(f"Extracted {len(extracted_skills)} skills")
        
        # Step 4: Compute embedding
        embedding = embed_single(normalized_text)
        
        logger.debug(f"Computed embedding: {len(embedding)} dimensions")
        
        # Step 5: Persist to database
        candidate = models.Candidate(
            full_name=full_name,
            resume_raw=raw_text,
            resume_normalized=normalized_text,
            metadata=file_metadata,
        )
        session.add(candidate)
        await session.flush()
        
        # Store embedding
        candidate_embedding = models.CandidateEmbedding(
            candidate_id=candidate.id,
            embedding=embedding,
            embedding_model=settings.embeddings.model_name,
            embedding_model_version=settings.embeddings.model_name,  # Could track version separately
        )
        session.add(candidate_embedding)
        
        # Store extracted skills
        skills_data = []
        for skill in extracted_skills:
            skill_record = models.ExtractedSkillsCandidate(
                candidate_id=candidate.id,
                canonical_skill=skill.canonical_skill,
                raw_text=skill.raw_text,
                confidence=skill.confidence,
                evidence_text=skill.evidence_text,
                span_start=skill.span_start,
                span_end=skill.span_end,
                taxonomy_version=settings.matching.taxonomy_version,
            )
            session.add(skill_record)
            skills_data.append({
                "canonical_skill": skill.canonical_skill,
                "confidence": skill.confidence,
                "evidence": skill.evidence_text[:100],
            })
        
        await session.commit()
        
        logger.info(f"Successfully processed candidate {candidate.id}: {full_name}")
        
        return ProcessedCandidate(
            candidate_id=candidate.id,
            full_name=full_name,
            raw_text=raw_text,
            normalized_text=normalized_text,
            skills=skills_data,
            embedding=embedding,
            metadata=file_metadata,
        )
        
    except Exception as e:
        logger.error(f"Candidate processing failed: {e}", exc_info=True)
        await session.rollback()
        raise CandidateProcessingError(f"Processing failed: {e}") from e


def extract_name_heuristic(text: str) -> str | None:
    """Extract candidate name using simple heuristics.
    
    This is a basic implementation; production should use NER.
    """
    lines = text.strip().split('\n')
    if not lines:
        return None
    
    # Often the first non-empty line is the name
    for line in lines[:5]:
        line = line.strip()
        if len(line) > 3 and len(line) < 50:
            # Check if it looks like a name (no numbers, not too long)
            if not any(char.isdigit() for char in line):
                return line
    
    return None


async def process_batch_csv_excel(
    session: AsyncSession,
    records: list[dict],
    *,
    column_mapping: dict[str, str] | None = None,
) -> list[ProcessedCandidate]:
    """Process multiple candidates from CSV/Excel.
    
    Args:
        session: Database session
        records: List of row dictionaries
        column_mapping: Mapping from file columns to candidate fields
        
    Returns:
        List of ProcessedCandidate objects
    """
    # MVP: This should be implemented for batch CSV/Excel upload
    # For now, raise to indicate it needs separate implementation
    raise NotImplementedError(
        "Batch CSV/Excel processing should be implemented based on specific schema"
    )
