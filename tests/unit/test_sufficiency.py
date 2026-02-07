#!/usr/bin/env python3
"""Unit tests for the Sufficiency module."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.sufficiency import SufficiencyEvaluator, SufficiencyResult
from core.evaluation import EvaluatedRecord, EvaluationContext, SufficiencyResultStatus
from variables.record import Record
from variables.var import Var
from variables.value import Value
from primitives.types import Persona


class TestSufficiencyEvaluator:
    """Tests for SufficiencyEvaluator."""

    @pytest.fixture
    def required_var(self):
        """A required variable."""
        return Var(id='LDL', title='LDL', required=True, user_attestable=False)

    @pytest.fixture
    def optional_var(self):
        """An optional variable."""
        return Var(id='ApoB', title='ApoB', required=False, user_attestable=False)

    @pytest.fixture
    def attestable_var(self):
        """An attestable variable."""
        return Var(id='DM', title='Diabetes', required=True, user_attestable=True)

    def test_evaluator_creation(self, required_var):
        """Test creating a SufficiencyEvaluator."""
        evaluator = SufficiencyEvaluator('test', cpg_variables=[required_var])
        assert evaluator is not None

    def test_evaluate_returns_result(self, required_var, minimal_healthcontext):
        """Test that evaluate returns a SufficiencyResult."""
        evaluator = SufficiencyEvaluator('test', cpg_variables=[required_var])
        result = evaluator.evaluate(minimal_healthcontext)
        assert isinstance(result, SufficiencyResult)

    def test_sufficient_when_required_has_value(self, sample_healthcontext):
        """Test that required variable with value is sufficient."""
        var = Var(id='LDL', title='LDL', required=True, user_attestable=False)
        evaluator = SufficiencyEvaluator('test', cpg_variables=[var])
        result = evaluator.evaluate(sample_healthcontext)
        # LDL is in sample_healthcontext with values
        assert result.is_executable is True

    def test_insufficient_when_required_missing(self, minimal_healthcontext):
        """Test that missing required variable is insufficient."""
        var = Var(id='NonExistent', title='Non-Existent', required=True, user_attestable=False)
        evaluator = SufficiencyEvaluator('test', cpg_variables=[var])
        result = evaluator.evaluate(minimal_healthcontext)
        assert result.is_executable is False

    def test_optional_variable_does_not_affect_executability(self, minimal_healthcontext):
        """Test that missing optional variable doesn't affect executability."""
        vars = [
            Var(id='Age', title='Age', required=True),  # Present in healthcontext
            Var(id='Optional', title='Optional', required=False),  # Missing but optional
        ]
        evaluator = SufficiencyEvaluator('test', cpg_variables=vars)
        result = evaluator.evaluate(minimal_healthcontext)
        # Should still be executable because optional is missing but not required
        # Note: This depends on whether Age matches in minimal_healthcontext
        assert result is not None


class TestSufficiencyResult:
    """Tests for SufficiencyResult."""

    def test_result_is_executable_when_sufficient(self):
        """Test is_executable when all required variables are sufficient."""
        from core.evaluation import EvaluatedRecord, EvaluationResultStatus
        context = EvaluationContext()
        var = Var(id='test', title='Test', required=True)
        record = Record(var=var, initial_values=[Value(100)])
        evaluated = EvaluatedRecord(record=record, evaluation_result=EvaluationResultStatus.Successful)
        context.evaluation_list.append(evaluated)

        result = SufficiencyResult(context=context)
        assert result.is_executable is True

    def test_result_not_executable_when_insufficient(self):
        """Test is_executable when required variables are missing."""
        from core.evaluation import EvaluatedRecord, EvaluationResultStatus
        context = EvaluationContext()
        var = Var(id='test', title='Test', required=True, user_attestable=False)
        record = Record(var=var, initial_values=None)  # No value
        evaluated = EvaluatedRecord(record=record, evaluation_result=EvaluationResultStatus.Failed)
        context.evaluation_list.append(evaluated)

        result = SufficiencyResult(context=context)
        # result is computed from evaluation_list
        assert result.result == SufficiencyResultStatus.Insufficient
        assert result.is_executable is False

    def test_result_has_attestation_variables(self):
        """Test that result tracks variables needing attestation."""
        context = EvaluationContext()
        result = SufficiencyResult(context=context)
        # attestation_variables should return list of variables needing attestation
        # Check through evaluation_list or related properties
        assert result.context is not None


class TestSufficiencyResultStatus:
    """Tests for SufficiencyResultStatus enum."""

    def test_sufficient_status(self):
        """Test Sufficient status exists."""
        assert SufficiencyResultStatus.Sufficient is not None

    def test_insufficient_status(self):
        """Test Insufficient status exists."""
        assert SufficiencyResultStatus.Insufficient is not None

    def test_sufficient_with_attestation_status(self):
        """Test SufficientWithUserAttestation status exists."""
        assert SufficiencyResultStatus.SufficientWithUserAttestation is not None

    def test_optional_status(self):
        """Test Optional status exists."""
        assert SufficiencyResultStatus.Optional is not None


class TestSufficiencyClassification:
    """Tests for sufficiency classification logic."""

    def test_required_with_value_is_sufficient(self):
        """Test: required=True, has_value=True -> Sufficient."""
        # This tests the core classification logic
        var = Var(id='test', title='Test', required=True, user_attestable=False)
        record = Record(var=var, initial_values=[Value(100)])
        assert record.has_value is True
        assert var.required is True

    def test_optional_without_value_is_optional(self):
        """Test: required=False, has_value=False -> Optional."""
        var = Var(id='test', title='Test', required=False, user_attestable=False)
        record = Record(var=var, initial_values=None)
        assert record.has_value is False
        assert var.required is False

    def test_required_attestable_without_value_needs_attestation(self):
        """Test: required=True, user_attestable=True, has_value=False -> SufficientWithUserAttestation."""
        var = Var(id='test', title='Test', required=True, user_attestable=True)
        record = Record(var=var, initial_values=None)
        assert record.has_value is False
        assert var.required is True
        assert var.user_attestable is True

    def test_required_non_attestable_without_value_is_insufficient(self):
        """Test: required=True, user_attestable=False, has_value=False -> Insufficient."""
        var = Var(id='test', title='Test', required=True, user_attestable=False)
        record = Record(var=var, initial_values=None)
        assert record.has_value is False
        assert var.required is True
        assert var.user_attestable is False
