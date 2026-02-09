#!/usr/bin/env python3
"""End-to-end integration test for the PGHD flow.

Tests the complete pipeline:
    PGHDConverter.to_record() -> ConcordUser.add_input() -> build_health_context() -> Concord.evaluate()

Uses the real cholesterol CPG to verify the full evaluation lifecycle.
"""

import pytest
from concordcore.core.concord import Concord, PipelineResult
from concordcore.core.cpg import CPG
from concordcore.core.healthcontext import HealthContext
from concordcore.core.eligibility import EligibilityResult
from concordcore.core.sufficiency import SufficiencyResult
from concordcore.core.assessment import AssessmentResult
from concordcore.core.recommendation import RecommendationResult
from concordcore.core.concord_user import ConcordUser
from concordcore.pghd.converter import PGHDConverter
from concordcore.pghd.input_source import InputSource
from concordcore.variables.record import Record
from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.variables.age import Age
from concordcore.primitives.code import Code
from concordcore.primitives.types import Persona
from concordcore.ontology.codes import ConcordDefinition, CodeGender, CodeRaceEthnicity


@pytest.fixture
def cholesterol_cpg():
    """Load the real cholesterol CPG from disk."""
    from concordcore.core.cpg_registry import get_registry
    try:
        return get_registry().get('2019AccPrimaryPreventionASCVD')
    except KeyError:
        pytest.skip("Cholesterol CPG not found")


@pytest.fixture
def ehr_records():
    """Simulate EHR-sourced records for non-attestable clinical data.

    These represent structured data that would come from a hospital EHR system.
    Non-attestable variables (lab results, vitals) cannot go through PGHD.
    """
    age = Age(55)
    gender = ConcordDefinition.code_Gender.as_record(CodeGender.female_snomed.value)
    ethnicity = ConcordDefinition.code_Ethnicity.as_record(CodeRaceEthnicity.White.value)

    ldl = Record(
        var=Var(id='LDL', code=[Code.loinc('13457-7')]),
        initial_values=[Value(165), Value(158), Value(170)]
    )
    hdl = Record(
        var=Var(id='HDL', code=[Code.loinc('2085-9')]),
        initial_values=[Value(42)]
    )
    chol = Record(
        var=Var(id='Chol', code=[Code.loinc('2093-3')]),
        initial_values=[Value(250)]
    )
    triglycerides = Record(
        var=Var(id='triglycerides', code=[Code.loinc('2571-8')]),
        initial_values=[Value(200), Value(190), Value(185)]
    )
    bp = Record(
        var=Var(id='bloodpressure', code=[Code.loinc('55284-4')]),
        initial_values=[Value(130)]
    )
    smoker = Record(
        var=Var(id='is_smoker', code=[Code.loinc('72166-2')]),
        initial_values=[Value(False)]
    )
    htn = Record(
        var=Var(id='htn', code=[Code.snomed('38341003')]),
        initial_values=[Value(True)]
    )
    med_htn = Record(
        var=Var(id='med_for_htn'),
        initial_values=[Value(True)]
    )
    med_statins = Record(
        var=Var(id='med_statins'),
        initial_values=[Value(False)]
    )
    med_nonstatins = Record(
        var=Var(id='med_nonstatins_chol'),
        initial_values=[Value(False)]
    )

    return [
        age, gender, ethnicity,
        ldl, hdl, chol, triglycerides,
        bp, smoker, htn,
        med_htn, med_statins, med_nonstatins,
    ]


@pytest.mark.integration
class TestE2EPGHDFlow:
    """End-to-end tests for the PGHDConverter -> ConcordUser -> Concord pipeline."""

    def test_pghd_converter_to_record_creates_valid_record(self):
        """Verify PGHDConverter.to_record() produces a proper Record with source metadata."""
        converter = PGHDConverter()
        var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)

        record = converter.to_record(var, True)

        assert isinstance(record, Record)
        assert record.id == 'diabetesMellitus'
        assert record.has_value is True
        assert record.value.value is True
        assert record.value.source is not None
        assert 'patient-reported' in record.value.source

    def test_concord_user_add_input_accumulates_records(self):
        """Verify ConcordUser.add_input() accumulates records and tracks attestations."""
        user = ConcordUser(user_id='test-patient-1', persona=Persona.patient)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        record = user.add_input('diabetesMellitus', True, var=dm_var)

        assert isinstance(record, Record)
        assert len(user.records) == 1
        assert user.has_data_for('diabetesMellitus') is True
        assert len(user.attestation_log) == 1

    def test_build_health_context_merges_pghd_and_ehr(self, ehr_records):
        """Verify build_health_context() merges PGHD inputs with EHR records."""
        user = ConcordUser(user_id='test-patient-2', persona=Persona.patient)

        # Add patient-reported data for attestable variables
        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        user.add_input('diabetesMellitus', True, var=dm_var)

        ctx = user.build_health_context(ehr_records=ehr_records)

        assert isinstance(ctx, HealthContext)
        assert ctx.persona == Persona.patient

        record_ids = {r.id for r in ctx.records}
        # PGHD-sourced
        assert 'diabetesMellitus' in record_ids
        # EHR-sourced
        assert 'LDL' in record_ids
        assert 'HDL' in record_ids
        assert 'Age' in record_ids
        assert 'Gender' in record_ids

    def test_ehr_records_override_pghd_for_same_variable(self, ehr_records):
        """Verify EHR records take priority over PGHD when both supply the same variable."""
        user = ConcordUser(user_id='test-patient-3', persona=Persona.patient)

        # User reports htn via PGHD
        htn_var = Var(id='htn', title='Hypertension', user_attestable=True)
        user.add_input('htn', False, var=htn_var)

        # EHR also has htn=True
        ctx = user.build_health_context(ehr_records=ehr_records)

        # Find the htn record - EHR (True) should override PGHD (False)
        htn_record = next(r for r in ctx.records if r.id == 'htn')
        assert htn_record.value.value is True

    def test_full_pipeline_evaluate(self, cholesterol_cpg, ehr_records):
        """Full end-to-end: PGHD + EHR -> HealthContext -> Concord.evaluate().

        This is the primary integration test verifying the complete flow:
        1. Create a ConcordUser and add patient-reported inputs
        2. Build a HealthContext merging PGHD with EHR records
        3. Run the full CPG evaluation pipeline
        4. Verify all phases produce valid results
        """
        # Step 1: Patient reports data via PGHD
        user = ConcordUser(user_id='patient-e2e', persona=Persona.patient)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        user.add_input('diabetesMellitus', True, var=dm_var)

        # Step 2: Build HealthContext from PGHD + EHR
        ctx = user.build_health_context(ehr_records=ehr_records)
        assert isinstance(ctx, HealthContext)

        # Step 3: Run the full evaluation pipeline
        concord = Concord(cpg=cholesterol_cpg, healthcontext=ctx)
        result = concord.evaluate(ignore_attestations=True)

        # Step 4: Verify the PipelineResult
        assert isinstance(result, PipelineResult)
        assert result.metadata is not None
        assert result.metadata.cpg_id == '2019AccPrimaryPreventionASCVD'

        # Eligibility: 55-year-old should be eligible (40-75 range)
        assert result.eligibility is not None
        assert isinstance(result.eligibility, EligibilityResult)
        assert result.is_eligible is True

        # Sufficiency: we provided all required variables
        assert result.sufficiency is not None
        assert isinstance(result.sufficiency, SufficiencyResult)

        # Assessment: should have completed
        assert result.assessment is not None
        assert isinstance(result.assessment, AssessmentResult)

        # Recommendations: should have been generated
        assert result.recommendations is not None
        assert isinstance(result.recommendations, RecommendationResult)

        # Pipeline should be complete
        assert result.is_complete is True
        assert len(result.errors) == 0

    def test_stepwise_pipeline(self, cholesterol_cpg, ehr_records):
        """Test the step-by-step pipeline: eligibility -> sufficiency -> assess -> recommendations.

        Validates each intermediate result type individually.
        """
        user = ConcordUser(user_id='patient-stepwise', persona=Persona.patient)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        user.add_input('diabetesMellitus', True, var=dm_var)

        ctx = user.build_health_context(ehr_records=ehr_records)
        concord = Concord(cpg=cholesterol_cpg, healthcontext=ctx)

        # Phase 1: Eligibility
        elig = concord.eligibility()
        assert isinstance(elig, EligibilityResult)
        assert elig.is_eligible is True

        # Phase 2: Sufficiency
        suff = concord.sufficiency()
        assert isinstance(suff, SufficiencyResult)

        # Phase 3: Assessment
        assessment = concord.assess(ignore_required_variable_attestations=True)
        assert isinstance(assessment, AssessmentResult)
        assert assessment.assessments is not None

        # Verify specific assessment IDs exist
        assessed_ids = {a.id for a in assessment.assessments}
        assert 'ascvd_ten_year_risk_score' in assessed_ids
        assert 'ldl_over_190' in assessed_ids or 'ldl_over_190' in assessed_ids
        assert 'has_diabetes' in assessed_ids

        # Phase 4: Recommendations
        recs = concord.recommendations()
        assert isinstance(recs, RecommendationResult)
        assert recs.recommendations is not None
        assert len(recs.recommendations) > 0

    def test_evaluate_ineligible_patient(self, cholesterol_cpg):
        """Verify pipeline short-circuits for an ineligible patient (age outside 40-75)."""
        user = ConcordUser(user_id='patient-young', persona=Persona.patient)

        # No PGHD needed, just build context with young patient EHR data
        age = Age(30)
        ctx = user.build_health_context(ehr_records=[age])

        concord = Concord(cpg=cholesterol_cpg, healthcontext=ctx)
        result = concord.evaluate()

        assert isinstance(result, PipelineResult)
        assert result.is_eligible is False
        assert result.is_complete is False
        # Assessment and recommendations should not have run
        assert result.assessment is None
        assert result.recommendations is None

    def test_multiple_pghd_inputs_accumulated(self):
        """Verify ConcordUser accumulates multiple inputs from different interactions."""
        user = ConcordUser(user_id='patient-multi', persona=Persona.patient)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        waist_var = Var(id='waist_circumference', title='Waist circumference', user_attestable=True)

        user.add_input('diabetesMellitus', True, var=dm_var)
        user.add_input('waist_circumference', 38, var=waist_var)

        assert len(user.records) == 2
        assert user.has_data_for('diabetesMellitus') is True
        assert user.has_data_for('waist_circumference') is True
        assert len(user.attestation_log) == 2

        ctx = user.build_health_context()
        record_ids = {r.id for r in ctx.records}
        assert 'diabetesMellitus' in record_ids
        assert 'waist_circumference' in record_ids

    def test_provider_persona_produces_results(self, cholesterol_cpg, ehr_records):
        """Verify the pipeline works with provider persona."""
        user = ConcordUser(user_id='provider-view', persona=Persona.provider)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        user.add_input('diabetesMellitus', False, var=dm_var)

        ctx = user.build_health_context(ehr_records=ehr_records)
        assert ctx.persona == Persona.provider

        concord = Concord(cpg=cholesterol_cpg, healthcontext=ctx)
        result = concord.evaluate(ignore_attestations=True)

        assert isinstance(result, PipelineResult)
        assert result.is_eligible is True
        assert result.is_complete is True

    def test_pghd_converter_rejects_non_attestable_variable(self):
        """Verify PGHDConverter refuses to create records for non-attestable variables."""
        from concordcore.pghd.validator import PGHDValidationError

        converter = PGHDConverter()
        ldl_var = Var(id='LDL', title='LDL Cholesterol', user_attestable=False)

        with pytest.raises(PGHDValidationError, match='not user-attestable'):
            converter.to_record(ldl_var, 150)

    def test_pipeline_metadata_tracking(self, cholesterol_cpg, ehr_records):
        """Verify evaluation metadata is populated for reproducibility."""
        user = ConcordUser(user_id='patient-meta', persona=Persona.patient)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        user.add_input('diabetesMellitus', True, var=dm_var)

        ctx = user.build_health_context(ehr_records=ehr_records)
        concord = Concord(cpg=cholesterol_cpg, healthcontext=ctx)
        result = concord.evaluate(ignore_attestations=True)

        assert result.metadata is not None
        assert result.metadata.cpg_id == '2019AccPrimaryPreventionASCVD'
        assert result.metadata.evaluation_timestamp is not None
        assert result.metadata.input_data_hash is not None
        assert len(result.metadata.input_data_hash) == 64  # SHA-256 hex length

    def test_concord_user_serialization_roundtrip(self):
        """Verify ConcordUser can be serialized and deserialized."""
        user = ConcordUser(user_id='patient-serial', persona=Persona.patient)

        dm_var = Var(id='diabetesMellitus', title='Diabetes Mellitus', user_attestable=True)
        user.add_input('diabetesMellitus', True, var=dm_var)

        data = user.to_dict()
        restored = ConcordUser.from_dict(data)

        assert restored.user_id == 'patient-serial'
        assert restored.persona == Persona.patient
        assert restored.has_data_for('diabetesMellitus') is True
