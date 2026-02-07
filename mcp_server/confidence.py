#!/usr/bin/env python3
"""Confidence scoring for CPG evaluation results.

This module calculates confidence scores for CPG evaluations based on:
- Data completeness (% of required variables with data)
- Data freshness (how old the data is)
- Validation status (% passed plausibility checks)
- Attestation burden (inverse of attestations needed)

The overall confidence score is a weighted combination of these factors.

Example usage:
    from mcp_server.confidence import ConfidenceCalculator

    calculator = ConfidenceCalculator()
    score = calculator.calculate(concord)
    print(f"Confidence: {score.overall:.1%}")
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.concord import Concord
from core.evaluation import SufficiencyResultStatus

log = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Comprehensive confidence score for evaluation.

    Attributes:
        overall: Combined confidence score (0.0 - 1.0)
        completeness: Proportion of required variables with data
        freshness: Score based on data age
        validation: Proportion passed plausibility checks
        attestation_burden: Inverse of attestation ratio

        total_required: Total required variables
        total_with_data: Variables with data
        oldest_data_days: Age of oldest data in days
        validation_passed: Count of passed validations
        validation_total: Total validations performed
        attestations_needed: Variables needing user attestation
    """
    overall: float
    completeness: float
    freshness: float
    validation: float
    attestation_burden: float

    # Breakdown details
    total_required: int
    total_with_data: int
    oldest_data_days: int
    validation_passed: int
    validation_total: int
    attestations_needed: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_confidence": round(self.overall, 3),
            "confidence_level": self._confidence_level(),
            "components": {
                "completeness": round(self.completeness, 3),
                "freshness": round(self.freshness, 3),
                "validation": round(self.validation, 3),
                "attestation_burden": round(self.attestation_burden, 3)
            },
            "details": {
                "required_variables": self.total_required,
                "variables_with_data": self.total_with_data,
                "oldest_data_age_days": self.oldest_data_days,
                "validation_passed": self.validation_passed,
                "validation_checked": self.validation_total,
                "attestations_needed": self.attestations_needed
            }
        }

    def _confidence_level(self) -> str:
        """Get human-readable confidence level."""
        if self.overall >= 0.9:
            return "HIGH"
        elif self.overall >= 0.7:
            return "MODERATE"
        elif self.overall >= 0.5:
            return "LOW"
        else:
            return "VERY_LOW"


class ConfidenceCalculator:
    """Calculate confidence scores for CPG evaluations.

    The confidence score is calculated as a weighted sum of four components:
    1. Completeness (35%): How many required variables have data
    2. Freshness (25%): How recent the data is
    3. Validation (25%): How many values passed plausibility checks
    4. Attestation burden (15%): Inverse of user attestation needs

    Configurable weights and freshness thresholds allow customization
    for different clinical contexts.

    Attributes:
        WEIGHT_*: Component weights (must sum to 1.0)
        FRESHNESS_*: Age thresholds in days for freshness scoring
    """

    # Configurable weights
    WEIGHT_COMPLETENESS = 0.35
    WEIGHT_FRESHNESS = 0.25
    WEIGHT_VALIDATION = 0.25
    WEIGHT_ATTESTATION = 0.15

    # Freshness thresholds (days)
    FRESHNESS_OPTIMAL = 30      # Data within 30 days = 1.0
    FRESHNESS_GOOD = 90         # Data within 90 days = 0.8
    FRESHNESS_ACCEPTABLE = 365  # Data within 1 year = 0.5
    FRESHNESS_STALE = 730       # Data older than 2 years = 0.2

    def calculate(self, concord: Concord) -> ConfidenceScore:
        """Calculate comprehensive confidence score.

        Algorithm:
        1. Completeness: required_with_data / total_required
        2. Freshness: weighted average of data age scores
        3. Validation: passed_checks / total_checks
        4. Attestation burden: 1 - (attestations_needed / total_required)

        Overall = weighted sum of components

        Args:
            concord: Concord instance with completed sufficiency evaluation

        Returns:
            ConfidenceScore with all metrics
        """
        # Get evaluation results
        sufficiency = concord.sufficiency_result
        if not sufficiency:
            log.warning("No sufficiency result available")
            return self._empty_score()

        eval_records = sufficiency.context.evaluation_list

        # 1. Completeness
        required_vars = [er for er in eval_records if er.record.var.required]
        required_with_data = [er for er in required_vars if er.record.has_value]
        total_required = len(required_vars)
        total_with_data = len(required_with_data)
        completeness = total_with_data / total_required if total_required > 0 else 1.0

        # 2. Freshness
        freshness, oldest_days = self._calculate_freshness(eval_records)

        # 3. Validation
        validation_passed, validation_total = self._calculate_validation(eval_records)
        validation = validation_passed / validation_total if validation_total > 0 else 1.0

        # 4. Attestation burden
        attestations = sufficiency.attestation_variables or []
        attestations_needed = len(attestations)
        attestation_burden = 1.0 - (attestations_needed / total_required) if total_required > 0 else 1.0

        # Overall weighted score
        overall = (
            self.WEIGHT_COMPLETENESS * completeness +
            self.WEIGHT_FRESHNESS * freshness +
            self.WEIGHT_VALIDATION * validation +
            self.WEIGHT_ATTESTATION * attestation_burden
        )

        score = ConfidenceScore(
            overall=overall,
            completeness=completeness,
            freshness=freshness,
            validation=validation,
            attestation_burden=attestation_burden,
            total_required=total_required,
            total_with_data=total_with_data,
            oldest_data_days=oldest_days,
            validation_passed=validation_passed,
            validation_total=validation_total,
            attestations_needed=attestations_needed
        )

        log.debug(f"Calculated confidence: {score.overall:.2f}")
        return score

    def _calculate_freshness(self, eval_records) -> tuple[float, int]:
        """Calculate freshness score based on data age.

        Args:
            eval_records: List of EvaluatedRecord objects

        Returns:
            Tuple of (freshness_score, oldest_age_days)
        """
        now = datetime.now()
        ages_days = []

        for er in eval_records:
            if er.record.has_value and er.record.value:
                date = er.record.value.date
                if date:
                    # Handle ValueDate wrapper
                    if hasattr(date, 'dt'):
                        date = date.dt
                    if isinstance(date, datetime):
                        age = (now - date).days
                        ages_days.append(age)

        if not ages_days:
            return 1.0, 0

        oldest = max(ages_days)

        # Calculate weighted freshness
        freshness_scores = []
        for age in ages_days:
            score = self._age_to_freshness(age)
            freshness_scores.append(score)

        avg_freshness = sum(freshness_scores) / len(freshness_scores)
        return avg_freshness, oldest

    def _age_to_freshness(self, age_days: int) -> float:
        """Convert data age to freshness score.

        Args:
            age_days: Age of data in days

        Returns:
            Freshness score (0.0 - 1.0)
        """
        if age_days <= self.FRESHNESS_OPTIMAL:
            return 1.0
        elif age_days <= self.FRESHNESS_GOOD:
            return 0.8
        elif age_days <= self.FRESHNESS_ACCEPTABLE:
            return 0.5
        else:
            return 0.2

    def _calculate_validation(self, eval_records) -> tuple[int, int]:
        """Count validation pass/fail.

        Args:
            eval_records: List of EvaluatedRecord objects

        Returns:
            Tuple of (passed_count, total_count)
        """
        passed = 0
        total = 0

        for er in eval_records:
            if er.record.has_value:
                total += 1
                if er.error is None:
                    passed += 1

        return passed, total

    def _empty_score(self) -> ConfidenceScore:
        """Return empty confidence score when no data available."""
        return ConfidenceScore(
            overall=0.0,
            completeness=0.0,
            freshness=0.0,
            validation=0.0,
            attestation_burden=0.0,
            total_required=0,
            total_with_data=0,
            oldest_data_days=0,
            validation_passed=0,
            validation_total=0,
            attestations_needed=0
        )

    def calculate_for_multiple(
        self,
        concord_instances: dict[str, Concord]
    ) -> dict[str, ConfidenceScore]:
        """Calculate confidence scores for multiple CPG evaluations.

        Args:
            concord_instances: Map of CPG ID to Concord instances

        Returns:
            Map of CPG ID to ConfidenceScore
        """
        scores = {}
        for cpg_id, concord in concord_instances.items():
            try:
                scores[cpg_id] = self.calculate(concord)
            except Exception as e:
                log.warning(f"Failed to calculate confidence for {cpg_id}: {e}")
                scores[cpg_id] = self._empty_score()
        return scores
