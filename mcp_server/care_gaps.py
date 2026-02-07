#!/usr/bin/env python3
"""Care gap detection for Concord MCP server.

This module identifies preventive care gaps by evaluating patient data
against all applicable CPGs and finding:
1. Missing screenings - eligible but not performed
2. Overdue tests - last performed beyond recommended interval
3. Unmet recommendations - CPG recommends action not yet taken

Example usage:
    from mcp_server.care_gaps import CareGapDetector

    detector = CareGapDetector(cpgs=[cpg1, cpg2, ...])
    gaps = detector.detect(health_context)

    for gap in gaps:
        print(f"{gap.priority}: {gap.title} - {gap.reason}")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg import CPG
from core.concord import Concord
from core.healthcontext import HealthContext

log = logging.getLogger(__name__)


class GapPriority(Enum):
    """Priority level for care gaps."""
    CRITICAL = "critical"      # Immediate action needed
    HIGH = "high"              # Action needed soon
    MODERATE = "moderate"      # Should address
    LOW = "low"                # Consider addressing
    INFORMATIONAL = "info"     # For awareness


class GapType(Enum):
    """Type of care gap."""
    MISSING_SCREENING = "missing_screening"
    OVERDUE_SCREENING = "overdue_screening"
    UNMET_RECOMMENDATION = "unmet_recommendation"
    MISSING_DATA = "missing_data"
    ELIGIBLE_NOT_ENROLLED = "eligible_not_enrolled"


@dataclass
class CareGap:
    """Represents a single care gap.

    Attributes:
        id: Unique identifier for this gap
        title: Human-readable title
        description: Detailed description of the gap
        gap_type: Type of care gap
        priority: Priority level
        cpg_id: Source CPG identifier
        cpg_title: Source CPG title
        recommendation_id: Related recommendation ID if applicable
        uspstf_grade: USPSTF grade if applicable
        last_performed: Date last performed (for overdue gaps)
        due_date: When the action is due
        reason: Why this is a gap
        suggested_action: What to do about it
        evidence_summary: Brief evidence summary
    """
    id: str
    title: str
    description: str
    gap_type: GapType
    priority: GapPriority
    cpg_id: str
    cpg_title: str
    recommendation_id: str | None = None
    uspstf_grade: str | None = None
    last_performed: datetime | None = None
    due_date: datetime | None = None
    reason: str = ""
    suggested_action: str = ""
    evidence_summary: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "gap_type": self.gap_type.value,
            "priority": self.priority.value,
            "cpg_id": self.cpg_id,
            "cpg_title": self.cpg_title,
            "recommendation_id": self.recommendation_id,
            "uspstf_grade": self.uspstf_grade,
            "last_performed": self.last_performed.isoformat() if self.last_performed else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "evidence_summary": self.evidence_summary,
        }


@dataclass
class CareGapReport:
    """Report of all detected care gaps.

    Attributes:
        patient_id: Patient identifier
        evaluation_date: When gaps were evaluated
        total_cpgs_evaluated: Number of CPGs evaluated
        gaps: List of detected care gaps
        summary: Summary statistics
    """
    patient_id: str
    evaluation_date: datetime
    total_cpgs_evaluated: int
    gaps: list[CareGap]
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "patient_id": self.patient_id,
            "evaluation_date": self.evaluation_date.isoformat(),
            "total_cpgs_evaluated": self.total_cpgs_evaluated,
            "total_gaps": len(self.gaps),
            "gaps_by_priority": self.summary.get("by_priority", {}),
            "gaps_by_type": self.summary.get("by_type", {}),
            "gaps": [g.to_dict() for g in self.gaps],
        }


class CareGapDetector:
    """Detects care gaps by evaluating patient against multiple CPGs.

    This class evaluates a patient's health context against all provided
    CPGs and identifies gaps in preventive care.

    Example:
        ```python
        detector = CareGapDetector(cpgs=all_cpgs)
        report = detector.detect(
            health_context=patient_context,
            patient_id="patient123"
        )

        for gap in report.gaps:
            print(f"{gap.priority.value}: {gap.title}")
        ```
    """

    # Screening intervals (in days) for common screenings
    SCREENING_INTERVALS = {
        "colorectal_cancer": 365 * 10,      # 10 years for colonoscopy
        "cervical_cancer": 365 * 3,          # 3 years for pap
        "breast_cancer": 365 * 2,            # 2 years for mammogram
        "diabetes": 365 * 3,                 # 3 years
        "hypertension": 365,                 # Annual
        "cholesterol": 365 * 5,              # 5 years
        "hiv": 365,                          # Annual for high risk
        "hepatitis_c": None,                 # One-time for most
        "hepatitis_b": None,                 # Based on risk
        "depression": 365,                   # Annual
    }

    def __init__(self, cpgs: list[CPG]):
        """Initialize care gap detector.

        Args:
            cpgs: List of CPGs to evaluate against
        """
        self.cpgs = cpgs

    def detect(
        self,
        health_context: HealthContext,
        patient_id: str = "unknown",
        include_ineligible: bool = False
    ) -> CareGapReport:
        """Detect care gaps for a patient.

        Args:
            health_context: Patient health data
            patient_id: Patient identifier
            include_ineligible: Whether to include gaps for CPGs patient isn't eligible for

        Returns:
            CareGapReport with all detected gaps
        """
        gaps: list[CareGap] = []
        cpgs_evaluated = 0

        for cpg in self.cpgs:
            try:
                cpg_gaps = self._evaluate_cpg(cpg, health_context, include_ineligible)
                gaps.extend(cpg_gaps)
                cpgs_evaluated += 1
            except Exception as e:
                log.warning(f"Error evaluating CPG {cpg.identifier}: {e}")

        # Sort by priority
        priority_order = {
            GapPriority.CRITICAL: 0,
            GapPriority.HIGH: 1,
            GapPriority.MODERATE: 2,
            GapPriority.LOW: 3,
            GapPriority.INFORMATIONAL: 4,
        }
        gaps.sort(key=lambda g: priority_order.get(g.priority, 99))

        # Build summary
        summary = self._build_summary(gaps)

        return CareGapReport(
            patient_id=patient_id,
            evaluation_date=datetime.now(),
            total_cpgs_evaluated=cpgs_evaluated,
            gaps=gaps,
            summary=summary,
        )

    def _evaluate_cpg(
        self,
        cpg: CPG,
        health_context: HealthContext,
        include_ineligible: bool
    ) -> list[CareGap]:
        """Evaluate a single CPG for care gaps.

        Args:
            cpg: CPG to evaluate
            health_context: Patient health data
            include_ineligible: Include gaps even if patient isn't eligible

        Returns:
            List of care gaps from this CPG
        """
        gaps = []

        try:
            concord = Concord(cpg, health_context)
            result = concord.evaluate(ignore_attestations=True)

            # Check eligibility
            is_eligible = result.is_eligible
            if not is_eligible and not include_ineligible:
                return gaps

            # Find recommendations that apply but may not be met
            if result.recommendations:
                for rec in result.recommendations.recommendations:
                    if rec.applies:
                        gap = self._recommendation_to_gap(cpg, rec)
                        if gap:
                            gaps.append(gap)

            # Check for missing required data
            if result.sufficiency:
                missing_vars = self._get_missing_required(cpg, health_context)
                for var_id in missing_vars[:3]:  # Limit to top 3
                    gaps.append(CareGap(
                        id=f"{cpg.identifier}_missing_{var_id}",
                        title=f"Missing data: {var_id}",
                        description=f"Data for '{var_id}' is required for complete {cpg.title} evaluation",
                        gap_type=GapType.MISSING_DATA,
                        priority=GapPriority.LOW,
                        cpg_id=cpg.identifier,
                        cpg_title=cpg.title,
                        reason=f"Required variable '{var_id}' has no value",
                        suggested_action=f"Collect {var_id} data",
                    ))

        except Exception as e:
            log.debug(f"CPG {cpg.identifier} evaluation error: {e}")

        return gaps

    def _recommendation_to_gap(self, cpg: CPG, rec) -> CareGap | None:
        """Convert an applied recommendation to a care gap.

        Args:
            cpg: Source CPG
            rec: EvaluatedRecommendation

        Returns:
            CareGap if this represents a gap, None otherwise
        """
        rec_var = rec.recommendation

        # Get USPSTF grade
        uspstf_grade = None
        if hasattr(rec_var, 'uspstf_grade') and rec_var.uspstf_grade:
            uspstf_grade = rec_var.uspstf_grade.value if hasattr(rec_var.uspstf_grade, 'value') else str(rec_var.uspstf_grade)

        # Determine priority based on grade
        priority = self._grade_to_priority(uspstf_grade)

        # Get recommendation type to determine gap type
        gap_type = GapType.UNMET_RECOMMENDATION
        rec_type = getattr(rec_var, 'type', None)
        if rec_type:
            type_str = rec_type.value if hasattr(rec_type, 'value') else str(rec_type)
            if 'screening' in type_str.lower() or 'evaluation' in type_str.lower():
                gap_type = GapType.MISSING_SCREENING

        title = rec_var.title or rec_var.id
        description = rec.narrative or ""

        # Build suggested action
        suggested_action = "Discuss with healthcare provider"
        if uspstf_grade in ['A', 'B']:
            suggested_action = "Strongly recommended - schedule appointment"
        elif uspstf_grade == 'C':
            suggested_action = "Consider based on individual circumstances"

        return CareGap(
            id=f"{cpg.identifier}_{rec_var.id}",
            title=title,
            description=description[:500] if description else "",
            gap_type=gap_type,
            priority=priority,
            cpg_id=cpg.identifier,
            cpg_title=cpg.title,
            recommendation_id=rec_var.id,
            uspstf_grade=uspstf_grade,
            reason=f"Recommendation applies based on patient data",
            suggested_action=suggested_action,
            evidence_summary=f"USPSTF Grade {uspstf_grade}" if uspstf_grade else "",
        )

    def _grade_to_priority(self, grade: str | None) -> GapPriority:
        """Convert USPSTF grade to priority level.

        Args:
            grade: USPSTF grade (A, B, C, D, I)

        Returns:
            Corresponding priority level
        """
        if grade == 'A':
            return GapPriority.CRITICAL
        elif grade == 'B':
            return GapPriority.HIGH
        elif grade == 'C':
            return GapPriority.MODERATE
        elif grade == 'D':
            return GapPriority.INFORMATIONAL  # D = recommend against
        else:
            return GapPriority.LOW

    def _get_missing_required(self, cpg: CPG, health_context: HealthContext) -> list[str]:
        """Get list of missing required variables.

        Args:
            cpg: CPG to check
            health_context: Patient health data

        Returns:
            List of missing required variable IDs
        """
        missing = []
        existing_ids = {r.id for r in health_context.records}

        for var in (cpg.variables or []):
            if var.required and var.id not in existing_ids:
                missing.append(var.id)

        return missing

    def _build_summary(self, gaps: list[CareGap]) -> dict:
        """Build summary statistics for gaps.

        Args:
            gaps: List of care gaps

        Returns:
            Summary dictionary
        """
        by_priority = {}
        by_type = {}

        for gap in gaps:
            # Count by priority
            p = gap.priority.value
            by_priority[p] = by_priority.get(p, 0) + 1

            # Count by type
            t = gap.gap_type.value
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "by_priority": by_priority,
            "by_type": by_type,
        }


def detect_care_gaps(
    cpgs: list[CPG],
    health_context: HealthContext,
    patient_id: str = "unknown"
) -> CareGapReport:
    """Convenience function to detect care gaps.

    Args:
        cpgs: List of CPGs to evaluate
        health_context: Patient health data
        patient_id: Patient identifier

    Returns:
        CareGapReport with all detected gaps
    """
    detector = CareGapDetector(cpgs)
    return detector.detect(health_context, patient_id)
