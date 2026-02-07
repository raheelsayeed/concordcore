#!/usr/bin/env python3
"""Example 5: Error Handling

This example demonstrates proper error handling in ConcordCore,
including handling missing data, attestation requirements, and
validation errors.

Error types covered:
- NeedAttestationError: User input required for missing data
- ExceptionGroup: Multiple validation errors
- Expression errors: Missing variables, evaluation failures
- Security errors: Invalid paths, module loading issues
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg import CPG
from core.concord import Concord, NeedAttestationError
from core.healthcontext import HealthContext
from core.security import SecurityError
from variables.record import Record
from variables.var import Var
from variables.value import Value
from variables.age import Age
from primitives.code import Code
from primitives.types import Persona
from primitives.errors import (
    ExpressionVariableNotFound,
    ExpressionEvaluationError,
    VarError
)


def main():
    """Demonstrate error handling patterns."""

    print("=" * 60)
    print("Error Handling Examples")
    print("=" * 60)

    # =========================================================================
    # Example 1: Handling NeedAttestationError
    # =========================================================================
    print("\n--- Example 1: Handling Attestation Requirements ---\n")

    demonstrate_attestation_handling()

    # =========================================================================
    # Example 2: Handling Insufficient Data
    # =========================================================================
    print("\n--- Example 2: Handling Insufficient Data ---\n")

    demonstrate_insufficiency_handling()

    # =========================================================================
    # Example 3: Handling Ineligibility
    # =========================================================================
    print("\n--- Example 3: Handling Ineligibility ---\n")

    demonstrate_ineligibility_handling()

    # =========================================================================
    # Example 4: Handling Validation Errors
    # =========================================================================
    print("\n--- Example 4: Handling Validation Errors ---\n")

    demonstrate_validation_errors()

    # =========================================================================
    # Example 5: Security Error Handling
    # =========================================================================
    print("\n--- Example 5: Security Error Handling ---\n")

    demonstrate_security_errors()


def demonstrate_attestation_handling():
    """Show how to handle NeedAttestationError."""

    cpg_path = Path(__file__).parent.parent / 'cpgs' / 'cholesterol.yaml'
    cpg = CPG.from_document_path(str(cpg_path))

    # Create health context with some data missing
    age = Age(55)
    ldl = Record(
        var=Var(id='LDL', code=[Code.loinc('13457-7')]),
        _Record__values=[Value(150)]
    )

    healthcontext = HealthContext(
        records=[age, ldl],
        persona=Persona.patient
    )

    concord = Concord(cpg=cpg, healthcontext=healthcontext)
    concord.eligibility()
    concord.sufficiency()

    try:
        # This may raise NeedAttestationError
        assessment = concord.assess()
        print("Assessment completed successfully")

    except NeedAttestationError as e:
        print(f"Attestation required for {len(e.records)} variables:")

        for eval_record in e.records:
            var = eval_record.record.var
            print(f"\n  Variable: {var.id}")
            print(f"  Title: {var.title}")
            print(f"  Required: {var.required}")

            # In a real application, you would:
            # 1. Present this to the user
            # 2. Collect their input
            # 3. Set the attested_value
            # 4. Re-run assessment

            # Example of setting attested value:
            # eval_record.record.attested_value = Value(user_input)

        print("\nTo proceed, collect user input and set attested_value on each record.")

    except Exception as e:
        print(f"Other error: {type(e).__name__}: {e}")


def demonstrate_insufficiency_handling():
    """Show how to handle insufficient data."""

    cpg_path = Path(__file__).parent.parent / 'cpgs' / 'cholesterol.yaml'
    cpg = CPG.from_document_path(str(cpg_path))

    # Create health context with only age
    age = Age(55)

    healthcontext = HealthContext(
        records=[age],
        persona=Persona.patient
    )

    concord = Concord(cpg=cpg, healthcontext=healthcontext)
    concord.eligibility()
    sufficiency = concord.sufficiency()

    print(f"Is Executable: {sufficiency.is_executable}")

    if not sufficiency.is_executable:
        print("\nMissing required data:")

        # Get insufficient variables
        insufficient = sufficiency.insufficient_variables
        for ev in insufficient:
            print(f"  - {ev.record.id}: {ev.record.var.title or 'No title'}")
            if ev.error:
                print(f"    Error: {ev.error}")

        # Get variables that could be attested
        attestable = sufficiency.attestation_variables
        if attestable:
            print("\nVariables that can be user-provided:")
            for ev in attestable:
                print(f"  - {ev.record.id}")


def demonstrate_ineligibility_handling():
    """Show how to handle ineligible patients."""

    cpg_path = Path(__file__).parent.parent / 'cpgs' / 'cholesterol.yaml'
    cpg = CPG.from_document_path(str(cpg_path))

    # Create health context with age outside eligibility range
    age = Age(35)  # Too young for cholesterol CPG (typically 40-75)
    ldl = Record(
        var=Var(id='LDL', code=[Code.loinc('13457-7')]),
        _Record__values=[Value(150)]
    )

    healthcontext = HealthContext(
        records=[age, ldl],
        persona=Persona.patient
    )

    concord = Concord(cpg=cpg, healthcontext=healthcontext)

    eligibility = concord.eligibility()

    print(f"Is Eligible: {eligibility.is_eligible}")

    if not eligibility.is_eligible:
        print("\nEligibility criteria not met:")

        # Check each eligibility variable
        for ev in eligibility.context.evaluation_list:
            record = ev.record
            print(f"\n  Criterion: {record.id}")
            print(f"  Title: {record.var.title}")
            if record.value:
                print(f"  Result: {record.value.value}")

        print("\nThis CPG does not apply to this patient.")
        print("Consider alternative guidelines or clinical judgment.")


def demonstrate_validation_errors():
    """Show how to handle validation errors."""

    print("Creating a value with potential validation issues...")

    from variables.var import VarImplausibleError

    # Example: Value outside plausible range
    ldl_var = Var(
        id='LDL',
        title='LDL',
        validator={'plausible': '$value > 40'}  # LDL must be > 40
    )

    ldl_record = Record(var=ldl_var, _Record__values=[Value(25)])  # Invalid: < 40

    try:
        # Strict validation will raise error
        ldl_record.validate(strict=True)
    except VarImplausibleError as e:
        print(f"Validation Error: {e}")
        print("The value appears implausible based on clinical ranges.")
    except VarError as e:
        print(f"Variable Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

    # Non-strict validation logs warning but doesn't raise
    print("\nWith strict=False (logs warning instead):")
    try:
        result = ldl_record.validate(strict=False)
        print(f"Validation result: {result}")
    except Exception as e:
        print(f"Error: {e}")


def demonstrate_security_errors():
    """Show how to handle security-related errors."""

    print("Attempting to load CPG with path traversal...")

    try:
        # This should fail security validation
        CPG.from_document_path('../../../etc/passwd.yaml')
    except SecurityError as e:
        print(f"Security Error (expected): {e}")
        print("Path traversal attempts are blocked.")
    except FileNotFoundError as e:
        print(f"File not found (also acceptable): {e}")
    except Exception as e:
        print(f"Other error: {type(e).__name__}: {e}")

    print("\nAttempting to load non-YAML file...")

    try:
        # Create a temp file for testing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'print("malicious")')
            temp_path = f.name

        CPG.from_document_path(temp_path)
    except SecurityError as e:
        print(f"Security Error (expected): {e}")
        print("Non-YAML files are rejected.")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    finally:
        import os
        try:
            os.unlink(temp_path)
        except:
            pass


def show_error_handling_best_practices():
    """Show best practices for error handling."""

    print("\n" + "=" * 60)
    print("Error Handling Best Practices")
    print("=" * 60)

    print("""
1. ALWAYS wrap evaluation in try/except:

    try:
        concord.eligibility()
        concord.sufficiency()
        concord.assess()
        concord.recommendations()
    except NeedAttestationError as e:
        # Collect user input
        handle_attestation(e.records)
    except ExceptionGroup as e:
        # Multiple errors - iterate through
        for error in e.exceptions:
            log_error(error)
    except Exception as e:
        # Catch-all for unexpected errors
        log_error(e)

2. Check results before proceeding:

    eligibility = concord.eligibility()
    if not eligibility.is_eligible:
        return show_ineligibility_message()

    sufficiency = concord.sufficiency()
    if not sufficiency.is_executable:
        return show_missing_data(sufficiency.insufficient_variables)

3. Use ignore flags sparingly:

    # Only for development/testing
    concord.assess(
        ignore_sufficiency=True,
        ignore_required_variable_attestations=True
    )

4. Handle security errors appropriately:

    try:
        cpg = CPG.from_document_path(user_provided_path)
    except SecurityError:
        return error_response("Invalid CPG path")

5. Log errors with context:

    import logging
    logger = logging.getLogger(__name__)

    try:
        result = concord.assess()
    except Exception as e:
        logger.error(f"Assessment failed for CPG={cpg.identifier}", exc_info=True)
        raise
    """)


if __name__ == '__main__':
    main()
    show_error_handling_best_practices()
