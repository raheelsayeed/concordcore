#!/usr/bin/env python3
"""Preventive care gap analysis for patient populations.

This module identifies gaps in preventive care by evaluating patients
against all applicable Clinical Practice Guidelines and identifying
screenings and preventive measures that are due or overdue.

Example usage:
    ```python
    from core.gap_analysis import GapAnalyzer, CareGap

    analyzer = GapAnalyzer(cpgs=all_cpgs)
    gaps = analyzer.analyze(healthcontext)

    for gap in gaps.open_gaps:
        print(f"Due: {gap.title} - Priority: {gap.priority}")
    ```
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any
import logging

from .cpg import CPG
from .concord import Concord
from .healthcontext import HealthContext

log = logging.getLogger(__name__)


class GapPriority(Enum):
    """Priority level for care gaps."""
    CRITICAL = "critical"  # Significantly overdue, high-risk condition
    HIGH = "high"  # Overdue or high-value screening
    MEDIUM = "medium"  # Coming due soon
    LOW = "low"  # Optional or low-risk screening


class GapStatus(Enum):
    """Status of a care gap."""
    OPEN = "open"  # Screening/intervention is due
    OVERDUE = "overdue"  # Past due date
    SCHEDULED = "scheduled"  # Appointment scheduled
    COMPLETED = "completed"  # Recently completed
    NOT_APPLICABLE = "not_applicable"  # Patient not eligible
    DECLINED = "declined"  # Patient declined


@dataclass(slots=True)
class CareGap:
    """A gap in preventive care.

    Attributes:
        gap_id: Unique identifier for this gap
        cpg_id: ID of the CPG that defines this screening/intervention
        cpg_title: Title of the CPG
        title: Human-readable title of the gap
        description: Detailed description
        category: Category (screening, vaccination, counseling, etc.)
        priority: Priority level
        status: Current status
        due_date: When the screening is due
        last_completed: When last completed (if ever)
        recommended_interval_days: Recommended interval between screenings
        evidence_grade: Evidence grade for this recommendation
        age_range: Age range this applies to (min, max)
        gender_specific: Gender this applies to (None = all)
    """
    gap_id: str
    cpg_id: str
    cpg_title: str
    title: str
    description: str = ""
    category: str = "screening"
    priority: GapPriority = GapPriority.MEDIUM
    status: GapStatus = GapStatus.OPEN
    due_date: date = None
    last_completed: date = None
    recommended_interval_days: int = 365
    evidence_grade: str = None
    age_range: tuple[int, int] = None
    gender_specific: str = None

    def is_overdue(self) -> bool:
        """Check if this gap is overdue."""
        if self.due_date and date.today() > self.due_date:
            return True
        return False

    def days_overdue(self) -> int | None:
        """Get number of days overdue, or None if not overdue."""
        if self.due_date and date.today() > self.due_date:
            return (date.today() - self.due_date).days
        return None

    def days_until_due(self) -> int | None:
        """Get number of days until due, or None if already overdue."""
        if self.due_date and date.today() <= self.due_date:
            return (self.due_date - date.today()).days
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "gap_id": self.gap_id,
            "cpg_id": self.cpg_id,
            "cpg_title": self.cpg_title,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority.value,
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "last_completed": self.last_completed.isoformat() if self.last_completed else None,
            "is_overdue": self.is_overdue(),
            "days_overdue": self.days_overdue(),
            "days_until_due": self.days_until_due(),
            "evidence_grade": self.evidence_grade,
            "age_range": list(self.age_range) if self.age_range else None,
            "gender_specific": self.gender_specific
        }


@dataclass(slots=True)
class GapAnalysisReport:
    """Complete gap analysis report for a patient.

    Attributes:
        patient_id: Patient identifier (if available)
        analysis_date: When the analysis was performed
        open_gaps: List of open care gaps
        completed_gaps: List of recently completed items
        not_applicable_gaps: List of items patient is not eligible for
        declined_gaps: List of items patient declined
        cpgs_evaluated: Number of CPGs evaluated
        summary: Summary statistics
    """
    patient_id: str = None
    analysis_date: date = field(default_factory=date.today)
    open_gaps: list[CareGap] = field(default_factory=list)
    completed_gaps: list[CareGap] = field(default_factory=list)
    not_applicable_gaps: list[CareGap] = field(default_factory=list)
    declined_gaps: list[CareGap] = field(default_factory=list)
    cpgs_evaluated: int = 0
    summary: dict = field(default_factory=dict)

    def __post_init__(self):
        self._compute_summary()

    def _compute_summary(self):
        """Compute summary statistics."""
        overdue = [g for g in self.open_gaps if g.is_overdue()]
        self.summary = {
            "total_open_gaps": len(self.open_gaps),
            "overdue_count": len(overdue),
            "critical_count": len([g for g in self.open_gaps if g.priority == GapPriority.CRITICAL]),
            "high_priority_count": len([g for g in self.open_gaps if g.priority == GapPriority.HIGH]),
            "completed_count": len(self.completed_gaps),
            "cpgs_evaluated": self.cpgs_evaluated
        }

    @property
    def has_overdue_gaps(self) -> bool:
        return any(g.is_overdue() for g in self.open_gaps)

    @property
    def has_critical_gaps(self) -> bool:
        return any(g.priority == GapPriority.CRITICAL for g in self.open_gaps)

    def get_gaps_by_priority(self) -> dict[str, list[CareGap]]:
        """Get open gaps grouped by priority."""
        result = {p.value: [] for p in GapPriority}
        for gap in self.open_gaps:
            result[gap.priority.value].append(gap)
        return result

    def get_gaps_by_category(self) -> dict[str, list[CareGap]]:
        """Get open gaps grouped by category."""
        result = {}
        for gap in self.open_gaps:
            if gap.category not in result:
                result[gap.category] = []
            result[gap.category].append(gap)
        return result

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "patient_id": self.patient_id,
            "analysis_date": self.analysis_date.isoformat(),
            "summary": self.summary,
            "open_gaps": [g.to_dict() for g in self.open_gaps],
            "completed_gaps": [g.to_dict() for g in self.completed_gaps],
            "not_applicable_count": len(self.not_applicable_gaps),
            "declined_count": len(self.declined_gaps)
        }


# Preventive care definitions with intervals and age/gender criteria
PREVENTIVE_CARE_CATALOG = [
    {
        "id": "colorectal_cancer_screening",
        "title": "Colorectal Cancer Screening",
        "category": "cancer_screening",
        "cpg_pattern": ["colorectal", "colon"],
        "age_range": (45, 75),
        "interval_years": 10,  # For colonoscopy
        "evidence_grade": "A",
        "priority_base": GapPriority.HIGH
    },
    {
        "id": "breast_cancer_screening",
        "title": "Breast Cancer Screening (Mammogram)",
        "category": "cancer_screening",
        "cpg_pattern": ["breast", "mammogram"],
        "age_range": (50, 74),
        "gender": "female",
        "interval_years": 2,
        "evidence_grade": "B",
        "priority_base": GapPriority.HIGH
    },
    {
        "id": "lung_cancer_screening",
        "title": "Lung Cancer Screening",
        "category": "cancer_screening",
        "cpg_pattern": ["lung"],
        "age_range": (50, 80),
        "interval_years": 1,
        "evidence_grade": "B",
        "priority_base": GapPriority.MEDIUM,
        "conditions": ["smoking_history"]
    },
    {
        "id": "cervical_cancer_screening",
        "title": "Cervical Cancer Screening (Pap/HPV)",
        "category": "cancer_screening",
        "cpg_pattern": ["cervical", "pap"],
        "age_range": (21, 65),
        "gender": "female",
        "interval_years": 3,
        "evidence_grade": "A",
        "priority_base": GapPriority.HIGH
    },
    {
        "id": "diabetes_screening",
        "title": "Type 2 Diabetes Screening",
        "category": "metabolic",
        "cpg_pattern": ["diabetes_screening", "prediabetes"],
        "age_range": (35, 70),
        "interval_years": 3,
        "evidence_grade": "B",
        "priority_base": GapPriority.MEDIUM
    },
    {
        "id": "hypertension_screening",
        "title": "Blood Pressure Screening",
        "category": "cardiovascular",
        "cpg_pattern": ["hypertension", "blood_pressure"],
        "age_range": (18, 999),
        "interval_years": 1,
        "evidence_grade": "A",
        "priority_base": GapPriority.HIGH
    },
    {
        "id": "cholesterol_screening",
        "title": "Lipid Screening",
        "category": "cardiovascular",
        "cpg_pattern": ["cholesterol", "lipid", "statin"],
        "age_range": (40, 75),
        "interval_years": 5,
        "evidence_grade": "B",
        "priority_base": GapPriority.MEDIUM
    },
    {
        "id": "hiv_screening",
        "title": "HIV Screening",
        "category": "infectious_disease",
        "cpg_pattern": ["hiv"],
        "age_range": (15, 65),
        "interval_years": 5,  # At least once; more often if high risk
        "evidence_grade": "A",
        "priority_base": GapPriority.MEDIUM
    },
    {
        "id": "hepatitis_c_screening",
        "title": "Hepatitis C Screening",
        "category": "infectious_disease",
        "cpg_pattern": ["hepatitis_c", "hcv"],
        "age_range": (18, 79),
        "interval_years": 999,  # One-time for most
        "evidence_grade": "B",
        "priority_base": GapPriority.MEDIUM
    },
    {
        "id": "depression_screening",
        "title": "Depression Screening",
        "category": "behavioral_health",
        "cpg_pattern": ["depression"],
        "age_range": (12, 999),
        "interval_years": 1,
        "evidence_grade": "B",
        "priority_base": GapPriority.MEDIUM
    },
]


class GapAnalyzer:
    """Analyzes patient health data to identify preventive care gaps.

    The analyzer evaluates a patient against multiple CPGs and identifies
    screenings and preventive measures that are due or overdue.
    """

    def __init__(self, cpgs: list[CPG] = None, catalog: list[dict] = None):
        """Initialize the gap analyzer.

        Args:
            cpgs: List of CPGs to evaluate against
            catalog: Preventive care catalog (defaults to built-in)
        """
        self.cpgs = cpgs or []
        self.catalog = catalog or PREVENTIVE_CARE_CATALOG

    def analyze(self, healthcontext: HealthContext, patient_id: str = None) -> GapAnalysisReport:
        """Analyze a patient's health context for care gaps.

        Args:
            healthcontext: Patient health context
            patient_id: Optional patient identifier

        Returns:
            GapAnalysisReport with identified gaps
        """
        open_gaps = []
        completed_gaps = []
        not_applicable_gaps = []

        # Get patient demographics
        age = self._get_patient_age(healthcontext)
        gender = self._get_patient_gender(healthcontext)

        log.info(f"Analyzing gaps for patient age={age}, gender={gender}")

        # Check each catalog item
        for item in self.catalog:
            gap = self._evaluate_catalog_item(item, healthcontext, age, gender)
            if gap:
                if gap.status == GapStatus.OPEN or gap.status == GapStatus.OVERDUE:
                    open_gaps.append(gap)
                elif gap.status == GapStatus.COMPLETED:
                    completed_gaps.append(gap)
                elif gap.status == GapStatus.NOT_APPLICABLE:
                    not_applicable_gaps.append(gap)

        # Also evaluate actual CPGs
        for cpg in self.cpgs:
            cpg_gaps = self._evaluate_cpg(cpg, healthcontext, age, gender)
            for gap in cpg_gaps:
                # Avoid duplicates
                if not any(g.gap_id == gap.gap_id for g in open_gaps + completed_gaps):
                    if gap.status == GapStatus.OPEN or gap.status == GapStatus.OVERDUE:
                        open_gaps.append(gap)
                    elif gap.status == GapStatus.COMPLETED:
                        completed_gaps.append(gap)

        # Sort open gaps by priority
        priority_order = {GapPriority.CRITICAL: 0, GapPriority.HIGH: 1, GapPriority.MEDIUM: 2, GapPriority.LOW: 3}
        open_gaps.sort(key=lambda g: (priority_order.get(g.priority, 99), g.due_date or date.max))

        return GapAnalysisReport(
            patient_id=patient_id,
            open_gaps=open_gaps,
            completed_gaps=completed_gaps,
            not_applicable_gaps=not_applicable_gaps,
            cpgs_evaluated=len(self.cpgs)
        )

    def _get_patient_age(self, healthcontext: HealthContext) -> int | None:
        """Extract patient age from health context."""
        for record in healthcontext.records:
            if record.id.lower() == 'age':
                if record.value:
                    return int(record.value.value)
        return None

    def _get_patient_gender(self, healthcontext: HealthContext) -> str | None:
        """Extract patient gender from health context."""
        for record in healthcontext.records:
            if record.id.lower() == 'gender':
                if record.value:
                    val = str(record.value.value)
                    # Handle SNOMED codes
                    if '248153007' in val:
                        return 'male'
                    elif '248152002' in val:
                        return 'female'
                    return val.lower()
        return None

    def _evaluate_catalog_item(self, item: dict, healthcontext: HealthContext,
                                age: int | None, gender: str | None) -> CareGap | None:
        """Evaluate a catalog item against patient context."""

        # Check age eligibility
        age_range = item.get('age_range', (0, 999))
        if age is not None:
            if age < age_range[0] or age > age_range[1]:
                return CareGap(
                    gap_id=item['id'],
                    cpg_id=item['id'],
                    cpg_title=item['title'],
                    title=item['title'],
                    category=item.get('category', 'screening'),
                    status=GapStatus.NOT_APPLICABLE,
                    age_range=age_range
                )

        # Check gender eligibility
        item_gender = item.get('gender')
        if item_gender and gender and item_gender != gender:
            return CareGap(
                gap_id=item['id'],
                cpg_id=item['id'],
                cpg_title=item['title'],
                title=item['title'],
                category=item.get('category', 'screening'),
                status=GapStatus.NOT_APPLICABLE,
                gender_specific=item_gender
            )

        # Check if screening was completed
        last_completed = self._find_last_screening(item, healthcontext)

        # Calculate due date
        interval_days = item.get('interval_years', 1) * 365
        if last_completed:
            due_date = last_completed + timedelta(days=interval_days)
            if date.today() < due_date:
                # Not yet due - completed
                return CareGap(
                    gap_id=item['id'],
                    cpg_id=item['id'],
                    cpg_title=item['title'],
                    title=item['title'],
                    category=item.get('category', 'screening'),
                    status=GapStatus.COMPLETED,
                    last_completed=last_completed,
                    due_date=due_date,
                    recommended_interval_days=interval_days,
                    evidence_grade=item.get('evidence_grade'),
                    age_range=age_range
                )
        else:
            due_date = date.today()  # Due now if never done

        # Determine priority
        priority = item.get('priority_base', GapPriority.MEDIUM)
        if due_date and date.today() > due_date:
            # Overdue - escalate priority
            days_late = (date.today() - due_date).days
            if days_late > 365:
                priority = GapPriority.CRITICAL
            elif days_late > 180:
                priority = GapPriority.HIGH

        return CareGap(
            gap_id=item['id'],
            cpg_id=item['id'],
            cpg_title=item['title'],
            title=item['title'],
            description=f"Recommended every {item.get('interval_years', 1)} year(s)",
            category=item.get('category', 'screening'),
            priority=priority,
            status=GapStatus.OVERDUE if (due_date and date.today() > due_date) else GapStatus.OPEN,
            due_date=due_date,
            last_completed=last_completed,
            recommended_interval_days=interval_days,
            evidence_grade=item.get('evidence_grade'),
            age_range=age_range,
            gender_specific=item_gender
        )

    def _find_last_screening(self, item: dict, healthcontext: HealthContext) -> date | None:
        """Find the date of the last screening for this item."""
        patterns = item.get('cpg_pattern', [])

        for record in healthcontext.records:
            record_id = record.id.lower()
            for pattern in patterns:
                if pattern in record_id:
                    if record.value and hasattr(record.value, 'date') and record.value.date:
                        return record.value.date
        return None

    def _evaluate_cpg(self, cpg: CPG, healthcontext: HealthContext,
                      age: int | None, gender: str | None) -> list[CareGap]:
        """Evaluate a CPG against patient context."""
        gaps = []

        try:
            concord = Concord(cpg=cpg, healthcontext=healthcontext)

            # Check eligibility
            if cpg.eligibility_variables:
                elig_result = concord.eligibility()
                if not elig_result.is_eligible:
                    return []  # Not eligible for this CPG

            # Check for recommendations that apply
            pipeline = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

            if pipeline.recommendations:
                for rec in (pipeline.recommendations.applied or []):
                    if rec.applies:
                        gap = CareGap(
                            gap_id=f"{cpg.identifier}_{rec.recommendation.id}",
                            cpg_id=cpg.identifier,
                            cpg_title=cpg.title,
                            title=rec.recommendation.title,
                            description=rec.narrative or "",
                            category="recommendation",
                            priority=self._get_recommendation_priority(rec.recommendation),
                            status=GapStatus.OPEN,
                            evidence_grade=str(rec.recommendation.class_of_recommendation) if rec.recommendation.class_of_recommendation else None
                        )
                        gaps.append(gap)

        except Exception as e:
            log.warning(f"Error evaluating CPG {cpg.identifier}: {e}")

        return gaps

    def _get_recommendation_priority(self, recommendation) -> GapPriority:
        """Determine priority from recommendation evidence grade."""
        grade = recommendation.class_of_recommendation
        if grade:
            grade_str = str(grade).upper()
            if grade_str in ['A', 'I']:
                return GapPriority.HIGH
            elif grade_str in ['B', 'IIA']:
                return GapPriority.MEDIUM

        return GapPriority.MEDIUM
