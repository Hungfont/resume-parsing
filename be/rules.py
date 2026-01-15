"""Rule engine for config-driven candidate filtering and scoring.

Implements hard and soft rule evaluation with full audit traces.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Rule types."""
    # Hard rules (filters)
    SKILLS_REQUIRED = "skills_required"
    MIN_YEARS = "min_years"
    LOCATION_MATCH = "location_match"
    
    # Soft rules (scoring)
    SKILLS_BONUS = "skills_bonus"
    YEARS_BONUS = "years_bonus"
    LOCATION_BONUS = "location_bonus"


class RuleStatus(str, Enum):
    """Rule evaluation status."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class Evidence:
    """Evidence for a rule evaluation."""
    source: str  # e.g., "candidate_resume", "extracted_skills"
    text: str
    span: dict[str, int] = field(default_factory=dict)


@dataclass
class RuleTrace:
    """Audit trace for a single rule evaluation."""
    rule_id: str
    name: str
    status: RuleStatus
    reason: str
    evidence: list[Evidence] = field(default_factory=list)
    score_delta: float = 0.0


@dataclass
class RuleConfig:
    """Configuration for a single rule."""
    id: str
    name: str
    type: RuleType
    params: dict[str, Any]
    weight: float = 1.0


class RuleEngine:
    """Config-driven rule engine for candidate evaluation.
    
    Evaluates both hard rules (filters) and soft rules (scoring) with
    full audit trails.
    """

    def __init__(self, rules: list[RuleConfig]):
        """Initialize rule engine.
        
        Args:
            rules: List of RuleConfig objects
        """
        self.rules = rules
        self.hard_rules = [r for r in rules if self._is_hard_rule(r.type)]
        self.soft_rules = [r for r in rules if not self._is_hard_rule(r.type)]
        
        logger.info(
            f"Initialized rule engine: {len(self.hard_rules)} hard, "
            f"{len(self.soft_rules)} soft rules"
        )

    @staticmethod
    def _is_hard_rule(rule_type: RuleType) -> bool:
        """Check if a rule type is a hard constraint."""
        hard_types = {
            RuleType.SKILLS_REQUIRED,
            RuleType.MIN_YEARS,
            RuleType.LOCATION_MATCH,
        }
        return rule_type in hard_types

    def evaluate_hard_rules(
        self,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
    ) -> tuple[bool, list[RuleTrace]]:
        """Evaluate hard filtering rules.
        
        Args:
            candidate_data: Candidate features and metadata
            job_data: Job requirements and metadata
            
        Returns:
            Tuple of (passed, rule_traces)
        """
        traces = []
        
        for rule in self.hard_rules:
            trace = self._evaluate_rule(rule, candidate_data, job_data)
            traces.append(trace)
            
            if trace.status == RuleStatus.FAIL:
                # Hard rule failed - candidate is filtered out
                return False, traces
        
        return True, traces

    def evaluate_soft_rules(
        self,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
        base_score: float,
    ) -> tuple[float, list[RuleTrace]]:
        """Evaluate soft scoring rules.
        
        Args:
            candidate_data: Candidate features and metadata
            job_data: Job requirements and metadata
            base_score: Base score (e.g., from similarity)
            
        Returns:
            Tuple of (adjusted_score, rule_traces)
        """
        traces = []
        total_delta = 0.0
        
        for rule in self.soft_rules:
            trace = self._evaluate_rule(rule, candidate_data, job_data)
            traces.append(trace)
            
            if trace.status == RuleStatus.PASS:
                total_delta += trace.score_delta * rule.weight
        
        final_score = base_score + total_delta
        return final_score, traces

    def _evaluate_rule(
        self,
        rule: RuleConfig,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
    ) -> RuleTrace:
        """Evaluate a single rule.
        
        Args:
            rule: Rule configuration
            candidate_data: Candidate features
            job_data: Job requirements
            
        Returns:
            RuleTrace with evaluation result
        """
        try:
            if rule.type == RuleType.SKILLS_REQUIRED:
                return self._eval_skills_required(rule, candidate_data, job_data)
            elif rule.type == RuleType.MIN_YEARS:
                return self._eval_min_years(rule, candidate_data, job_data)
            elif rule.type == RuleType.SKILLS_BONUS:
                return self._eval_skills_bonus(rule, candidate_data, job_data)
            elif rule.type == RuleType.YEARS_BONUS:
                return self._eval_years_bonus(rule, candidate_data, job_data)
            else:
                logger.warning(f"Unknown rule type: {rule.type}")
                return RuleTrace(
                    rule_id=rule.id,
                    name=rule.name,
                    status=RuleStatus.SKIP,
                    reason=f"Unknown rule type: {rule.type}",
                )
        except Exception as e:
            logger.error(f"Rule evaluation failed for {rule.id}: {e}")
            return RuleTrace(
                rule_id=rule.id,
                name=rule.name,
                status=RuleStatus.SKIP,
                reason=f"Evaluation error: {e}",
            )

    def _eval_skills_required(
        self,
        rule: RuleConfig,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
    ) -> RuleTrace:
        """Evaluate skills_required rule."""
        required_skills = set(rule.params.get("all_of", []))
        min_confidence = rule.params.get("min_confidence", 0.6)
        
        candidate_skills = {
            s["canonical_skill"]: s
            for s in candidate_data.get("skills", [])
            if s.get("confidence", 0) >= min_confidence
        }
        
        missing_skills = required_skills - set(candidate_skills.keys())
        
        if missing_skills:
            return RuleTrace(
                rule_id=rule.id,
                name=rule.name,
                status=RuleStatus.FAIL,
                reason=f"Missing required skills: {', '.join(missing_skills)}",
            )
        
        # Build evidence
        evidence = [
            Evidence(
                source="extracted_skills",
                text=candidate_skills[skill].get("evidence", ""),
            )
            for skill in required_skills
        ]
        
        return RuleTrace(
            rule_id=rule.id,
            name=rule.name,
            status=RuleStatus.PASS,
            reason=f"Has all required skills: {', '.join(required_skills)}",
            evidence=evidence,
        )

    def _eval_min_years(
        self,
        rule: RuleConfig,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
    ) -> RuleTrace:
        """Evaluate min_years rule."""
        required_years = rule.params.get("min", 0)
        candidate_years = candidate_data.get("years_experience", 0)
        
        if candidate_years < required_years:
            return RuleTrace(
                rule_id=rule.id,
                name=rule.name,
                status=RuleStatus.FAIL,
                reason=f"Only {candidate_years} years, requires {required_years}",
            )
        
        return RuleTrace(
            rule_id=rule.id,
            name=rule.name,
            status=RuleStatus.PASS,
            reason=f"Has {candidate_years} years (>= {required_years})",
        )

    def _eval_skills_bonus(
        self,
        rule: RuleConfig,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
    ) -> RuleTrace:
        """Evaluate skills_bonus rule."""
        nice_to_have = set(rule.params.get("any_of", []))
        per_skill_bonus = rule.params.get("per_skill_bonus", 5.0)
        min_confidence = rule.params.get("min_confidence", 0.6)
        
        candidate_skills = {
            s["canonical_skill"]
            for s in candidate_data.get("skills", [])
            if s.get("confidence", 0) >= min_confidence
        }
        
        matched_skills = nice_to_have & candidate_skills
        
        if not matched_skills:
            return RuleTrace(
                rule_id=rule.id,
                name=rule.name,
                status=RuleStatus.PASS,
                reason="No nice-to-have skills found",
                score_delta=0.0,
            )
        
        bonus = len(matched_skills) * per_skill_bonus
        
        return RuleTrace(
            rule_id=rule.id,
            name=rule.name,
            status=RuleStatus.PASS,
            reason=f"Has {len(matched_skills)} nice-to-have skills: {', '.join(matched_skills)}",
            score_delta=bonus,
        )

    def _eval_years_bonus(
        self,
        rule: RuleConfig,
        candidate_data: dict[str, Any],
        job_data: dict[str, Any],
    ) -> RuleTrace:
        """Evaluate years_bonus rule."""
        candidate_years = candidate_data.get("years_experience", 0)
        bonus_per_year = rule.params.get("bonus_per_year", 1.0)
        max_bonus = rule.params.get("max_bonus", 10.0)
        
        bonus = min(candidate_years * bonus_per_year, max_bonus)
        
        return RuleTrace(
            rule_id=rule.id,
            name=rule.name,
            status=RuleStatus.PASS,
            reason=f"Experience bonus: {candidate_years} years",
            score_delta=bonus,
        )
