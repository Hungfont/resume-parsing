"""Job processing pipeline for job description ingestion and feature extraction.

Similar to candidate processing but for job postings.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ai.embeddings import embed_single
from ai.skills import SkillExtractor
from be import models
from be.config import settings
from be.pipelines.normalization import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class ProcessedJob:
    """Result of complete job processing."""
    job_id: int
    title: str
    raw_text: str
    normalized_text: str
    skills: list[dict]
    embedding: list[float]
    metadata: dict


class JobProcessingError(Exception):
    """Raised when job processing fails."""
    pass


async def process_job(
    session: AsyncSession,
    *,
    title: str,
    description: str,
    location: str | None = None,
    remote_policy: str | None = None,
    min_years_experience: int | None = None,
    metadata: dict | None = None,
) -> ProcessedJob:
    """Process a single job through the complete pipeline.
    
    Steps:
    1. Normalize job description text
    2. Extract skills with evidence
    3. Compute embeddings
    4. Persist to database
    
    Args:
        session: Database session
        title: Job title
        description: Job description text
        location: Job location
        remote_policy: Remote work policy
        min_years_experience: Minimum years of experience required
        metadata: Additional metadata
        
    Returns:
        ProcessedJob with all computed features
        
    Raises:
        JobProcessingError: If processing fails
    """
    try:
        logger.info(f"Processing job: {title}")
        
        raw_text = description
        
        # Step 1: Normalize text
        normalized_text = normalize_text(
            raw_text,
            lowercase=True,
            clean_urls=True,
            clean_emails=False,
            preserve_vietnamese_diacritics=True,
        )
        
        logger.debug(f"Normalized text: {len(normalized_text)} characters")
        
        # Step 2: Extract skills
        skill_extractor = SkillExtractor()
        extracted_skills = skill_extractor.extract(
            normalized_text,
            min_confidence=settings.skills.min_confidence,
        )
        
        logger.info(f"Extracted {len(extracted_skills)} skills from job")
        
        # Step 3: Compute embedding
        embedding = embed_single(normalized_text)
        
        logger.debug(f"Computed embedding: {len(embedding)} dimensions")
        
        # Step 4: Persist to database
        job = models.Job(
            title=title,
            description_raw=raw_text,
            description_normalized=normalized_text,
            location=location,
            remote_policy=remote_policy,
            min_years_experience=min_years_experience,
            metadata=metadata or {},
        )
        session.add(job)
        await session.flush()
        
        # Store embedding
        job_embedding = models.JobEmbedding(
            job_id=job.id,
            embedding=embedding,
            embedding_model=settings.embeddings.model_name,
            embedding_model_version=settings.embeddings.model_name,
        )
        session.add(job_embedding)
        
        # Store extracted skills
        skills_data = []
        for skill in extracted_skills:
            skill_record = models.ExtractedSkillsJob(
                job_id=job.id,
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
                "evidence": skill.evidence_text[:100] if skill.evidence_text else "",
            })
        
        await session.commit()
        
        logger.info(f"Successfully processed job {job.id}: {title}")
        
        return ProcessedJob(
            job_id=job.id,
            title=title,
            raw_text=raw_text,
            normalized_text=normalized_text,
            skills=skills_data,
            embedding=embedding,
            metadata=metadata or {},
        )
        
    except Exception as e:
        logger.error(f"Job processing failed: {e}", exc_info=True)
        await session.rollback()
        raise JobProcessingError(f"Processing failed: {e}") from e
