#!/usr/bin/env python3
"""Example 3: FHIR Data Integration

This example demonstrates how to load patient data from FHIR R4 resources
and use it with ConcordCore for CPG evaluation.

Supported FHIR Resources:
- Observation (lab results, vitals)
- Condition (diagnoses)
- MedicationRequest (prescriptions)
- Procedure (procedures)
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg_registry import get_registry
from core.concord import Concord
from core.healthcontext import HealthContext
from fhir_parsers.fhirvalue import FHIRValue
from primitives.types import Persona


def load_ndjson(filepath: Path) -> list[dict]:
    """Load FHIR resources from NDJSON file."""
    resources = []
    if filepath.exists():
        with open(filepath, 'r') as f:
            for line in f:
                resources.append(json.loads(line))
    return resources


def main():
    """Demonstrate FHIR data integration."""

    print("=" * 60)
    print("FHIR Integration Example")
    print("=" * 60)

    # =========================================================================
    # Load FHIR Resources from NDJSON files
    # =========================================================================
    print("\nLoading FHIR resources...")

    fhir_path = Path(__file__).parent.parent / 'samples' / 'fhir_r4' / 'ndjson'

    observations = load_ndjson(fhir_path / 'Observation.ndjson')
    conditions = load_ndjson(fhir_path / 'Condition.ndjson')
    medications = load_ndjson(fhir_path / 'MedicationRequest.ndjson')
    procedures = load_ndjson(fhir_path / 'Procedure.ndjson')

    print(f"  Observations: {len(observations)}")
    print(f"  Conditions: {len(conditions)}")
    print(f"  MedicationRequests: {len(medications)}")
    print(f"  Procedures: {len(procedures)}")

    # =========================================================================
    # Convert FHIR Resources to FHIRValues
    # =========================================================================
    print("\nConverting FHIR resources to ConcordCore values...")

    all_resources = observations + conditions + medications + procedures
    fhir_values = []
    errors = []

    for resource in all_resources:
        try:
            fhir_value = FHIRValue.from_fhir(resource)
            if fhir_value:
                fhir_values.append(fhir_value)
        except Exception as e:
            errors.append(e)

    print(f"  Successfully converted: {len(fhir_values)}")
    print(f"  Errors: {len(errors)}")

    if not fhir_values:
        print("No FHIR values to process. Check sample data.")
        return

    # Show sample values
    print("\nSample FHIR values:")
    for fv in fhir_values[:5]:
        code_str = fv.code.as_string if fv.code else 'No code'
        print(f"  - {code_str}: {fv.value}")

    # =========================================================================
    # Load CPG and Create HealthContext
    # =========================================================================
    print("\n" + "=" * 60)
    print("Creating HealthContext from FHIR values")
    print("=" * 60)

    cpg = get_registry().get('2019AccPrimaryPreventionASCVD')

    print(f"\nCPG: {cpg.title}")
    print(f"Required variables: {len(cpg.variables)}")

    # Create HealthContext from FHIR values
    # This matches FHIR values to CPG variables by code
    healthcontext = HealthContext.from_values(
        values=fhir_values,
        for_variables=cpg.variables,
        persona=Persona.patient
    )

    print(f"\nMatched records: {len(healthcontext.records)}")
    for record in healthcontext.records:
        if record.has_value:
            print(f"  - {record.id}: {record.value.value}")

    # =========================================================================
    # Run Evaluation
    # =========================================================================
    print("\n" + "=" * 60)
    print("Running CPG Evaluation")
    print("=" * 60)

    concord = Concord(cpg=cpg, healthcontext=healthcontext)

    # Eligibility
    try:
        eligibility = concord.eligibility()
        print(f"\nEligibility: {eligibility.is_eligible}")
    except Exception as e:
        print(f"Eligibility check failed: {e}")
        return

    if not eligibility.is_eligible:
        print("Patient not eligible for this CPG")
        return

    # Sufficiency
    sufficiency = concord.sufficiency()
    print(f"Sufficiency: {sufficiency.is_executable}")

    if sufficiency.attestation_variables:
        print(f"Variables needing attestation: {len(sufficiency.attestation_variables)}")
        for av in sufficiency.attestation_variables:
            print(f"  - {av.record.id}")

    # Continue if possible
    if sufficiency.is_executable:
        try:
            assessment = concord.assess(ignore_required_variable_attestations=True)
            print(f"\nAssessments: {len(assessment.context.evaluation_list)}")

            recommendations = concord.recommendations()
            print(f"Recommendations: {len(recommendations.applied)}")

            for rec in recommendations.applied[:3]:
                print(f"\n  [{rec.recommendation.id}] {rec.recommendation.title}")

        except Exception as e:
            print(f"Assessment/Recommendations failed: {e}")


def show_fhir_parsing():
    """Show how individual FHIR resources are parsed."""

    print("\n" + "=" * 60)
    print("FHIR Resource Parsing Details")
    print("=" * 60)

    # Example Observation
    observation = {
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
            "unit": "mg/dL"
        },
        "effectiveDateTime": "2024-01-15T10:30:00Z"
    }

    print("\nExample FHIR Observation:")
    print(json.dumps(observation, indent=2))

    print("\nParsing to FHIRValue:")
    fhir_value = FHIRValue.from_fhir(observation)
    print(f"  Value: {fhir_value.value}")
    print(f"  Code: {fhir_value.code.as_string if fhir_value.code else 'None'}")
    print(f"  Date: {fhir_value.date}")
    print(f"  Unit: {fhir_value.unit}")

    # Example Condition
    condition = {
        "resourceType": "Condition",
        "id": "diabetes-example",
        "clinicalStatus": {
            "coding": [{
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

    print("\nExample FHIR Condition:")
    print(json.dumps(condition, indent=2))

    print("\nParsing to FHIRValue:")
    fhir_value = FHIRValue.from_fhir(condition)
    print(f"  Value: {fhir_value.value} (presence of condition)")
    print(f"  Code: {fhir_value.code.as_string if fhir_value.code else 'None'}")


if __name__ == '__main__':
    main()
    show_fhir_parsing()
