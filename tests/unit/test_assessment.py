#!/usr/bin/env python3
"""Unit tests for the Assessment module."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.assessment import AssessmentVar, AssessmentRecord, AssessmentEvaluator, AssessmentResult, AssessedRecord
from core.evaluation import EvaluatedRecord, EvaluationResultStatus
from variables.record import Record
from variables.var import Var, Narrative
from variables.value import Value
from primitives.types import Persona


class TestAssessmentVarCreation:
    """Tests for AssessmentVar instantiation."""

    def test_create_assessment_var_with_expression(self):
        """Test creating an AssessmentVar with an expression."""
        av = AssessmentVar(
            id='high_ldl',
            title='High LDL Assessment',
            expression='$LDL > 130'
        )
        assert av.id == 'high_ldl'
        assert av.expression == '$LDL > 130'
        assert av.function is None

    def test_create_assessment_var_with_function(self):
        """Test creating an AssessmentVar with a function."""
        av = AssessmentVar(
            id='risk_score',
            title='Risk Score',
            function='calculate_risk'
        )
        assert av.id == 'risk_score'
        assert av.function == 'calculate_risk'
        assert av.expression is None

    def test_assessment_var_requires_expression_or_function(self):
        """Test that AssessmentVar requires either expression or function."""
        with pytest.raises(Exception, match='must have either an expression or a function'):
            AssessmentVar(id='invalid', title='Invalid')

    def test_assessment_var_with_narrative(self):
        """Test creating an AssessmentVar with narrative."""
        narrative = Narrative({
            'patient': {True: 'High', False: 'Normal'},
            'provider': {True: 'Elevated', False: 'Within range'}
        })
        av = AssessmentVar(
            id='test',
            title='Test',
            expression='$LDL > 100',
            narr=narrative
        )
        assert av.narr is not None


class TestAssessmentVarFromYaml:
    """Tests for AssessmentVar YAML instantiation."""

    def test_instantiate_from_yaml_with_expression(self):
        """Test instantiating AssessmentVar from YAML dict."""
        yml = {
            'id': 'ldl_high',
            'title': 'LDL High',
            'expression': '$LDL > 189'
        }
        av = AssessmentVar.instantiate_from_yaml(yml)
        assert av.id == 'ldl_high'
        assert av.expression == '$LDL > 189'

    def test_instantiate_from_yaml_with_narrative(self):
        """Test instantiating AssessmentVar with narrative from YAML."""
        yml = {
            'id': 'test',
            'title': 'Test',
            'expression': '$LDL > 100',
            'narrative': {
                'patient': {True: 'Elevated LDL'},
                'provider': {True: 'LDL above threshold'}
            }
        }
        av = AssessmentVar.instantiate_from_yaml(yml)
        assert av.narr is not None


class TestAssessmentRecordCreation:
    """Tests for AssessmentRecord instantiation."""

    def test_create_assessment_record(self, sample_assessment_var):
        """Test creating an AssessmentRecord."""
        ar = AssessmentRecord(var=sample_assessment_var)
        assert ar.var == sample_assessment_var
        assert ar.value is None  # Not yet evaluated

    def test_assessment_record_has_expression(self, sample_assessment_var):
        """Test that AssessmentRecord initializes expression."""
        ar = AssessmentRecord(var=sample_assessment_var)
        assert ar.expression is not None


class TestAssessmentRecordEvaluation:
    """Tests for AssessmentRecord evaluation."""

    @pytest.fixture
    def ldl_record(self):
        """Create an LDL record for testing."""
        var = Var(id='LDL', title='LDL')
        return Record(var=var, initial_values=[Value(150)])

    @pytest.fixture
    def assessment_var_ldl(self):
        """Create an assessment var for LDL check."""
        return AssessmentVar(
            id='high_ldl',
            title='High LDL',
            expression='$LDL > 100'
        )

    def test_evaluate_returns_value(self, assessment_var_ldl, ldl_record):
        """Test that evaluate returns a value."""
        ar = AssessmentRecord(var=assessment_var_ldl)
        result = ar.evaluate([ldl_record])
        assert result is not None
        assert ar.value is not None

    def test_evaluate_expression_true(self, assessment_var_ldl, ldl_record):
        """Test evaluation when expression is true."""
        ar = AssessmentRecord(var=assessment_var_ldl)
        ar.evaluate([ldl_record])
        assert ar.value.value is True

    def test_evaluate_expression_false(self, ldl_record):
        """Test evaluation when expression is false."""
        av = AssessmentVar(id='low_ldl', title='Low LDL', expression='$LDL < 100')
        ar = AssessmentRecord(var=av)
        ar.evaluate([ldl_record])
        assert ar.value.value is False

    def test_evaluate_sets_narrative(self, ldl_record):
        """Test that evaluation sets narrative."""
        av = AssessmentVar(
            id='test',
            title='Test',
            expression='$LDL > 100',
            narr=Narrative({
                'patient': {True: 'LDL is high', False: 'LDL is normal'}
            })
        )
        ar = AssessmentRecord(var=av)
        ar.evaluate([ldl_record], persona=Persona.patient)
        assert ar.narrative is not None


class TestAssessmentEvaluator:
    """Tests for AssessmentEvaluator."""

    @pytest.fixture
    def ldl_evaluated_record(self):
        """Create an evaluated LDL record."""
        from core.evaluation import EvaluationResultStatus
        var = Var(id='LDL', title='LDL')
        record = Record(var=var, initial_values=[Value(150)])
        return EvaluatedRecord(record=record, evaluation_result=EvaluationResultStatus.Successful)

    @pytest.fixture
    def assessment_variables(self):
        """Create a list of assessment variables."""
        return [
            AssessmentVar(id='high_ldl', title='High LDL', expression='$LDL > 130'),
            AssessmentVar(id='very_high_ldl', title='Very High LDL', expression='$LDL > 190'),
        ]

    def test_assess_returns_result(self, assessment_variables, ldl_evaluated_record):
        """Test that assess returns an AssessmentResult."""
        evaluator = AssessmentEvaluator()
        result = evaluator.assess(
            assessment_variables=assessment_variables,
            evaluated_records=[ldl_evaluated_record]
        )
        assert isinstance(result, AssessmentResult)

    def test_assess_evaluates_all_variables(self, assessment_variables, ldl_evaluated_record):
        """Test that all assessment variables are evaluated."""
        evaluator = AssessmentEvaluator()
        result = evaluator.assess(
            assessment_variables=assessment_variables,
            evaluated_records=[ldl_evaluated_record]
        )
        assert len(result.assessments) == len(assessment_variables)

    def test_assess_with_chained_assessments(self, ldl_evaluated_record):
        """Test assessment that references another assessment."""
        av1 = AssessmentVar(id='high_ldl', title='High LDL', expression='$LDL > 130')
        # av2 references av1 - this tests chained assessments
        av2 = AssessmentVar(id='needs_statin', title='Needs Statin', expression='$high_ldl == True')

        evaluator = AssessmentEvaluator()
        result = evaluator.assess(
            assessment_variables=[av1, av2],
            evaluated_records=[ldl_evaluated_record]
        )
        # First assessment should be True (150 > 130)
        # Second should also be True (high_ldl == True)
        assert result.assessments[0].value.value is True
        assert result.assessments[1].value.value is True


class TestAssessmentResult:
    """Tests for AssessmentResult."""

    def test_assessment_result_success(self):
        """Test AssessmentResult success property."""
        av = AssessmentVar(id='test', title='Test', expression='$x > 0')
        ar = AssessmentRecord(var=av)
        assessed = AssessedRecord(
            record=ar,
            evaluation_result=EvaluationResultStatus.Successful
        )

        result = AssessmentResult(assessments=[assessed])
        assert result.success is True
