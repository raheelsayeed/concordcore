#!/usr/bin/env python3
"""Benchmarking suite for Concord performance metrics.

This module provides tools to measure and prove Concord's performance claims:
- Time per evaluation (<100ms)
- Batch throughput (thousands per second)
- Memory usage profiling
- LLM cost comparison metrics

Example usage:
    ```python
    from core.benchmarks import BenchmarkRunner, BenchmarkReport

    # Quick benchmark
    runner = BenchmarkRunner()
    report = runner.run_full_benchmark()
    print(report.summary())

    # Single CPG benchmark
    result = runner.benchmark_single_cpg("cholesterol")
    print(f"Average: {result.avg_ms:.2f}ms")
    ```
"""

import gc
import json
import statistics
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import logging

log = logging.getLogger(__name__)


@dataclass(slots=True)
class SingleEvaluationMetrics:
    """Metrics for a single CPG evaluation."""
    cpg_id: str
    elapsed_ms: float
    memory_peak_mb: float = 0.0
    memory_current_mb: float = 0.0
    is_complete: bool = False
    recommendations_count: int = 0


@dataclass(slots=True)
class BenchmarkResult:
    """Result of benchmarking a single CPG."""
    cpg_id: str
    iterations: int
    total_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    memory_peak_mb: float
    memory_avg_mb: float
    evaluations_per_second: float
    all_times_ms: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "cpg_id": self.cpg_id,
            "iterations": self.iterations,
            "timing": {
                "total_ms": round(self.total_ms, 3),
                "avg_ms": round(self.avg_ms, 3),
                "min_ms": round(self.min_ms, 3),
                "max_ms": round(self.max_ms, 3),
                "std_dev_ms": round(self.std_dev_ms, 3),
                "p50_ms": round(self.p50_ms, 3),
                "p95_ms": round(self.p95_ms, 3),
                "p99_ms": round(self.p99_ms, 3),
            },
            "memory": {
                "peak_mb": round(self.memory_peak_mb, 2),
                "avg_mb": round(self.memory_avg_mb, 2),
            },
            "throughput": {
                "evaluations_per_second": round(self.evaluations_per_second, 1),
            },
        }


@dataclass(slots=True)
class BatchBenchmarkResult:
    """Result of batch processing benchmark."""
    patient_count: int
    cpg_id: str
    mode: str  # sequential, thread_pool, process_pool
    total_ms: float
    avg_per_patient_ms: float
    patients_per_second: float
    successful_count: int
    failed_count: int
    memory_peak_mb: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "patient_count": self.patient_count,
            "cpg_id": self.cpg_id,
            "mode": self.mode,
            "timing": {
                "total_ms": round(self.total_ms, 2),
                "avg_per_patient_ms": round(self.avg_per_patient_ms, 3),
            },
            "throughput": {
                "patients_per_second": round(self.patients_per_second, 1),
            },
            "results": {
                "successful": self.successful_count,
                "failed": self.failed_count,
            },
            "memory_peak_mb": round(self.memory_peak_mb, 2),
        }


@dataclass(slots=True)
class MultiCPGBenchmarkResult:
    """Result of multi-CPG evaluation benchmark."""
    cpg_count: int
    cpg_ids: list[str]
    parallel: bool
    total_ms: float
    avg_per_cpg_ms: float
    cpgs_per_second: float
    conflicts_detected: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "cpg_count": self.cpg_count,
            "cpg_ids": self.cpg_ids,
            "parallel": self.parallel,
            "timing": {
                "total_ms": round(self.total_ms, 2),
                "avg_per_cpg_ms": round(self.avg_per_cpg_ms, 3),
            },
            "throughput": {
                "cpgs_per_second": round(self.cpgs_per_second, 1),
            },
            "conflicts_detected": self.conflicts_detected,
        }


@dataclass(slots=True)
class LLMCostComparison:
    """Cost comparison between Concord and LLM approaches."""
    scenario: str
    evaluation_count: int
    concord_time_ms: float
    concord_cost_usd: float  # Always 0 for local computation
    llm_estimated_time_ms: float
    llm_estimated_cost_usd: float
    speedup_factor: float
    cost_savings_usd: float
    cost_savings_percent: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "scenario": self.scenario,
            "evaluation_count": self.evaluation_count,
            "concord": {
                "time_ms": round(self.concord_time_ms, 2),
                "cost_usd": round(self.concord_cost_usd, 4),
            },
            "llm_estimated": {
                "time_ms": round(self.llm_estimated_time_ms, 2),
                "cost_usd": round(self.llm_estimated_cost_usd, 4),
            },
            "comparison": {
                "speedup_factor": round(self.speedup_factor, 1),
                "cost_savings_usd": round(self.cost_savings_usd, 2),
                "cost_savings_percent": round(self.cost_savings_percent, 1),
            },
        }


@dataclass(slots=True)
class BenchmarkReport:
    """Complete benchmark report."""
    timestamp: str
    system_info: dict
    single_cpg_results: list[BenchmarkResult] = field(default_factory=list)
    batch_results: list[BatchBenchmarkResult] = field(default_factory=list)
    multi_cpg_results: list[MultiCPGBenchmarkResult] = field(default_factory=list)
    cost_comparisons: list[LLMCostComparison] = field(default_factory=list)

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        lines.append("=" * 70)
        lines.append("CONCORD BENCHMARK REPORT")
        lines.append("=" * 70)
        lines.append(f"Timestamp: {self.timestamp}")
        lines.append(f"Python: {self.system_info.get('python_version', 'unknown')}")
        lines.append(f"Platform: {self.system_info.get('platform', 'unknown')}")
        lines.append("")

        # Single CPG Results
        if self.single_cpg_results:
            lines.append("-" * 70)
            lines.append("SINGLE CPG EVALUATION PERFORMANCE")
            lines.append("-" * 70)
            lines.append(f"{'CPG':<30} {'Avg (ms)':<10} {'P95 (ms)':<10} {'Evals/sec':<12}")
            lines.append("-" * 70)
            for r in self.single_cpg_results:
                lines.append(f"{r.cpg_id:<30} {r.avg_ms:<10.2f} {r.p95_ms:<10.2f} {r.evaluations_per_second:<12.0f}")
            lines.append("")

        # Batch Results
        if self.batch_results:
            lines.append("-" * 70)
            lines.append("BATCH PROCESSING PERFORMANCE")
            lines.append("-" * 70)
            lines.append(f"{'Patients':<10} {'Mode':<15} {'Total (ms)':<12} {'Pat/sec':<10}")
            lines.append("-" * 70)
            for r in self.batch_results:
                lines.append(f"{r.patient_count:<10} {r.mode:<15} {r.total_ms:<12.1f} {r.patients_per_second:<10.0f}")
            lines.append("")

        # Multi-CPG Results
        if self.multi_cpg_results:
            lines.append("-" * 70)
            lines.append("MULTI-CPG EVALUATION PERFORMANCE")
            lines.append("-" * 70)
            lines.append(f"{'CPGs':<10} {'Mode':<12} {'Total (ms)':<12} {'CPGs/sec':<10}")
            lines.append("-" * 70)
            for r in self.multi_cpg_results:
                mode = "parallel" if r.parallel else "sequential"
                lines.append(f"{r.cpg_count:<10} {mode:<12} {r.total_ms:<12.2f} {r.cpgs_per_second:<10.0f}")
            lines.append("")

        # Cost Comparisons
        if self.cost_comparisons:
            lines.append("-" * 70)
            lines.append("COST COMPARISON: CONCORD vs LLM")
            lines.append("-" * 70)
            lines.append(f"{'Scenario':<25} {'Concord':<15} {'LLM Est.':<15} {'Savings':<15}")
            lines.append("-" * 70)
            for c in self.cost_comparisons:
                concord = f"${c.concord_cost_usd:.2f}"
                llm = f"${c.llm_estimated_cost_usd:.2f}"
                savings = f"{c.cost_savings_percent:.0f}%"
                lines.append(f"{c.scenario:<25} {concord:<15} {llm:<15} {savings:<15}")
            lines.append("")

        # Summary Statistics
        lines.append("-" * 70)
        lines.append("KEY METRICS")
        lines.append("-" * 70)
        if self.single_cpg_results:
            avg_eval_time = statistics.mean(r.avg_ms for r in self.single_cpg_results)
            lines.append(f"Average evaluation time: {avg_eval_time:.2f}ms (<100ms target: {'PASS' if avg_eval_time < 100 else 'FAIL'})")
        if self.batch_results:
            max_throughput = max(r.patients_per_second for r in self.batch_results)
            lines.append(f"Max batch throughput: {max_throughput:.0f} patients/second")
        if self.cost_comparisons:
            total_savings = sum(c.cost_savings_usd for c in self.cost_comparisons)
            lines.append(f"Total cost savings (vs LLM): ${total_savings:.2f}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "system_info": self.system_info,
            "single_cpg_results": [r.to_dict() for r in self.single_cpg_results],
            "batch_results": [r.to_dict() for r in self.batch_results],
            "multi_cpg_results": [r.to_dict() for r in self.multi_cpg_results],
            "cost_comparisons": [c.to_dict() for c in self.cost_comparisons],
        }

    def save(self, filepath: str) -> None:
        """Save report to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# LLM cost assumptions (conservative estimates)
LLM_COSTS = {
    "gpt4_turbo": {
        "input_tokens_per_1k": 0.01,
        "output_tokens_per_1k": 0.03,
        "avg_input_tokens": 2000,  # CPG context + patient data
        "avg_output_tokens": 500,   # Recommendations
        "avg_latency_ms": 3000,     # 3 seconds typical
    },
    "claude_opus": {
        "input_tokens_per_1k": 0.015,
        "output_tokens_per_1k": 0.075,
        "avg_input_tokens": 2000,
        "avg_output_tokens": 500,
        "avg_latency_ms": 2500,
    },
    "claude_sonnet": {
        "input_tokens_per_1k": 0.003,
        "output_tokens_per_1k": 0.015,
        "avg_input_tokens": 2000,
        "avg_output_tokens": 500,
        "avg_latency_ms": 2000,
    },
}


def estimate_llm_cost(model: str, evaluation_count: int) -> tuple[float, float]:
    """Estimate LLM cost and time for a number of evaluations.

    Returns:
        Tuple of (total_cost_usd, total_time_ms)
    """
    if model not in LLM_COSTS:
        model = "claude_sonnet"  # Default

    costs = LLM_COSTS[model]
    input_cost = (costs["avg_input_tokens"] / 1000) * costs["input_tokens_per_1k"]
    output_cost = (costs["avg_output_tokens"] / 1000) * costs["output_tokens_per_1k"]
    cost_per_eval = input_cost + output_cost
    time_per_eval = costs["avg_latency_ms"]

    return (cost_per_eval * evaluation_count, time_per_eval * evaluation_count)


class BenchmarkRunner:
    """Runner for Concord benchmarks."""

    def __init__(self, cpg_dir: str = "cpgs"):
        """Initialize the benchmark runner.

        Args:
            cpg_dir: Directory containing CPG YAML files
        """
        self.cpg_dir = Path(cpg_dir)
        self._sample_healthcontext = None
        from core.cpg_registry import get_registry
        self._registry = get_registry(self.cpg_dir)

    def _get_sample_healthcontext(self):
        """Get or create sample health context for benchmarking."""
        if self._sample_healthcontext is None:
            from misc import sample_healthcontext
            self._sample_healthcontext = sample_healthcontext()
        return self._sample_healthcontext

    def _load_cpg(self, cpg_id: str):
        """Load a CPG by ID."""
        return self._registry.get(cpg_id)

    def _get_available_cpgs(self) -> list[str]:
        """Get list of available CPG identifiers."""
        return self._registry.identifiers()

    def benchmark_single_cpg(
        self,
        cpg_id: str,
        iterations: int = 100,
        warmup: int = 5,
        track_memory: bool = True,
    ) -> BenchmarkResult:
        """Benchmark a single CPG evaluation.

        Args:
            cpg_id: CPG identifier
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not counted)
            track_memory: Whether to track memory usage

        Returns:
            BenchmarkResult with timing and memory metrics
        """
        from core.concord import Concord

        cpg = self._load_cpg(cpg_id)
        hc = self._get_sample_healthcontext()

        # Warmup
        for _ in range(warmup):
            concord = Concord(cpg=cpg, healthcontext=hc)
            concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        # Force garbage collection before benchmark
        gc.collect()

        times_ms = []
        memory_samples = []

        if track_memory:
            tracemalloc.start()

        for _ in range(iterations):
            start = time.perf_counter()

            concord = Concord(cpg=cpg, healthcontext=hc)
            concord.evaluate(skip_eligibility=True, ignore_attestations=True)

            elapsed = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed)

            if track_memory:
                current, peak = tracemalloc.get_traced_memory()
                memory_samples.append(current / 1024 / 1024)  # MB

        if track_memory:
            _, memory_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            memory_peak_mb = memory_peak / 1024 / 1024
            memory_avg_mb = statistics.mean(memory_samples) if memory_samples else 0
        else:
            memory_peak_mb = 0
            memory_avg_mb = 0

        # Calculate statistics
        sorted_times = sorted(times_ms)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)

        return BenchmarkResult(
            cpg_id=cpg_id,
            iterations=iterations,
            total_ms=sum(times_ms),
            avg_ms=statistics.mean(times_ms),
            min_ms=min(times_ms),
            max_ms=max(times_ms),
            std_dev_ms=statistics.stdev(times_ms) if len(times_ms) > 1 else 0,
            p50_ms=statistics.median(times_ms),
            p95_ms=sorted_times[p95_idx],
            p99_ms=sorted_times[p99_idx],
            memory_peak_mb=memory_peak_mb,
            memory_avg_mb=memory_avg_mb,
            evaluations_per_second=1000 / statistics.mean(times_ms),
            all_times_ms=times_ms,
        )

    def benchmark_batch_processing(
        self,
        cpg_id: str,
        patient_counts: list[int] = None,
        modes: list[str] = None,
    ) -> list[BatchBenchmarkResult]:
        """Benchmark batch processing performance.

        Args:
            cpg_id: CPG identifier
            patient_counts: List of patient counts to test
            modes: Processing modes to test

        Returns:
            List of BatchBenchmarkResult for each combination
        """
        from core.batch_processor import BatchProcessor, ProcessingMode

        if patient_counts is None:
            patient_counts = [10, 100, 1000]
        if modes is None:
            modes = ["sequential", "thread_pool"]

        cpg = self._load_cpg(cpg_id)
        base_hc = self._get_sample_healthcontext()

        results = []

        for count in patient_counts:
            # Create patient list
            patients = []
            for i in range(count):
                patients.append((f"patient_{i}", base_hc))

            for mode_str in modes:
                mode = ProcessingMode[mode_str.upper()]
                processor = BatchProcessor(cpg=cpg)

                gc.collect()
                tracemalloc.start()

                start = time.perf_counter()
                report = processor.process(
                    patients=patients,
                    mode=mode,
                    workers=4,
                    skip_eligibility=True,
                    ignore_attestations=True,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                _, memory_peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                results.append(BatchBenchmarkResult(
                    patient_count=count,
                    cpg_id=cpg_id,
                    mode=mode_str,
                    total_ms=elapsed_ms,
                    avg_per_patient_ms=elapsed_ms / count,
                    patients_per_second=(count / elapsed_ms) * 1000,
                    successful_count=report.successful_count,
                    failed_count=report.failed_count,
                    memory_peak_mb=memory_peak / 1024 / 1024,
                ))

        return results

    def benchmark_multi_cpg(
        self,
        cpg_ids: list[str] = None,
        parallel: bool = True,
    ) -> MultiCPGBenchmarkResult:
        """Benchmark multi-CPG evaluation.

        Args:
            cpg_ids: List of CPG IDs to evaluate
            parallel: Whether to run in parallel

        Returns:
            MultiCPGBenchmarkResult with timing metrics
        """
        from core.batch_processor import MultiCPGEvaluator

        if cpg_ids is None:
            cpg_ids = self._get_available_cpgs()[:5]  # First 5 CPGs

        cpgs = [self._load_cpg(cpg_id) for cpg_id in cpg_ids]
        hc = self._get_sample_healthcontext()

        evaluator = MultiCPGEvaluator(cpgs=cpgs, detect_conflicts=True)

        gc.collect()

        start = time.perf_counter()
        result = evaluator.evaluate(
            patient_id="benchmark_patient",
            healthcontext=hc,
            parallel=parallel,
            workers=4,
            skip_eligibility=True,
            ignore_attestations=True,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        conflicts_count = len(result.conflicts.conflicts) if result.conflicts else 0

        return MultiCPGBenchmarkResult(
            cpg_count=len(cpg_ids),
            cpg_ids=cpg_ids,
            parallel=parallel,
            total_ms=elapsed_ms,
            avg_per_cpg_ms=elapsed_ms / len(cpg_ids),
            cpgs_per_second=(len(cpg_ids) / elapsed_ms) * 1000,
            conflicts_detected=conflicts_count,
        )

    def calculate_cost_comparison(
        self,
        scenarios: list[tuple[str, int]] = None,
        llm_model: str = "claude_sonnet",
    ) -> list[LLMCostComparison]:
        """Calculate cost comparison between Concord and LLM.

        Args:
            scenarios: List of (scenario_name, evaluation_count) tuples
            llm_model: LLM model to compare against

        Returns:
            List of LLMCostComparison for each scenario
        """
        if scenarios is None:
            scenarios = [
                ("Single patient", 1),
                ("Small clinic (daily)", 100),
                ("Medium clinic (daily)", 1000),
                ("Large health system (daily)", 10000),
                ("Population health (monthly)", 100000),
            ]

        # First, benchmark Concord to get actual timing
        cpg_ids = self._get_available_cpgs()
        if not cpg_ids:
            return []

        # Get single evaluation time
        bench_result = self.benchmark_single_cpg(cpg_ids[0], iterations=50)
        concord_time_per_eval_ms = bench_result.avg_ms

        results = []
        for scenario_name, count in scenarios:
            concord_time = concord_time_per_eval_ms * count
            concord_cost = 0.0  # Local computation

            llm_cost, llm_time = estimate_llm_cost(llm_model, count)

            speedup = llm_time / concord_time if concord_time > 0 else float('inf')
            savings = llm_cost - concord_cost
            savings_pct = (savings / llm_cost * 100) if llm_cost > 0 else 100

            results.append(LLMCostComparison(
                scenario=scenario_name,
                evaluation_count=count,
                concord_time_ms=concord_time,
                concord_cost_usd=concord_cost,
                llm_estimated_time_ms=llm_time,
                llm_estimated_cost_usd=llm_cost,
                speedup_factor=speedup,
                cost_savings_usd=savings,
                cost_savings_percent=savings_pct,
            ))

        return results

    def run_full_benchmark(
        self,
        cpg_ids: list[str] = None,
        iterations: int = 50,
        include_batch: bool = True,
        include_multi_cpg: bool = True,
        include_cost_comparison: bool = True,
    ) -> BenchmarkReport:
        """Run a full benchmark suite.

        Args:
            cpg_ids: CPGs to benchmark (default: all available)
            iterations: Iterations per CPG
            include_batch: Include batch processing benchmarks
            include_multi_cpg: Include multi-CPG benchmarks
            include_cost_comparison: Include LLM cost comparison

        Returns:
            BenchmarkReport with all results
        """
        import platform
        import sys

        if cpg_ids is None:
            cpg_ids = self._get_available_cpgs()[:5]  # First 5 for speed

        system_info = {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpg_count": len(cpg_ids),
        }

        report = BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            system_info=system_info,
        )

        # Single CPG benchmarks
        log.info(f"Benchmarking {len(cpg_ids)} CPGs...")
        for cpg_id in cpg_ids:
            try:
                result = self.benchmark_single_cpg(cpg_id, iterations=iterations)
                report.single_cpg_results.append(result)
                log.info(f"  {cpg_id}: {result.avg_ms:.2f}ms avg")
            except Exception as e:
                log.warning(f"  {cpg_id}: FAILED - {e}")

        # Batch processing benchmarks
        if include_batch and cpg_ids:
            log.info("Benchmarking batch processing...")
            try:
                batch_results = self.benchmark_batch_processing(
                    cpg_ids[0],
                    patient_counts=[10, 100, 500],
                    modes=["sequential", "thread_pool"],
                )
                report.batch_results.extend(batch_results)
            except Exception as e:
                log.warning(f"Batch benchmark failed: {e}")

        # Multi-CPG benchmarks
        if include_multi_cpg and len(cpg_ids) >= 2:
            log.info("Benchmarking multi-CPG evaluation...")
            try:
                for parallel in [True, False]:
                    result = self.benchmark_multi_cpg(cpg_ids[:5], parallel=parallel)
                    report.multi_cpg_results.append(result)
            except Exception as e:
                log.warning(f"Multi-CPG benchmark failed: {e}")

        # Cost comparison
        if include_cost_comparison:
            log.info("Calculating cost comparisons...")
            try:
                cost_results = self.calculate_cost_comparison()
                report.cost_comparisons.extend(cost_results)
            except Exception as e:
                log.warning(f"Cost comparison failed: {e}")

        return report


def run_benchmark_cli():
    """Run benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Concord benchmarks")
    parser.add_argument("--cpg-dir", default="cpgs", help="CPG directory")
    parser.add_argument("--iterations", type=int, default=50, help="Iterations per CPG")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--quick", action="store_true", help="Quick benchmark (fewer iterations)")

    args = parser.parse_args()

    runner = BenchmarkRunner(cpg_dir=args.cpg_dir)
    iterations = 10 if args.quick else args.iterations

    print("Running Concord benchmarks...")
    report = runner.run_full_benchmark(iterations=iterations)

    print(report.summary())

    if args.output:
        report.save(args.output)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    run_benchmark_cli()
