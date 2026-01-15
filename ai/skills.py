"""Skill extraction using taxonomy + rapidfuzz with evidence tracking.

Implements extraction with synonyms, fuzzy matching, and span detection.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable

from rapidfuzz import fuzz, process

from be.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedSkill:
    """Represents an extracted skill with evidence."""
    canonical_skill: str
    raw_text: str
    confidence: float
    evidence_text: str = ""
    span_start: int = -1
    span_end: int = -1
    method: str = "fuzzy"  # fuzzy, exact, synonym


@dataclass
class SkillTaxonomy:
    """Skill taxonomy with synonyms."""
    canonical_skill: str
    synonyms: list[str] = field(default_factory=list)
    category: str = ""
    patterns: list[str] = field(default_factory=list)  # Regex patterns


class SkillExtractor:
    """Production-ready skill extractor with taxonomy, synonyms, and fuzzy matching.
    
    Supports:
    - Exact matching
    - Synonym matching
    - Fuzzy matching via rapidfuzz
    - Regex patterns
    - Evidence/span extraction
    """

    def __init__(self, taxonomy: list[SkillTaxonomy] | None = None) -> None:
        """Initialize skill extractor.
        
        Args:
            taxonomy: List of SkillTaxonomy objects. If None, loads default taxonomy.
        """
        self.taxonomy = taxonomy or self._load_default_taxonomy()
        
        # Build lookup structures
        self._canonical_skills: list[str] = []
        self._synonym_map: dict[str, str] = {}  # synonym -> canonical
        self._patterns: dict[str, list[re.Pattern]] = {}  # canonical -> compiled patterns
        
        self._build_indices()
        
        logger.info(f"Loaded {len(self.taxonomy)} skills with {len(self._synonym_map)} synonyms")

    def _load_default_taxonomy(self) -> list[SkillTaxonomy]:
        """Load default skill taxonomy (MVP placeholder).
        
        In production, this should load from DB or config file.
        """
        # Common tech skills (vi/en) as MVP default
        default_skills = [
            SkillTaxonomy("Python", ["python", "python3", "py"], "programming"),
            SkillTaxonomy("JavaScript", ["javascript", "js", "node.js", "nodejs"], "programming"),
            SkillTaxonomy("Java", ["java", "spring", "spring boot"], "programming"),
            SkillTaxonomy("SQL", ["sql", "mysql", "postgresql", "postgres"], "database"),
            SkillTaxonomy("PostgreSQL", ["postgresql", "postgres", "psql"], "database"),
            SkillTaxonomy("Docker", ["docker", "containerization"], "devops"),
            SkillTaxonomy("Kubernetes", ["kubernetes", "k8s"], "devops"),
            SkillTaxonomy("FastAPI", ["fastapi", "fast api"], "framework"),
            SkillTaxonomy("React", ["react", "reactjs", "react.js"], "frontend"),
            SkillTaxonomy("Machine Learning", ["machine learning", "ml", "học máy"], "ai"),
            SkillTaxonomy("Deep Learning", ["deep learning", "dl", "học sâu"], "ai"),
            SkillTaxonomy("NLP", ["nlp", "natural language processing"], "ai"),
        ]
        return default_skills

    def _build_indices(self) -> None:
        """Build internal lookup structures."""
        for tax in self.taxonomy:
            canonical = tax.canonical_skill
            self._canonical_skills.append(canonical)
            
            # Map synonyms to canonical
            for syn in tax.synonyms:
                self._synonym_map[syn.lower()] = canonical
            
            # Compile regex patterns
            if tax.patterns:
                self._patterns[canonical] = [
                    re.compile(p, re.IGNORECASE) for p in tax.patterns
                ]

    def _find_span(self, text: str, skill_text: str) -> tuple[int, int]:
        """Find the span of a skill mention in text.
        
        Returns:
            Tuple of (start, end) indices, or (-1, -1) if not found
        """
        text_lower = text.lower()
        skill_lower = skill_text.lower()
        
        idx = text_lower.find(skill_lower)
        if idx != -1:
            return idx, idx + len(skill_text)
        
        return -1, -1

    def extract(
        self,
        text: str,
        *,
        min_confidence: float | None = None,
        max_results: int | None = None,
    ) -> list[ExtractedSkill]:
        """Extract skills from text with evidence.
        
        Args:
            text: Input text to extract skills from
            min_confidence: Minimum confidence threshold (uses config default if None)
            max_results: Maximum number of results (uses config default if None)
            
        Returns:
            List of ExtractedSkill objects sorted by confidence
        """
        if not text or not text.strip():
            return []
        
        min_conf = min_confidence or settings.skills.min_confidence
        max_res = max_results or settings.skills.max_skills_per_doc
        
        results: list[ExtractedSkill] = []
        text_lower = text.lower()
        seen_skills: set[str] = set()
        
        # 1. Exact synonym matching (highest confidence)
        for synonym, canonical in self._synonym_map.items():
            if canonical in seen_skills:
                continue
                
            if synonym in text_lower:
                span_start, span_end = self._find_span(text, synonym)
                evidence = text[max(0, span_start - 30):min(len(text), span_end + 30)] if span_start != -1 else ""
                
                results.append(ExtractedSkill(
                    canonical_skill=canonical,
                    raw_text=synonym,
                    confidence=0.95,
                    evidence_text=evidence.strip(),
                    span_start=span_start,
                    span_end=span_end,
                    method="exact",
                ))
                seen_skills.add(canonical)
        
        # 2. Regex pattern matching
        for canonical, patterns in self._patterns.items():
            if canonical in seen_skills:
                continue
                
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    matched_text = match.group(0)
                    span_start, span_end = match.span()
                    evidence = text[max(0, span_start - 30):min(len(text), span_end + 30)]
                    
                    results.append(ExtractedSkill(
                        canonical_skill=canonical,
                        raw_text=matched_text,
                        confidence=0.90,
                        evidence_text=evidence.strip(),
                        span_start=span_start,
                        span_end=span_end,
                        method="pattern",
                    ))
                    seen_skills.add(canonical)
                    break
        
        # 3. Fuzzy matching on canonical skills
        fuzzy_threshold = settings.skills.fuzzy_threshold
        matches = process.extract(
            text_lower,
            [s for s in self._canonical_skills if s not in seen_skills],
            scorer=fuzz.partial_ratio,
            limit=max_res * 2,
        )
        
        for canonical_skill, score, _ in matches:
            if canonical_skill in seen_skills:
                continue
                
            confidence = score / 100.0
            if confidence >= (fuzzy_threshold / 100.0):
                # Find best span (approximate)
                span_start, span_end = self._find_span(text, canonical_skill)
                evidence = text[max(0, span_start - 30):min(len(text), span_end + 30)] if span_start != -1 else text[:100]
                
                results.append(ExtractedSkill(
                    canonical_skill=canonical_skill,
                    raw_text=canonical_skill.lower(),
                    confidence=confidence,
                    evidence_text=evidence.strip(),
                    span_start=span_start,
                    span_end=span_end,
                    method="fuzzy",
                ))
                seen_skills.add(canonical_skill)
        
        # Filter by min confidence and sort
        results = [r for r in results if r.confidence >= min_conf]
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # Limit results
        results = results[:max_res]
        
        logger.debug(f"Extracted {len(results)} skills from text of length {len(text)}")
        return results
