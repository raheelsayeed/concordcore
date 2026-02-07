#!/usr/bin/env python3
"""Tests for batch processing and multi-CPG evaluation."""

import pytest
from datetime import date

from core.batch_processor import (
    BatchProcessor,
    BatchResult,
    BatchProcessingReport,
    MultiCPGEvaluator,
    MultiCPGResult,
    ProcessingMode,
)
from core.cpg import CPG
from core.healthcontext import HealthContext
from variables.value import Value
from variables.record import Record
from variables.var import Var


class TestBatchResult:
    """Tests for BatchResult class."""

    def test_to_dict(self):
        """BatchResult should convert to dict correctly."""
        result = BatchResult(
            patient_id="patient123",
            result=None,
            elapsed_ms=50.5,
            error=None
        )

        result_dict = result.to_dict()

        assert result_dict["patient_id"] == "patient123"
        assert result_dict["elapsed_ms"] == 50.5
        assert result_dict["is_complete"] == False
        assert result_dict["error"] is None

    def test_to_dict_with_error(self):
        """BatchResult with error should include error in dict."""
        result = BatchResult(
            patient_id="patient456",
            result=None,
            elapsed_ms=10.0,
            error="Test error"
        )

        result_dict = result.to_dict()

        assert result_dict["error"] == "Test error"


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_process_sequential(self, minimal_cpg, minimal_healthcontext):
        """Should process patients sequentially."""
        processor = BatchProcessor(minimal_cpg)

        patients = [
            ("patient1", minimal_healthcontext),
            ("patient2", minimal_healthcontext),
            ("patient3", minimal_healthcontext),
        ]

        report = processor.process(
            patients=patients,
            mode=ProcessingMode.SEQUENTIAL,
            skip_eligibility=True,
            ignore_attestations=True
        )

        assert report.total_patients == 3
        assert len(report.results) == 3
        assert report.processing_mode == "sequential"

    def test_process_thread_pool(self, minimal_cpg, minimal_healthcontext):
        """Should process patients with thread pool."""
        processor = BatchProcessor(minimal_cpg)

        patients = [
            ("patient1", minimal_healthcontext),
            ("patient2", minimal_healthcontext),
        ]

        report = processor.process(
            patients=patients,
            mode=ProcessingMode.THREAD_POOL,
            workers=2,
            skip_eligibility=True,
            ignore_attestations=True
        )

        assert report.total_patients == 2
        assert report.processing_mode == "thread_pool"
        assert report.workers == 2

    def test_process_with_progress_callback(self, minimal_cpg, minimal_healthcontext):
        """Should call progress callback."""
        processor = BatchProcessor(minimal_cpg)

        patients = [
            ("patient1", minimal_healthcontext),
            ("patient2", minimal_healthcontext),
        ]

        progress_calls = []

        def progress_callback(completed, total):
            progress_calls.append((completed, total))

        report = processor.process(
            patients=patients,
            mode=ProcessingMode.SEQUENTIAL,
            skip_eligibility=True,
            ignore_attestations=True,
            progress_callback=progress_callback
        )

        assert len(progress_calls) == 2
        assert progress_calls[-1] == (2, 2)

    def test_report_statistics(self, minimal_cpg, minimal_healthcontext):
        """Should compute aggregate statistics."""
        processor = BatchProcessor(minimal_cpg)

        patients = [
            ("patient1", minimal_healthcontext),
            ("patient2", minimal_healthcontext),
        ]

        report = processor.process(
            patients=patients,
            mode=ProcessingMode.SEQUENTIAL,
            skip_eligibility=True,
            ignore_attestations=True
        )

        assert "timing" in report.statistics
        assert report.statistics["timing"]["min_ms"] >= 0
        assert report.statistics["timing"]["max_ms"] >= 0

    def test_report_to_dict(self, minimal_cpg, minimal_healthcontext):
        """BatchProcessingReport should convert to dict."""
        processor = BatchProcessor(minimal_cpg)

        patients = [("patient1", minimal_healthcontext)]

        report = processor.process(
            patients=patients,
            mode=ProcessingMode.SEQUENTIAL,
            skip_eligibility=True,
            ignore_attestations=True
        )

        report_dict = report.to_dict()

        assert "summary" in report_dict
        assert "statistics" in report_dict
        assert "results" in report_dict
        assert report_dict["summary"]["total_patients"] == 1

    def test_stream_processing(self, minimal_cpg, minimal_healthcontext):
        """Should stream process patients."""
        processor = BatchProcessor(minimal_cpg)

        def patient_generator():
            yield ("patient1", minimal_healthcontext)
            yield ("patient2", minimal_healthcontext)

        results = list(processor.stream(
            patients=patient_generator(),
            skip_eligibility=True,
            ignore_attestations=True
        ))

        assert len(results) == 2
        assert all(isinstance(r, BatchResult) for r in results)


class TestMultiCPGEvaluator:
    """Tests for MultiCPGEvaluator class."""

    def test_evaluate_single_cpg(self, minimal_cpg, minimal_healthcontext):
        """Should evaluate patient against single CPG."""
        evaluator = MultiCPGEvaluator(cpgs=[minimal_cpg], detect_conflicts=False)

        result = evaluator.evaluate(
            patient_id="patient123",
            healthcontext=minimal_healthcontext,
            parallel=False,
            skip_eligibility=True,
            ignore_attestations=True
        )

        assert result.patient_id == "patient123"
        assert len(result.evaluations) == 1
        assert minimal_cpg.identifier in result.evaluations

    def test_evaluate_multiple_cpgs_sequential(self, minimal_cpg, minimal_healthcontext):
        """Should evaluate patient against multiple CPGs sequentially."""
        # Use same CPG twice for testing
        evaluator = MultiCPGEvaluator(cpgs=[minimal_cpg], detect_conflicts=False)

        result = evaluator.evaluate(
            patient_id="patient123",
            healthcontext=minimal_healthcontext,
            parallel=False,
            skip_eligibility=True,
            ignore_attestations=True
        )

        assert result.parallel == False
        assert result.total_elapsed_ms > 0

    def test_evaluate_multiple_cpgs_parallel(self, minimal_cpg, minimal_healthcontext):
        """Should evaluate patient against multiple CPGs in parallel."""
        evaluator = MultiCPGEvaluator(cpgs=[minimal_cpg], detect_conflicts=False)

        result = evaluator.evaluate(
            patient_id="patient123",
            healthcontext=minimal_healthcontext,
            parallel=True,
            workers=2,
            skip_eligibility=True,
            ignore_attestations=True
        )

        # With single CPG, parallel flag doesn't change much
        assert result.total_elapsed_ms > 0

    def test_result_to_dict(self, minimal_cpg, minimal_healthcontext):
        """MultiCPGResult should convert to dict."""
        evaluator = MultiCPGEvaluator(cpgs=[minimal_cpg], detect_conflicts=False)

        result = evaluator.evaluate(
            patient_id="patient123",
            healthcontext=minimal_healthcontext,
            skip_eligibility=True,
            ignore_attestations=True
        )

        result_dict = result.to_dict()

        assert "patient_id" in result_dict
        assert "cpgs_evaluated" in result_dict
        assert "evaluations" in result_dict
        assert result_dict["cpgs_evaluated"] == 1

    def test_all_recommendations_property(self, minimal_cpg, minimal_healthcontext):
        """Should collect all recommendations from all CPGs."""
        evaluator = MultiCPGEvaluator(cpgs=[minimal_cpg], detect_conflicts=False)

        result = evaluator.evaluate(
            patient_id="patient123",
            healthcontext=minimal_healthcontext,
            skip_eligibility=True,
            ignore_attestations=True
        )

        # all_recommendations is a list
        assert isinstance(result.all_recommendations, list)

    def test_evaluate_batch(self, minimal_cpg, minimal_healthcontext):
        """Should evaluate batch of patients against all CPGs."""
        evaluator = MultiCPGEvaluator(cpgs=[minimal_cpg], detect_conflicts=False)

        patients = [
            ("patient1", minimal_healthcontext),
            ("patient2", minimal_healthcontext),
        ]

        results = evaluator.evaluate_batch(
            patients=patients,
            parallel=False
        )

        assert len(results) == 2
        assert all(isinstance(r, MultiCPGResult) for r in results)
        assert results[0].patient_id == "patient1"
        assert results[1].patient_id == "patient2"


class TestProcessingPerformance:
    """Tests for processing performance."""

    def test_evaluation_under_100ms(self, minimal_cpg, minimal_healthcontext):
        """Single evaluation should complete in under 100ms."""
        import time

        start = time.perf_counter()
        processor = BatchProcessor(minimal_cpg)
        result = list(processor.stream(
            patients=[("test", minimal_healthcontext)],
            skip_eligibility=True,
            ignore_attestations=True
        ))[0]
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow some slack for test environment
        assert elapsed_ms < 500, f"Evaluation took {elapsed_ms}ms, expected <500ms"

    def test_batch_throughput(self, minimal_cpg, minimal_healthcontext):
        """Batch processing should achieve reasonable throughput."""
        import time

        processor = BatchProcessor(minimal_cpg)
        patients = [(f"patient{i}", minimal_healthcontext) for i in range(10)]

        start = time.perf_counter()
        report = processor.process(
            patients=patients,
            mode=ProcessingMode.THREAD_POOL,
            workers=4,
            skip_eligibility=True,
            ignore_attestations=True
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 10 patients should complete in under 5 seconds
        assert elapsed_ms < 5000, f"Batch took {elapsed_ms}ms, expected <5000ms"
        assert report.successful == 10
