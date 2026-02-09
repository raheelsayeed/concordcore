#!/usr/bin/env python3
"""Multi-CPG conflict detection for clinical recommendations.

This module detects and reports conflicts when a patient is evaluated
against multiple Clinical Practice Guidelines. Conflicts may arise from:
- Direct contradictions (one CPG recommends action, another contraindicates)
- Different target values (e.g., different BP goals)
- Drug interactions between recommended medications
- Priority conflicts (which recommendation takes precedence)

Example usage:
    ```python
    from concordcore.core.conflict_detection import ConflictDetector, ConflictType

    detector = ConflictDetector()
    conflicts = detector.detect_conflicts(evaluation_results)

    for conflict in conflicts:
        print(f"Conflict: {conflict.description}")
        print(f"Resolution: {conflict.suggested_resolution}")
    ```
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import logging

log = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts between CPG recommendations."""
    DIRECT_CONTRADICTION = "direct_contradiction"  # One says do X, another says don't do X
    TARGET_VALUE_MISMATCH = "target_value_mismatch"  # Different target values (e.g., LDL < 70 vs < 100)
    DRUG_INTERACTION = "drug_interaction"  # Recommended drugs may interact
    PRIORITY_CONFLICT = "priority_conflict"  # Unclear which recommendation takes precedence
    RESOURCE_CONFLICT = "resource_conflict"  # Competing for same resource (e.g., specialist time)
    TIMING_CONFLICT = "timing_conflict"  # Conflicting timing requirements


class ConflictSeverity(Enum):
    """Severity level of a conflict."""
    LOW = "low"  # Minor conflict, easily resolved
    MEDIUM = "medium"  # Moderate conflict, requires clinical judgment
    HIGH = "high"  # Significant conflict, may affect patient safety
    CRITICAL = "critical"  # Critical conflict, must be resolved before proceeding


@dataclass(slots=True)
class ConflictingRecommendation:
    """A recommendation involved in a conflict.

    Attributes:
        cpg_id: ID of the CPG
        cpg_title: Title of the CPG
        recommendation_id: ID of the recommendation
        recommendation_title: Title of the recommendation
        value: The recommended value or action
        evidence_grade: Evidence grade (e.g., "A", "B", "I", "IIa")
        evidence_level: Level of evidence
    """
    cpg_id: str
    cpg_title: str
    recommendation_id: str
    recommendation_title: str
    value: Any = None
    evidence_grade: str = None
    evidence_level: str = None


@dataclass(slots=True)
class Conflict:
    """A detected conflict between CPG recommendations.

    Attributes:
        conflict_type: Type of conflict
        severity: Severity level
        description: Human-readable description of the conflict
        recommendations: List of conflicting recommendations
        affected_variables: Variable IDs affected by this conflict
        suggested_resolution: Suggested way to resolve the conflict
        resolution_rationale: Explanation of why this resolution is suggested
        requires_clinical_review: Whether a clinician must review this conflict
    """
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    recommendations: list[ConflictingRecommendation]
    affected_variables: list[str] = field(default_factory=list)
    suggested_resolution: str = None
    resolution_rationale: str = None
    requires_clinical_review: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "conflict_type": self.conflict_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "recommendations": [
                {
                    "cpg_id": r.cpg_id,
                    "cpg_title": r.cpg_title,
                    "recommendation_id": r.recommendation_id,
                    "recommendation_title": r.recommendation_title,
                    "value": r.value,
                    "evidence_grade": r.evidence_grade
                }
                for r in self.recommendations
            ],
            "affected_variables": self.affected_variables,
            "suggested_resolution": self.suggested_resolution,
            "resolution_rationale": self.resolution_rationale,
            "requires_clinical_review": self.requires_clinical_review
        }


@dataclass(slots=True)
class ConflictReport:
    """Complete report of conflicts from multi-CPG evaluation.

    Attributes:
        conflicts: List of detected conflicts
        cpgs_evaluated: List of CPG IDs that were evaluated
        total_recommendations: Total number of recommendations across all CPGs
        has_critical_conflicts: Whether any critical conflicts were found
    """
    conflicts: list[Conflict]
    cpgs_evaluated: list[str]
    total_recommendations: int
    has_critical_conflicts: bool = False

    def __post_init__(self):
        self.has_critical_conflicts = any(
            c.severity == ConflictSeverity.CRITICAL for c in self.conflicts
        )

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def high_severity_count(self) -> int:
        return sum(1 for c in self.conflicts if c.severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL])

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "conflict_count": self.conflict_count,
            "high_severity_count": self.high_severity_count,
            "has_critical_conflicts": self.has_critical_conflicts,
            "cpgs_evaluated": self.cpgs_evaluated,
            "total_recommendations": self.total_recommendations,
            "conflicts": [c.to_dict() for c in self.conflicts]
        }


# Known drug interaction pairs (simplified - in production, use a drug interaction database)
KNOWN_DRUG_INTERACTIONS = [
    {"drugs": ["statin", "fibrate"], "severity": "high", "description": "Increased risk of myopathy"},
    {"drugs": ["statin", "niacin"], "severity": "medium", "description": "Increased risk of myopathy"},
    {"drugs": ["ace_inhibitor", "potassium_supplement"], "severity": "high", "description": "Risk of hyperkalemia"},
    {"drugs": ["aspirin", "anticoagulant"], "severity": "high", "description": "Increased bleeding risk"},
    {"drugs": ["metformin", "contrast_dye"], "severity": "high", "description": "Risk of lactic acidosis"},
]

# Known target value conflicts (variable_id -> list of {cpg_pattern, target, direction})
TARGET_VALUE_RULES = {
    "LDL": [
        {"context": "diabetes", "target": 70, "direction": "below"},
        {"context": "high_risk", "target": 70, "direction": "below"},
        {"context": "moderate_risk", "target": 100, "direction": "below"},
        {"context": "low_risk", "target": 130, "direction": "below"},
    ],
    "systolic_bp": [
        {"context": "diabetes", "target": 130, "direction": "below"},
        {"context": "elderly", "target": 150, "direction": "below"},
        {"context": "high_risk", "target": 120, "direction": "below"},
    ],
    "HbA1c": [
        {"context": "diabetes_standard", "target": 7.0, "direction": "below"},
        {"context": "diabetes_elderly", "target": 8.0, "direction": "below"},
        {"context": "diabetes_strict", "target": 6.5, "direction": "below"},
    ],
}


class ConflictDetector:
    """Detects conflicts between multiple CPG recommendations.

    The detector analyzes evaluation results from multiple CPGs and identifies
    potential conflicts that require clinical attention.
    """

    def __init__(self):
        self.drug_interactions = KNOWN_DRUG_INTERACTIONS
        self.target_rules = TARGET_VALUE_RULES

    def detect_conflicts(self, evaluation_results: list[dict]) -> ConflictReport:
        """Detect conflicts across multiple CPG evaluation results.

        Args:
            evaluation_results: List of evaluation result dictionaries,
                each containing cpg_id, recommendations, and assessments

        Returns:
            ConflictReport with all detected conflicts
        """
        conflicts = []
        cpg_ids = []
        total_recs = 0

        # Collect all recommendations
        all_recommendations = []
        for result in evaluation_results:
            cpg_id = result.get('cpg_id', 'unknown')
            cpg_title = result.get('cpg_title', cpg_id)
            cpg_ids.append(cpg_id)

            for rec in result.get('recommendations', []):
                if rec.get('applies', True):
                    total_recs += 1
                    all_recommendations.append({
                        'cpg_id': cpg_id,
                        'cpg_title': cpg_title,
                        'recommendation': rec
                    })

        # Check for direct contradictions
        contradiction_conflicts = self._detect_contradictions(all_recommendations)
        conflicts.extend(contradiction_conflicts)

        # Check for drug interactions
        drug_conflicts = self._detect_drug_interactions(all_recommendations)
        conflicts.extend(drug_conflicts)

        # Check for target value mismatches
        target_conflicts = self._detect_target_mismatches(evaluation_results)
        conflicts.extend(target_conflicts)

        return ConflictReport(
            conflicts=conflicts,
            cpgs_evaluated=cpg_ids,
            total_recommendations=total_recs
        )

    def _detect_contradictions(self, recommendations: list[dict]) -> list[Conflict]:
        """Detect direct contradictions between recommendations.

        Looks for patterns like:
        - "Start medication X" vs "Avoid medication X"
        - "Increase dose" vs "Decrease dose"
        - "Recommend screening" vs "Do not recommend screening"
        """
        conflicts = []

        # Group recommendations by category/action
        action_groups = {}
        for rec_data in recommendations:
            rec = rec_data['recommendation']
            rec_id = rec.get('id', '')
            rec_title = (rec.get('title', '') or '').lower()

            # Categorize by action type
            if 'start' in rec_title or 'initiate' in rec_title or 'recommend' in rec_title:
                action = 'positive'
            elif 'stop' in rec_title or 'avoid' in rec_title or 'do not' in rec_title or 'contraindicated' in rec_title:
                action = 'negative'
            else:
                action = 'neutral'

            # Extract target (medication, procedure, etc.)
            # Simple keyword extraction - could be enhanced with NLP
            target = self._extract_target(rec_title)
            if target:
                key = f"{target}_{action}"
                if key not in action_groups:
                    action_groups[key] = []
                action_groups[key].append(rec_data)

        # Find opposing recommendations for the same target
        targets_seen = set()
        for key, recs in action_groups.items():
            target, action = key.rsplit('_', 1)
            if target in targets_seen:
                continue

            opposite_action = 'negative' if action == 'positive' else 'positive'
            opposite_key = f"{target}_{opposite_action}"

            if opposite_key in action_groups:
                targets_seen.add(target)
                conflicting_recs = recs + action_groups[opposite_key]

                conflict = Conflict(
                    conflict_type=ConflictType.DIRECT_CONTRADICTION,
                    severity=ConflictSeverity.HIGH,
                    description=f"Conflicting recommendations for '{target}': one CPG recommends it, another advises against it",
                    recommendations=[
                        ConflictingRecommendation(
                            cpg_id=r['cpg_id'],
                            cpg_title=r['cpg_title'],
                            recommendation_id=r['recommendation'].get('id', ''),
                            recommendation_title=r['recommendation'].get('title', ''),
                            evidence_grade=r['recommendation'].get('class_of_recommendation')
                        )
                        for r in conflicting_recs
                    ],
                    affected_variables=[target],
                    suggested_resolution="Review patient-specific factors to determine which recommendation applies",
                    resolution_rationale="Direct contradictions require clinical judgment based on patient context",
                    requires_clinical_review=True
                )
                conflicts.append(conflict)

        return conflicts

    def _extract_target(self, text: str) -> str | None:
        """Extract the target of a recommendation (medication, procedure, etc.)."""
        # Common medication keywords
        med_keywords = ['statin', 'aspirin', 'ace inhibitor', 'arb', 'beta blocker',
                       'metformin', 'insulin', 'anticoagulant', 'antiplatelet']

        for keyword in med_keywords:
            if keyword in text:
                return keyword

        # Common procedure keywords
        proc_keywords = ['screening', 'colonoscopy', 'mammogram', 'ct scan', 'mri']
        for keyword in proc_keywords:
            if keyword in text:
                return keyword

        return None

    def _detect_drug_interactions(self, recommendations: list[dict]) -> list[Conflict]:
        """Detect potential drug interactions between recommended medications."""
        conflicts = []

        # Extract all recommended drugs
        recommended_drugs = []
        for rec_data in recommendations:
            rec = rec_data['recommendation']
            rec_title = (rec.get('title', '') or '').lower()

            for interaction in self.drug_interactions:
                for drug in interaction['drugs']:
                    if drug in rec_title:
                        recommended_drugs.append({
                            'drug': drug,
                            'rec_data': rec_data
                        })

        # Check for interactions
        for interaction in self.drug_interactions:
            drugs_in_recs = [d for d in recommended_drugs if d['drug'] in interaction['drugs']]

            if len(set(d['drug'] for d in drugs_in_recs)) >= 2:
                # Found an interaction
                severity = ConflictSeverity.HIGH if interaction['severity'] == 'high' else ConflictSeverity.MEDIUM

                conflict = Conflict(
                    conflict_type=ConflictType.DRUG_INTERACTION,
                    severity=severity,
                    description=f"Potential drug interaction: {interaction['description']}",
                    recommendations=[
                        ConflictingRecommendation(
                            cpg_id=d['rec_data']['cpg_id'],
                            cpg_title=d['rec_data']['cpg_title'],
                            recommendation_id=d['rec_data']['recommendation'].get('id', ''),
                            recommendation_title=d['rec_data']['recommendation'].get('title', ''),
                        )
                        for d in drugs_in_recs
                    ],
                    affected_variables=interaction['drugs'],
                    suggested_resolution="Consult pharmacist or use drug interaction checker",
                    resolution_rationale=interaction['description'],
                    requires_clinical_review=True
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_target_mismatches(self, evaluation_results: list[dict]) -> list[Conflict]:
        """Detect conflicting target values between CPGs."""
        conflicts = []

        # Collect target values from assessments
        targets_by_variable = {}

        for result in evaluation_results:
            cpg_id = result.get('cpg_id', 'unknown')
            cpg_title = result.get('cpg_title', cpg_id)

            for assessment in result.get('assessments', []):
                var_id = assessment.get('id', '')
                value = assessment.get('value')

                if var_id and value is not None:
                    if var_id not in targets_by_variable:
                        targets_by_variable[var_id] = []
                    targets_by_variable[var_id].append({
                        'cpg_id': cpg_id,
                        'cpg_title': cpg_title,
                        'assessment_id': var_id,
                        'value': value
                    })

        # Check for mismatches in target values
        for var_id, targets in targets_by_variable.items():
            if len(targets) > 1:
                # Check if values differ significantly
                values = [t['value'] for t in targets if isinstance(t['value'], (int, float))]
                if len(values) > 1:
                    min_val = min(values)
                    max_val = max(values)

                    # If values differ by more than 20%, flag as potential conflict
                    if min_val > 0 and (max_val - min_val) / min_val > 0.2:
                        conflict = Conflict(
                            conflict_type=ConflictType.TARGET_VALUE_MISMATCH,
                            severity=ConflictSeverity.MEDIUM,
                            description=f"Different target values for '{var_id}': ranging from {min_val} to {max_val}",
                            recommendations=[
                                ConflictingRecommendation(
                                    cpg_id=t['cpg_id'],
                                    cpg_title=t['cpg_title'],
                                    recommendation_id=t['assessment_id'],
                                    recommendation_title=f"Target: {t['value']}",
                                    value=t['value']
                                )
                                for t in targets
                            ],
                            affected_variables=[var_id],
                            suggested_resolution="Use the most conservative target unless patient-specific factors indicate otherwise",
                            resolution_rationale="When target values conflict, prioritize by evidence strength and patient risk profile",
                            requires_clinical_review=False
                        )
                        conflicts.append(conflict)

        return conflicts

    def resolve_conflict(self, conflict: Conflict, strategy: str = "evidence_based") -> dict:
        """Suggest a resolution for a conflict.

        Args:
            conflict: The conflict to resolve
            strategy: Resolution strategy - "evidence_based", "conservative", "patient_specific"

        Returns:
            Dictionary with resolution recommendation
        """
        if strategy == "evidence_based":
            # Prefer recommendation with strongest evidence
            best_rec = max(
                conflict.recommendations,
                key=lambda r: self._evidence_score(r.evidence_grade)
            )
            return {
                "strategy": "evidence_based",
                "selected_recommendation": best_rec.recommendation_id,
                "selected_cpg": best_rec.cpg_id,
                "rationale": f"Selected based on evidence grade: {best_rec.evidence_grade}"
            }

        elif strategy == "conservative":
            # Choose the most conservative option
            return {
                "strategy": "conservative",
                "rationale": "Recommend clinical review to determine most conservative approach",
                "requires_review": True
            }

        else:
            return {
                "strategy": "patient_specific",
                "rationale": "Resolution requires patient-specific clinical judgment",
                "requires_review": True
            }

    def _evidence_score(self, grade: str | None) -> int:
        """Convert evidence grade to numeric score for comparison."""
        if not grade:
            return 0

        grade = str(grade).upper()
        scores = {
            'A': 100, 'I': 100,
            'B': 80, 'IIA': 80,
            'C': 60, 'IIB': 60,
            'D': 40, 'III': 40,
        }
        return scores.get(grade, 50)
