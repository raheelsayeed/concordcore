#!/usr/bin/env python3
"""Outcome tracking system for CPG recommendations.

This module tracks the outcomes of CPG recommendations to enable:
- Quality measurement (HEDIS, MIPS)
- Recommendation effectiveness analysis
- Feedback loops for CPG improvement
- Population health analytics

Example usage:
    ```python
    from core.outcome_tracking import OutcomeTracker, RecommendationOutcome

    tracker = OutcomeTracker()

    # Record when a recommendation is made
    tracker.record_recommendation(
        patient_id="P123",
        cpg_id="uspstf_statinuse",
        recommendation_id="MED_B",
        context={"ascvd_risk": 15.5}
    )

    # Record the action taken
    tracker.record_action(
        patient_id="P123",
        recommendation_id="MED_B",
        action="accepted",
        details={"medication": "atorvastatin", "dose": "20mg"}
    )

    # Record outcome
    tracker.record_outcome(
        patient_id="P123",
        recommendation_id="MED_B",
        outcome_type="lab_improvement",
        value={"ldl_before": 145, "ldl_after": 95}
    )
    ```
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any
import logging
import json
import hashlib

log = logging.getLogger(__name__)


class ActionType(Enum):
    """Type of action taken on a recommendation."""
    ACCEPTED = "accepted"  # Provider/patient accepted recommendation
    REJECTED = "rejected"  # Explicitly rejected
    DEFERRED = "deferred"  # Postponed for later
    MODIFIED = "modified"  # Accepted with modifications
    NOT_APPLICABLE = "not_applicable"  # Found to not apply after review
    PENDING = "pending"  # No action taken yet


class OutcomeType(Enum):
    """Type of outcome measured."""
    LAB_IMPROVEMENT = "lab_improvement"  # Lab value improved
    LAB_STABLE = "lab_stable"  # Lab value maintained
    LAB_WORSENED = "lab_worsened"  # Lab value worsened
    EVENT_PREVENTED = "event_prevented"  # Adverse event prevented
    EVENT_OCCURRED = "event_occurred"  # Adverse event occurred
    HOSPITALIZATION_AVOIDED = "hospitalization_avoided"
    HOSPITALIZATION_OCCURRED = "hospitalization_occurred"
    GOAL_MET = "goal_met"  # Treatment goal achieved
    GOAL_NOT_MET = "goal_not_met"  # Treatment goal not achieved
    SIDE_EFFECT = "side_effect"  # Side effect experienced
    ADHERENCE_GOOD = "adherence_good"  # Good medication adherence
    ADHERENCE_POOR = "adherence_poor"  # Poor medication adherence


@dataclass
class RecommendationRecord:
    """Record of a recommendation made.

    Attributes:
        id: Unique record ID
        patient_id: Patient identifier (hashed for privacy)
        cpg_id: CPG that generated the recommendation
        cpg_version: Version of the CPG
        recommendation_id: ID of the recommendation
        recommendation_title: Title of the recommendation
        timestamp: When the recommendation was made
        context: Relevant context (assessments, risk scores, etc.)
        evidence_grade: Evidence grade of the recommendation
    """
    id: str
    patient_id: str
    cpg_id: str
    cpg_version: str
    recommendation_id: str
    recommendation_title: str
    timestamp: datetime
    context: dict = field(default_factory=dict)
    evidence_grade: str = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "cpg_id": self.cpg_id,
            "cpg_version": self.cpg_version,
            "recommendation_id": self.recommendation_id,
            "recommendation_title": self.recommendation_title,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "evidence_grade": self.evidence_grade
        }


@dataclass
class ActionRecord:
    """Record of action taken on a recommendation.

    Attributes:
        id: Unique record ID
        recommendation_record_id: ID of the recommendation record
        action_type: Type of action taken
        action_timestamp: When the action was taken
        actor: Who took the action (provider, patient, system)
        details: Additional details about the action
        reason: Reason for the action (especially if rejected/deferred)
    """
    id: str
    recommendation_record_id: str
    action_type: ActionType
    action_timestamp: datetime
    actor: str = "unknown"
    details: dict = field(default_factory=dict)
    reason: str = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recommendation_record_id": self.recommendation_record_id,
            "action_type": self.action_type.value,
            "action_timestamp": self.action_timestamp.isoformat(),
            "actor": self.actor,
            "details": self.details,
            "reason": self.reason
        }


@dataclass
class OutcomeRecord:
    """Record of an outcome.

    Attributes:
        id: Unique record ID
        recommendation_record_id: ID of the recommendation record
        outcome_type: Type of outcome
        outcome_timestamp: When the outcome was measured
        value: Outcome value/measurement
        baseline_value: Value before intervention (for comparison)
        improvement_pct: Percentage improvement (if applicable)
        notes: Additional notes
    """
    id: str
    recommendation_record_id: str
    outcome_type: OutcomeType
    outcome_timestamp: datetime
    value: Any = None
    baseline_value: Any = None
    improvement_pct: float = None
    notes: str = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recommendation_record_id": self.recommendation_record_id,
            "outcome_type": self.outcome_type.value,
            "outcome_timestamp": self.outcome_timestamp.isoformat(),
            "value": self.value,
            "baseline_value": self.baseline_value,
            "improvement_pct": self.improvement_pct,
            "notes": self.notes
        }


@dataclass
class QualityMeasure:
    """A quality measure metric.

    Attributes:
        measure_id: Quality measure ID (e.g., NQF number)
        measure_name: Human-readable name
        numerator: Patients meeting criteria
        denominator: Total eligible patients
        rate: Performance rate (numerator/denominator)
        target_rate: Target/benchmark rate
        period_start: Measurement period start
        period_end: Measurement period end
    """
    measure_id: str
    measure_name: str
    numerator: int
    denominator: int
    rate: float
    target_rate: float = None
    period_start: date = None
    period_end: date = None

    @property
    def meets_target(self) -> bool | None:
        if self.target_rate is None:
            return None
        return self.rate >= self.target_rate

    def to_dict(self) -> dict:
        return {
            "measure_id": self.measure_id,
            "measure_name": self.measure_name,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "rate": round(self.rate * 100, 1),
            "rate_pct": f"{round(self.rate * 100, 1)}%",
            "target_rate": round(self.target_rate * 100, 1) if self.target_rate else None,
            "meets_target": self.meets_target,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None
        }


class OutcomeTracker:
    """Tracks outcomes of CPG recommendations.

    This class provides methods to record recommendations, actions,
    and outcomes, and to compute quality measures and analytics.
    """

    def __init__(self, storage_backend=None):
        """Initialize the outcome tracker.

        Args:
            storage_backend: Optional storage backend. If None, uses in-memory storage.
        """
        self.storage = storage_backend or InMemoryStorage()

    def record_recommendation(self,
                              patient_id: str,
                              cpg_id: str,
                              recommendation_id: str,
                              recommendation_title: str = None,
                              cpg_version: str = "1.0.0",
                              context: dict = None,
                              evidence_grade: str = None) -> RecommendationRecord:
        """Record a recommendation made.

        Args:
            patient_id: Patient identifier
            cpg_id: CPG that generated the recommendation
            recommendation_id: ID of the recommendation
            recommendation_title: Title of the recommendation
            cpg_version: Version of the CPG
            context: Relevant context data
            evidence_grade: Evidence grade

        Returns:
            The created RecommendationRecord
        """
        # Hash patient ID for privacy
        patient_hash = self._hash_patient_id(patient_id)

        record = RecommendationRecord(
            id=self._generate_id("rec"),
            patient_id=patient_hash,
            cpg_id=cpg_id,
            cpg_version=cpg_version,
            recommendation_id=recommendation_id,
            recommendation_title=recommendation_title or recommendation_id,
            timestamp=datetime.utcnow(),
            context=context or {},
            evidence_grade=evidence_grade
        )

        self.storage.save_recommendation(record)
        log.info(f"Recorded recommendation: {cpg_id}/{recommendation_id} for patient {patient_hash[:8]}...")

        return record

    def record_action(self,
                      recommendation_record_id: str,
                      action_type: ActionType | str,
                      actor: str = "unknown",
                      details: dict = None,
                      reason: str = None) -> ActionRecord:
        """Record an action taken on a recommendation.

        Args:
            recommendation_record_id: ID of the recommendation record
            action_type: Type of action taken
            actor: Who took the action
            details: Additional details
            reason: Reason for the action

        Returns:
            The created ActionRecord
        """
        if isinstance(action_type, str):
            action_type = ActionType(action_type)

        record = ActionRecord(
            id=self._generate_id("act"),
            recommendation_record_id=recommendation_record_id,
            action_type=action_type,
            action_timestamp=datetime.utcnow(),
            actor=actor,
            details=details or {},
            reason=reason
        )

        self.storage.save_action(record)
        log.info(f"Recorded action: {action_type.value} for recommendation {recommendation_record_id}")

        return record

    def record_outcome(self,
                       recommendation_record_id: str,
                       outcome_type: OutcomeType | str,
                       value: Any = None,
                       baseline_value: Any = None,
                       notes: str = None) -> OutcomeRecord:
        """Record an outcome.

        Args:
            recommendation_record_id: ID of the recommendation record
            outcome_type: Type of outcome
            value: Outcome value
            baseline_value: Baseline value for comparison
            notes: Additional notes

        Returns:
            The created OutcomeRecord
        """
        if isinstance(outcome_type, str):
            outcome_type = OutcomeType(outcome_type)

        # Calculate improvement percentage if applicable
        improvement_pct = None
        if baseline_value is not None and value is not None:
            if isinstance(baseline_value, (int, float)) and isinstance(value, (int, float)):
                if baseline_value != 0:
                    improvement_pct = ((baseline_value - value) / baseline_value) * 100

        record = OutcomeRecord(
            id=self._generate_id("out"),
            recommendation_record_id=recommendation_record_id,
            outcome_type=outcome_type,
            outcome_timestamp=datetime.utcnow(),
            value=value,
            baseline_value=baseline_value,
            improvement_pct=improvement_pct,
            notes=notes
        )

        self.storage.save_outcome(record)
        log.info(f"Recorded outcome: {outcome_type.value} for recommendation {recommendation_record_id}")

        return record

    def get_acceptance_rate(self, cpg_id: str = None, recommendation_id: str = None) -> dict:
        """Calculate recommendation acceptance rate.

        Args:
            cpg_id: Optional filter by CPG
            recommendation_id: Optional filter by recommendation

        Returns:
            Dictionary with acceptance statistics
        """
        recommendations = self.storage.get_recommendations(cpg_id=cpg_id, recommendation_id=recommendation_id)
        actions = self.storage.get_actions()

        # Match actions to recommendations
        action_by_rec = {}
        for action in actions:
            action_by_rec[action.recommendation_record_id] = action

        total = len(recommendations)
        accepted = 0
        rejected = 0
        deferred = 0
        pending = 0

        for rec in recommendations:
            action = action_by_rec.get(rec.id)
            if action:
                if action.action_type == ActionType.ACCEPTED:
                    accepted += 1
                elif action.action_type == ActionType.REJECTED:
                    rejected += 1
                elif action.action_type == ActionType.DEFERRED:
                    deferred += 1
                else:
                    pending += 1
            else:
                pending += 1

        return {
            "total_recommendations": total,
            "accepted": accepted,
            "rejected": rejected,
            "deferred": deferred,
            "pending": pending,
            "acceptance_rate": accepted / total if total > 0 else 0,
            "rejection_rate": rejected / total if total > 0 else 0
        }

    def get_outcome_summary(self, cpg_id: str = None) -> dict:
        """Get summary of outcomes.

        Args:
            cpg_id: Optional filter by CPG

        Returns:
            Dictionary with outcome statistics
        """
        outcomes = self.storage.get_outcomes()
        recommendations = self.storage.get_recommendations(cpg_id=cpg_id)
        rec_ids = {r.id for r in recommendations}

        # Filter outcomes by CPG if specified
        if cpg_id:
            outcomes = [o for o in outcomes if o.recommendation_record_id in rec_ids]

        positive_outcomes = []
        negative_outcomes = []
        neutral_outcomes = []

        positive_types = {OutcomeType.LAB_IMPROVEMENT, OutcomeType.EVENT_PREVENTED,
                        OutcomeType.HOSPITALIZATION_AVOIDED, OutcomeType.GOAL_MET,
                        OutcomeType.ADHERENCE_GOOD}
        negative_types = {OutcomeType.LAB_WORSENED, OutcomeType.EVENT_OCCURRED,
                        OutcomeType.HOSPITALIZATION_OCCURRED, OutcomeType.GOAL_NOT_MET,
                        OutcomeType.ADHERENCE_POOR, OutcomeType.SIDE_EFFECT}

        for outcome in outcomes:
            if outcome.outcome_type in positive_types:
                positive_outcomes.append(outcome)
            elif outcome.outcome_type in negative_types:
                negative_outcomes.append(outcome)
            else:
                neutral_outcomes.append(outcome)

        # Calculate average improvement
        improvements = [o.improvement_pct for o in outcomes if o.improvement_pct is not None]
        avg_improvement = sum(improvements) / len(improvements) if improvements else None

        return {
            "total_outcomes": len(outcomes),
            "positive_outcomes": len(positive_outcomes),
            "negative_outcomes": len(negative_outcomes),
            "neutral_outcomes": len(neutral_outcomes),
            "positive_rate": len(positive_outcomes) / len(outcomes) if outcomes else 0,
            "average_improvement_pct": avg_improvement
        }

    def compute_quality_measure(self,
                                measure_id: str,
                                measure_name: str,
                                numerator_criteria: callable,
                                denominator_criteria: callable = None,
                                period_start: date = None,
                                period_end: date = None,
                                target_rate: float = None) -> QualityMeasure:
        """Compute a quality measure.

        Args:
            measure_id: Quality measure ID
            measure_name: Human-readable name
            numerator_criteria: Function to determine numerator eligibility
            denominator_criteria: Function to determine denominator eligibility
            period_start: Measurement period start
            period_end: Measurement period end
            target_rate: Target rate for comparison

        Returns:
            QualityMeasure with computed values
        """
        recommendations = self.storage.get_recommendations()
        actions = self.storage.get_actions()
        outcomes = self.storage.get_outcomes()

        # Filter by period if specified
        if period_start:
            recommendations = [r for r in recommendations if r.timestamp.date() >= period_start]
        if period_end:
            recommendations = [r for r in recommendations if r.timestamp.date() <= period_end]

        # Build lookup dicts
        action_by_rec = {a.recommendation_record_id: a for a in actions}
        outcomes_by_rec = {}
        for o in outcomes:
            if o.recommendation_record_id not in outcomes_by_rec:
                outcomes_by_rec[o.recommendation_record_id] = []
            outcomes_by_rec[o.recommendation_record_id].append(o)

        # Apply criteria
        denominator = 0
        numerator = 0

        for rec in recommendations:
            action = action_by_rec.get(rec.id)
            rec_outcomes = outcomes_by_rec.get(rec.id, [])

            context = {
                "recommendation": rec,
                "action": action,
                "outcomes": rec_outcomes
            }

            if denominator_criteria is None or denominator_criteria(context):
                denominator += 1
                if numerator_criteria(context):
                    numerator += 1

        rate = numerator / denominator if denominator > 0 else 0

        return QualityMeasure(
            measure_id=measure_id,
            measure_name=measure_name,
            numerator=numerator,
            denominator=denominator,
            rate=rate,
            target_rate=target_rate,
            period_start=period_start,
            period_end=period_end
        )

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _hash_patient_id(self, patient_id: str) -> str:
        """Hash patient ID for privacy."""
        return hashlib.sha256(patient_id.encode()).hexdigest()


class InMemoryStorage:
    """Simple in-memory storage for development/testing."""

    def __init__(self):
        self.recommendations: list[RecommendationRecord] = []
        self.actions: list[ActionRecord] = []
        self.outcomes: list[OutcomeRecord] = []

    def save_recommendation(self, record: RecommendationRecord):
        self.recommendations.append(record)

    def save_action(self, record: ActionRecord):
        self.actions.append(record)

    def save_outcome(self, record: OutcomeRecord):
        self.outcomes.append(record)

    def get_recommendations(self, cpg_id: str = None, recommendation_id: str = None) -> list[RecommendationRecord]:
        result = self.recommendations
        if cpg_id:
            result = [r for r in result if r.cpg_id == cpg_id]
        if recommendation_id:
            result = [r for r in result if r.recommendation_id == recommendation_id]
        return result

    def get_actions(self) -> list[ActionRecord]:
        return self.actions

    def get_outcomes(self) -> list[OutcomeRecord]:
        return self.outcomes
