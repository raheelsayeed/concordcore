# ConcordCore Architecture

This document describes the architecture and design of the ConcordCore framework.

## Overview

ConcordCore is a Python framework for evaluating Clinical Practice Guidelines (CPGs) against patient health data. It processes YAML-defined CPGs through a 5-phase evaluation pipeline to generate personalized health recommendations.

```
┌─────────────────┐     ┌─────────────────┐
│   CPG (YAML)    │     │  Health Data    │
│   Definition    │     │  (HealthContext)│
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │       Concord         │
         │    (Orchestrator)     │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌────────┐     ┌──────────┐     ┌────────────┐
│Eligible│────▶│Sufficient│────▶│ Assessment │
└────────┘     └──────────┘     └─────┬──────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │Recommendations│
                              └───────────────┘
```

## Core Components

### 1. CPG (Clinical Practice Guideline)

**Location**: `core/cpg.py`

The CPG class represents a clinical practice guideline definition loaded from YAML. It contains:

- **Variables**: Health data points required for evaluation (labs, vitals, conditions)
- **Eligibility Variables**: Criteria determining if the CPG applies
- **Assessment Variables**: Expressions/functions for health status evaluation
- **Recommendation Variables**: Conditional recommendations based on assessments

```python
cpg = CPG.from_document_path('cpgs/cholesterol.yaml')
```

### 2. HealthContext

**Location**: `core/healthcontext.py`

Contains patient health data and interaction context:

- **Records**: Collection of Record objects (variable + values)
- **Persona**: Who is viewing the results (patient, provider)
- **Until Date**: Optional date filter for historical analysis

```python
healthcontext = HealthContext(records=patient_records, persona=Persona.patient)
```

### 3. Concord (Orchestrator)

**Location**: `core/concord.py`

The main orchestrator managing the evaluation pipeline:

```python
concord = Concord(cpg=cpg, healthcontext=healthcontext)

# Phase 1: Eligibility
eligibility_result = concord.eligibility()

# Phase 2: Sufficiency
sufficiency_result = concord.sufficiency()

# Phase 3: Assessment
assessment_result = concord.assess()

# Phase 4: Recommendations
recommendations = concord.recommendations()
```

## Data Model

### Variable Hierarchy

```
Var (Base)
├── EligibilityVar      # Inclusion/exclusion criteria
├── AssessmentVar       # Health status evaluations
└── RecommendationVar   # Conditional recommendations
```

### Value and Record

```
Value
├── value: Any          # The actual value (int, float, bool, Code)
├── date: datetime      # When the value was recorded
├── code: Code          # Associated medical code
├── unit: str           # Unit of measurement
└── source: list        # Provenance tracking

Record
├── var: Var            # Variable definition
├── values: list[Value] # One or more values
└── attested_value      # User-provided value
```

### Evaluation Results

```
EvaluationResult
├── EligibilityResult   # is_eligible: bool
├── SufficiencyResult   # is_executable: bool, attestation_variables
├── AssessmentResult    # evaluated assessments
└── RecommendationResult# applicable recommendations
```

## Evaluation Pipeline

### Phase 1: Eligibility

Determines if the CPG applies to the patient.

```
Input: HealthContext, EligibilityVariables
Output: EligibilityResult (is_eligible: True/False)

For each eligibility criterion:
  1. Extract variables from expression
  2. Match with patient records
  3. Evaluate expression
  4. All must pass for eligibility
```

### Phase 2: Sufficiency

Checks if health data is sufficient for CPG execution.

```
Classification Matrix:
┌──────────┬───────────────┬─────────────────────────────┐
│ Required │ Has Value     │ Status                      │
├──────────┼───────────────┼─────────────────────────────┤
│ True     │ True          │ Sufficient                  │
│ True     │ False         │ Check user_attestable       │
│          │               │ ├─ True: NeedAttestation    │
│          │               │ └─ False: Insufficient      │
│ False    │ True          │ Sufficient                  │
│ False    │ False         │ Optional                    │
└──────────┴───────────────┴─────────────────────────────┘
```

### Phase 3: Assessment

Evaluates health status using expressions or functions.

```
AssessmentVar with expression:
  "$LDL > 130" → evaluates to True/False

AssessmentVar with function:
  "calculate_ascvd_risk" → calls function in CPG module
```

Assessments can chain (reference other assessments):
```yaml
- id: high_ldl
  expression: $LDL > 130

- id: needs_treatment
  expression: $high_ldl == True and $Age > 40
```

### Phase 4: Recommendations

Generates personalized recommendations.

```
Types:
- display: Always shown (informational)
- display_patient: Shown only to patients
- display_provider: Shown only to providers
- medication: Treatment recommendations
- evaluation: Further testing recommendations

Each recommendation includes:
- Condition expression (based on assessments)
- Narratives per persona
- Evidence classification (COR, LOE, USPSTF)
- Citations
```

## Expression System

**Location**: `core/expression.py`

Expressions use `$VarID` syntax and are evaluated with `simpleeval`:

```python
# Simple comparisons
"$LDL > 130"
"$Age >= 40 and $Age <= 75"

# Reference assessments
"$high_ldl == True"

# Access value properties
"$LDL.count > 3"
"$BP.date < '2024-01-01'"
```

Variables are extracted from expressions and matched to records by ID or code.

## Narrative System

**Location**: `variables/var.py` (Narrative class)

Generates persona-aware text with value substitution:

```yaml
narrative:
  patient:
    True: "Your LDL is $LDL mg/dL, which is above the recommended 130 mg/dL."
    False: "Your LDL is within the normal range."
  provider:
    True: "LDL: $LDL mg/dL (elevated)"
    False: "LDL within normal limits"
```

Placeholders:
- `$VarID` - Variable value
- `$self.value` - Current record's value
- `$self.values` - All values for current record
- `$self.date` - Date of current value

## Medical Code System

**Location**: `primitives/code.py`

Supports standard medical terminologies:

```python
Code.loinc('13457-7')    # LDL Cholesterol
Code.snomed('44054006')  # Type 2 Diabetes
Code.rxnorm('83367')     # Atorvastatin
Code.cpt('99213')        # Office Visit
```

Codes are used for:
- Matching FHIR resources to CPG variables
- Semantic interoperability
- Compliance with standards

## FHIR Integration

**Location**: `fhir/`

Parses FHIR R4 resources into ConcordCore Values:

```
Supported Resources:
├── Observation      → Lab results, vitals
├── Condition        → Diagnoses
├── MedicationRequest→ Prescriptions
└── Procedure        → Procedures
```

```python
from fhir.fhirvalue import FHIRValue

fhir_value = FHIRValue.from_fhir(observation_json)
```

## Security

**Location**: `core/security.py`

Security measures:
- **Path Validation**: Prevents directory traversal attacks
- **Module Sanitization**: Validates CPG function module names
- **Secure Logging**: Masks PII in log output

```python
from core.security import validate_module_path, sanitize_module_name

# Validates module loading
is_valid, error = validate_module_path(base_dir, module_name)
```

## Rendering

**Location**: `renderer/`

Jinja2-based templating for output generation:

```python
from renderer.templates import LocalRenderer

renderer = LocalRenderer()
output = renderer.render(
    template='document',
    cpg=cpg,
    concord=concord,
    persona=Persona.patient
)
```

## Key Design Patterns

### Frozen Dataclasses

Most domain objects are immutable:
```python
@dataclass(frozen=True)
class Var:
    id: str
    title: str
```

### Protocol Classes

Define interfaces for evaluators:
```python
class EligibilityEvaluatorProtocol(Protocol):
    def evaluate(self, healthcontext: HealthContext) -> EligibilityResult:
        ...
```

### Exception Aggregation

Use `ExceptionGroup` for multiple errors:
```python
if errors:
    raise ExceptionGroup('CPG Validation Errors', errors)
```

## Extension Points

### Custom Evaluators

Implement protocol classes for custom evaluation logic:

```python
class CustomAssessmentEvaluator(AssessmentEvaluatorProtocol):
    def assess(self, ...) -> AssessmentResult:
        # Custom logic
        ...

concord.assess(assessment_evaluator=CustomAssessmentEvaluator())
```

### CPG Functions

Add Python functions for complex calculations:

```python
# cpgs/my_cpg.py
def calculate_risk_score(records: dict) -> float:
    ldl = records['LDL'].value
    age = records['Age'].value
    # Complex calculation
    return risk_score
```

```yaml
# cpgs/my_cpg.yaml
assessments:
  - id: risk_score
    function: calculate_risk_score
```

### Data Format Adapters

Implement `DataFormatProtocol` for new data formats:

```python
class HL7v2Adapter(DataFormatProtocol):
    def parse_resource(self, resource: Any) -> Value:
        # Parse HL7v2 message
        ...
```
