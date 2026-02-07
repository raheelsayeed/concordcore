#!/usr/bin/env python3
"""Priority ranking for recommendations.

This module provides priority ranking algorithms for clinical recommendations
based on evidence strength and urgency indicators:

- Class of Recommendation (ACC/AHA): I, IIa, IIb, III
- Level of Evidence: A, B-R, B-NR, C-LD, C-EO
- USPSTF Grade: A, B, C, D, I

Priority levels: CRITICAL, HIGH, MODERATE, LOW, INFORMATIONAL

Example usage:
    from mcp_server.priority import PriorityRanker

    ranker = PriorityRanker()
    prioritized = ranker.rank(recommendations)
    for p in prioritized:
        print(f"{p.priority_level}: {p.recommendation.title}")
"""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.recommendation import (
    ClassOfRecommendation,
    LevelOfEvidence,
    USPSTFGrading,
    EvaluatedRecommendation
)

log = logging.getLogger(__name__)


class PriorityLevel(IntEnum):
    """Priority levels for recommendations.

    Values are ordered from highest to lowest priority.
    """
    CRITICAL = 1
    HIGH = 2
    MODERATE = 3
    LOW = 4
    INFORMATIONAL = 5

    def to_dict(self) -> dict:
        """Get dict representation with description."""
        descriptions = {
            PriorityLevel.CRITICAL: "Immediate action recommended",
            PriorityLevel.HIGH: "Action strongly recommended",
            PriorityLevel.MODERATE: "Consider action",
            PriorityLevel.LOW: "Optional consideration",
            PriorityLevel.INFORMATIONAL: "For information only"
        }
        return {
            "level": self.name,
            "value": self.value,
            "description": descriptions.get(self, "")
        }


@dataclass
class PrioritizedRecommendation:
    """Recommendation with priority scoring.

    Attributes:
        recommendation: The evaluated recommendation
        priority_level: Categorical priority level
        priority_score: Numeric score (0-100, higher = more urgent)
        rationale: Human-readable explanation of priority
    """
    recommendation: EvaluatedRecommendation
    priority_level: PriorityLevel
    priority_score: float
    rationale: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        rec = self.recommendation
        rec_var = rec.recommendation

        return {
            "id": rec_var.id,
            "title": rec_var.title,
            "priority_level": self.priority_level.name,
            "priority_score": round(self.priority_score, 1),
            "rationale": self.rationale,
            "applies": rec.applies,
            "narrative": rec.narrative,
            "type": str(rec_var.type) if rec_var.type else None,
            "evidence": {
                "class_of_recommendation": str(rec_var.class_of_recommendation)
                    if rec_var.class_of_recommendation else None,
                "level_of_evidence": str(rec_var.level_of_evidence)
                    if rec_var.level_of_evidence else None,
                "uspstf_grade": rec_var.uspstf_grade.value
                    if rec_var.uspstf_grade else None
            },
            "citations_count": len(rec_var.citations) if rec_var.citations else 0
        }


class PriorityRanker:
    """Rank recommendations by evidence strength and urgency.

    Scoring Algorithm:
    - Primary: Class of Recommendation (45%)
    - Secondary: Level of Evidence (35%)
    - Tertiary: USPSTF Grade (20%)

    Composite score = weighted sum normalized to 0-100

    Priority Level Thresholds:
    - CRITICAL: COR I + score >= 80
    - HIGH: score >= 70
    - MODERATE: score >= 50
    - LOW: score >= 30
    - INFORMATIONAL: score < 30

    Attributes:
        COR_SCORES: Mapping of ClassOfRecommendation to score
        LOE_SCORES: Mapping of LevelOfEvidence to score
        USPSTF_SCORES: Mapping of USPSTFGrading to score
        WEIGHT_*: Component weights (must sum to 1.0)
    """

    # Class of Recommendation scores (higher = stronger)
    COR_SCORES = {
        ClassOfRecommendation.I: 100,
        ClassOfRecommendation.II_A: 75,
        ClassOfRecommendation.II_B: 50,
        ClassOfRecommendation.III: 25,
        ClassOfRecommendation.III_Moderate: 15,
        ClassOfRecommendation.III_Strong: 10,
    }

    # Level of Evidence scores
    LOE_SCORES = {
        LevelOfEvidence.A: 100,
        LevelOfEvidence.B_R: 80,
        LevelOfEvidence.B_NR: 60,
        LevelOfEvidence.C_LD: 40,
        LevelOfEvidence.C_EO: 20,
    }

    # USPSTF Grade scores
    USPSTF_SCORES = {
        USPSTFGrading.A: 100,
        USPSTFGrading.B: 75,
        USPSTFGrading.C: 50,
        USPSTFGrading.D: 25,
        USPSTFGrading.I: 10,
    }

    # Weights for composite score
    WEIGHT_COR = 0.45
    WEIGHT_LOE = 0.35
    WEIGHT_USPSTF = 0.20

    def rank(
        self,
        recommendations: list[EvaluatedRecommendation],
        include_non_applicable: bool = False
    ) -> list[PrioritizedRecommendation]:
        """Rank recommendations by priority.

        Args:
            recommendations: List of evaluated recommendations
            include_non_applicable: If True, include recommendations
                where applies=False (with lower priority)

        Returns:
            List of PrioritizedRecommendation sorted by priority score
        """
        prioritized = []

        for rec in recommendations:
            # Skip non-applicable unless requested
            if not rec.applies and not include_non_applicable:
                continue

            score = self._calculate_score(rec)
            level = self._determine_level(score, rec)
            rationale = self._generate_rationale(rec, score)

            prioritized.append(PrioritizedRecommendation(
                recommendation=rec,
                priority_level=level,
                priority_score=score,
                rationale=rationale
            ))

        # Sort by priority score (descending)
        prioritized.sort(key=lambda p: (
            -p.priority_score,
            p.priority_level.value  # Secondary: level enum value
        ))

        log.debug(f"Ranked {len(prioritized)} recommendations")
        return prioritized

    def _calculate_score(self, rec: EvaluatedRecommendation) -> float:
        """Calculate composite priority score.

        Args:
            rec: Evaluated recommendation

        Returns:
            Score from 0-100
        """
        rec_var = rec.recommendation
        cor = rec_var.class_of_recommendation
        loe = rec_var.level_of_evidence
        uspstf = rec_var.uspstf_grade

        # Get scores, defaulting to neutral (50) if not specified
        cor_score = self.COR_SCORES.get(cor, 50) if cor else 50
        loe_score = self.LOE_SCORES.get(loe, 50) if loe else 50
        uspstf_score = self.USPSTF_SCORES.get(uspstf, 50) if uspstf else 50

        composite = (
            self.WEIGHT_COR * cor_score +
            self.WEIGHT_LOE * loe_score +
            self.WEIGHT_USPSTF * uspstf_score
        )

        # Penalize non-applicable recommendations
        if not rec.applies:
            composite *= 0.3

        return composite

    def _determine_level(
        self,
        score: float,
        rec: EvaluatedRecommendation
    ) -> PriorityLevel:
        """Map score to priority level.

        Args:
            score: Numeric priority score
            rec: Evaluated recommendation

        Returns:
            PriorityLevel enum value
        """
        cor = rec.recommendation.class_of_recommendation

        # Class I with high evidence = Critical
        if cor == ClassOfRecommendation.I and score >= 80:
            return PriorityLevel.CRITICAL
        elif score >= 70:
            return PriorityLevel.HIGH
        elif score >= 50:
            return PriorityLevel.MODERATE
        elif score >= 30:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.INFORMATIONAL

    def _generate_rationale(
        self,
        rec: EvaluatedRecommendation,
        score: float
    ) -> str:
        """Generate human-readable priority rationale.

        Args:
            rec: Evaluated recommendation
            score: Numeric priority score

        Returns:
            Rationale string explaining the priority
        """
        parts = []
        rec_var = rec.recommendation

        cor = rec_var.class_of_recommendation
        loe = rec_var.level_of_evidence
        uspstf = rec_var.uspstf_grade

        # Class of Recommendation explanation
        if cor:
            cor_text = {
                ClassOfRecommendation.I:
                    "Strong recommendation (Class I: benefit greatly outweighs risk)",
                ClassOfRecommendation.II_A:
                    "Reasonable recommendation (Class IIa: benefit outweighs risk)",
                ClassOfRecommendation.II_B:
                    "May be considered (Class IIb: benefit may outweigh risk)",
                ClassOfRecommendation.III:
                    "Not recommended (Class III: risk outweighs benefit)",
                ClassOfRecommendation.III_Moderate:
                    "No benefit (Class III: moderate certainty)",
                ClassOfRecommendation.III_Strong:
                    "Potentially harmful (Class III: strong certainty)",
            }
            parts.append(cor_text.get(cor, f"Class {cor} recommendation"))

        # Level of Evidence explanation
        if loe:
            loe_text = {
                LevelOfEvidence.A:
                    "supported by high-quality evidence",
                LevelOfEvidence.B_R:
                    "supported by moderate-quality randomized evidence",
                LevelOfEvidence.B_NR:
                    "supported by moderate-quality non-randomized evidence",
                LevelOfEvidence.C_LD:
                    "based on limited data",
                LevelOfEvidence.C_EO:
                    "based on expert opinion",
            }
            parts.append(loe_text.get(loe, f"Level {loe} evidence"))

        # USPSTF Grade explanation
        if uspstf:
            uspstf_text = {
                USPSTFGrading.A: "USPSTF Grade A: strongly recommended",
                USPSTFGrading.B: "USPSTF Grade B: recommended",
                USPSTFGrading.C: "USPSTF Grade C: selective recommendation",
                USPSTFGrading.D: "USPSTF Grade D: not recommended",
                USPSTFGrading.I: "USPSTF Grade I: insufficient evidence",
            }
            parts.append(uspstf_text.get(uspstf, f"USPSTF Grade {uspstf.value}"))

        if not parts:
            return "Priority based on clinical guidelines"

        return "; ".join(parts)

    def get_summary(
        self,
        prioritized: list[PrioritizedRecommendation]
    ) -> dict:
        """Get summary statistics for prioritized recommendations.

        Args:
            prioritized: List of prioritized recommendations

        Returns:
            Summary dict with counts by level
        """
        summary = {
            "total": len(prioritized),
            "by_level": {level.name: 0 for level in PriorityLevel}
        }

        for p in prioritized:
            summary["by_level"][p.priority_level.name] += 1

        # Add top priority items
        if prioritized:
            summary["highest_priority"] = {
                "id": prioritized[0].recommendation.recommendation.id,
                "title": prioritized[0].recommendation.recommendation.title,
                "level": prioritized[0].priority_level.name,
                "score": round(prioritized[0].priority_score, 1)
            }

        return summary
