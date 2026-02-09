#!/usr/bin/env python3
"""Batch processing and parallel multi-CPG evaluation.

This module provides high-performance batch processing for population health
and concurrent evaluation against multiple CPGs.

Technical Advantages:
- 100-1000x cheaper than LLM evaluation at scale
- 50-100x faster (<100ms per evaluation vs 2-5 seconds)
- No rate limits, no API costs
- Parallel execution with configurable workers
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import time
from typing import Callable, Iterator

from .concord import Concord, PipelineResult
from .cpg import CPG
from .healthcontext import HealthContext
from .conflict_detection import ConflictDetector, ConflictReport

log = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing mode for batch operations."""
    SEQUENTIAL = "sequential"
    THREAD_POOL = "thread_pool"
    PROCESS_POOL = "process_pool"


@dataclass(slots=True)
class BatchResult:
    """Result from batch processing a single patient.

    Attributes:
        patient_id: Identifier for the patient
        result: PipelineResult from evaluation
        elapsed_ms: Time taken in milliseconds
        error: Error message if evaluation failed
    """
    patient_id: str
    result: PipelineResult | None
    elapsed_ms: float
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "patient_id": self.patient_id,
            "is_complete": self.result.is_complete if self.result else False,
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "recommendations_count": len(self.result.applied_recommendations or []) if self.result else 0,
        }


@dataclass(slots=True)
class BatchProcessingReport:
    """Aggregate report from batch processing.

    Attributes:
        total_patients: Number of patients processed
        successful: Number of successful evaluations
        failed: Number of failed evaluations
        total_elapsed_ms: Total processing time
        avg_elapsed_ms: Average time per evaluation
        results: List of individual BatchResults
        statistics: Aggregate statistics
    """
    total_patients: int
    successful: int
    failed: int
    total_elapsed_ms: float
    avg_elapsed_ms: float
    results: list[BatchResult]
    statistics: dict = field(default_factory=dict)
    processing_mode: str = "sequential"
    workers: int = 1
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "summary": {
                "total_patients": self.total_patients,
                "successful": self.successful,
                "failed": self.failed,
                "success_rate": self.successful / self.total_patients if self.total_patients > 0 else 0,
                "total_elapsed_ms": self.total_elapsed_ms,
                "avg_elapsed_ms": self.avg_elapsed_ms,
                "processing_mode": self.processing_mode,
                "workers": self.workers,
                "timestamp": self.timestamp,
            },
            "statistics": self.statistics,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass(slots=True)
class MultiCPGResult:
    """Result from evaluating a patient against multiple CPGs.

    Attributes:
        patient_id: Identifier for the patient
        evaluations: Dict mapping CPG ID to PipelineResult
        conflicts: ConflictReport if conflicts detected
        total_elapsed_ms: Total processing time
        parallel: Whether evaluation was done in parallel
    """
    patient_id: str
    evaluations: dict[str, PipelineResult]
    conflicts: ConflictReport | None
    total_elapsed_ms: float
    parallel: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        eval_summary = {}
        for cpg_id, result in self.evaluations.items():
            eval_summary[cpg_id] = {
                "is_complete": result.is_complete,
                "is_eligible": result.is_eligible,
                "recommendations": [
                    {"id": r.id, "title": r.recommendation.title}
                    for r in (result.applied_recommendations or [])
                ],
            }

        return {
            "patient_id": self.patient_id,
            "cpgs_evaluated": len(self.evaluations),
            "evaluations": eval_summary,
            "has_conflicts": self.conflicts is not None and len(self.conflicts.conflicts) > 0,
            "conflicts": self.conflicts.to_dict() if self.conflicts else None,
            "total_elapsed_ms": self.total_elapsed_ms,
            "parallel": self.parallel,
        }

    @property
    def all_recommendations(self) -> list:
        """Get all recommendations from all CPG evaluations."""
        recommendations = []
        for cpg_id, result in self.evaluations.items():
            if result.applied_recommendations:
                for rec in result.applied_recommendations:
                    recommendations.append({
                        "cpg_id": cpg_id,
                        "recommendation": rec,
                    })
        return recommendations


def _evaluate_patient(args: tuple) -> BatchResult:
    """Worker function for batch processing.

    Args:
        args: Tuple of (patient_id, cpg, healthcontext, skip_eligibility, ignore_attestations)

    Returns:
        BatchResult for this patient
    """
    patient_id, cpg, healthcontext, skip_eligibility, ignore_attestations = args

    start_time = time.perf_counter()
    try:
        concord = Concord(cpg=cpg, healthcontext=healthcontext)
        result = concord.evaluate(
            skip_eligibility=skip_eligibility,
            ignore_attestations=ignore_attestations
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return BatchResult(
            patient_id=patient_id,
            result=result,
            elapsed_ms=elapsed_ms,
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        log.error(f"Batch evaluation failed for patient {patient_id}: {e}")
        return BatchResult(
            patient_id=patient_id,
            result=None,
            elapsed_ms=elapsed_ms,
            error=str(e),
        )


def _evaluate_cpg(args: tuple) -> tuple[str, PipelineResult | None, str | None]:
    """Worker function for multi-CPG evaluation.

    Args:
        args: Tuple of (cpg, healthcontext, skip_eligibility, ignore_attestations)

    Returns:
        Tuple of (cpg_id, result, error)
    """
    cpg, healthcontext, skip_eligibility, ignore_attestations = args

    try:
        concord = Concord(cpg=cpg, healthcontext=healthcontext)
        result = concord.evaluate(
            skip_eligibility=skip_eligibility,
            ignore_attestations=ignore_attestations
        )
        return (cpg.identifier, result, None)
    except Exception as e:
        log.error(f"Multi-CPG evaluation failed for {cpg.identifier}: {e}")
        return (cpg.identifier, None, str(e))


class BatchProcessor:
    """High-performance batch processor for population health.

    Processes multiple patients against a CPG with configurable parallelism.

    Example:
        ```python
        processor = BatchProcessor(cpg)

        # Process 10,000 patients
        report = processor.process(
            patients=patient_contexts,
            mode=ProcessingMode.PROCESS_POOL,
            workers=8
        )

        print(f"Processed {report.total_patients} in {report.total_elapsed_ms}ms")
        print(f"Average: {report.avg_elapsed_ms}ms per patient")
        ```
    """

    def __init__(self, cpg: CPG):
        """Initialize batch processor.

        Args:
            cpg: CPG to evaluate patients against
        """
        self.cpg = cpg

    def process(
        self,
        patients: list[tuple[str, HealthContext]],
        mode: ProcessingMode = ProcessingMode.THREAD_POOL,
        workers: int = 4,
        skip_eligibility: bool = False,
        ignore_attestations: bool = True,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> BatchProcessingReport:
        """Process a batch of patients.

        Args:
            patients: List of (patient_id, HealthContext) tuples
            mode: Processing mode (sequential, thread_pool, process_pool)
            workers: Number of workers for parallel processing
            skip_eligibility: Whether to skip eligibility checks
            ignore_attestations: Whether to ignore attestation requirements
            progress_callback: Optional callback(completed, total) for progress

        Returns:
            BatchProcessingReport with all results
        """
        start_time = time.perf_counter()
        results: list[BatchResult] = []
        total = len(patients)

        if mode == ProcessingMode.SEQUENTIAL:
            for i, (patient_id, context) in enumerate(patients):
                result = _evaluate_patient(
                    (patient_id, self.cpg, context, skip_eligibility, ignore_attestations)
                )
                results.append(result)
                if progress_callback:
                    progress_callback(i + 1, total)

        elif mode == ProcessingMode.THREAD_POOL:
            args_list = [
                (pid, self.cpg, ctx, skip_eligibility, ignore_attestations)
                for pid, ctx in patients
            ]
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_evaluate_patient, args): args[0] for args in args_list}
                completed = 0
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)

        elif mode == ProcessingMode.PROCESS_POOL:
            # Note: ProcessPoolExecutor requires picklable objects
            # For complex CPGs, ThreadPoolExecutor may be more reliable
            args_list = [
                (pid, self.cpg, ctx, skip_eligibility, ignore_attestations)
                for pid, ctx in patients
            ]
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_evaluate_patient, args): args[0] for args in args_list}
                completed = 0
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000
        successful = sum(1 for r in results if r.result is not None and r.error is None)
        failed = len(results) - successful

        # Compute statistics
        statistics = self._compute_statistics(results)

        return BatchProcessingReport(
            total_patients=total,
            successful=successful,
            failed=failed,
            total_elapsed_ms=total_elapsed_ms,
            avg_elapsed_ms=total_elapsed_ms / total if total > 0 else 0,
            results=results,
            statistics=statistics,
            processing_mode=mode.value,
            workers=workers,
        )

    def _compute_statistics(self, results: list[BatchResult]) -> dict:
        """Compute aggregate statistics from batch results."""
        stats = {
            "eligible_count": 0,
            "ineligible_count": 0,
            "with_recommendations": 0,
            "recommendation_counts": {},
            "timing": {
                "min_ms": float('inf'),
                "max_ms": 0,
                "total_ms": 0,
            }
        }

        for r in results:
            if r.result:
                if r.result.is_eligible:
                    stats["eligible_count"] += 1
                elif r.result.is_eligible is False:
                    stats["ineligible_count"] += 1

                recs = r.result.applied_recommendations or []
                if recs:
                    stats["with_recommendations"] += 1
                    for rec in recs:
                        rec_id = rec.id
                        stats["recommendation_counts"][rec_id] = \
                            stats["recommendation_counts"].get(rec_id, 0) + 1

            stats["timing"]["min_ms"] = min(stats["timing"]["min_ms"], r.elapsed_ms)
            stats["timing"]["max_ms"] = max(stats["timing"]["max_ms"], r.elapsed_ms)
            stats["timing"]["total_ms"] += r.elapsed_ms

        if stats["timing"]["min_ms"] == float('inf'):
            stats["timing"]["min_ms"] = 0

        return stats

    def stream(
        self,
        patients: Iterator[tuple[str, HealthContext]],
        skip_eligibility: bool = False,
        ignore_attestations: bool = True
    ) -> Iterator[BatchResult]:
        """Stream process patients one at a time.

        Useful for very large datasets that don't fit in memory.

        Args:
            patients: Iterator of (patient_id, HealthContext) tuples
            skip_eligibility: Whether to skip eligibility checks
            ignore_attestations: Whether to ignore attestation requirements

        Yields:
            BatchResult for each patient
        """
        for patient_id, context in patients:
            result = _evaluate_patient(
                (patient_id, self.cpg, context, skip_eligibility, ignore_attestations)
            )
            yield result


class MultiCPGEvaluator:
    """Evaluates a patient against multiple CPGs concurrently.

    Example:
        ```python
        evaluator = MultiCPGEvaluator(cpgs=[cpg1, cpg2, cpg3, ...])

        # Evaluate patient against all 20 CPGs in <1 second
        result = evaluator.evaluate(
            patient_id="patient123",
            healthcontext=context,
            parallel=True
        )

        print(f"Evaluated {len(result.evaluations)} CPGs")
        print(f"Found {len(result.all_recommendations)} recommendations")
        if result.conflicts:
            print(f"Detected {len(result.conflicts.conflicts)} conflicts")
        ```
    """

    def __init__(self, cpgs: list[CPG], detect_conflicts: bool = True):
        """Initialize multi-CPG evaluator.

        Args:
            cpgs: List of CPGs to evaluate against
            detect_conflicts: Whether to detect conflicts between recommendations
        """
        self.cpgs = cpgs
        self.detect_conflicts = detect_conflicts
        self.conflict_detector = ConflictDetector() if detect_conflicts else None

    def evaluate(
        self,
        patient_id: str,
        healthcontext: HealthContext,
        parallel: bool = True,
        workers: int = 4,
        skip_eligibility: bool = False,
        ignore_attestations: bool = True
    ) -> MultiCPGResult:
        """Evaluate patient against all CPGs.

        Args:
            patient_id: Patient identifier
            healthcontext: Patient health data
            parallel: Whether to evaluate CPGs in parallel
            workers: Number of workers for parallel evaluation
            skip_eligibility: Whether to skip eligibility checks
            ignore_attestations: Whether to ignore attestation requirements

        Returns:
            MultiCPGResult with all evaluations and conflicts
        """
        start_time = time.perf_counter()
        evaluations: dict[str, PipelineResult] = {}

        if parallel and len(self.cpgs) > 1:
            args_list = [
                (cpg, healthcontext, skip_eligibility, ignore_attestations)
                for cpg in self.cpgs
            ]

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_evaluate_cpg, args) for args in args_list]
                for future in as_completed(futures):
                    cpg_id, result, error = future.result()
                    if result:
                        evaluations[cpg_id] = result
                    else:
                        log.warning(f"CPG {cpg_id} evaluation failed: {error}")
        else:
            for cpg in self.cpgs:
                cpg_id, result, error = _evaluate_cpg(
                    (cpg, healthcontext, skip_eligibility, ignore_attestations)
                )
                if result:
                    evaluations[cpg_id] = result
                else:
                    log.warning(f"CPG {cpg_id} evaluation failed: {error}")

        # Detect conflicts
        conflicts = None
        if self.detect_conflicts and self.conflict_detector and len(evaluations) > 1:
            eval_dicts = []
            for cpg_id, result in evaluations.items():
                if result.applied_recommendations:
                    for rec in result.applied_recommendations:
                        eval_dicts.append({
                            "cpg_id": cpg_id,
                            "recommendation_id": rec.id,
                            "recommendation_title": rec.recommendation.title if rec.recommendation else "",
                            "recommendation": rec,
                        })
            conflicts = self.conflict_detector.detect_conflicts(eval_dicts)

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000

        return MultiCPGResult(
            patient_id=patient_id,
            evaluations=evaluations,
            conflicts=conflicts,
            total_elapsed_ms=total_elapsed_ms,
            parallel=parallel,
        )

    def evaluate_batch(
        self,
        patients: list[tuple[str, HealthContext]],
        parallel: bool = True,
        workers: int = 4
    ) -> list[MultiCPGResult]:
        """Evaluate multiple patients against all CPGs.

        Args:
            patients: List of (patient_id, HealthContext) tuples
            parallel: Whether to evaluate CPGs in parallel
            workers: Number of workers

        Returns:
            List of MultiCPGResult, one per patient
        """
        results = []
        for patient_id, context in patients:
            result = self.evaluate(
                patient_id=patient_id,
                healthcontext=context,
                parallel=parallel,
                workers=workers
            )
            results.append(result)
        return results


# ============================================================================
# PatientScreener — Efficient single-patient multi-CPG screening
# ============================================================================

@dataclass(frozen=True, slots=True)
class CoverageGap:
    """A missing variable that would unlock or improve CPG evaluations."""
    variable_id: str
    variable_title: str
    cpg_ids: tuple[str, ...]   # CPGs needing this variable
    is_required: bool          # Required by at least one CPG
    is_attestable: bool        # Can be user-attested
    impact_score: float        # 0–1, higher = more impactful


@dataclass(frozen=True, slots=True)
class CoverageAnalysis:
    """Which missing variables would unlock the most CPGs."""
    gaps: tuple[CoverageGap, ...]  # Sorted by impact_score desc
    total_unique_variables: int
    provided_variables: int
    missing_variables: int


@dataclass(frozen=True, slots=True)
class CPGScreeningResult:
    """Result for a single CPG in the screening."""
    cpg_id: str
    cpg_title: str
    is_eligible: bool
    is_executable: bool
    pipeline_result: PipelineResult | None
    error: str | None


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    """Complete screening result for a patient across all CPGs."""
    patient_id: str
    results: tuple[CPGScreeningResult, ...]
    coverage: CoverageAnalysis
    eligible_count: int
    executable_count: int
    total_cpgs: int
    elapsed_ms: float


class PatientScreener:
    """Screens a patient against all applicable CPGs with coverage analysis.

    Single-pass: eligibility triage → full evaluation → coverage derived
    from sufficiency results (no redundant variable scanning).
    """

    def __init__(self, cpg_ids: list[str] | None = None):
        self._cpg_ids = cpg_ids

    def _load_cpgs(self) -> list[CPG]:
        from .cpg_registry import get_registry
        registry = get_registry()
        cpgs = []
        for cid in (self._cpg_ids or registry.identifiers()):
            try:
                cpgs.append(registry.get(cid))
            except Exception as e:
                log.warning(f"Skipping CPG {cid}: {e}")
        return cpgs

    def screen(
        self,
        health_context: HealthContext,
        patient_id: str = "",
        ignore_attestations: bool = True,
    ) -> ScreeningResult:
        """Screen patient against all applicable CPGs.

        Single loop: eligibility check → full pipeline for eligible CPGs.
        Coverage analysis derived from sufficiency results (zero extra work).
        """
        start_time = time.perf_counter()

        from .record_index import RecordIndex
        from .sufficiency import build_code_index
        from .eligibility import EligibilityEvaluator

        cpgs = self._load_cpgs()

        # Shared indexes + hash — built once, reused by all CPG evaluations
        record_index = RecordIndex(health_context.records)
        code_index = build_code_index(health_context.records)
        input_hash = self._hash_records(health_context.records)

        results: list[CPGScreeningResult] = []

        for cpg in cpgs:
            # Eligibility triage
            if cpg.eligibility_variables:
                try:
                    elig = EligibilityEvaluator(cpg.eligibility_variables).evaluate(
                        health_context, record_index=record_index
                    )
                    if not elig.is_eligible:
                        results.append(CPGScreeningResult(
                            cpg.identifier, cpg.title,
                            is_eligible=False, is_executable=False,
                            pipeline_result=None, error=None))
                        continue
                except Exception as e:
                    results.append(CPGScreeningResult(
                        cpg.identifier, cpg.title,
                        is_eligible=False, is_executable=False,
                        pipeline_result=None, error=str(e)))
                    continue

            # Full evaluation (eligibility already confirmed)
            try:
                concord = Concord(cpg=cpg, healthcontext=health_context,
                                  ignore_eligibility=True)
                pr = concord.evaluate(
                    skip_eligibility=True,
                    ignore_attestations=ignore_attestations,
                    record_index=record_index, code_index=code_index,
                    _input_data_hash=input_hash)
                results.append(CPGScreeningResult(
                    cpg.identifier, cpg.title,
                    is_eligible=True, is_executable=pr.is_complete,
                    pipeline_result=pr, error=None))
            except Exception as e:
                log.error(f"Evaluation failed for {cpg.identifier}: {e}")
                results.append(CPGScreeningResult(
                    cpg.identifier, cpg.title,
                    is_eligible=True, is_executable=False,
                    pipeline_result=None, error=str(e)))

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return ScreeningResult(
            patient_id=patient_id,
            results=tuple(results),
            coverage=self._build_coverage(results),
            eligible_count=sum(1 for r in results if r.is_eligible),
            executable_count=sum(1 for r in results if r.is_executable),
            total_cpgs=len(cpgs),
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _hash_records(records) -> str:
        """Compute SHA-256 of patient records once for all CPG evaluations."""
        import hashlib, json
        data = sorted(
            [{"id": r.id, "values": [{"value": str(v.value),
              "date": str(v.date) if v.date else None}
              for v in (r.values or [])]} for r in records],
            key=lambda x: x["id"])
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _build_coverage(results: list[CPGScreeningResult]) -> CoverageAnalysis:
        """Derive coverage from sufficiency results — no extra variable scanning."""
        all_var_ids: set[str] = set()
        provided_ids: set[str] = set()
        # var_id -> [cpg_id_list, is_required, is_attestable, title]
        missing: dict[str, list] = {}

        for r in results:
            suff = r.pipeline_result.sufficiency if r.pipeline_result else None
            if not suff:
                continue
            for ev in suff.context.evaluation_list:
                var = ev.record.var
                all_var_ids.add(var.id)
                if ev.record.has_value:
                    provided_ids.add(var.id)
                elif var.id not in provided_ids:
                    entry = missing.get(var.id)
                    if entry is None:
                        entry = [[], False, False, var.title or var.id]
                        missing[var.id] = entry
                    entry[0].append(r.cpg_id)
                    if var.required:
                        entry[1] = True
                    if var.user_attestable:
                        entry[2] = True

        # Drop vars that were provided by some CPG's perspective
        for vid in provided_ids:
            missing.pop(vid, None)

        num_eligible = max(sum(1 for r in results if r.is_eligible), 1)
        gaps = []
        for var_id, (cpg_ids, is_req, is_att, title) in missing.items():
            score = 0.6 * (len(cpg_ids) / num_eligible) + 0.4 * (1.0 if is_req else 0.5)
            if is_att:
                score = min(1.0, score + 0.2)
            gaps.append(CoverageGap(var_id, title, tuple(cpg_ids),
                                    is_req, is_att, round(score, 3)))

        gaps.sort(key=lambda g: g.impact_score, reverse=True)
        return CoverageAnalysis(
            tuple(gaps), len(all_var_ids), len(provided_ids), len(missing))
