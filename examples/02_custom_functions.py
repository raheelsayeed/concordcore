#!/usr/bin/env python3
"""Example 2: Custom Assessment Functions

This example demonstrates how to use custom Python functions for complex
assessments that cannot be expressed as simple expressions.

Custom functions are useful for:
- Multi-step calculations (e.g., risk scores)
- Complex conditional logic
- External data lookups
- Algorithm implementations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg_registry import get_registry
from core.concord import Concord
from core.healthcontext import HealthContext
from variables.record import Record
from variables.var import Var
from variables.value import Value
from variables.age import Age
from primitives.code import Code
from primitives.types import Persona


def main():
    """Demonstrate custom assessment functions."""

    print("=" * 60)
    print("Custom Assessment Functions Example")
    print("=" * 60)

    # =========================================================================
    # Load Cholesterol CPG (has custom ASCVD risk calculation)
    # =========================================================================
    print("\nLoading Cholesterol CPG with custom functions...")

    cpg = get_registry().get('2019AccPrimaryPreventionASCVD')

    print(f"Functions module: {cpg.functions_module}")

    # The cholesterol CPG uses a custom function for ASCVD risk calculation
    # See cpgs/cholesterol/ascvd_risk_scores.py for the implementation

    # =========================================================================
    # Create comprehensive patient data for risk calculation
    # =========================================================================
    print("\nCreating patient health context...")

    from ontology.codes import ConcordDefinition, CodeGender, CodeRaceEthnicity

    # Demographics
    age = Age(58)
    gender = ConcordDefinition.code_Gender.as_record(CodeGender.female_snomed.value)
    race = ConcordDefinition.code_Ethnicity.as_record(CodeRaceEthnicity.White.value)

    # Lab values
    ldl = Record(
        var=Var(id='LDL', code=[Code.loinc('13457-7')]),
        _Record__values=[Value(145)]
    )
    hdl = Record(
        var=Var(id='HDL', code=[Code.loinc('2085-9')]),
        _Record__values=[Value(48)]
    )
    chol = Record(
        var=Var(id='Chol', code=[Code.loinc('2093-3')]),
        _Record__values=[Value(240)]
    )
    tg = Record(
        var=Var(id='TG', code=[Code.loinc('2571-8')]),
        _Record__values=[Value(180)]
    )

    # Blood pressure (as tuple for systolic/diastolic)
    bp = Record(
        var=Var(id='BP', code=[Code.loinc('55284-4')]),
        _Record__values=[Value((142, 88))]
    )

    # Conditions
    dm = Record(
        var=Var(id='DM', code=[Code.snomed('44054006')]),
        _Record__values=[Value(True)]
    )
    htn = Record(
        var=Var(id='htn', code=[Code.snomed('38341003')]),
        _Record__values=[Value(True)]
    )
    smoker = Record(
        var=Var(id='is_smoker', code=[Code.loinc('72166-2')]),
        _Record__values=[Value(False)]
    )

    # Medications
    med_htn = Record(
        var=Var(id='med_for_htn', code=[Code.rxnorm('104375')]),
        _Record__values=[Value(True)]
    )

    healthcontext = HealthContext(
        records=[age, gender, race, ldl, hdl, chol, tg, bp, dm, htn, smoker, med_htn],
        persona=Persona.patient
    )

    print(f"Loaded {len(healthcontext.records)} patient records")

    # =========================================================================
    # Run evaluation
    # =========================================================================
    print("\nRunning evaluation with custom risk calculation...")

    concord = Concord(cpg=cpg, healthcontext=healthcontext)

    # Run pipeline
    eligibility = concord.eligibility()
    print(f"\nEligibility: {eligibility.is_eligible}")

    if not eligibility.is_eligible:
        print("Not eligible for this CPG")
        return

    sufficiency = concord.sufficiency()
    print(f"Sufficiency: {sufficiency.is_executable}")

    if not sufficiency.is_executable:
        print("Insufficient data")
        return

    try:
        assessment = concord.assess(ignore_required_variable_attestations=True)
    except Exception as e:
        print(f"Assessment error: {e}")
        return

    # =========================================================================
    # Show risk assessment results
    # =========================================================================
    print("\n" + "=" * 60)
    print("Assessment Results (including custom function calculations)")
    print("=" * 60)

    for eval_record in assessment.context.evaluation_list:
        record = eval_record.record
        if record.value:
            # Check if this was calculated by a function
            is_function = record.var.function if hasattr(record.var, 'function') else None
            calc_type = "(function)" if is_function else "(expression)"
            print(f"\n{record.id} {calc_type}:")
            print(f"  Value: {record.value.value}")
            if record.narrative:
                print(f"  Narrative: {record.narrative[:100]}...")

    # =========================================================================
    # Show recommendations
    # =========================================================================
    print("\n" + "=" * 60)
    print("Recommendations")
    print("=" * 60)

    recommendations = concord.recommendations()

    for rec in recommendations.applied:
        print(f"\n[{rec.recommendation.id}]")
        print(f"  Title: {rec.recommendation.title}")
        if rec.recommendation.class_of_recommendation:
            print(f"  Class: {rec.recommendation.class_of_recommendation}")
        if rec.narrative:
            print(f"  {rec.narrative[:150]}...")


def show_function_module_contents():
    """Show the custom functions defined in the CPG module."""
    print("\n" + "=" * 60)
    print("Custom Functions in ascvd_risk_scores.py")
    print("=" * 60)

    print("""
The ASCVD risk score calculation involves:

1. Pooled Cohort Equation coefficients (race/gender specific)
2. Multiple risk factors:
   - Age
   - Total Cholesterol
   - HDL Cholesterol
   - Systolic Blood Pressure
   - Treatment for Hypertension
   - Diabetes
   - Smoking Status

The function signature:
    def calculate_ascvd_risk(healthcontext: dict) -> float:
        '''Calculate 10-year ASCVD risk score.'''
        ...

This function is called when assessing:
    assessments:
      - id: ascvd_risk_score
        function: calculate_ascvd_risk
    """)


if __name__ == '__main__':
    main()
    show_function_module_contents()
