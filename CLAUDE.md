# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ConcordCore is a Python framework for evaluating Clinical Practice Guidelines (CPGs) against patient health data. It processes YAML-defined CPGs through a 5-phase evaluation pipeline: CPG Loading → Eligibility Check → Sufficiency Check → Assessment → Recommendations.

The framework is pip-installable as `concordcore`. Library code lives under `src/concordcore/`.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# Run pytest suite
pytest tests/                           # All tests
pytest tests/unit/                      # Unit tests only
pytest tests/integration/               # Integration tests only
pytest tests/unit/test_expression.py    # Single test file
pytest -k "test_value"                  # Tests matching pattern
pytest -v                               # Verbose output
```

## Architecture

### Package Structure

All library code lives under `src/concordcore/`:

```
src/concordcore/
├── core/          # Evaluation pipeline + registry
├── variables/     # Var, Value, Record data model
├── primitives/    # Types, codes, units, validation
├── ontology/      # Code system definitions
├── pghd/          # Patient-generated health data
├── formats/       # FHIR adapter, protocol
├── fhir_parsers/  # FHIR R4 resource parsing
├── cpgs/          # CPG YAML definitions + Python modules
└── ai/            # LLM integration (notes extraction, copilot, adapters)
```

Application code lives under `apps/`:

```
apps/
├── api/           # FastAPI REST server (uvicorn apps.api.server:app)
├── dashboard/     # Streamlit dashboard (streamlit run apps/dashboard/run.py)
└── mcp/           # MCP server (python -m apps.mcp)
```

### CPG Registry

`CPGRegistry` (`src/concordcore/core/cpg_registry.py`) is the single source of truth for discovering and loading CPGs:

```python
from concordcore.core.cpg_registry import get_registry

registry = get_registry()                  # Module-level singleton
cpg = registry.get('2019AccPrimaryPreventionASCVD')  # Load by identifier
entries = registry.list()                  # Lightweight metadata (CPGEntry)
by_cat = registry.list_by_category()       # Grouped by category
ids = registry.identifiers()               # All discovered identifiers
```

All consumers (`apps/dashboard`, `apps/mcp`, `apps/api`, `core/benchmarks`) delegate to the registry. Do not construct CPG file paths manually—use `get_registry().get(identifier)`.

### Core Evaluation Flow

The `Concord` orchestrator class (`src/concordcore/core/concord.py`) manages the evaluation pipeline:

```python
from concordcore.core.cpg_registry import get_registry
from concordcore.core.concord import Concord

cpg = get_registry().get('2019AccPrimaryPreventionASCVD')
concord = Concord(cpg, healthcontext)
concord.eligibility()      # Check if CPG applies to patient
concord.sufficiency()      # Check if health data is sufficient
concord.assess()           # Evaluate health status
concord.recommendations()  # Generate personalized recommendations
```

Each phase must complete successfully before the next can proceed. `NeedAttestationError` is raised when user input is required for missing data.

### Key Modules

- **`core/`**: Evaluation pipeline (`concord.py`, `eligibility.py`, `sufficiency.py`, `assessment.py`, `recommendation.py`) + `cpg_registry.py` for auto-discovery
- **`variables/`**: Data model - `Var` (variable definition), `Value` (data value), `Record` (var + values)
- **`primitives/`**: Types, codes (LOINC, SNOMED, RxNorm, CPT), units, validation
- **`fhir_parsers/`**: FHIR R4 resource parsing (Observation, Condition, MedicationRequest, Procedure)
- **`cpgs/`**: CPG YAML definitions and accompanying Python function modules
- **`ai/`**: LLM integration - notes extraction (`ClinicalNotesExtractor`), copilot (`HealthCopilot`), adapters (Anthropic, OpenAI), instruction scaffolding

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

- `samples/fhir_r4/ndjson/` - FHIR R4 test resources
- `tests/conftest.py` - pytest fixtures for Values, Vars, Records, HealthContexts, and CPGs

## Available CPGs

CPGs are auto-discovered by `CPGRegistry` from `src/concordcore/cpgs/**/*.yaml`. Use `get_registry().identifiers()` to list all available identifiers. Key CPGs:

| Identifier | Description |
|---|---|
| `2019AccPrimaryPreventionASCVD` | Cholesterol/lipid management (ACC/AHA 2019) |
| `uspstfStatinUse` | Statin use for primary prevention (USPSTF) |
| `screening_for_cervical_cancer` | Cervical cancer screening |
| `uspstf_colorectal_cancer_screening` | Colorectal cancer screening |
| `uspstf_hypertension_screening` | Hypertension screening |
| `uspstf_diabetes_screening` | Diabetes screening |
| `uspstf_hiv_screening` | HIV screening |
| `uspstf_hepatitis_c_screening` | Hepatitis C screening |
| `uspstf_hepatitis_b_screening` | Hepatitis B screening |
| `uspstf_depression_screening` | Depression screening |

Each YAML CPG can have an accompanying `.py` module for custom functions (e.g., `cholesterol/ascvd_risk_scores.py`).
