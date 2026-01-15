"""FastAPI app with health, upload endpoints, and proper error handling.

Implements realtime resume upload wired to the full processing pipeline.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .logging_config import setup_logging
from .parsers import ParseError
from .pipelines.processing import CandidateProcessingError, process_single_resume
from .pipelines.job_processing import JobProcessingError, process_job
from .pipelines.matching import MatchingError, match_job_to_candidates

logger = logging.getLogger(__name__)


# Pydantic response models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


class SkillDTO(BaseModel):
    """Skill data transfer object."""
    canonical_skill: str
    confidence: float
    evidence: str


class UploadResumeResponse(BaseModel):
    """Resume upload response."""
    status: str
    candidate_id: int
    full_name: str
    skills_extracted: int
    skills: list[SkillDTO] = Field(default_factory=list)
    embedding_dim: int
    message: str


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: str | None = None


class CreateJobRequest(BaseModel):
    """Create job request."""
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=10)
    location: str | None = None
    remote_policy: str | None = None
    min_years_experience: int | None = Field(default=None, ge=0, le=50)
    metadata: dict | None = None


class CreateJobResponse(BaseModel):
    """Create job response."""
    status: str
    job_id: int
    title: str
    skills_extracted: int
    skills: list[SkillDTO] = Field(default_factory=list)
    embedding_dim: int
    message: str


class MatchRequest(BaseModel):
    """Match job to candidates request."""
    top_k: int | None = Field(default=None, ge=10, le=5000)
    top_n: int | None = Field(default=None, ge=1, le=500)
    rules_version: str | None = None


class RuleTraceDTO(BaseModel):
    """Rule trace data transfer object."""
    rule_id: str
    name: str
    status: str
    reason: str
    evidence: list[dict]
    score_delta: float = 0.0


class MatchResultDTO(BaseModel):
    """Single match result."""
    candidate_id: int
    rank: int
    retrieval_similarity: float
    final_score: float
    rule_trace: list[RuleTraceDTO]


class MatchResponse(BaseModel):
    """Match response."""
    status: str
    job_id: int
    top_n: int
    matches: list[MatchResultDTO]
    embedding_model_version: str
    taxonomy_version: str
    rules_version: str
    computed_at: str
    message: str


class ShortlistResponse(BaseModel):
    """Shortlist retrieval response."""
    job_id: int
    top_n: int
    matches: list[MatchResultDTO]
    embedding_model_version: str
    taxonomy_version: str
    rules_version: str
    computed_at: str
    is_stale: bool
    detail: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown logic."""
    # Startup
    setup_logging()
    logger.info("Application starting up")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title="Job → Candidates Matching MVP",
    version="0.1.0",
    description="Realtime resume upload with ML-powered matching",
    lifespan=lifespan,
)


# CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ParseError)
async def parse_error_handler(request, exc: ParseError):
    """Handle document parsing errors."""
    logger.error(f"Parse error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="parse_error",
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(CandidateProcessingError)
async def processing_error_handler(request, exc: CandidateProcessingError):
    """Handle candidate processing errors."""
    logger.error(f"Processing error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="processing_error",
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(JobProcessingError)
async def job_processing_error_handler(request, exc: JobProcessingError):
    """Handle job processing errors."""
    logger.error(f"Job processing error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="job_processing_error",
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(MatchingError)
async def matching_error_handler(request, exc: MatchingError):
    """Handle matching pipeline errors."""
    logger.error(f"Matching error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="matching_error",
            detail=str(exc),
        ).model_dump(),
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    from .config import settings
    
    return HealthResponse(
        status="ok",
        version=settings.version,
    )


@app.post(
    "/upload-resume",
    response_model=UploadResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF, CSV, or Excel)"),
    full_name: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> UploadResumeResponse:
    """Upload and process a single resume.
    
    This endpoint:
    1. Parses the file (PDF with OCR fallback, or CSV/Excel)
    2. Normalizes text
    3. Extracts skills with evidence
    4. Computes embeddings
    5. Persists to database
    
    Args:
        file: Uploaded resume file
        full_name: Optional candidate name (extracted if not provided)
        session: Database session (injected)
        
    Returns:
        UploadResumeResponse with candidate details and extracted features
        
    Raises:
        HTTPException: For validation or processing errors
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    # Validate file type
    allowed_extensions = {'.pdf', '.csv', '.xls', '.xlsx'}
    file_ext = '.' + file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )
    
    logger.info(f"Received resume upload: {file.filename}")
    
    try:
        # Read file content
        content = await file.read()
        
        # Create file-like object for processing
        from io import BytesIO
        file_obj = BytesIO(content)
        
        # Process through pipeline
        processed = await process_single_resume(
            session=session,
            file_obj=file_obj,
            filename=file.filename,
            full_name=full_name,
            metadata={"upload_source": "api", "file_size": len(content)},
        )
        
        # Build response
        skills_dtos = [
            SkillDTO(
                canonical_skill=s["canonical_skill"],
                confidence=s["confidence"],
                evidence=s["evidence"],
            )
            for s in processed.skills[:10]  # Return top 10 skills in response
        ]
        
        return UploadResumeResponse(
            status="success",
            candidate_id=processed.candidate_id,
            full_name=processed.full_name,
            skills_extracted=len(processed.skills),
            skills=skills_dtos,
            embedding_dim=len(processed.embedding),
            message=f"Successfully processed resume for {processed.full_name}",
        )
        
    except (ParseError, CandidateProcessingError):
        # Re-raise to be caught by exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing resume: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
    finally:
        await file.close()


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "app": "Resume Matching MVP",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "upload_resume": "/upload-resume",
            "create_job": "/jobs",
            "match_job": "/jobs/{job_id}/match",
            "get_shortlist": "/jobs/{job_id}/shortlist",
            "docs": "/docs",
        },
    }


@app.post(
    "/jobs",
    response_model=CreateJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    request: CreateJobRequest,
    session: AsyncSession = Depends(get_session),
) -> CreateJobResponse:
    """Create and process a job posting.
    
    This endpoint:
    1. Normalizes job description text
    2. Extracts skills with evidence
    3. Computes embeddings
    4. Persists to database
    
    Args:
        request: Job creation request
        session: Database session (injected)
        
    Returns:
        CreateJobResponse with job details and extracted features
    """
    logger.info(f"Creating job: {request.title}")
    
    try:
        processed = await process_job(
            session=session,
            title=request.title,
            description=request.description,
            location=request.location,
            remote_policy=request.remote_policy,
            min_years_experience=request.min_years_experience,
            metadata=request.metadata,
        )
        
        skills_dtos = [
            SkillDTO(
                canonical_skill=s["canonical_skill"],
                confidence=s["confidence"],
                evidence=s["evidence"],
            )
            for s in processed.skills[:10]
        ]
        
        return CreateJobResponse(
            status="success",
            job_id=processed.job_id,
            title=processed.title,
            skills_extracted=len(processed.skills),
            skills=skills_dtos,
            embedding_dim=len(processed.embedding),
            message=f"Successfully created job: {processed.title}",
        )
        
    except JobProcessingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.post(
    "/jobs/{job_id}/match",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
)
async def match_job(
    job_id: int,
    request: MatchRequest = MatchRequest(),
    session: AsyncSession = Depends(get_session),
) -> MatchResponse:
    """Match a job to candidates using TopK retrieval and rule-based scoring.
    
    This endpoint executes the complete matching pipeline:
    1. Retrieves job embedding
    2. Queries pgvector for TopK similar candidates
    3. Applies hard rules (filters)
    4. Applies soft rules (scoring)
    5. Computes final_score and rank
    6. Persists TopN shortlist with full audit trail
    
    Args:
        job_id: Job ID to match
        request: Match configuration (optional)
        session: Database session (injected)
        
    Returns:
        MatchResponse with shortlist and audit trails
    """
    logger.info(f"Matching job {job_id}")
    
    try:
        shortlist = await match_job_to_candidates(
            session=session,
            job_id=job_id,
            top_k=request.top_k,
            top_n=request.top_n,
            rules_version=request.rules_version,
        )
        
        match_dtos = [
            MatchResultDTO(
                candidate_id=m.candidate_id,
                rank=m.rank,
                retrieval_similarity=m.retrieval_similarity,
                final_score=m.final_score,
                rule_trace=[
                    RuleTraceDTO(
                        rule_id=t["rule_id"],
                        name=t["name"],
                        status=t["status"],
                        reason=t["reason"],
                        evidence=t["evidence"],
                        score_delta=t.get("score_delta", 0.0),
                    )
                    for t in m.rule_trace
                ],
            )
            for m in shortlist.matches
        ]
        
        return MatchResponse(
            status="success",
            job_id=shortlist.job_id,
            top_n=shortlist.top_n,
            matches=match_dtos,
            embedding_model_version=shortlist.embedding_model_version,
            taxonomy_version=shortlist.taxonomy_version,
            rules_version=shortlist.rules_version,
            computed_at=shortlist.computed_at.isoformat(),
            message=f"Successfully matched {shortlist.top_n} candidates for job {job_id}",
        )
        
    except MatchingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error matching job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.get(
    "/jobs/{job_id}/shortlist",
    response_model=ShortlistResponse,
    status_code=status.HTTP_200_OK,
)
async def get_shortlist(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> ShortlistResponse:
    """Retrieve stored shortlist for a job.
    
    Returns the most recent (non-stale) shortlist for the specified job.
    
    Args:
        job_id: Job ID
        session: Database session (injected)
        
    Returns:
        ShortlistResponse with stored shortlist
    """
    from sqlalchemy import select
    from . import models
    
    logger.info(f"Retrieving shortlist for job {job_id}")
    
    try:
        query = (
            select(models.JobShortlist)
            .where(
                models.JobShortlist.job_id == job_id,
                models.JobShortlist.is_stale == False,
            )
            .order_by(models.JobShortlist.rank)
        )
        
        result = await session.execute(query)
        shortlist_records = result.scalars().all()
        
        if not shortlist_records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No shortlist found for job {job_id}. Run matching first.",
            )
        
        match_dtos = [
            MatchResultDTO(
                candidate_id=record.candidate_id,
                rank=record.rank,
                retrieval_similarity=record.retrieval_similarity,
                final_score=record.final_score,
                rule_trace=[
                    RuleTraceDTO(
                        rule_id=t["rule_id"],
                        name=t["name"],
                        status=t["status"],
                        reason=t["reason"],
                        evidence=t["evidence"],
                        score_delta=t.get("score_delta", 0.0),
                    )
                    for t in record.rule_trace.get("traces", [])
                ],
            )
            for record in shortlist_records
        ]
        
        first_record = shortlist_records[0]
        
        return ShortlistResponse(
            job_id=job_id,
            top_n=len(match_dtos),
            matches=match_dtos,
            embedding_model_version=first_record.embedding_model_version,
            taxonomy_version=first_record.taxonomy_version,
            rules_version=first_record.rules_version,
            computed_at=first_record.computed_at.isoformat(),
            is_stale=first_record.is_stale,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving shortlist: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
