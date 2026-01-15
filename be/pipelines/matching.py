"""Matching pipeline: Job → Candidates with TopK retrieval and rule-based scoring.

Implements the core MVP matching workflow from instructions section 5.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from be import models
from be.config import settings
from be.rules import RuleConfig, RuleEngine, RuleTrace

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Single candidate match result."""
    candidate_id: int
    rank: int
    retrieval_similarity: float
    final_score: float
    rule_trace: list[dict]


@dataclass
class JobShortlist:
    """Complete shortlist for a job."""
    job_id: int
    top_n: int
    matches: list[MatchResult]
    embedding_model_version: str
    taxonomy_version: str
    rules_version: str
    computed_at: datetime


class MatchingError(Exception):
    """Raised when matching pipeline fails."""
    pass


async def retrieve_topk_candidates(
    session: AsyncSession,
    job_embedding: list[float],
    top_k: int,
    min_similarity: float = 0.0,
) -> list[tuple[int, float]]:
    """Retrieve TopK similar candidates using pgvector cosine similarity.
    
    Args:
        session: Database session
        job_embedding: Job embedding vector
        top_k: Number of candidates to retrieve
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of (candidate_id, similarity) tuples sorted by similarity DESC
    """
    try:
        # pgvector cosine similarity: 1 - (embedding <=> job_embedding)
        # <=> is cosine distance operator
        query = text("""
            SELECT 
                candidate_id,
                1 - (embedding <=> :job_embedding) AS similarity
            FROM candidate_embeddings
            WHERE 1 - (embedding <=> :job_embedding) >= :min_similarity
            ORDER BY embedding <=> :job_embedding
            LIMIT :top_k
        """)
        
        result = await session.execute(
            query,
            {
                "job_embedding": str(job_embedding),
                "min_similarity": min_similarity,
                "top_k": top_k,
            }
        )
        
        rows = result.fetchall()
        candidates = [(row[0], float(row[1])) for row in rows]
        
        logger.info(f"Retrieved {len(candidates)} candidates (TopK={top_k})")
        return candidates
        
    except Exception as e:
        logger.error(f"TopK retrieval failed: {e}")
        raise MatchingError(f"Failed to retrieve candidates: {e}") from e


async def load_candidate_features(
    session: AsyncSession,
    candidate_ids: list[int],
) -> dict[int, dict]:
    """Load candidate features (skills, metadata) for rule evaluation.
    
    Args:
        session: Database session
        candidate_ids: List of candidate IDs to load
        
    Returns:
        Dictionary mapping candidate_id to feature dict
    """
    if not candidate_ids:
        return {}
    
    # Load candidates
    candidates_query = select(models.Candidate).where(
        models.Candidate.id.in_(candidate_ids)
    )
    candidates_result = await session.execute(candidates_query)
    candidates = {c.id: c for c in candidates_result.scalars().all()}
    
    # Load skills
    skills_query = select(models.ExtractedSkillsCandidate).where(
        models.ExtractedSkillsCandidate.candidate_id.in_(candidate_ids)
    )
    skills_result = await session.execute(skills_query)
    skills_by_candidate = {}
    for skill in skills_result.scalars().all():
        if skill.candidate_id not in skills_by_candidate:
            skills_by_candidate[skill.candidate_id] = []
        skills_by_candidate[skill.candidate_id].append({
            "canonical_skill": skill.canonical_skill,
            "confidence": skill.confidence,
            "evidence": skill.evidence_text,
        })
    
    # Build feature dicts
    features = {}
    for candidate_id, candidate in candidates.items():
        features[candidate_id] = {
            "candidate_id": candidate_id,
            "full_name": candidate.full_name,
            "location": candidate.location,
            "years_experience": candidate.years_experience or 0,
            "skills": skills_by_candidate.get(candidate_id, []),
            "metadata": candidate.metadata or {},
        }
    
    return features


async def load_job_features(
    session: AsyncSession,
    job_id: int,
) -> dict:
    """Load job features for rule evaluation.
    
    Args:
        session: Database session
        job_id: Job ID to load
        
    Returns:
        Job feature dictionary
    """
    # Load job
    job_query = select(models.Job).where(models.Job.id == job_id)
    job_result = await session.execute(job_query)
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise MatchingError(f"Job {job_id} not found")
    
    # Load skills
    skills_query = select(models.ExtractedSkillsJob).where(
        models.ExtractedSkillsJob.job_id == job_id
    )
    skills_result = await session.execute(skills_query)
    skills = [
        {
            "canonical_skill": s.canonical_skill,
            "confidence": s.confidence,
            "evidence": s.evidence_text,
        }
        for s in skills_result.scalars().all()
    ]
    
    return {
        "job_id": job_id,
        "title": job.title,
        "location": job.location,
        "remote_policy": job.remote_policy,
        "min_years_experience": job.min_years_experience or 0,
        "skills": skills,
        "metadata": job.metadata or {},
    }


def load_rules_config(version: str = "v1.0.0") -> list[RuleConfig]:
    """Load rule configuration.
    
    For MVP, returns default hardcoded rules. In production, should load from DB.
    
    Args:
        version: Rules version to load
        
    Returns:
        List of RuleConfig objects
    """
    # MVP: Default rules matching instruction examples
    from be.rules import RuleType
    
    default_rules = [
        # Hard rules (filters)
        RuleConfig(
            id="must_have_skills",
            name="Must-have skills",
            type=RuleType.SKILLS_REQUIRED,
            params={
                "all_of": ["Python", "PostgreSQL"],
                "min_confidence": 0.7,
            },
            weight=1.0,
        ),
        RuleConfig(
            id="min_years_experience",
            name="Minimum years of experience",
            type=RuleType.MIN_YEARS,
            params={"min": 2},
            weight=1.0,
        ),
        # Soft rules (scoring)
        RuleConfig(
            id="nice_to_have_skills",
            name="Nice-to-have skills",
            type=RuleType.SKILLS_BONUS,
            params={
                "any_of": ["FastAPI", "Docker", "Kubernetes"],
                "per_skill_bonus": 5.0,
            },
            weight=1.0,
        ),
        RuleConfig(
            id="experience_bonus",
            name="Experience bonus",
            type=RuleType.YEARS_BONUS,
            params={
                "bonus_per_year": 1.0,
                "max_bonus": 10.0,
            },
            weight=1.0,
        ),
    ]
    
    logger.info(f"Loaded {len(default_rules)} rules (version: {version})")
    return default_rules


async def match_job_to_candidates(
    session: AsyncSession,
    job_id: int,
    *,
    top_k: int | None = None,
    top_n: int | None = None,
    rules_version: str | None = None,
) -> JobShortlist:
    """Execute complete matching pipeline for a single job.
    
    Workflow (from instructions section 5):
    1. Retrieve job embedding
    2. Query pgvector for TopK similar candidates
    3. Apply hard rules (filters)
    4. Apply soft rules (scoring)
    5. Compute final_score
    6. Sort and select TopN
    7. Persist to job_shortlists with full audit
    
    Args:
        session: Database session
        job_id: Job ID to match
        top_k: Initial retrieval size (default from config)
        top_n: Final shortlist size (default from config)
        rules_version: Rules version to use (default from config)
        
    Returns:
        JobShortlist with all match results
        
    Raises:
        MatchingError: If matching fails
    """
    top_k = top_k or settings.matching.top_k
    top_n = top_n or settings.matching.top_n
    rules_version = rules_version or settings.matching.rules_version
    
    try:
        logger.info(f"Starting matching for job {job_id} (TopK={top_k}, TopN={top_n})")
        
        # Step 1: Retrieve job embedding
        job_embedding_query = select(models.JobEmbedding).where(
            models.JobEmbedding.job_id == job_id
        )
        job_embedding_result = await session.execute(job_embedding_query)
        job_embedding_record = job_embedding_result.scalar_one_or_none()
        
        if not job_embedding_record:
            raise MatchingError(f"No embedding found for job {job_id}")
        
        job_embedding = job_embedding_record.embedding
        
        # Step 2: Retrieve TopK candidates via pgvector
        topk_candidates = await retrieve_topk_candidates(
            session,
            job_embedding,
            top_k,
            min_similarity=settings.matching.min_similarity,
        )
        
        if not topk_candidates:
            logger.warning(f"No candidates retrieved for job {job_id}")
            return JobShortlist(
                job_id=job_id,
                top_n=0,
                matches=[],
                embedding_model_version=settings.embeddings.model_name,
                taxonomy_version=settings.matching.taxonomy_version,
                rules_version=rules_version,
                computed_at=datetime.utcnow(),
            )
        
        candidate_ids = [c_id for c_id, _ in topk_candidates]
        similarities = {c_id: sim for c_id, sim in topk_candidates}
        
        # Load features for rule evaluation
        logger.info(f"Loading features for {len(candidate_ids)} candidates")
        candidate_features = await load_candidate_features(session, candidate_ids)
        job_features = await load_job_features(session, job_id)
        
        # Load rules
        rules = load_rules_config(rules_version)
        rule_engine = RuleEngine(rules)
        
        # Step 3 & 4: Evaluate rules and compute scores
        logger.info("Evaluating rules and computing scores")
        scored_candidates = []
        
        for candidate_id in candidate_ids:
            base_similarity = similarities[candidate_id]
            candidate_data = candidate_features.get(candidate_id)
            
            if not candidate_data:
                logger.warning(f"Missing features for candidate {candidate_id}, skipping")
                continue
            
            # Evaluate hard rules (filters)
            passed_hard, hard_traces = rule_engine.evaluate_hard_rules(
                candidate_data,
                job_features,
            )
            
            if not passed_hard:
                # Candidate filtered out
                logger.debug(f"Candidate {candidate_id} filtered by hard rules")
                continue
            
            # Evaluate soft rules (scoring)
            final_score, soft_traces = rule_engine.evaluate_soft_rules(
                candidate_data,
                job_features,
                base_score=base_similarity * 100,  # Scale to 0-100 range
            )
            
            # Combine traces
            all_traces = hard_traces + soft_traces
            
            scored_candidates.append({
                "candidate_id": candidate_id,
                "retrieval_similarity": base_similarity,
                "final_score": final_score,
                "rule_trace": [
                    {
                        "rule_id": t.rule_id,
                        "name": t.name,
                        "status": t.status.value,
                        "reason": t.reason,
                        "evidence": [
                            {
                                "source": e.source,
                                "text": e.text,
                                "span": e.span,
                            }
                            for e in t.evidence
                        ],
                        "score_delta": t.score_delta,
                    }
                    for t in all_traces
                ],
            })
        
        # Step 5: Sort by final_score and select TopN
        scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)
        topn_candidates = scored_candidates[:top_n]
        
        logger.info(
            f"Matched {len(scored_candidates)} candidates, "
            f"returning top {len(topn_candidates)}"
        )
        
        # Step 6: Build match results
        matches = [
            MatchResult(
                candidate_id=c["candidate_id"],
                rank=idx + 1,
                retrieval_similarity=c["retrieval_similarity"],
                final_score=c["final_score"],
                rule_trace=c["rule_trace"],
            )
            for idx, c in enumerate(topn_candidates)
        ]
        
        shortlist = JobShortlist(
            job_id=job_id,
            top_n=len(matches),
            matches=matches,
            embedding_model_version=settings.embeddings.model_name,
            taxonomy_version=settings.matching.taxonomy_version,
            rules_version=rules_version,
            computed_at=datetime.utcnow(),
        )
        
        # Step 7: Persist to database
        await persist_shortlist(session, shortlist)
        
        logger.info(f"Successfully completed matching for job {job_id}")
        return shortlist
        
    except MatchingError:
        raise
    except Exception as e:
        logger.error(f"Matching failed for job {job_id}: {e}", exc_info=True)
        raise MatchingError(f"Matching pipeline failed: {e}") from e


async def persist_shortlist(
    session: AsyncSession,
    shortlist: JobShortlist,
) -> None:
    """Persist shortlist to job_shortlists table.
    
    Marks existing shortlist entries as stale and creates new ones.
    
    Args:
        session: Database session
        shortlist: JobShortlist to persist
    """
    try:
        # Mark existing shortlist entries as stale
        update_query = text("""
            UPDATE job_shortlists 
            SET is_stale = true 
            WHERE job_id = :job_id AND is_stale = false
        """)
        await session.execute(update_query, {"job_id": shortlist.job_id})
        
        # Insert new shortlist entries
        for match in shortlist.matches:
            shortlist_record = models.JobShortlist(
                job_id=shortlist.job_id,
                candidate_id=match.candidate_id,
                rank=match.rank,
                retrieval_similarity=match.retrieval_similarity,
                final_score=match.final_score,
                rule_trace={"traces": match.rule_trace},
                embedding_model_version=shortlist.embedding_model_version,
                taxonomy_version=shortlist.taxonomy_version,
                rules_version=shortlist.rules_version,
                computed_at=shortlist.computed_at,
                is_stale=False,
            )
            session.add(shortlist_record)
        
        await session.commit()
        logger.info(f"Persisted {len(shortlist.matches)} shortlist entries for job {shortlist.job_id}")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to persist shortlist: {e}")
        raise MatchingError(f"Shortlist persistence failed: {e}") from e
