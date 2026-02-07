#!/usr/bin/env python3
"""Multi-CPG evaluation service."""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.cpg import CPG
from core.concord import Concord, PipelineResult
from core.healthcontext import HealthContext
from core.conflict_detection import ConflictDetector, ConflictReport
from primitives import Persona

from .cpg_loader import get_cpg_loader


@dataclass
class CPGEvaluationResult:
    """Result of evaluating a single CPG."""

    cpg_id: str
    cpg_title: str
    cpg_publisher: str
    is_eligible: bool | None
    is_executable: bool | None
    pipeline_result: PipelineResult | None
    applied_recommendations: list[Any]
    all_recommendations: list[Any]
    assessments: list[Any]
    error: str | None = None
    elapsed_ms: float = 0.0


@dataclass
class EvaluationSummary:
    """Summary of multi-CPG evaluation results."""

    patient_id: str
    patient_name: str
    total_cpgs: int
    eligible_cpgs: int
    executable_cpgs: int
    total_recommendations: int
    applied_recommendations: int
    conflicts: ConflictReport | None
    evaluations: dict[str, CPGEvaluationResult] = field(default_factory=dict)
    total_elapsed_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return self.conflicts is not None and len(self.conflicts.conflicts) > 0

    @property
    def critical_conflicts(self) -> list:
        """Get critical severity conflicts."""
        if not self.conflicts:
            return []
        return [c for c in self.conflicts.conflicts if c.severity.value == "CRITICAL"]

    @property
    def high_priority_recommendations(self) -> list:
        """Get recommendations with high evidence grades."""
        high_priority = []
        for eval_result in self.evaluations.values():
            for rec in eval_result.applied_recommendations:
                # Check for high-grade evidence
                grade = getattr(rec.recommendation, 'class_of_recommendation', None)
                uspstf = getattr(rec.recommendation, 'uspstf_grade', None)
                if grade and grade.value == 'I':
                    high_priority.append((eval_result.cpg_id, rec))
                elif uspstf and uspstf.value in ['A', 'B']:
                    high_priority.append((eval_result.cpg_id, rec))
        return high_priority


class MultiCPGService:
    """Service for evaluating multiple CPGs against patient data."""

    def __init__(self, detect_conflicts: bool = True, max_workers: int = 4):
        """Initialize the service.

        Args:
            detect_conflicts: Whether to run conflict detection
            max_workers: Maximum number of parallel workers
        """
        self.detect_conflicts = detect_conflicts
        self.max_workers = max_workers
        self.loader = get_cpg_loader()
        self.conflict_detector = ConflictDetector() if detect_conflicts else None

    def evaluate_single_cpg(
        self,
        cpg: CPG,
        health_context: HealthContext,
        persona: Persona = Persona.patient
    ) -> CPGEvaluationResult:
        """Evaluate a single CPG against patient data.

        Args:
            cpg: The CPG to evaluate
            health_context: Patient health data
            persona: Persona for rendering narratives

        Returns:
            CPGEvaluationResult with evaluation details
        """
        start_time = time.time()

        try:
            concord = Concord(cpg=cpg, healthcontext=health_context)
            result = concord.evaluate(
                skip_eligibility=False,
                ignore_attestations=True
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Extract assessments from context.evaluation_list
            assessments = []
            if result.assessment and hasattr(result.assessment, 'context'):
                if hasattr(result.assessment.context, 'evaluation_list'):
                    assessments = list(result.assessment.context.evaluation_list or [])

            # Extract all recommendations from recommendations.recommendations
            all_recs = []
            if result.recommendations:
                if hasattr(result.recommendations, 'recommendations'):
                    all_recs = list(result.recommendations.recommendations or [])

            # Get applied recommendations
            applied_recs = []
            if result.recommendations:
                if hasattr(result.recommendations, 'applied'):
                    applied_recs = list(result.recommendations.applied or [])

            return CPGEvaluationResult(
                cpg_id=cpg.identifier,
                cpg_title=cpg.title,
                cpg_publisher=cpg.publisher,
                is_eligible=result.is_eligible,
                is_executable=result.is_executable,
                pipeline_result=result,
                applied_recommendations=applied_recs,
                all_recommendations=all_recs,
                assessments=assessments,
                elapsed_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return CPGEvaluationResult(
                cpg_id=cpg.identifier,
                cpg_title=cpg.title,
                cpg_publisher=cpg.publisher,
                is_eligible=None,
                is_executable=None,
                pipeline_result=None,
                applied_recommendations=[],
                all_recommendations=[],
                assessments=[],
                error=str(e),
                elapsed_ms=elapsed_ms,
            )

    def evaluate_multiple_cpgs(
        self,
        cpg_ids: list[str],
        health_context: HealthContext,
        patient_id: str = "unknown",
        patient_name: str = "Patient",
        persona: Persona = Persona.patient,
        parallel: bool = True
    ) -> EvaluationSummary:
        """Evaluate multiple CPGs against patient data.

        Args:
            cpg_ids: List of CPG IDs to evaluate
            health_context: Patient health data
            patient_id: Patient identifier
            patient_name: Patient display name
            persona: Persona for rendering narratives
            parallel: Whether to evaluate in parallel

        Returns:
            EvaluationSummary with all results
        """
        start_time = time.time()

        # Load all CPGs
        cpgs = self.loader.load_cpgs(cpg_ids)

        evaluations: dict[str, CPGEvaluationResult] = {}
        errors: list[str] = []

        if parallel and len(cpgs) > 1:
            # Parallel evaluation
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self.evaluate_single_cpg, cpg, health_context, persona
                    ): cpg
                    for cpg in cpgs
                }

                for future in as_completed(futures):
                    cpg = futures[future]
                    try:
                        result = future.result()
                        evaluations[result.cpg_id] = result
                        if result.error:
                            errors.append(f"{result.cpg_id}: {result.error}")
                    except Exception as e:
                        errors.append(f"{cpg.identifier}: {str(e)}")
        else:
            # Sequential evaluation
            for cpg in cpgs:
                result = self.evaluate_single_cpg(cpg, health_context, persona)
                evaluations[result.cpg_id] = result
                if result.error:
                    errors.append(f"{result.cpg_id}: {result.error}")

        # Calculate statistics
        eligible_count = sum(1 for e in evaluations.values() if e.is_eligible)
        executable_count = sum(1 for e in evaluations.values() if e.is_executable)
        total_recs = sum(len(e.all_recommendations) for e in evaluations.values())
        applied_recs = sum(len(e.applied_recommendations) for e in evaluations.values())

        # Detect conflicts if enabled
        conflicts = None
        if self.detect_conflicts and self.conflict_detector and len(evaluations) > 1:
            # Prepare data for conflict detection
            eval_data = []
            for eval_result in evaluations.values():
                if eval_result.applied_recommendations:
                    eval_data.append({
                        'cpg_id': eval_result.cpg_id,
                        'cpg_title': eval_result.cpg_title,
                        'recommendations': eval_result.applied_recommendations,
                        'assessments': eval_result.assessments,
                    })

            if len(eval_data) > 1:
                try:
                    conflicts = self.conflict_detector.detect_conflicts(eval_data)
                except Exception as e:
                    errors.append(f"Conflict detection error: {str(e)}")

        total_elapsed = (time.time() - start_time) * 1000

        return EvaluationSummary(
            patient_id=patient_id,
            patient_name=patient_name,
            total_cpgs=len(cpgs),
            eligible_cpgs=eligible_count,
            executable_cpgs=executable_count,
            total_recommendations=total_recs,
            applied_recommendations=applied_recs,
            conflicts=conflicts,
            evaluations=evaluations,
            total_elapsed_ms=total_elapsed,
            errors=errors,
        )

    def evaluate_all_available_cpgs(
        self,
        health_context: HealthContext,
        patient_id: str = "unknown",
        patient_name: str = "Patient",
        persona: Persona = Persona.patient,
    ) -> EvaluationSummary:
        """Evaluate all available CPGs against patient data.

        Args:
            health_context: Patient health data
            patient_id: Patient identifier
            patient_name: Patient display name
            persona: Persona for rendering narratives

        Returns:
            EvaluationSummary with all results
        """
        available = self.loader.get_available_cpgs()
        cpg_ids = [cfg["id"] for cfg in available]
        return self.evaluate_multiple_cpgs(
            cpg_ids=cpg_ids,
            health_context=health_context,
            patient_id=patient_id,
            patient_name=patient_name,
            persona=persona,
        )
