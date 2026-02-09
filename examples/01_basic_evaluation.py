#!/usr/bin/env python3
"""Example 1: Basic CPG Evaluation

This example demonstrates the basic workflow for evaluating a Clinical Practice
Guideline (CPG) against patient health data.

The workflow consists of four phases:
1. Load CPG definition
2. Create patient health context
3. Run evaluation pipeline
4. Access results
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from concordcore.core.cpg_registry import get_registry
from concordcore.core.concord import Concord, NeedAttestationError
from concordcore.core.healthcontext import HealthContext
from concordcore.variables.record import Record
from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.variables.age import Age
from concordcore.primitives.code import Code
from concordcore.primitives.types import Persona


def main():
    """Run basic CPG evaluation example."""

    # =========================================================================
    # Step 1: Load CPG Definition
    # =========================================================================
    print("=" * 60)
    print("Step 1: Loading CPG Definition")
    print("=" * 60)

    cpg = get_registry().get('2019AccPrimaryPreventionASCVD')

    print(f"Loaded: {cpg.title}")
    print(f"Publisher: {cpg.publisher}")
    print(f"Variables: {len(cpg.variables)}")
    print(f"Assessments: {len(cpg.assessment_variables)}")
    print(f"Recommendations: {len(cpg.recommendation_variables)}")

    # =========================================================================
    # Step 2: Create Patient Health Context
    # =========================================================================
    print("\n" + "=" * 60)
    print("Step 2: Creating Patient Health Context")
    print("=" * 60)

    # Create patient records
    age = Age(55)  # 55 years old

    ldl = Record(
        var=Var(id='LDL', title='LDL Cholesterol', code=[Code.loinc('13457-7')]),
        _Record__values=[Value(165), Value(158), Value(170)]
    )

    hdl = Record(
        var=Var(id='HDL', title='HDL Cholesterol', code=[Code.loinc('2085-9')]),
        _Record__values=[Value(52)]
    )

    chol = Record(
        var=Var(id='Chol', title='Total Cholesterol', code=[Code.loinc('2093-3')]),
        _Record__values=[Value(265)]
    )

    # Create health context with patient persona
    healthcontext = HealthContext(
        records=[age, ldl, hdl, chol],
        persona=Persona.patient
    )

    print(f"Patient records loaded: {len(healthcontext.records)}")
    for record in healthcontext.records:
        if record.value:
            print(f"  - {record.id}: {record.value.value}")

    # =========================================================================
    # Step 3: Run Evaluation Pipeline
    # =========================================================================
    print("\n" + "=" * 60)
    print("Step 3: Running Evaluation Pipeline")
    print("=" * 60)

    # Initialize Concord orchestrator
    concord = Concord(cpg=cpg, healthcontext=healthcontext)

    # Phase 1: Eligibility
    print("\n--- Eligibility Check ---")
    eligibility = concord.eligibility()
    print(f"Is Eligible: {eligibility.is_eligible}")

    if not eligibility.is_eligible:
        print("Patient does not meet eligibility criteria. Stopping evaluation.")
        return

    # Phase 2: Sufficiency
    print("\n--- Sufficiency Check ---")
    sufficiency = concord.sufficiency()
    print(f"Is Executable: {sufficiency.is_executable}")

    if not sufficiency.is_executable:
        print("Insufficient data for CPG execution.")
        # Show what's missing
        for ev in sufficiency.insufficient_variables:
            print(f"  Missing: {ev.record.id}")
        return

    # Phase 3: Assessment
    print("\n--- Assessment ---")
    try:
        assessment = concord.assess(ignore_required_variable_attestations=True)
        print(f"Assessments evaluated: {len(assessment.context.evaluation_list)}")

        for eval_record in assessment.context.evaluation_list:
            if eval_record.record.value:
                print(f"  - {eval_record.record.id}: {eval_record.record.value.value}")

    except NeedAttestationError as e:
        print(f"Need user attestation for: {e}")
        return
    except Exception as e:
        print(f"Assessment error: {e}")
        return

    # Phase 4: Recommendations
    print("\n--- Recommendations ---")
    recommendations = concord.recommendations()

    print(f"Total recommendations: {len(recommendations.recommendations)}")
    print(f"Applicable recommendations: {len(recommendations.applied)}")

    # =========================================================================
    # Step 4: Access Results
    # =========================================================================
    print("\n" + "=" * 60)
    print("Step 4: Results")
    print("=" * 60)

    for rec in recommendations.applied:
        print(f"\n[{rec.recommendation.id}] {rec.recommendation.title}")
        if rec.narrative:
            print(f"  {rec.narrative[:100]}...")

    print("\n" + "=" * 60)
    print("Evaluation Complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
