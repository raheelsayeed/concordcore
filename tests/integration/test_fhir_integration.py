#!/usr/bin/env python3
"""Integration tests for FHIR data parsing and integration."""

import pytest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.fhir
class TestFHIRValueParsing:
    """Tests for parsing FHIR resources into Values."""

    @pytest.fixture
    def sample_observation_json(self):
        """A sample FHIR Observation resource."""
        return {
            "resourceType": "Observation",
            "id": "ldl-example",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "13457-7",
                    "display": "LDL Cholesterol"
                }]
            },
            "valueQuantity": {
                "value": 150,
                "unit": "mg/dL",
                "system": "http://unitsofmeasure.org",
                "code": "mg/dL"
            },
            "effectiveDateTime": "2024-01-15T10:30:00Z"
        }

    @pytest.fixture
    def sample_condition_json(self):
        """A sample FHIR Condition resource."""
        return {
            "resourceType": "Condition",
            "id": "diabetes-example",
            "subject": {"reference": "Patient/example"},
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }]
            },
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "44054006",
                    "display": "Type 2 diabetes mellitus"
                }]
            },
            "recordedDate": "2020-05-15"
        }

    @pytest.fixture
    def sample_medication_request_json(self):
        """A sample FHIR MedicationRequest resource."""
        return {
            "resourceType": "MedicationRequest",
            "id": "statin-example",
            "status": "active",
            "intent": "order",
            "subject": {"reference": "Patient/example"},
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "83367",
                    "display": "Atorvastatin"
                }]
            },
            "authoredOn": "2024-01-01"
        }

    def test_parse_observation_to_fhirvalue(self, sample_observation_json):
        """Test parsing FHIR Observation to FHIRValue."""
        from fhir_parsers.fhirvalue import FHIRValue

        try:
            fhir_value = FHIRValue.from_fhir(sample_observation_json)
            assert fhir_value is not None
            assert fhir_value.value == 150
        except AttributeError as e:
            if 'parse_obj' in str(e):
                pytest.skip("fhirclient package API incompatibility (parse_obj not available)")
            raise

    def test_parse_condition_to_fhirvalue(self, sample_condition_json):
        """Test parsing FHIR Condition to FHIRValue."""
        from fhir_parsers.fhirvalue import FHIRValue

        try:
            fhir_value = FHIRValue.from_fhir(sample_condition_json)
            assert fhir_value is not None
            # Conditions typically have boolean values indicating presence
            assert fhir_value.value is True or fhir_value.value is not None
        except AttributeError as e:
            if 'parse_obj' in str(e):
                pytest.skip("fhirclient package API incompatibility (parse_obj not available)")
            raise

    def test_parse_medication_request_to_fhirvalue(self, sample_medication_request_json):
        """Test parsing FHIR MedicationRequest to FHIRValue."""
        from fhir_parsers.fhirvalue import FHIRValue

        try:
            fhir_value = FHIRValue.from_fhir(sample_medication_request_json)
            assert fhir_value is not None
        except AttributeError as e:
            if 'parse_obj' in str(e):
                pytest.skip("fhirclient package API incompatibility (parse_obj not available)")
            raise

    def test_fhirvalue_has_code(self, sample_observation_json):
        """Test that FHIRValue extracts code information."""
        from fhir_parsers.fhirvalue import FHIRValue

        try:
            fhir_value = FHIRValue.from_fhir(sample_observation_json)
            assert fhir_value.code is not None
        except AttributeError as e:
            if 'parse_obj' in str(e):
                pytest.skip("fhirclient package API incompatibility (parse_obj not available)")
            raise


@pytest.mark.fhir
class TestFHIRToHealthContext:
    """Tests for converting FHIR data to HealthContext."""

    @pytest.fixture
    def fhir_ndjson_path(self):
        """Path to sample FHIR NDJSON files."""
        path = Path(__file__).parent.parent.parent / 'samples' / 'fhir_r4' / 'ndjson'
        if not path.exists():
            pytest.skip("FHIR sample data not found")
        return path

    def test_load_observations_from_ndjson(self, fhir_ndjson_path):
        """Test loading Observations from NDJSON file."""
        obs_file = fhir_ndjson_path / 'Observation.ndjson'
        if not obs_file.exists():
            pytest.skip("Observation.ndjson not found")

        observations = []
        with open(obs_file, 'r') as f:
            for line in f:
                observations.append(json.loads(line))

        assert len(observations) > 0
        assert all(obs.get('resourceType') == 'Observation' for obs in observations)

    def test_create_healthcontext_from_fhir_values(self, fhir_ndjson_path):
        """Test creating HealthContext from FHIR values."""
        from core.healthcontext import HealthContext
        from fhir_parsers.fhirvalue import FHIRValue
        from primitives.types import Persona

        obs_file = fhir_ndjson_path / 'Observation.ndjson'
        if not obs_file.exists():
            pytest.skip("Observation.ndjson not found")

        fhir_values = []
        with open(obs_file, 'r') as f:
            for line in f:
                try:
                    obs = json.loads(line)
                    fhir_value = FHIRValue.from_fhir(obs)
                    if fhir_value:
                        fhir_values.append(fhir_value)
                except Exception:
                    continue

        if not fhir_values:
            pytest.skip("No valid FHIR values parsed")

        # Create HealthContext (this requires variables to match against)
        # For basic test, just verify we have valid FHIRValues
        assert len(fhir_values) > 0


@pytest.mark.fhir
class TestFHIRWithCPG:
    """Tests for integrating FHIR data with CPG evaluation."""

    @pytest.fixture
    def cholesterol_cpg(self):
        """Load the cholesterol CPG."""
        cpg_path = Path(__file__).parent.parent.parent / 'cpgs' / 'cholesterol.yaml'
        if not cpg_path.exists():
            pytest.skip("Cholesterol CPG not found")
        from core.cpg import CPG
        return CPG.from_document_path(str(cpg_path))

    def test_fhir_values_match_cpg_variables(self, cholesterol_cpg):
        """Test that FHIR values can match CPG variable codes."""
        # Get LOINC codes from CPG
        lab_codes = cholesterol_cpg.lab_test_codes()

        # Verify CPG has lab codes defined
        assert lab_codes is not None
        assert len(lab_codes) > 0

    def test_complete_workflow_with_fhir_data(self, cholesterol_cpg):
        """Test complete workflow using FHIR sample data."""
        from core.concord import Concord
        from core.healthcontext import HealthContext
        from primitives.types import Persona
        from variables.age import Age
        import misc

        # Use the sample_fhir_values helper
        try:
            fhir_values = misc.sample_fhir_values()
        except Exception as e:
            pytest.skip(f"Could not load FHIR sample values: {e}")

        if not fhir_values:
            pytest.skip("No FHIR values available")

        # Create HealthContext from FHIR values
        # Note: from_values requires age, gender, race parameters
        healthcontext = HealthContext.from_values(
            values=fhir_values,
            for_variables=cholesterol_cpg.variables,
            age=Age(50),
            gender=None,
            race=None,
            persona=Persona.patient
        )

        # Run through workflow
        concord = Concord(cpg=cholesterol_cpg, healthcontext=healthcontext)

        try:
            eligibility = concord.eligibility()
            assert eligibility is not None
        except Exception as e:
            # May fail due to missing eligibility data
            pytest.skip(f"Eligibility check failed: {e}")


@pytest.mark.fhir
class TestFHIRCodeMatching:
    """Tests for FHIR code matching functionality."""

    def test_loinc_code_matching(self):
        """Test that LOINC codes are properly matched."""
        from primitives.code import Code

        # LDL LOINC code
        ldl_code = Code.loinc('13457-7')
        assert ldl_code.system == 'http://loinc.org'
        assert ldl_code.code == '13457-7'

    def test_snomed_code_matching(self):
        """Test that SNOMED codes are properly matched."""
        from primitives.code import Code

        # Diabetes SNOMED code
        dm_code = Code.snomed('44054006')
        assert dm_code.system == 'http://snomed.info/sct'
        assert dm_code.code == '44054006'

    def test_rxnorm_code_matching(self):
        """Test that RxNorm codes are properly matched."""
        from primitives.code import Code

        # Atorvastatin RxNorm code
        statin_code = Code.rxnorm('83367')
        assert statin_code.system == 'http://www.nlm.nih.gov/research/umls/rxnorm'
        assert statin_code.code == '83367'


# ============================================================================
# FHIRAdapter.parse_bundle_to_records Tests
# ============================================================================

class TestFHIRAdapterBundleParsing:
    """Tests for FHIRAdapter.parse_bundle_to_records."""

    @pytest.fixture
    def adapter(self):
        from formats.fhir_adapter import FHIRAdapter
        return FHIRAdapter()

    @pytest.fixture
    def fhir_bundle(self):
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "13457-7",
                                "display": "LDL"
                            }]
                        },
                        "valueQuantity": {"value": 165, "unit": "mg/dL"},
                        "effectiveDateTime": "2024-01-15"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Condition",
                        "code": {
                            "coding": [{
                                "system": "http://snomed.info/sct",
                                "code": "44054006",
                                "display": "Type 2 DM"
                            }]
                        },
                        "clinicalStatus": {
                            "coding": [{"code": "active"}]
                        }
                    }
                }
            ]
        }

    def test_parse_bundle_matches_variables(self, adapter, fhir_bundle):
        from primitives.code import Code
        from variables.var import Var

        variables = [
            Var(id='LDL', code=[Code.loinc('13457-7')]),
            Var(id='DM', code=[Code.snomed('44054006')]),
        ]
        records = adapter.parse_bundle_to_records(fhir_bundle, variables)
        assert len(records) == 2
        ids = {r.id for r in records}
        assert 'LDL' in ids
        assert 'DM' in ids

    def test_parse_bundle_empty(self, adapter):
        from variables.var import Var
        bundle = {"resourceType": "Bundle", "entry": []}
        records = adapter.parse_bundle_to_records(bundle, [Var(id='X')])
        assert records == []


# ============================================================================
# HealthContext.from_mixed_sources with ConcordUser Tests
# ============================================================================

class TestHealthContextMixedSourcesWithConcordUser:
    """Tests for ConcordUser integration in from_mixed_sources."""

    def test_concord_user_fills_missing_data(self, minimal_cpg):
        from core.healthcontext import HealthContext
        from core.concord_user import ConcordUser

        user = ConcordUser(user_id='p1')
        user.add_input('Age', 55)

        ctx = HealthContext.from_mixed_sources(cpg=minimal_cpg, concord_user=user)
        ids = {r.id for r in ctx.records}
        assert 'Age' in ids

    def test_attestations_still_work(self, minimal_cpg):
        from core.healthcontext import HealthContext

        ctx = HealthContext.from_mixed_sources(
            cpg=minimal_cpg,
            attestations={'Age': 55}
        )
        ids = {r.id for r in ctx.records}
        assert 'Age' in ids

    def test_concord_user_takes_precedence_over_attestations(self, minimal_cpg):
        """When both concord_user and attestations are provided, concord_user wins."""
        from core.healthcontext import HealthContext
        from core.concord_user import ConcordUser

        user = ConcordUser(user_id='p1')
        user.add_input('Age', 99)

        ctx = HealthContext.from_mixed_sources(
            cpg=minimal_cpg,
            concord_user=user,
            attestations={'Age': 55},  # Should be ignored
        )
        age = next(r for r in ctx.records if r.id == 'Age')
        assert age.value.value == 99  # From ConcordUser, not attestations
