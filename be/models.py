"""Core SQLAlchemy models (2.x style) for the MVP schema.

Production-ready models with proper indexes, constraints.
Using PostgreSQL with pgvector for embeddings.
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Job(Base):
    """Job postings table."""
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_normalized: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255), index=True)
    remote_policy: Mapped[str | None] = mapped_column(String(100))
    min_years_experience: Mapped[int | None] = mapped_column(Integer)
    metadata_: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    embedding: Mapped[JobEmbedding | None] = relationship("JobEmbedding", back_populates="job", uselist=False)
    shortlists: Mapped[list[JobShortlist]] = relationship("JobShortlist", back_populates="job")

    __table_args__ = (
        Index("ix_jobs_created_at", "created_at"),
    )


class Candidate(Base):
    """Candidates table."""
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resume_raw: Mapped[str] = mapped_column(Text, nullable=False)
    resume_normalized: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255), index=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, index=True)
    metadata_: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    embedding: Mapped[CandidateEmbedding | None] = relationship(
        "CandidateEmbedding",
        back_populates="candidate",
        uselist=False,
    )
    skills: Mapped[list[ExtractedSkillsCandidate]] = relationship(
        "ExtractedSkillsCandidate",
        back_populates="candidate",
    )
    shortlists: Mapped[list[JobShortlist]] = relationship("JobShortlist", back_populates="candidate")

    __table_args__ = (
        Index("ix_candidates_created_at", "created_at"),
    )


class ExtractedSkillsJob(Base):
    """Extracted skills from job descriptions."""
    __tablename__ = "extracted_skills_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_skill: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text)
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationship
    job: Mapped[Job] = relationship("Job")

    __table_args__ = (
        Index("ix_extracted_skills_jobs_skill", "canonical_skill"),
        Index("ix_extracted_skills_jobs_job_skill", "job_id", "canonical_skill"),
    )


class ExtractedSkillsCandidate(Base):
    """Extracted skills from candidate resumes."""
    __tablename__ = "extracted_skills_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_skill: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text)
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationship
    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="skills")

    __table_args__ = (
        Index("ix_extracted_skills_candidates_skill", "canonical_skill"),
        Index("ix_extracted_skills_candidates_cand_skill", "candidate_id", "canonical_skill"),
    )


class JobEmbedding(Base):
    """Job embeddings using pgvector."""
    __tablename__ = "job_embeddings"

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_model_version: Mapped[str] = mapped_column(String(255), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationship
    job: Mapped[Job] = relationship("Job", back_populates="embedding")


class CandidateEmbedding(Base):
    """Candidate embeddings using pgvector."""
    __tablename__ = "candidate_embeddings"

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_model_version: Mapped[str] = mapped_column(String(255), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationship
    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="embedding")


class RulesConfig(Base):
    """Config-driven business rules (versioned)."""
    __tablename__ = "rules_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rules_version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    scope: Mapped[str] = mapped_column(String(100), nullable=False)  # global, per-job-type, etc.
    rules_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SkillTaxonomyModel(Base):
    """Skill taxonomy with synonyms."""
    __tablename__ = "skill_taxonomy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_skill: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    synonyms: Mapped[list[str] | None] = mapped_column(JSON)  # Array of synonym strings
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)


class JobShortlist(Base):
    """Computed shortlists with full audit trail."""
    __tablename__ = "job_shortlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    rule_trace: Mapped[dict] = mapped_column(JSON, nullable=False)  # Full audit trace
    embedding_model_version: Mapped[str] = mapped_column(String(255), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(50), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="shortlists")
    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="shortlists")

    __table_args__ = (
        Index("ix_job_shortlists_job_rank", "job_id", "rank"),
        Index("ix_job_shortlists_job_score", "job_id", "final_score"),
        # Ensure unique (job, candidate) per shortlist computation
        Index("ix_job_shortlists_job_candidate", "job_id", "candidate_id", unique=True),
    )
