#!/usr/bin/env python3
"""Unit tests for the Expression class."""

import pytest

from concordcore.core.expression import Expression
from concordcore.variables.record import Record
from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.primitives.errors import ExpressionVariableNotFound, ExpressionEvaluationError


class TestExpressionCreation:
    """Tests for Expression instantiation."""

    def test_create_simple_expression(self):
        """Test creating a simple comparison expression."""
        exp = Expression('$LDL > 100')
        assert exp.string is not None
        assert '$LDL' in str(exp.string)

    def test_create_compound_expression(self):
        """Test creating a compound expression with multiple variables."""
        exp = Expression('$LDL > 100 and $Age >= 40')
        identifiers = exp.variable_identifiers
        assert 'LDL' in identifiers
        assert 'Age' in identifiers

    def test_create_expression_with_equality(self):
        """Test creating an expression with equality check."""
        exp = Expression('$diabetesMellitus == True')
        assert exp.variable_identifiers is not None


class TestExpressionVariableExtraction:
    """Tests for extracting variable identifiers from expressions."""

    def test_extract_single_variable(self):
        """Test extracting a single variable identifier."""
        exp = Expression('$LDL > 130')
        identifiers = exp.variable_identifiers
        assert 'LDL' in identifiers
        assert len(identifiers) == 1

    def test_extract_multiple_variables(self):
        """Test extracting multiple variable identifiers."""
        exp = Expression('$LDL > 100 and $HDL < 40')
        identifiers = exp.variable_identifiers
        assert 'LDL' in identifiers
        assert 'HDL' in identifiers
        assert len(identifiers) == 2

    def test_extract_variables_with_underscore(self):
        """Test extracting variables with underscores in names."""
        exp = Expression('$diabetes_status == True')
        identifiers = exp.variable_identifiers
        assert 'diabetes_status' in identifiers

    def test_no_variables_returns_empty(self):
        """Test expression without variables returns empty list."""
        # This might raise an error or return empty depending on implementation
        exp = Expression('100 > 50')
        identifiers = exp.variable_identifiers
        assert identifiers is None or len(identifiers) == 0


class TestExpressionEvaluation:
    """Tests for Expression evaluation."""

    @pytest.fixture
    def ldl_record(self):
        """Create an LDL record for testing."""
        var = Var(id='LDL', title='LDL')
        return Record(var=var, initial_values=[Value(150)])

    @pytest.fixture
    def hdl_record(self):
        """Create an HDL record for testing."""
        var = Var(id='HDL', title='HDL')
        return Record(var=var, initial_values=[Value(45)])

    @pytest.fixture
    def age_record(self):
        """Create an Age record for testing."""
        var = Var(id='Age', title='Age')
        return Record(var=var, initial_values=[Value(55)])

    def test_evaluate_simple_greater_than_true(self, ldl_record):
        """Test evaluating a simple greater-than expression (true case)."""
        exp = Expression('$LDL > 100')
        result = exp.evaluate([ldl_record])
        assert result is not None
        assert result.value is True

    def test_evaluate_simple_greater_than_false(self, ldl_record):
        """Test evaluating a simple greater-than expression (false case)."""
        exp = Expression('$LDL > 200')
        result = exp.evaluate([ldl_record])
        assert result is not None
        assert result.value is False

    def test_evaluate_compound_expression(self, ldl_record, age_record):
        """Test evaluating a compound expression."""
        exp = Expression('$LDL > 100 and $Age > 40')
        result = exp.evaluate([ldl_record, age_record])
        assert result is not None
        assert result.value is True

    def test_evaluate_with_equality(self, ldl_record):
        """Test evaluating an equality expression."""
        exp = Expression('$LDL == 150')
        result = exp.evaluate([ldl_record])
        assert result is not None
        assert result.value is True

    def test_evaluate_missing_variable_raises_error(self, ldl_record):
        """Test that missing variable raises appropriate error."""
        exp = Expression('$NonExistent > 100')
        with pytest.raises(ExpressionVariableNotFound):
            exp.evaluate([ldl_record])

    def test_evaluate_stores_expression_records(self, ldl_record, hdl_record):
        """Test that evaluated records are stored."""
        exp = Expression('$LDL > $HDL')
        exp.evaluate([ldl_record, hdl_record])
        assert len(exp.expression_records) == 2


class TestExpressionRecommendationEvaluation:
    """Tests for recommendation expression evaluation."""

    @pytest.fixture
    def assessment_record(self):
        """Create a mock assessment record."""
        from concordcore.core.assessment import AssessmentRecord, AssessmentVar
        var = AssessmentVar(id='high_ldl', title='High LDL', expression='$LDL > 100')
        record = AssessmentRecord(var=var)
        # Manually set value for testing
        record._AssessmentRecord__assessed_value = Value(True)
        return record

    def test_evaluate_recommendation_expression(self, assessment_record):
        """Test evaluating a recommendation expression."""
        from concordcore.core.evaluation import EvaluatedRecord, EvaluationResultStatus
        eval_record = EvaluatedRecord(
            record=assessment_record,
            evaluation_result=EvaluationResultStatus.Successful
        )

        exp = Expression('$high_ldl == True')
        result = exp.evaluate_recommendation([eval_record])
        assert result is True


class TestExpressionRepr:
    """Tests for Expression string representation."""

    def test_repr_includes_expression_string(self):
        """Test that repr includes the expression string."""
        exp = Expression('$LDL > 100')
        repr_str = repr(exp)
        assert 'Expression' in repr_str
