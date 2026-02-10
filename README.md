# ConcordCore

A deterministic Python framework for evaluating Clinical Practice Guidelines (CPGs) against patient health data.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

## What is ConcordCore?

ConcordCore is an offline-capable engine that evaluates published clinical practice guidelines against a patient's health record. It processes YAML-defined CPGs through a structured pipeline — eligibility, sufficiency, assessment, and recommendations — producing deterministic, reproducible results. No LLM or internet connection required. FHIR R4 compatible.

## Key Features

- **5-phase evaluation pipeline** — eligibility, sufficiency, assessment, recommendations, and narrative generation
- **15+ bundled CPGs** — USPSTF screenings, ACC/AHA cholesterol management, and more
- **FHIR R4 parsing** — Observation, Condition, MedicationRequest, Procedure, Patient resources
- **Expression engine** — `$VarID` syntax with accessors, custom functions, and cross-variable references
- **Persona-aware narratives** — patient, provider, and guardian-facing text with value substitution
- **MCP server** — expose CPG evaluation as tools for LLM assistants
- **Offline / air-gap capable** — no network calls, fully deterministic

## Installation

```bash
pip install git+https://github.com/raheelsayeed/concordcore.git
```

With AI integration (Anthropic/OpenAI adapters):

```bash
pip install "concordcore[ai] @ git+https://github.com/raheelsayeed/concordcore.git"
```

For development:

```bash
git clone https://github.com/raheelsayeed/concordcore.git
cd concordcore
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

```python
from concordcore.core.cpg_registry import get_registry
from concordcore.core.concord import Concord
from concordcore.core.healthcontext import HealthContext
from concordcore.variables.record import Record
from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.variables.age import Age
from concordcore.primitives.code import Code
from concordcore.primitives.types import Persona

# 1. Load a CPG from the registry
cpg = get_registry().get('2019AccPrimaryPreventionASCVD')

# 2. Build patient health context
healthcontext = HealthContext(
    records=[
        Age(55),
        Record(Var(id='LDL', title='LDL Cholesterol', code=[Code.loinc('13457-7')]),
               _Record__values=[Value(165)]),
        Record(Var(id='HDL', title='HDL Cholesterol', code=[Code.loinc('2085-9')]),
               _Record__values=[Value(52)]),
    ],
    persona=Persona.patient,
)

# 3. Evaluate
concord = Concord(cpg=cpg, healthcontext=healthcontext)
result = concord.evaluate()

print(result.eligibility.is_eligible)
print(result.sufficiency.is_executable)
for rec in result.recommendations.applied:
    print(rec.recommendation.title, rec.narrative)
```

## Available Clinical Practice Guidelines

| Identifier | Guideline | Publisher |
|---|---|---|
| `2019AccPrimaryPreventionASCVD` | Primary Prevention of ASCVD — Blood Cholesterol Management | ACC / AHA |
| `uspstfStatinUse` | Statin Use for Primary Prevention of Cardiovascular Disease | USPSTF |
| `screening_for_cervical_cancer` | Cervical Cancer Screening | USPSTF |
| `uspstf_colorectal_cancer_screening_2021` | Colorectal Cancer Screening | USPSTF |
| `uspstf_hypertension_screening_2021` | Hypertension Screening in Adults | USPSTF |
| `uspstf_diabetes_screening_2021` | Prediabetes and Type 2 Diabetes Screening | USPSTF |
| `uspstf_hiv_screening` | HIV Screening | USPSTF |
| `uspstf_hepatitis_c_screening` | Hepatitis C Virus Screening | USPSTF |
| `uspstf_hepatitis_b_screening` | Hepatitis B Virus Screening | USPSTF |
| `uspstf_depression_screening` | Depression Screening in Adults | USPSTF |
| `uspstf_breast_cancer_screening_2024` | Breast Cancer Screening | USPSTF |
| `uspstf_lung_cancer_screening_2021` | Lung Cancer Screening | USPSTF |
| `uspstf_obesity_screening_2018` | Obesity Screening and Behavioral Interventions | USPSTF |
| `uspstf_osteoporosis_screening_2018` | Osteoporosis Screening to Prevent Fractures | USPSTF |
| `uspstf_alcohol_use_screening_2018` | Unhealthy Alcohol Use Screening and Counseling | USPSTF |

```python
# List all available CPGs programmatically
from concordcore.core.cpg_registry import get_registry
for entry in get_registry().list():
    print(entry.identifier, entry.title)
```

## Evaluation Pipeline

Each phase must complete successfully before the next can proceed:

```
CPG + HealthContext
    → Eligibility    Does this guideline apply to the patient?
    → Sufficiency    Is there enough data to evaluate?
    → Assessment     What does the data indicate?
    → Recommendations  What actions are recommended?
```

Step-by-step API:

```python
concord = Concord(cpg=cpg, healthcontext=healthcontext)

eligibility = concord.eligibility()       # EligibilityResult
sufficiency = concord.sufficiency()       # SufficiencyResult
assessment  = concord.assess()            # AssessmentResult
recommendations = concord.recommendations()  # RecommendationResult
```

Or run all phases at once:

```python
result = concord.evaluate()  # PipelineResult
```

## Expression System

CPG variables use `$VarID` references evaluated with `simpleeval`:

```yaml
# Direct value comparison
expression: $LDL > 189

# Reference assessment results
expression: $ldl_over_189 == True

# Value count and date accessors
expression: $LDL.count > 3
expression: $LDL.date

# Built-in functions
expression: in_range($Age, 40, 75)
```

## FHIR Integration

ConcordCore parses FHIR R4 resources into its internal data model:

- **Resources**: Observation, Condition, MedicationRequest, Procedure, Patient
- **Code systems**: LOINC, SNOMED CT, RxNorm, CPT, ICD-10, CVX

## Applications

ConcordCore ships with three application frontends under `apps/`:

**MCP Server** — expose CPG evaluation as tools for Claude and other LLM assistants:

```bash
python -m apps.mcp
```

**Streamlit Dashboard** — interactive patient screening and CPG explorer:

```bash
streamlit run apps/dashboard/run.py
```

**FastAPI Server** — REST API for CPG evaluation:

```bash
uvicorn apps.api.server:app
```

## Project Structure

```
src/concordcore/
├── core/           # Evaluation pipeline, registry, orchestrator
├── variables/      # Var, Value, Record data model
├── primitives/     # Types, codes, units, validation
├── ontology/       # Code system definitions (LOINC, SNOMED, etc.)
├── pghd/           # Patient-generated health data
├── formats/        # FHIR adapter and protocol
├── fhir_parsers/   # FHIR R4 resource parsing
├── cpgs/           # Bundled CPG definitions (YAML + Python)
└── ai/             # LLM integration (copilot, notes extraction)

apps/
├── api/            # FastAPI REST server
├── dashboard/      # Streamlit dashboard
└── mcp/            # MCP server for LLM tool use
```

## Development

```bash
git clone https://github.com/raheelsayeed/concordcore.git
cd concordcore
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

## License

MIT
