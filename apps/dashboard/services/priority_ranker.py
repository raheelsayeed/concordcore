#!/usr/bin/env python3
"""Priority ranking service for recommendations."""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .evaluator import EvaluationSummary, CPGEvaluationResult


class PriorityLevel(Enum):
    """Priority levels for recommendations."""

    CRITICAL = 1    # Must address immediately
    HIGH = 2        # Should address soon
    MODERATE = 3    # Address when convenient
    LOW = 4         # Consider addressing
    INFORMATIONAL = 5  # For awareness only


@dataclass
class RankedRecommendation:
    """A recommendation with priority ranking."""

    cpg_id: str
    cpg_title: str
    recommendation: Any  # EvaluatedRecommendation
    priority: PriorityLevel
    priority_score: float  # 0-100, higher is more urgent
    evidence_grade: str
    evidence_description: str
    category: str
    action_type: str  # DISPLAY, MEDICATION, EVALUATION, etc.
    supporting_assessments: list[str]
    conflicts_with: list[str]  # IDs of conflicting recommendations


class PriorityRanker:
    """Service for ranking recommendations by priority."""

    # Evidence grade weights (higher = more weight)
    EVIDENCE_WEIGHTS = {
        # Class of Recommendation (ACC/AHA)
        "I": 100,
        "IIa": 75,
        "IIb": 50,
        "III": 10,  # Low priority - harmful or no benefit
        # USPSTF
        "A": 100,
        "B": 80,
        "C": 40,
        "D": 5,
        "I": 20,  # Insufficient evidence
    }

    # Level of Evidence weights
    LOE_WEIGHTS = {
        "A": 1.0,       # High quality evidence
        "B-R": 0.9,     # Moderate quality (randomized)
        "B-NR": 0.8,    # Moderate quality (non-randomized)
        "C-LD": 0.6,    # Limited data
        "C-EO": 0.5,    # Expert opinion
    }

    # Action type urgency multipliers
    ACTION_MULTIPLIERS = {
        "MEDICATION": 1.2,
        "EVALUATION": 1.1,
        "LIFESTYLE": 0.9,
        "DISPLAY": 0.8,
    }

    def rank_recommendations(
        self,
        summary: EvaluationSummary,
        include_non_applicable: bool = False
    ) -> list[RankedRecommendation]:
        """Rank all recommendations from a multi-CPG evaluation.

        Args:
            summary: The evaluation summary to rank
            include_non_applicable: Include recommendations that don't apply

        Returns:
            List of RankedRecommendation sorted by priority (highest first)
        """
        ranked = []

        # Build conflict map
        conflict_map = self._build_conflict_map(summary)

        for cpg_id, eval_result in summary.evaluations.items():
            recommendations = (
                eval_result.applied_recommendations
                if not include_non_applicable
                else eval_result.all_recommendations
            )

            for rec in recommendations:
                ranked_rec = self._rank_single_recommendation(
                    cpg_id=cpg_id,
                    cpg_title=eval_result.cpg_title,
                    recommendation=rec,
                    conflict_map=conflict_map,
                )
                ranked.append(ranked_rec)

        # Sort by priority score (descending)
        ranked.sort(key=lambda r: r.priority_score, reverse=True)

        return ranked

    def _rank_single_recommendation(
        self,
        cpg_id: str,
        cpg_title: str,
        recommendation: Any,
        conflict_map: dict[str, list[str]]
    ) -> RankedRecommendation:
        """Rank a single recommendation."""
        rec_var = recommendation.recommendation

        # Get evidence grades
        class_of_rec = getattr(rec_var, 'class_of_recommendation', None)
        level_of_evidence = getattr(rec_var, 'level_of_evidence', None)
        uspstf_grade = getattr(rec_var, 'uspstf_grade', None)

        # Calculate base score from evidence
        evidence_grade = "Unknown"
        evidence_desc = "No evidence grade specified"

        if class_of_rec:
            grade_value = class_of_rec.value if hasattr(class_of_rec, 'value') else str(class_of_rec)
            base_score = self.EVIDENCE_WEIGHTS.get(grade_value, 50)
            evidence_grade = f"Class {grade_value}"
            evidence_desc = self._get_class_description(grade_value)
        elif uspstf_grade:
            grade_value = uspstf_grade.value if hasattr(uspstf_grade, 'value') else str(uspstf_grade)
            base_score = self.EVIDENCE_WEIGHTS.get(grade_value, 50)
            evidence_grade = f"USPSTF Grade {grade_value}"
            evidence_desc = self._get_uspstf_description(grade_value)
        else:
            base_score = 50

        # Apply level of evidence modifier
        if level_of_evidence:
            loe_value = level_of_evidence.value if hasattr(level_of_evidence, 'value') else str(level_of_evidence)
            loe_weight = self.LOE_WEIGHTS.get(loe_value, 0.7)
            base_score *= loe_weight

        # Apply action type multiplier
        action_type = getattr(rec_var, 'type', 'DISPLAY')
        if hasattr(action_type, 'value'):
            action_type = action_type.value
        multiplier = self.ACTION_MULTIPLIERS.get(str(action_type).upper(), 1.0)
        final_score = base_score * multiplier

        # Reduce score if there are conflicts
        rec_id = f"{cpg_id}:{rec_var.id}"
        conflicts_with = conflict_map.get(rec_id, [])
        if conflicts_with:
            final_score *= 0.8  # 20% penalty for conflicting recommendations

        # Determine priority level
        priority = self._score_to_priority(final_score)

        # Get supporting assessments
        supporting = []
        if hasattr(recommendation, 'based_on') and recommendation.based_on:
            for assessment in recommendation.based_on:
                if hasattr(assessment, 'assessment') and hasattr(assessment.assessment, 'id'):
                    supporting.append(assessment.assessment.id)

        # Get category from CPG
        category = self._infer_category(cpg_id, rec_var)

        return RankedRecommendation(
            cpg_id=cpg_id,
            cpg_title=cpg_title,
            recommendation=recommendation,
            priority=priority,
            priority_score=final_score,
            evidence_grade=evidence_grade,
            evidence_description=evidence_desc,
            category=category,
            action_type=str(action_type),
            supporting_assessments=supporting,
            conflicts_with=conflicts_with,
        )

    def _build_conflict_map(self, summary: EvaluationSummary) -> dict[str, list[str]]:
        """Build a map of recommendation IDs to conflicting recommendation IDs."""
        conflict_map: dict[str, list[str]] = {}

        if not summary.conflicts:
            return conflict_map

        for conflict in summary.conflicts.conflicts:
            # Extract recommendation IDs from conflict
            rec_ids = []
            for involved in conflict.involved_cpgs:
                cpg_id = involved.get('cpg_id', '')
                for rec in involved.get('recommendations', []):
                    rec_id = f"{cpg_id}:{rec.recommendation.id if hasattr(rec, 'recommendation') else rec}"
                    rec_ids.append(rec_id)

            # Add cross-references
            for rec_id in rec_ids:
                if rec_id not in conflict_map:
                    conflict_map[rec_id] = []
                for other_id in rec_ids:
                    if other_id != rec_id and other_id not in conflict_map[rec_id]:
                        conflict_map[rec_id].append(other_id)

        return conflict_map

    def _score_to_priority(self, score: float) -> PriorityLevel:
        """Convert a numeric score to a priority level."""
        if score >= 90:
            return PriorityLevel.CRITICAL
        elif score >= 70:
            return PriorityLevel.HIGH
        elif score >= 50:
            return PriorityLevel.MODERATE
        elif score >= 30:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.INFORMATIONAL

    def _get_class_description(self, grade: str) -> str:
        """Get description for class of recommendation."""
        descriptions = {
            "I": "Benefit substantially outweighs risk - recommended",
            "IIa": "Benefit outweighs risk - reasonable to perform",
            "IIb": "Benefit may outweigh risk - may be considered",
            "III": "No benefit or harm outweighs benefit - not recommended",
        }
        return descriptions.get(grade, "Unknown classification")

    def _get_uspstf_description(self, grade: str) -> str:
        """Get description for USPSTF grade."""
        descriptions = {
            "A": "High certainty of substantial net benefit",
            "B": "High certainty of moderate net benefit",
            "C": "Offer selectively based on individual circumstances",
            "D": "No net benefit or harms outweigh benefits",
            "I": "Insufficient evidence to assess benefit/harm balance",
        }
        return descriptions.get(grade, "Unknown grade")

    def _infer_category(self, cpg_id: str, rec_var: Any) -> str:
        """Infer the category of a recommendation."""
        cpg_id_lower = cpg_id.lower()

        if 'cholesterol' in cpg_id_lower or 'lipid' in cpg_id_lower or 'statin' in cpg_id_lower:
            return "Cardiovascular"
        elif 'cancer' in cpg_id_lower or 'screening' in cpg_id_lower:
            return "Cancer Screening"
        elif 'diabetes' in cpg_id_lower:
            return "Metabolic"
        elif 'hiv' in cpg_id_lower or 'hepatitis' in cpg_id_lower:
            return "Infectious Disease"
        elif 'depression' in cpg_id_lower or 'mental' in cpg_id_lower:
            return "Mental Health"
        elif 'hypertension' in cpg_id_lower or 'blood pressure' in cpg_id_lower:
            return "Cardiovascular"
        else:
            return "General"

    def get_recommendations_by_category(
        self,
        ranked: list[RankedRecommendation]
    ) -> dict[str, list[RankedRecommendation]]:
        """Group ranked recommendations by category."""
        by_category: dict[str, list[RankedRecommendation]] = {}
        for rec in ranked:
            if rec.category not in by_category:
                by_category[rec.category] = []
            by_category[rec.category].append(rec)
        return by_category

    def get_recommendations_by_priority(
        self,
        ranked: list[RankedRecommendation]
    ) -> dict[PriorityLevel, list[RankedRecommendation]]:
        """Group ranked recommendations by priority level."""
        by_priority: dict[PriorityLevel, list[RankedRecommendation]] = {}
        for rec in ranked:
            if rec.priority not in by_priority:
                by_priority[rec.priority] = []
            by_priority[rec.priority].append(rec)
        return by_priority
