# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ConcordCore is a Python framework for evaluating Clinical Practice Guidelines (CPGs) against patient health data. It processes YAML-defined CPGs through a 5-phase evaluation pipeline: CPG Loading → Eligibility Check → Sufficiency Check → Assessment → Recommendations.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Run with a CPG
./main.py -f cpgs/cholesterol.yaml -t document -p patient

# CLI arguments
#   -f <path/to/cpg.yaml>    CPG definition file
#   -t <template_name>       Template for rendering (e.g., 'document')
#   -p <persona>             'patient' or 'provider'
#   --inspect                Show detailed output

# Run legacy tests
./tests.py

# Run pytest suite
pytest tests/                           # All tests
pytest tests/unit/                      # Unit tests only
pytest tests/integration/               # Integration tests only
pytest tests/unit/test_expression.py    # Single test file
pytest -k "test_value"                  # Tests matching pattern
pytest -v                               # Verbose output
```

## Architecture

### Core Evaluation Flow

The `Concord` orchestrator class (`core/concord.py`) manages the evaluation pipeline:

```python
concord = Concord(cpg, healthcontext)
concord.eligibility()      # Check if CPG applies to patient
concord.sufficiency()      # Check if health data is sufficient
concord.assess()           # Evaluate health status
concord.recommendations()  # Generate personalized recommendations
```

Each phase must complete successfully before the next can proceed. `NeedAttestationError` is raised when user input is required for missing data.

### Key Modules

- **`core/`**: Evaluation pipeline (`concord.py`, `eligibility.py`, `sufficiency.py`, `assessment.py`, `recommendation.py`)
- **`variables/`**: Data model - `Var` (variable definition), `Value` (data value), `Record` (var + values)
- **`primitives/`**: Types, codes (LOINC, SNOMED, RxNorm, CPT), units, validation
- **`renderer/`**: Jinja2 templates for generating patient/provider output
- **`fhir/`**: FHIR R4 resource parsing (Observation, Condition, MedicationRequest, Procedure)
- **`inputsession/`**: CLI for collecting patient-reported data (attestations)
- **`cpgs/`**: CPG YAML definitions and accompanying Python function modules

### Expression System

Expressions use `$VarID` syntax and are evaluated with `simpleeval`:
- `$LDL > 189` - reference variable values
- `$ldl_over_189 == True` - reference assessment results
- `$LDL.count > 3` - count of values for a variable
- `$LDL.date` - date accessor
- `in_range($LDL, 100, 200)` - registry functions
- Variables must exist in the CPG definition or evaluation fails

Expression evaluation uses `RecordIndex` for O(1) lookups. Custom functions can be registered via `expression_registry`.

### Narrative System

Persona-aware text generation with value substitution:
- Personas: `patient`, `provider`, `guardian`
- Placeholders: `$value`, `$self.values`, `$LDL`
- Conditional narratives based on evaluation result (`True`/`False`/`None`)

### CPG Function Modules

CPGs can include custom Python modules for complex calculations:
```yaml
functions_module_name: ascvd_risk_scores  # loads ascvd_risk_scores.py from cpgs/
```
Functions receive a dict of variable values. Module names are sanitized and paths validated via `core/security.py`.

### Pipeline Methods

The `Concord` class provides two ways to run evaluations:
1. **Step-by-step**: `eligibility()` → `sufficiency()` → `assess()` → `recommendations()`
2. **All-at-once**: `evaluate()` returns `PipelineResult` with all phases

## Key Patterns

- **Frozen dataclasses** for immutability (create new objects, don't mutate)
- **`YMLStrEnum`** for YAML-serializable enums
- **Protocol classes** for evaluator interfaces (`EligibilityEvaluatorProtocol`, `AssessmentEvaluatorProtocol`, `SufficiencyEvaluatorProtocol`)
- **`ExceptionGroup`** for aggregated error handling
- **`cached_property`** for expensive computations (CPG indexes, evaluation results)
- **`RecordIndex`** for O(1) record lookups by ID during evaluation
- **`VarString`** for parsing `$VarID` placeholders in expressions and narratives

## Data Types

```python
# Variable types hierarchy
Var → EligibilityVar, AssessmentVar, RecommendationVar

# Result types
EvaluationResult → SufficiencyResult, EligibilityResult, AssessmentResult

# Sufficiency statuses
Sufficient, SufficientWithUserAttestation, Insufficient, Optional
```

## Sample Data

- `misc.sample_healthcontext()` - generates test patient data
- `misc.sample_fhir_values()` - generates FHIR-sourced test values
- `samples/fhir_r4/ndjson/` - FHIR R4 test resources
- `tests/conftest.py` - pytest fixtures for Values, Vars, Records, HealthContexts, and CPGs

## Available CPGs

Sample CPG definitions in `cpgs/`:
- `cholesterol.yaml` - Primary example for lipid management
- `uspstf_statinuse.yaml` - USPSTF statin recommendations
- `screeninglungcancer.yaml` - Lung cancer screening

Each YAML CPG can have an accompanying `.py` module for custom functions (e.g., `ascvd_risk_scores.py`).
