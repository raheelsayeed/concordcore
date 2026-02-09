#!/usr/bin/env python3
"""Shared pytest fixtures for ConcordCore tests.

This module provides reusable fixtures for testing the ConcordCore framework,
including sample Values, Vars, Records, HealthContexts, and CPGs.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from variables.value import Value
from variables.var import Var, Narrative
from variables.record import Record
from primitives.code import Code
from primitives.types import Persona, ValueType


# ============================================================================
# Value Fixtures
# ============================================================================

@pytest.fixture
def sample_value():
    """A basic numeric Value object."""
    return Value(100)


@pytest.fixture
def sample_value_with_date():
    """A Value object with a specific date."""
    return Value(150, date=datetime(2024, 1, 15))


@pytest.fixture
def sample_boolean_value_true():
    """A boolean True Value."""
    return Value(True)


@pytest.fixture
def sample_boolean_value_false():
    """A boolean False Value."""
    return Value(False)


@pytest.fixture
def sample_values_list():
    """A list of Values with different dates."""
    base_date = datetime.now()
    return [
        Value(100, date=base_date - timedelta(days=30)),
        Value(110, date=base_date - timedelta(days=20)),
        Value(105, date=base_date - timedelta(days=10)),
        Value(115, date=base_date),
    ]


# ============================================================================
# Var Fixtures
# ============================================================================

@pytest.fixture
def sample_var():
    """A basic Var object with minimal properties."""
    return Var(id='TestVar', title='Test Variable')


@pytest.fixture
def sample_var_required():
    """A required Var that is not user-attestable."""
    return Var(
        id='RequiredVar',
        title='Required Variable',
        required=True,
        user_attestable=False
    )


@pytest.fixture
def sample_var_attestable():
    """A Var that is user-attestable."""
    return Var(
        id='AttestableVar',
        title='Attestable Variable',
        required=True,
        user_attestable=True
    )


@pytest.fixture
def sample_var_optional():
    """An optional Var."""
    return Var(
        id='OptionalVar',
        title='Optional Variable',
        required=False,
        user_attestable=False
    )


@pytest.fixture
def sample_ldl_var():
    """A Var representing LDL cholesterol with LOINC code."""
    return Var(
        id='LDL',
        title='Low Density Lipoprotein',
        code=[Code.loinc('13457-7')],
        required=True,
        user_attestable=False
    )


@pytest.fixture
def sample_var_with_narrative():
    """A Var with narratives defined."""
    narrative_data = {
        'patient': {
            'HasValue': 'Your test result is $self.value',
            'NoValue': 'Test result not found in your record',
            True: 'Result is positive',
            False: 'Result is negative'
        },
        'provider': {
            'HasValue': 'Value: $self.value',
            'NoValue': 'Not in record',
            True: 'Positive',
            False: 'Negative'
        }
    }
    return Var(
        id='NarrativeVar',
        title='Variable with Narrative',
        narr=Narrative(narrative_data)
    )


# ============================================================================
# Record Fixtures
# ============================================================================

@pytest.fixture
def sample_record(sample_var, sample_value):
    """A basic Record with a single Value."""
    return Record(var=sample_var, initial_values=[sample_value])


@pytest.fixture
def sample_record_no_value(sample_var):
    """A Record without any values."""
    return Record(var=sample_var, initial_values=None)


@pytest.fixture
def sample_ldl_record(sample_ldl_var, sample_values_list):
    """An LDL Record with multiple values."""
    return Record(var=sample_ldl_var, initial_values=sample_values_list)


@pytest.fixture
def sample_record_attestable(sample_var_attestable):
    """An attestable Record without initial values."""
    return Record(var=sample_var_attestable, initial_values=None)


# ============================================================================
# Code Fixtures
# ============================================================================

@pytest.fixture
def sample_loinc_code():
    """A LOINC code for LDL."""
    return Code.loinc('13457-7')


@pytest.fixture
def sample_snomed_code():
    """A SNOMED code for diabetes mellitus."""
    return Code.snomed('44054006')


@pytest.fixture
def sample_rxnorm_code():
    """An RxNorm code for atorvastatin."""
    return Code.rxnorm('83367')


# ============================================================================
# HealthContext Fixtures
# ============================================================================

@pytest.fixture
def minimal_healthcontext():
    """A minimal HealthContext with basic patient data."""
    from core.healthcontext import HealthContext
    from variables.age import Age

    age = Age(55)
    gender = Record(
        var=Var(id='Gender', code=[Code.snomed('248153007')]),
        initial_values=[Value(True)]
    )

    return HealthContext(records=[age, gender], persona=Persona.patient)


@pytest.fixture
def sample_healthcontext():
    """A comprehensive HealthContext for testing."""
    from core.healthcontext import HealthContext
    from variables.age import Age

    age = Age(50)
    gender = Record(
        var=Var(id='Gender', code=[Code.snomed('248153007')]),
        initial_values=[Value(True)]
    )
    ldl = Record(
        var=Var(id='LDL', code=[Code.loinc('13457-7')]),
        initial_values=[Value(150), Value(145), Value(160)]
    )
    hdl = Record(
        var=Var(id='HDL', code=[Code.loinc('2085-9')]),
        initial_values=[Value(55)]
    )
    chol = Record(
        var=Var(id='Chol', code=[Code.loinc('2093-3')]),
        initial_values=[Value(250)]
    )
    dm = Record(
        var=Var(id='DM', code=[Code.snomed('44054006')]),
        initial_values=[Value(False)]
    )

    return HealthContext(
        records=[age, gender, ldl, hdl, chol, dm],
        persona=Persona.patient
    )


@pytest.fixture
def provider_healthcontext(sample_healthcontext):
    """A HealthContext with provider persona."""
    from core.healthcontext import HealthContext
    return HealthContext(
        records=sample_healthcontext.records,
        persona=Persona.provider
    )


# ============================================================================
# CPG Fixtures
# ============================================================================

@pytest.fixture
def minimal_cpg_dict():
    """A minimal CPG definition as a dictionary."""
    return {
        'CPG': {
            'identifier': 'test_cpg',
            'title': 'Test CPG',
            'publisher': 'Test Publisher'
        },
        'variables': [
            {'id': 'Age', 'code': {'concord': ['Age']}},
            {'id': 'LDL', 'title': 'LDL', 'code': {'loinc': ['13457-7']}}
        ],
        'eligibility': [
            {'id': 'age_check', 'title': 'Age Check', 'expression': '$Age >= 40'}
        ],
        'assessments': [
            {'id': 'high_ldl', 'title': 'High LDL', 'expression': '$LDL > 130'}
        ],
        'recommendations': [
            {
                'id': 'statin_rec',
                'title': 'Consider Statin',
                'expression': '$high_ldl == True',
                'narrative': {
                    'patient': {True: 'Consider starting statin therapy'},
                    'provider': {True: 'Recommend statin initiation'}
                }
            }
        ]
    }


@pytest.fixture
def minimal_cpg(minimal_cpg_dict):
    """A minimal CPG instance."""
    from core.cpg import CPG
    return CPG.from_document(minimal_cpg_dict)


@pytest.fixture
def cholesterol_cpg():
    """Load the cholesterol CPG from file."""
    from core.cpg_registry import get_registry
    try:
        return get_registry().get('2019AccPrimaryPreventionASCVD')
    except KeyError:
        pytest.skip("Cholesterol CPG not found")


# ============================================================================
# Assessment Fixtures
# ============================================================================

@pytest.fixture
def sample_assessment_var():
    """A sample AssessmentVar for testing."""
    from core.assessment import AssessmentVar
    return AssessmentVar(
        id='test_assessment',
        title='Test Assessment',
        expression='$LDL > 100'
    )


@pytest.fixture
def sample_assessment_var_with_narrative():
    """An AssessmentVar with narratives."""
    from core.assessment import AssessmentVar
    return AssessmentVar(
        id='ldl_high',
        title='High LDL Assessment',
        expression='$LDL > 130',
        narr=Narrative({
            'patient': {
                True: 'Your LDL is elevated',
                False: 'Your LDL is within normal range',
                None: 'Could not determine LDL status'
            },
            'provider': {
                True: 'LDL elevated',
                False: 'LDL normal',
                None: 'LDL status undetermined'
            }
        })
    )


# ============================================================================
# Eligibility Fixtures
# ============================================================================

@pytest.fixture
def sample_eligibility_var():
    """A sample EligibilityVar for testing."""
    from core.eligibility import EligibilityVar
    return EligibilityVar(
        id='age_eligibility',
        title='Age Eligibility',
        expression='$Age >= 40 and $Age <= 75'
    )


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def test_cpg_path():
    """Path to test CPG files."""
    return Path(__file__).parent / 'fixtures' / 'sample_cpgs'


@pytest.fixture
def persona_patient():
    """Patient persona."""
    return Persona.patient


@pytest.fixture
def persona_provider():
    """Provider persona."""
    return Persona.provider
