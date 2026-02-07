#!/usr/bin/env python3
"""Async streaming utilities for MCP server.

This module provides streaming evaluation capabilities for evaluating
patients against multiple CPGs with progress updates.

Example usage:
    from mcp_server.streaming import StreamingEvaluator

    evaluator = StreamingEvaluator()
    async for progress in evaluator.evaluate_all_streaming(
        health_context, cpgs
    ):
        print(f"{progress.cpg_id}: {progress.status}")
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, Any
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg import CPG
from core.concord import Concord
from core.healthcontext import HealthContext

log = logging.getLogger(__name__)


@dataclass
class StreamProgress:
    """Progress update for streaming evaluation.

    Attributes:
        cpg_id: CPG identifier being evaluated
        cpg_title: CPG title
        status: Current status ('started', 'completed', 'error')
        progress_pct: Percentage complete (0-100)
        result: Evaluation result if completed
        error: Error message if failed
        current_index: Current CPG index (1-based)
        total_count: Total number of CPGs
    """
    cpg_id: str
    cpg_title: str
    status: str  # 'started', 'completed', 'error'
    progress_pct: float
    result: dict | None = None
    error: str | None = None
    current_index: int = 0
    total_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "cpg_id": self.cpg_id,
            "cpg_title": self.cpg_title,
            "status": self.status,
            "progress_percent": round(self.progress_pct, 1),
            "current_index": self.current_index,
            "total_count": self.total_count,
            "result": self.result,
            "error": self.error
        }


@dataclass
class StreamingSummary:
    """Summary of streaming evaluation results.

    Attributes:
        total_evaluated: Number of CPGs evaluated
        successful: Number of successful evaluations
        failed: Number of failed evaluations
        total_recommendations: Total recommendations generated
        cpgs_with_recommendations: Number of CPGs with applicable recommendations
    """
    total_evaluated: int = 0
    successful: int = 0
    failed: int = 0
    total_recommendations: int = 0
    cpgs_with_recommendations: int = 0
    evaluation_results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_cpgs_evaluated": self.total_evaluated,
                "successful_evaluations": self.successful,
                "failed_evaluations": self.failed,
                "cpgs_with_recommendations": self.cpgs_with_recommendations,
                "total_recommendations": self.total_recommendations
            },
            "evaluations": self.evaluation_results
        }


class StreamingEvaluator:
    """Evaluate multiple CPGs with streaming progress updates.

    Provides async generator for streaming evaluation progress,
    allowing real-time updates as each CPG is evaluated.

    Uses asyncio.run_in_executor() for CPU-bound CPG evaluation
    to avoid blocking the event loop.
    """

    def __init__(self, include_confidence: bool = True):
        """Initialize streaming evaluator.

        Args:
            include_confidence: Whether to include confidence scores
        """
        self.include_confidence = include_confidence

    async def evaluate_all_streaming(
        self,
        health_context: HealthContext,
        cpgs: list[tuple[str, CPG]],
        include_confidence: bool | None = None
    ) -> AsyncGenerator[StreamProgress, None]:
        """Evaluate all CPGs with streaming progress updates.

        Yields StreamProgress updates as each CPG evaluation starts
        and completes, allowing real-time progress tracking.

        Args:
            health_context: Patient health context
            cpgs: List of (identifier, CPG) tuples
            include_confidence: Override instance setting for confidence

        Yields:
            StreamProgress objects for each CPG
        """
        total = len(cpgs)
        confidence = include_confidence if include_confidence is not None else self.include_confidence

        log.info(f"Starting streaming evaluation of {total} CPGs")

        for i, (cpg_id, cpg) in enumerate(cpgs):
            current = i + 1

            # Yield start notification
            yield StreamProgress(
                cpg_id=cpg_id,
                cpg_title=cpg.title,
                status='started',
                progress_pct=(i / total) * 100,
                current_index=current,
                total_count=total
            )

            try:
                # Run evaluation in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._evaluate_single,
                    cpg,
                    health_context,
                    confidence
                )

                yield StreamProgress(
                    cpg_id=cpg_id,
                    cpg_title=cpg.title,
                    status='completed',
                    progress_pct=(current / total) * 100,
                    result=result,
                    current_index=current,
                    total_count=total
                )

            except Exception as e:
                log.error(f"Error evaluating {cpg_id}: {e}")
                yield StreamProgress(
                    cpg_id=cpg_id,
                    cpg_title=cpg.title,
                    status='error',
                    progress_pct=(current / total) * 100,
                    error=str(e),
                    current_index=current,
                    total_count=total
                )

            # Small delay to allow other coroutines
            await asyncio.sleep(0.01)

    def _evaluate_single(
        self,
        cpg: CPG,
        health_context: HealthContext,
        include_confidence: bool
    ) -> dict:
        """Evaluate a single CPG synchronously.

        Called in executor to avoid blocking.

        Args:
            cpg: CPG to evaluate
            health_context: Patient health context
            include_confidence: Whether to include confidence

        Returns:
            Evaluation result dict
        """
        from .confidence import ConfidenceCalculator

        concord = Concord(
            cpg=cpg,
            healthcontext=health_context,
            ignore_eligibility=True
        )

        result = concord.evaluate(
            skip_eligibility=True,
            ignore_attestations=True
        )

        eval_result = {
            "cpg_id": cpg.identifier,
            "cpg_title": cpg.title,
            "is_complete": result.is_complete,
            "is_executable": result.is_executable,
            "recommendations_count": len(result.applied_recommendations) if result.applied_recommendations else 0,
            "applicable_recommendations": []
        }

        if result.recommendations and result.recommendations.applied:
            for rec in result.recommendations.applied:
                rec_data = {
                    "id": rec.recommendation.id,
                    "title": rec.recommendation.title,
                    "narrative": rec.narrative,
                    "type": str(rec.recommendation.type) if rec.recommendation.type else None
                }
                eval_result["applicable_recommendations"].append(rec_data)

        if include_confidence and result.sufficiency:
            try:
                calculator = ConfidenceCalculator()
                confidence = calculator.calculate(concord)
                eval_result["confidence"] = confidence.to_dict()
            except Exception as e:
                log.warning(f"Could not calculate confidence: {e}")

        return eval_result

    async def evaluate_all_with_summary(
        self,
        health_context: HealthContext,
        cpgs: list[tuple[str, CPG]],
        include_confidence: bool | None = None
    ) -> StreamingSummary:
        """Evaluate all CPGs and return summary.

        Collects all streaming results into a summary object.

        Args:
            health_context: Patient health context
            cpgs: List of (identifier, CPG) tuples
            include_confidence: Whether to include confidence

        Returns:
            StreamingSummary with all results
        """
        summary = StreamingSummary()

        async for progress in self.evaluate_all_streaming(
            health_context, cpgs, include_confidence
        ):
            if progress.status == 'completed':
                summary.total_evaluated += 1
                summary.successful += 1
                if progress.result:
                    summary.evaluation_results.append(progress.result)
                    rec_count = progress.result.get('recommendations_count', 0)
                    summary.total_recommendations += rec_count
                    if rec_count > 0:
                        summary.cpgs_with_recommendations += 1
            elif progress.status == 'error':
                summary.total_evaluated += 1
                summary.failed += 1
                summary.evaluation_results.append({
                    "cpg_id": progress.cpg_id,
                    "cpg_title": progress.cpg_title,
                    "error": progress.error
                })

        return summary


async def collect_streaming_results(
    evaluator: StreamingEvaluator,
    health_context: HealthContext,
    cpgs: list[tuple[str, CPG]]
) -> list[StreamProgress]:
    """Utility to collect all streaming results into a list.

    Args:
        evaluator: StreamingEvaluator instance
        health_context: Patient health context
        cpgs: CPGs to evaluate

    Returns:
        List of all StreamProgress updates
    """
    results = []
    async for progress in evaluator.evaluate_all_streaming(health_context, cpgs):
        results.append(progress)
    return results
