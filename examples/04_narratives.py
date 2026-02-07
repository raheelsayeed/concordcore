#!/usr/bin/env python3
"""Example 4: Narrative Generation

This example demonstrates ConcordCore's narrative generation system,
which creates persona-aware text output based on evaluation results.

Key features:
- Different narratives for patients vs providers
- Variable substitution ($VarID, $self.value)
- Conditional text based on evaluation results (True/False/None)
- Default narratives when custom ones aren't defined
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg import CPG
from core.concord import Concord
from core.healthcontext import HealthContext
from variables.record import Record
from variables.var import Var, Narrative
from variables.value import Value
from variables.age import Age
from primitives.code import Code
from primitives.types import Persona


def main():
    """Demonstrate narrative generation."""

    print("=" * 60)
    print("Narrative Generation Example")
    print("=" * 60)

    # =========================================================================
    # Create Custom Var with Narratives
    # =========================================================================
    print("\n--- Creating Variables with Narratives ---\n")

    # LDL with detailed narratives
    ldl_narrative = Narrative({
        'patient': {
            'HasValue': '''
Your LDL cholesterol is $self.value mg/dL.

LDL ("bad") cholesterol carries cholesterol to your arteries, where it can
collect in vessel walls and contribute to plaque buildup.
            ''',
            'NoValue': '''
We don't have your LDL cholesterol on record.

LDL cholesterol is an important measure of heart health. Consider asking
your doctor about getting this test.
            ''',
            True: 'Your LDL cholesterol is elevated at $self.value mg/dL.',
            False: 'Your LDL cholesterol is within normal range at $self.value mg/dL.'
        },
        'provider': {
            'HasValue': 'LDL: $self.value mg/dL (n=$self.count values)',
            'NoValue': 'LDL: Not available',
            True: 'LDL elevated: $self.value mg/dL',
            False: 'LDL normal: $self.value mg/dL'
        }
    })

    ldl_var = Var(
        id='LDL',
        title='LDL Cholesterol',
        code=[Code.loinc('13457-7')],
        narr=ldl_narrative
    )

    # Create records with values
    ldl_record = Record(
        var=ldl_var,
        _Record__values=[Value(165), Value(158), Value(170)]
    )

    # =========================================================================
    # Generate Patient Narrative
    # =========================================================================
    print("--- Patient Narrative ---")

    ldl_record.set_narrative(persona=Persona.patient)
    print(f"LDL Narrative (Patient):\n{ldl_record.narrative}")

    # =========================================================================
    # Generate Provider Narrative
    # =========================================================================
    print("\n--- Provider Narrative ---")

    # Need a fresh record for provider persona
    ldl_record_provider = Record(
        var=ldl_var,
        _Record__values=[Value(165), Value(158), Value(170)]
    )
    ldl_record_provider.set_narrative(persona=Persona.provider)
    print(f"LDL Narrative (Provider):\n{ldl_record_provider.narrative}")

    # =========================================================================
    # Full CPG Example with Narratives
    # =========================================================================
    print("\n" + "=" * 60)
    print("Full CPG Evaluation with Narratives")
    print("=" * 60)

    # Load CPG
    cpg_path = Path(__file__).parent.parent / 'cpgs' / 'cholesterol.yaml'
    cpg = CPG.from_document_path(str(cpg_path))

    # Create patient data
    age = Age(55)
    ldl = Record(
        var=Var(id='LDL', code=[Code.loinc('13457-7')]),
        _Record__values=[Value(195)]  # High LDL
    )
    hdl = Record(
        var=Var(id='HDL', code=[Code.loinc('2085-9')]),
        _Record__values=[Value(42)]
    )
    chol = Record(
        var=Var(id='Chol', code=[Code.loinc('2093-3')]),
        _Record__values=[Value(280)]
    )

    # Evaluate for Patient
    print("\n--- Patient View ---")
    patient_ctx = HealthContext(
        records=[age, ldl, hdl, chol],
        persona=Persona.patient
    )
    show_narratives(cpg, patient_ctx)

    # Evaluate for Provider
    print("\n--- Provider View ---")
    provider_ctx = HealthContext(
        records=[age, ldl, hdl, chol],
        persona=Persona.provider
    )
    show_narratives(cpg, provider_ctx)


def show_narratives(cpg: CPG, healthcontext: HealthContext):
    """Run evaluation and show narratives."""

    concord = Concord(cpg=cpg, healthcontext=healthcontext)

    try:
        eligibility = concord.eligibility()
        if not eligibility.is_eligible:
            print("Not eligible")
            return

        sufficiency = concord.sufficiency()
        assessment = concord.assess(ignore_required_variable_attestations=True)
        recommendations = concord.recommendations()

        # Show assessment narratives
        print("\nAssessment Narratives:")
        for er in assessment.context.evaluation_list:
            if er.record.narrative:
                print(f"\n[{er.record.id}]")
                print(f"  Value: {er.record.value.value if er.record.value else 'None'}")
                print(f"  {er.record.narrative[:200]}...")

        # Show recommendation narratives
        print("\nRecommendation Narratives:")
        for rec in recommendations.applied:
            if rec.narrative:
                print(f"\n[{rec.recommendation.id}]")
                print(f"  Applies: {rec.applies}")
                print(f"  {rec.narrative[:200]}...")

    except Exception as e:
        print(f"Error: {e}")


def show_narrative_variables():
    """Show how variable substitution works in narratives."""

    print("\n" + "=" * 60)
    print("Narrative Variable Substitution")
    print("=" * 60)

    print("""
Supported placeholders in narratives:

  $VarID          - Value of another variable (e.g., $LDL, $Age)
  $self.value     - Current record's primary value
  $self.values    - All values for current record (formatted)
  $self.date      - Date of the current value
  $self.count     - Number of values in record

Example narrative definition:

  narrative:
    patient:
      True: |
        Your LDL is $self.value mg/dL, which is above the recommended
        level of 130 mg/dL. At age $Age, elevated LDL increases your
        risk of cardiovascular disease.
      False: |
        Your LDL is $self.value mg/dL, which is within the recommended
        range.
      HasValue: |
        Your recent LDL results: $self.values
        Most recent: $self.value mg/dL on $self.date
      NoValue: |
        We don't have LDL cholesterol results on file for you.

The system automatically:
1. Detects $VarID placeholders
2. Looks up values from other records
3. Substitutes the actual values
4. Formats dates and lists appropriately
    """)


if __name__ == '__main__':
    main()
    show_narrative_variables()
