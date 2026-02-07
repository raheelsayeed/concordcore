#!/usr/bin/env python3
"""Unit tests for MCP server components.

Tests cover:
- State management (ConcordState, EvaluationSession)
- Confidence scoring
- Priority ranking
- Explanation generator
- Instruction handlers
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_server.state import ConcordState, EvaluationSession
from mcp_server.confidence import ConfidenceCalculator, ConfidenceScore
from mcp_server.priority import PriorityRanker, PriorityLevel, PrioritizedRecommendation
from mcp_server.explanation import ExplanationGenerator, RecommendationExplanation
from mcp_server.instructions_handler import (
    get_instruction_tools,
    handle_get_llm_instructions,
    handle_build_optimized_prompt,
)

from core.healthcontext import HealthContext
from core.recommendation import ClassOfRecommendation, LevelOfEvidence, USPSTFGrading
from variables.var import Var
from variables.value import Value
from variables.record import Record
from primitives.types import Persona


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def cpgs_dir(tmp_path):
    """Create a temporary CPGs directory with test CPG files."""
    cpgs = tmp_path / "cpgs"
    cpgs.mkdir()

    # Create a minimal test CPG - matches actual CPG YAML structure
    test_cpg = cpgs / "test_cpg.yaml"
    test_cpg.write_text("""
CPG:
  identifier: test_cpg
  title: Test CPG
  publisher: Test Publisher
  revision: "1.0"

variables:
  - id: Age
    title: Age
    required: true
    type: integer
  - id: LDL
    title: LDL Cholesterol
    required: true
    type: decimal

eligibility:
  - id: age_eligible
    expression: "$Age >= 18"

assessments:
  - id: high_ldl
    title: High LDL
    expression: "$LDL > 130"

recommendations:
  - id: rec_statin
    title: Consider Statin Therapy
    expression: "$high_ldl == True"
""")
    return cpgs


@pytest.fixture
def state(cpgs_dir):
    """Create a ConcordState with test CPGs directory."""
    return ConcordState(cpgs_dir=cpgs_dir)


@pytest.fixture
def sample_health_context():
    """Create a sample health context."""
    age_var = Var(id="Age", title="Age", required=True)
    ldl_var = Var(id="LDL", title="LDL Cholesterol", required=True)

    age_record = Record(var=age_var, initial_values=[Value(value=55)])
    ldl_record = Record(var=ldl_var, initial_values=[Value(value=145)])

    return HealthContext(records=[age_record, ldl_record], persona=Persona.patient)


@pytest.fixture
def mock_concord():
    """Create a mock Concord instance."""
    concord = MagicMock()

    # Mock CPG
    concord.cpg.title = "Test CPG"
    concord.cpg.identifier = "test_cpg"

    # Mock sufficiency result
    mock_eval_record = MagicMock()
    mock_eval_record.record.var.required = True
    mock_eval_record.record.has_value = True
    mock_eval_record.record.value.date = datetime.now()
    mock_eval_record.error = None

    concord.sufficiency_result.context.evaluation_list = [mock_eval_record]
    concord.sufficiency_result.attestation_variables = []

    return concord


@pytest.fixture
def mock_evaluated_recommendation():
    """Create a mock evaluated recommendation."""
    rec = MagicMock()
    rec.applies = True
    rec.narrative = "Consider statin therapy based on LDL levels."
    rec.based_on = []

    rec.recommendation.id = "rec_statin"
    rec.recommendation.title = "Consider Statin Therapy"
    rec.recommendation.type = None
    rec.recommendation.class_of_recommendation = ClassOfRecommendation.I
    rec.recommendation.level_of_evidence = LevelOfEvidence.A
    rec.recommendation.uspstf_grade = None
    rec.recommendation.citations = ["Citation 1", "Citation 2"]

    return rec


# =============================================================================
# STATE MANAGEMENT TESTS
# =============================================================================

class TestEvaluationSession:
    """Tests for EvaluationSession dataclass."""

    def test_create_session(self):
        """Test creating an evaluation session."""
        session = EvaluationSession(session_id="test-123")
        assert session.session_id == "test-123"
        assert session.health_context is None
        assert session.cpg_evaluations == {}
        assert session.attestations == {}

    def test_session_created_at(self):
        """Test that session has created_at timestamp."""
        before = datetime.now()
        session = EvaluationSession(session_id="test")
        after = datetime.now()
        assert before <= session.created_at <= after

    def test_has_health_context(self):
        """Test has_health_context property."""
        session = EvaluationSession(session_id="test")
        assert session.has_health_context is False

        session.health_context = MagicMock()
        assert session.has_health_context is True

    def test_active_concord_empty(self):
        """Test active_concord when no evaluations."""
        session = EvaluationSession(session_id="test")
        assert session.active_concord is None

    def test_active_concord_returns_last(self):
        """Test active_concord returns most recent."""
        session = EvaluationSession(session_id="test")
        mock1 = MagicMock()
        mock2 = MagicMock()

        session.cpg_evaluations["cpg1"] = mock1
        session.cpg_evaluations["cpg2"] = mock2

        assert session.active_concord == mock2

    def test_store_evaluation(self):
        """Test storing evaluation."""
        session = EvaluationSession(session_id="test")
        mock = MagicMock()

        session.store_evaluation("cpg1", mock)
        assert session.get_evaluation("cpg1") == mock

    def test_get_evaluation_not_found(self):
        """Test getting non-existent evaluation."""
        session = EvaluationSession(session_id="test")
        assert session.get_evaluation("nonexistent") is None


class TestConcordState:
    """Tests for ConcordState class."""

    def test_create_state(self, cpgs_dir):
        """Test creating state manager."""
        state = ConcordState(cpgs_dir=cpgs_dir)
        assert state.cpgs_dir == cpgs_dir
        assert state.loaded_cpgs == {}
        assert state.sessions == {}

    def test_get_session_creates_new(self, state):
        """Test get_session creates new session."""
        session = state.get_session("new-session")
        assert session is not None
        assert session.session_id == "new-session"
        assert "new-session" in state.sessions

    def test_get_session_returns_existing(self, state):
        """Test get_session returns existing session."""
        session1 = state.get_session("test")
        session2 = state.get_session("test")
        assert session1 is session2

    def test_get_session_no_create(self, state):
        """Test get_session with create=False."""
        result = state.get_session("nonexistent", create=False)
        assert result is None
        assert "nonexistent" not in state.sessions

    def test_delete_session(self, state):
        """Test deleting a session."""
        state.get_session("to-delete")
        assert state.delete_session("to-delete") is True
        assert "to-delete" not in state.sessions

    def test_delete_session_not_found(self, state):
        """Test deleting non-existent session."""
        assert state.delete_session("nonexistent") is False

    def test_get_available_cpgs(self, state, cpgs_dir):
        """Test listing available CPGs."""
        cpgs = state.get_available_cpgs()
        assert len(cpgs) == 1
        assert cpgs[0]["identifier"] == "test_cpg"
        assert cpgs[0]["filename"] == "test_cpg.yaml"

    def test_load_cpg(self, state):
        """Test loading a CPG."""
        cpg = state.load_cpg("test_cpg")
        assert cpg.identifier == "test_cpg"
        assert cpg.title == "Test CPG"

    def test_load_cpg_cached(self, state):
        """Test CPG caching."""
        cpg1 = state.load_cpg("test_cpg")
        cpg2 = state.load_cpg("test_cpg")
        assert cpg1 is cpg2

    def test_load_cpg_not_found(self, state):
        """Test loading non-existent CPG."""
        with pytest.raises(FileNotFoundError):
            state.load_cpg("nonexistent")

    def test_reload_cpg(self, state):
        """Test reloading a CPG."""
        cpg1 = state.load_cpg("test_cpg")
        cpg2 = state.reload_cpg("test_cpg")
        assert cpg1 is not cpg2

    def test_cleanup_stale_sessions(self, state):
        """Test cleaning up stale sessions."""
        # Create a stale session
        session = state.get_session("stale")
        session.created_at = datetime.now() - timedelta(hours=25)

        # Create a fresh session
        state.get_session("fresh")

        cleaned = state.cleanup_stale_sessions(max_age_hours=24)
        assert cleaned == 1
        assert "stale" not in state.sessions
        assert "fresh" in state.sessions

    def test_session_count(self, state):
        """Test session count."""
        assert state.session_count() == 0
        state.get_session("s1")
        state.get_session("s2")
        assert state.session_count() == 2

    def test_cpg_count(self, state):
        """Test CPG count."""
        assert state.cpg_count() == 0
        state.load_cpg("test_cpg")
        assert state.cpg_count() == 1


# =============================================================================
# CONFIDENCE SCORING TESTS
# =============================================================================

class TestConfidenceScore:
    """Tests for ConfidenceScore dataclass."""

    def test_create_score(self):
        """Test creating a confidence score."""
        score = ConfidenceScore(
            overall=0.85,
            completeness=0.9,
            freshness=0.8,
            validation=0.9,
            attestation_burden=0.75,
            total_required=10,
            total_with_data=9,
            oldest_data_days=30,
            validation_passed=9,
            validation_total=10,
            attestations_needed=2
        )
        assert score.overall == 0.85
        assert score.completeness == 0.9

    def test_to_dict(self):
        """Test converting score to dict."""
        score = ConfidenceScore(
            overall=0.85,
            completeness=0.9,
            freshness=0.8,
            validation=0.9,
            attestation_burden=0.75,
            total_required=10,
            total_with_data=9,
            oldest_data_days=30,
            validation_passed=9,
            validation_total=10,
            attestations_needed=2
        )
        result = score.to_dict()
        assert "overall_confidence" in result
        assert "confidence_level" in result
        assert "components" in result
        assert "details" in result

    def test_confidence_level_high(self):
        """Test HIGH confidence level."""
        score = ConfidenceScore(
            overall=0.92,
            completeness=1.0, freshness=1.0, validation=1.0, attestation_burden=1.0,
            total_required=5, total_with_data=5, oldest_data_days=0,
            validation_passed=5, validation_total=5, attestations_needed=0
        )
        assert score._confidence_level() == "HIGH"

    def test_confidence_level_moderate(self):
        """Test MODERATE confidence level."""
        score = ConfidenceScore(
            overall=0.75,
            completeness=0.8, freshness=0.7, validation=0.8, attestation_burden=0.7,
            total_required=5, total_with_data=4, oldest_data_days=60,
            validation_passed=4, validation_total=5, attestations_needed=1
        )
        assert score._confidence_level() == "MODERATE"

    def test_confidence_level_low(self):
        """Test LOW confidence level."""
        score = ConfidenceScore(
            overall=0.55,
            completeness=0.6, freshness=0.5, validation=0.6, attestation_burden=0.5,
            total_required=5, total_with_data=3, oldest_data_days=200,
            validation_passed=3, validation_total=5, attestations_needed=2
        )
        assert score._confidence_level() == "LOW"

    def test_confidence_level_very_low(self):
        """Test VERY_LOW confidence level."""
        score = ConfidenceScore(
            overall=0.3,
            completeness=0.4, freshness=0.2, validation=0.3, attestation_burden=0.3,
            total_required=5, total_with_data=2, oldest_data_days=500,
            validation_passed=1, validation_total=5, attestations_needed=3
        )
        assert score._confidence_level() == "VERY_LOW"


class TestConfidenceCalculator:
    """Tests for ConfidenceCalculator."""

    def test_calculator_creation(self):
        """Test creating calculator."""
        calc = ConfidenceCalculator()
        assert calc.WEIGHT_COMPLETENESS == 0.35
        assert calc.WEIGHT_FRESHNESS == 0.25

    def test_calculate_with_mock(self, mock_concord):
        """Test calculating confidence with mock."""
        calc = ConfidenceCalculator()
        score = calc.calculate(mock_concord)

        assert isinstance(score, ConfidenceScore)
        assert 0.0 <= score.overall <= 1.0
        assert score.total_required >= 0

    def test_calculate_no_sufficiency(self):
        """Test calculate with no sufficiency result."""
        concord = MagicMock()
        concord.sufficiency_result = None

        calc = ConfidenceCalculator()
        score = calc.calculate(concord)

        assert score.overall == 0.0
        assert score.total_required == 0

    def test_age_to_freshness_optimal(self):
        """Test freshness for optimal age data."""
        calc = ConfidenceCalculator()
        assert calc._age_to_freshness(10) == 1.0
        assert calc._age_to_freshness(30) == 1.0

    def test_age_to_freshness_good(self):
        """Test freshness for good age data."""
        calc = ConfidenceCalculator()
        assert calc._age_to_freshness(60) == 0.8
        assert calc._age_to_freshness(90) == 0.8

    def test_age_to_freshness_acceptable(self):
        """Test freshness for acceptable age data."""
        calc = ConfidenceCalculator()
        assert calc._age_to_freshness(180) == 0.5
        assert calc._age_to_freshness(365) == 0.5

    def test_age_to_freshness_stale(self):
        """Test freshness for stale data."""
        calc = ConfidenceCalculator()
        assert calc._age_to_freshness(800) == 0.2


# =============================================================================
# PRIORITY RANKING TESTS
# =============================================================================

class TestPriorityLevel:
    """Tests for PriorityLevel enum."""

    def test_priority_ordering(self):
        """Test priority levels are correctly ordered."""
        assert PriorityLevel.CRITICAL < PriorityLevel.HIGH
        assert PriorityLevel.HIGH < PriorityLevel.MODERATE
        assert PriorityLevel.MODERATE < PriorityLevel.LOW
        assert PriorityLevel.LOW < PriorityLevel.INFORMATIONAL

    def test_to_dict(self):
        """Test to_dict conversion."""
        result = PriorityLevel.CRITICAL.to_dict()
        assert result["level"] == "CRITICAL"
        assert result["value"] == 1
        assert "description" in result


class TestPrioritizedRecommendation:
    """Tests for PrioritizedRecommendation dataclass."""

    def test_to_dict(self, mock_evaluated_recommendation):
        """Test to_dict conversion."""
        pr = PrioritizedRecommendation(
            recommendation=mock_evaluated_recommendation,
            priority_level=PriorityLevel.HIGH,
            priority_score=85.5,
            rationale="Strong recommendation"
        )
        result = pr.to_dict()

        assert result["id"] == "rec_statin"
        assert result["priority_level"] == "HIGH"
        assert result["priority_score"] == 85.5
        assert "evidence" in result


class TestPriorityRanker:
    """Tests for PriorityRanker."""

    def test_ranker_creation(self):
        """Test creating ranker."""
        ranker = PriorityRanker()
        assert ranker.WEIGHT_COR == 0.45
        assert ranker.WEIGHT_LOE == 0.35

    def test_rank_empty_list(self):
        """Test ranking empty list."""
        ranker = PriorityRanker()
        result = ranker.rank([])
        assert result == []

    def test_rank_single_recommendation(self, mock_evaluated_recommendation):
        """Test ranking single recommendation."""
        ranker = PriorityRanker()
        result = ranker.rank([mock_evaluated_recommendation])

        assert len(result) == 1
        assert result[0].recommendation == mock_evaluated_recommendation
        assert result[0].priority_score > 0

    def test_rank_excludes_non_applicable(self, mock_evaluated_recommendation):
        """Test non-applicable excluded by default."""
        mock_evaluated_recommendation.applies = False

        ranker = PriorityRanker()
        result = ranker.rank([mock_evaluated_recommendation])

        assert len(result) == 0

    def test_rank_includes_non_applicable_when_requested(self, mock_evaluated_recommendation):
        """Test non-applicable included when requested."""
        mock_evaluated_recommendation.applies = False

        ranker = PriorityRanker()
        result = ranker.rank([mock_evaluated_recommendation], include_non_applicable=True)

        assert len(result) == 1

    def test_calculate_score_class_I(self, mock_evaluated_recommendation):
        """Test score calculation for Class I recommendation."""
        ranker = PriorityRanker()
        score = ranker._calculate_score(mock_evaluated_recommendation)

        # Class I (100) * 0.45 + LOE A (100) * 0.35 + default (50) * 0.20 = 90
        assert score >= 80

    def test_determine_level_critical(self, mock_evaluated_recommendation):
        """Test CRITICAL level determination."""
        ranker = PriorityRanker()
        level = ranker._determine_level(85.0, mock_evaluated_recommendation)
        assert level == PriorityLevel.CRITICAL

    def test_determine_level_high(self, mock_evaluated_recommendation):
        """Test HIGH level determination."""
        mock_evaluated_recommendation.recommendation.class_of_recommendation = None

        ranker = PriorityRanker()
        level = ranker._determine_level(75.0, mock_evaluated_recommendation)
        assert level == PriorityLevel.HIGH

    def test_get_summary(self, mock_evaluated_recommendation):
        """Test get_summary."""
        ranker = PriorityRanker()
        prioritized = ranker.rank([mock_evaluated_recommendation])
        summary = ranker.get_summary(prioritized)

        assert summary["total"] == 1
        assert "by_level" in summary
        assert "highest_priority" in summary


# =============================================================================
# EXPLANATION GENERATOR TESTS
# =============================================================================

class TestRecommendationExplanation:
    """Tests for RecommendationExplanation dataclass."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        explanation = RecommendationExplanation(
            recommendation_id="rec_test",
            title="Test Recommendation",
            applies=True,
            assessment_chain=[{"id": "assessment1", "value": True}],
            citations=["Citation 1"],
            class_of_recommendation="I",
            level_of_evidence="A",
            uspstf_grade=None,
            patient_summary="Patient summary",
            provider_summary="Provider summary",
            source_data=[{"variable_id": "LDL", "value": 145}]
        )
        result = explanation.to_dict()

        assert result["recommendation_id"] == "rec_test"
        assert result["applies"] is True
        assert len(result["assessment_chain"]) == 1
        assert "evidence" in result
        assert "summaries" in result


class TestExplanationGenerator:
    """Tests for ExplanationGenerator."""

    def test_generator_creation(self):
        """Test creating generator."""
        gen = ExplanationGenerator()
        assert gen is not None

    def test_explain_not_found(self):
        """Test explain with non-existent recommendation."""
        concord = MagicMock()
        concord.evaluated_recommendation.return_value = None

        gen = ExplanationGenerator()
        with pytest.raises(ValueError, match="not found"):
            gen.explain(concord, "nonexistent")

    def test_explain_found(self, mock_evaluated_recommendation):
        """Test explain with valid recommendation."""
        concord = MagicMock()
        concord.evaluated_recommendation.return_value = mock_evaluated_recommendation

        gen = ExplanationGenerator()
        result = gen.explain(concord, "rec_statin")

        assert isinstance(result, RecommendationExplanation)
        assert result.recommendation_id == "rec_statin"
        assert result.applies is True

    def test_patient_summary_applicable(self, mock_evaluated_recommendation):
        """Test patient summary for applicable recommendation."""
        gen = ExplanationGenerator()
        summary = gen._generate_patient_summary(
            mock_evaluated_recommendation,
            [{"id": "high_ldl", "title": "High LDL", "value": True}],
            [{"variable_id": "LDL", "value": 145}]
        )

        assert "based on your health information" in summary.lower()

    def test_patient_summary_not_applicable(self, mock_evaluated_recommendation):
        """Test patient summary for non-applicable recommendation."""
        mock_evaluated_recommendation.applies = False

        gen = ExplanationGenerator()
        summary = gen._generate_patient_summary(
            mock_evaluated_recommendation, [], []
        )

        assert "does not apply" in summary.lower()

    def test_provider_summary(self, mock_evaluated_recommendation):
        """Test provider summary generation."""
        gen = ExplanationGenerator()
        summary = gen._generate_provider_summary(
            mock_evaluated_recommendation,
            [{"id": "high_ldl", "expression": "$LDL > 130", "value": True}],
            [{"variable_id": "LDL", "value": 145, "date": "2024-01-01"}]
        )

        assert "RECOMMENDATION:" in summary
        assert "COR:" in summary
        assert "ASSESSMENT LOGIC:" in summary


# =============================================================================
# INSTRUCTION HANDLER TESTS
# =============================================================================

class TestInstructionTools:
    """Tests for instruction MCP tools."""

    def test_get_instruction_tools(self):
        """Test getting instruction tools."""
        tools = get_instruction_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "get_llm_instructions" in tool_names
        assert "build_optimized_prompt" in tool_names

    def test_tool_schemas(self):
        """Test tool schemas are valid."""
        tools = get_instruction_tools()

        for tool in tools:
            assert tool.inputSchema is not None
            assert "type" in tool.inputSchema
            assert "properties" in tool.inputSchema


class TestInstructionHandlers:
    """Tests for instruction handler functions."""

    def test_get_llm_instructions_claude(self):
        """Test getting Claude instructions."""
        result = asyncio.run(handle_get_llm_instructions({
            "provider": "claude",
            "context": "extraction"
        }))

        assert len(result) == 1
        data = json.loads(result[0].text)

        assert data["provider"] == "claude"
        assert data["context"] == "extraction"
        assert "instructions" in data
        assert data["instructions"]["formatting_style"] == "xml_tags"

    def test_get_llm_instructions_openai(self):
        """Test getting OpenAI instructions."""
        result = asyncio.run(handle_get_llm_instructions({
            "provider": "openai",
            "context": "conversation"
        }))

        data = json.loads(result[0].text)
        assert data["provider"] == "openai"
        assert data["instructions"]["formatting_style"] == "markdown"

    def test_get_llm_instructions_invalid_context(self):
        """Test with invalid context."""
        result = asyncio.run(handle_get_llm_instructions({
            "provider": "claude",
            "context": "invalid_context"
        }))

        data = json.loads(result[0].text)
        assert "error" in data

    def test_build_optimized_prompt(self):
        """Test building optimized prompt."""
        result = asyncio.run(handle_build_optimized_prompt({
            "provider": "claude",
            "context": "extraction",
            "user_content": "Extract LDL from: LDL-C 145 mg/dL"
        }))

        data = json.loads(result[0].text)

        assert data["provider"] == "claude"
        assert "prompt" in data
        assert "system" in data["prompt"]
        assert "user" in data["prompt"]
        assert "145" in data["prompt"]["user"]

    def test_build_optimized_prompt_no_content(self):
        """Test with missing user_content."""
        result = asyncio.run(handle_build_optimized_prompt({
            "provider": "claude",
            "context": "extraction",
            "user_content": ""
        }))

        data = json.loads(result[0].text)
        assert "error" in data

    def test_build_optimized_prompt_with_additional_context(self):
        """Test with additional context."""
        result = asyncio.run(handle_build_optimized_prompt({
            "provider": "claude",
            "context": "conversation",
            "user_content": "Why do I need a statin?",
            "additional_context": "Patient has LDL 180 mg/dL"
        }))

        data = json.loads(result[0].text)
        assert "LDL 180" in data["prompt"]["system"]


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestMCPServerIntegration:
    """Integration tests for MCP server components."""

    def test_full_workflow(self, state, sample_health_context):
        """Test full evaluation workflow through state management."""
        # Create session
        session = state.get_session("integration-test")
        session.health_context = sample_health_context

        # Load CPG
        cpg = state.load_cpg("test_cpg")
        assert cpg is not None

        # Verify session state
        assert session.has_health_context
        assert state.session_count() == 1
        assert state.cpg_count() == 1

    def test_confidence_and_priority_integration(self, mock_concord, mock_evaluated_recommendation):
        """Test confidence and priority work together."""
        # Calculate confidence
        calc = ConfidenceCalculator()
        score = calc.calculate(mock_concord)

        # Rank recommendations
        ranker = PriorityRanker()
        prioritized = ranker.rank([mock_evaluated_recommendation])

        # Both should work
        assert score.overall >= 0
        assert len(prioritized) == 1

    def test_explanation_with_ranker(self, mock_evaluated_recommendation):
        """Test explanation works with prioritized recommendations."""
        concord = MagicMock()
        concord.evaluated_recommendation.return_value = mock_evaluated_recommendation

        # Rank first
        ranker = PriorityRanker()
        prioritized = ranker.rank([mock_evaluated_recommendation])

        # Then explain
        gen = ExplanationGenerator()
        explanation = gen.explain(concord, prioritized[0].recommendation.recommendation.id)

        assert explanation is not None
        assert explanation.applies is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
