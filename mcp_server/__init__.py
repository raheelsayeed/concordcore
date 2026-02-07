#!/usr/bin/env python3
"""MCP Server for Concord - Clinical Practice Guideline evaluation.

This module provides an MCP (Model Context Protocol) server that exposes
Concord's clinical decision support capabilities to AI agents.

Tools available:
- list_cpgs: List available clinical practice guidelines
- get_cpg_info: Get detailed CPG information
- create_health_context: Create patient context from variable/value pairs
- create_health_context_from_fhir: Create patient context from FHIR R4 resources
- evaluate_patient: Evaluate patient against a specific CPG
- evaluate_all_cpgs: Evaluate against all CPGs with streaming
- get_recommendations: Get recommendations from evaluation
- get_prioritized_recommendations: Get recommendations ranked by evidence strength
- explain_recommendation: Deep explanation of a recommendation
- get_confidence_scores: Data quality metrics
- get_missing_data: Find missing required data
- submit_attestation: Submit patient-attested data

Example usage with Claude Desktop:
    Add to claude_desktop_config.json:
    {
        "mcpServers": {
            "concord": {
                "command": "python",
                "args": ["-m", "mcp_server"],
                "cwd": "/path/to/concordcore"
            }
        }
    }
"""

from .server import serve, main
from .state import ConcordState, EvaluationSession
from .fhir_handler import FHIRHandler, FHIRParseError
from .confidence import ConfidenceCalculator, ConfidenceScore
from .priority import PriorityRanker, PrioritizedRecommendation, PriorityLevel
from .explanation import ExplanationGenerator, RecommendationExplanation
from .streaming import StreamingEvaluator, StreamProgress, StreamingSummary

__all__ = [
    # Server
    'serve',
    'main',
    # State
    'ConcordState',
    'EvaluationSession',
    # FHIR
    'FHIRHandler',
    'FHIRParseError',
    # Confidence
    'ConfidenceCalculator',
    'ConfidenceScore',
    # Priority
    'PriorityRanker',
    'PrioritizedRecommendation',
    'PriorityLevel',
    # Explanation
    'ExplanationGenerator',
    'RecommendationExplanation',
    # Streaming
    'StreamingEvaluator',
    'StreamProgress',
    'StreamingSummary',
]
