"""Ingestion pipeline stubs for jobs and candidates.

Implementations should:
- Insert/update records in jobs and candidates.
- Be reusable from both batch jobs and realtime upload handlers.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


async def upsert_candidate_from_structured(
    session: AsyncSession,
    *,
    full_name: str,
    resume_raw: str,
    location: str | None = None,
    years_experience: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> models.Candidate:
    """Create or update a candidate from structured data.

    Real matching/upsert rules are to be defined later.
    """

    candidate = models.Candidate(
        full_name=full_name,
        resume_raw=resume_raw,
        location=location,
        years_experience=years_experience,
        metadata=dict(metadata) if metadata is not None else None,
    )
    session.add(candidate)
    await session.flush()
    return candidate
