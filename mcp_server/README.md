# ConcordCore MCP Server

A Model Context Protocol (MCP) server that provides clinical decision support by evaluating patient health data against evidence-based Clinical Practice Guidelines (CPGs).

## Overview

The ConcordCore MCP Server enables AI assistants and applications to:

- **Evaluate patient data** against 15+ clinical practice guidelines (USPSTF, ACC/AHA)
- **Accept multiple data formats**: FHIR R4 resources, variable/value pairs, or clinical notes
- **Extract data from clinical notes** using LLM-powered extraction with configurable prompts
- **Generate prioritized recommendations** ranked by evidence strength (Class of Recommendation, Level of Evidence, USPSTF Grade)
- **Provide detailed explanations** with assessment chains and citations
- **Track data quality** with confidence scoring and missing data identification

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/concordcore.git
cd concordcore

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Your MCP Client

#### Claude Desktop

Add to your `claude_desktop_config.json` (typically at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "concord": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/concordcore"
    }
  }
}
```

#### Claude Code CLI

Add to your project's `.mcp.json` or global Claude Code settings:

```json
{
  "mcpServers": {
    "concord": {
      "command": "/path/to/concordcore/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/concordcore"
    }
  }
}
```

### 3. Verify Installation

```bash
# Test the server starts correctly
python -m mcp_server
# (Press Ctrl+C to stop - it waits for MCP messages on stdio)
```

### 4. Start Using

Once configured, your AI assistant can use natural language:

```
"List all available clinical practice guidelines"
"Evaluate this patient against the cholesterol management guideline"
"What health screenings does this 55-year-old male patient need?"
"Explain why statin therapy is recommended for this patient"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client                                │
│              (Claude Desktop, Claude Code, etc.)                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │ MCP Protocol (stdio)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ConcordCore MCP Server                       │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  MANDATORY: acknowledge_guidelines (enforces patient safety) │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▼                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Tools     │  │  Resources  │  │        Prompts          │  │
│  │  (21 total) │  │ (CPG URIs)  │  │ (health_assessment,     │  │
│  │             │  │             │  │  explain_all_recs)      │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         └────────────────┼─────────────────────┘                 │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    ConcordCore Engine                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │  │
│  │  │Eligibility│→│Sufficiency│→│Assessment│→ │Recommend- │  │  │
│  │  │  Check   │  │  Check   │  │          │  │  ations   │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Care Gap Detection                      │  │
│  │  detect_care_gaps → prioritized by USPSTF grade           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Clinical Practice Guidelines                  │
│  cholesterol (ACC/AHA) │ diabetes (USPSTF) │ depression (USPSTF)│
│  hepatitis_b │ hepatitis_c │ hiv │ hypertension │ colorectal    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Input Methods

ConcordCore supports three methods for providing patient health data:

### Method 1: Variable/Value Pairs

The simplest method - directly specify health data variables and their values.

**Tool:** `create_health_context`

```json
{
  "session_id": "patient-123",
  "persona": "patient",
  "health_data": [
    {"variable_id": "Age", "value": 55},
    {"variable_id": "Gender", "value": "male"},
    {"variable_id": "LDL", "value": 160, "unit": "mg/dL"},
    {"variable_id": "HDL", "value": 45, "unit": "mg/dL"},
    {"variable_id": "TotalCholesterol", "value": 240},
    {"variable_id": "triglycerides", "value": 180},
    {"variable_id": "systolic_bp", "value": 145},
    {"variable_id": "is_smoker", "value": true},
    {"variable_id": "diabetesMellitus", "value": false},
    {"variable_id": "Ethnicity", "value": "White"}
  ]
}
```

**Common Variables:**

| Variable ID | Type | Description |
|-------------|------|-------------|
| `Age` | integer | Patient age in years |
| `Gender` | string | "male" or "female" |
| `LDL` | number | LDL cholesterol (mg/dL) |
| `HDL` | number | HDL cholesterol (mg/dL) |
| `TotalCholesterol` | number | Total cholesterol (mg/dL) |
| `triglycerides` | number | Triglycerides (mg/dL) |
| `systolic_bp` | number | Systolic blood pressure (mmHg) |
| `diastolic_bp` | number | Diastolic blood pressure (mmHg) |
| `is_smoker` | boolean | Current smoker status |
| `diabetesMellitus` | boolean | Has diabetes |
| `Ethnicity` | string | "White", "Black", "Hispanic", etc. |

### Method 2: FHIR R4 Resources

Send standard FHIR R4 resources for interoperability with EHR systems.

**Tool:** `create_health_context_from_fhir`

```json
{
  "session_id": "patient-456",
  "persona": "provider",
  "cpg_id": "cholesterol",
  "fhir_data": {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
      {
        "resource": {
          "resourceType": "Patient",
          "id": "patient-456",
          "birthDate": "1970-03-15",
          "gender": "male"
        }
      },
      {
        "resource": {
          "resourceType": "Observation",
          "id": "ldl-obs",
          "status": "final",
          "code": {
            "coding": [{
              "system": "http://loinc.org",
              "code": "18262-6",
              "display": "LDL Cholesterol"
            }]
          },
          "valueQuantity": {
            "value": 160,
            "unit": "mg/dL",
            "system": "http://unitsofmeasure.org",
            "code": "mg/dL"
          },
          "effectiveDateTime": "2024-01-15"
        }
      },
      {
        "resource": {
          "resourceType": "Condition",
          "id": "diabetes-condition",
          "clinicalStatus": {
            "coding": [{"code": "active"}]
          },
          "code": {
            "coding": [{
              "system": "http://snomed.info/sct",
              "code": "73211009",
              "display": "Diabetes mellitus"
            }]
          }
        }
      },
      {
        "resource": {
          "resourceType": "MedicationRequest",
          "id": "statin-rx",
          "status": "active",
          "medicationCodeableConcept": {
            "coding": [{
              "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
              "code": "617311",
              "display": "atorvastatin 20 MG"
            }]
          }
        }
      }
    ]
  }
}
```

**Supported FHIR Resources:**

| Resource Type | Mapped To |
|---------------|-----------|
| Patient | Age (from birthDate), Gender |
| Observation | Lab values (LDL, HDL, A1c, BP, etc.) via LOINC codes |
| Condition | Diagnoses (diabetes, hypertension, etc.) via SNOMED codes |
| MedicationRequest | Current medications via RxNorm codes |
| Procedure | Procedures (colonoscopy, etc.) via CPT codes |

**Common LOINC Codes:**

| Code | Variable | Description |
|------|----------|-------------|
| 18262-6 | LDL | LDL Cholesterol |
| 2085-9 | HDL | HDL Cholesterol |
| 2093-3 | TotalCholesterol | Total Cholesterol |
| 2571-8 | triglycerides | Triglycerides |
| 4548-4 | HbA1c | Hemoglobin A1c |
| 8480-6 | systolic_bp | Systolic Blood Pressure |
| 8462-4 | diastolic_bp | Diastolic Blood Pressure |

### Method 3: Clinical Notes with LLM Extraction

ConcordCore can extract variable values from unstructured clinical notes using LLM-powered extraction. Each CPG variable can define an `llm_prompt` that guides the extraction.

**Python API (for building applications):**

```python
from ai.notes_extractor import ClinicalNotesExtractor, ExtractionConfig
from core.cpg import CPG
from core.healthcontext import HealthContext

# Load CPG with llm_prompts defined
cpg = CPG.load('cpgs/cholesterol.yaml')

# Configure LLM provider
config = ExtractionConfig(
    provider='anthropic',      # or 'openai'
    model='claude-sonnet-4-20250514',
    min_confidence=0.7,
    batch_size=10
)

# Clinical notes input
notes = """
HISTORY OF PRESENT ILLNESS:
55-year-old male presenting for annual wellness visit.

PAST MEDICAL HISTORY:
- Hypertension, on lisinopril 10mg daily
- Type 2 Diabetes Mellitus, well controlled on metformin 1000mg BID

FAMILY HISTORY:
Father had myocardial infarction at age 58.
Mother has hyperlipidemia, currently on statin therapy.

SOCIAL HISTORY:
Former smoker, quit 5 years ago (20 pack-year history).
Denies alcohol use.

LABS (from 2 weeks ago):
- LDL: 168 mg/dL
- HDL: 42 mg/dL
- Triglycerides: 180 mg/dL
- Total Cholesterol: 245 mg/dL
- HbA1c: 7.2%

VITALS:
BP: 138/88 mmHg
BMI: 29.4 kg/m²

ASSESSMENT:
1. Hyperlipidemia with elevated LDL
2. Type 2 DM, controlled
3. Hypertension, controlled
4. Elevated cardiovascular risk
"""

# Extract variables from notes
extractor = ClinicalNotesExtractor(config)
records = extractor.extract_variables(notes, cpg.variables)

# Create health context from extracted records
health_context = HealthContext(records=records)

# Or use the combined method
health_context = HealthContext.from_clinical_notes(
    clinical_notes=notes,
    cpg=cpg,
    extraction_config=config
)
```

**Example llm_prompt in CPG YAML:**

```yaml
variables:
  - id: FamilyHxPrematureASCVD
    title: "Family History of Premature ASCVD"
    type: boolean
    user_attestable: True
    code:
      concord: ['Family History of Premature ASCVD']
    llm_prompt: |
      Does the patient have a family history of premature ASCVD
      (atherosclerotic cardiovascular disease)?

      Premature means:
      - Male first-degree relative (father, brother, son) < 55 years old
      - Female first-degree relative (mother, sister, daughter) < 65 years old

      Look for: father/brother with early heart attack, MI, stroke, coronary
      artery disease, coronary bypass, stent, angina, or cardiovascular death.

      Return: true if family history of premature ASCVD is present,
              false if explicitly denied or no family history mentioned,
              null if not mentioned at all.
    narrative:
      patient:
        True: "You have a family history of early heart disease."
        False: "No family history of early heart disease noted."
```

**ClinicalNote Source Tracking:**

When values are extracted from clinical notes, the `Value.source` contains a `ClinicalNote` object with metadata:

```python
from ai.clinical_note import ClinicalNote

# After extraction, each Value's source is a ClinicalNote
for record in records:
    if record.value and record.value.source:
        note = record.value.source[0]  # ClinicalNote object
        print(f"Variable: {record.id}")
        print(f"  Value: {record.value.value}")
        print(f"  Confidence: {note.confidence}")
        print(f"  Source snippet: {note.snippet}")
        print(f"  Provider: {note.provider}")
        print(f"  Model: {note.model}")
```

**Combining Multiple Data Sources:**

```python
# Priority: FHIR > Clinical Notes > Attestations
health_context = HealthContext.from_mixed_sources(
    fhir_bundle=fhir_data,           # Highest priority
    clinical_notes=notes_text,        # Fill gaps from notes
    attestations=user_responses,      # User-provided values
    cpg=cpg,
    extraction_config=config
)
```

---

## Available Tools (21)

### Mandatory First Step

#### `acknowledge_guidelines`
**REQUIRED FIRST STEP**: Acknowledge Concord usage guidelines before using protected tools.

This tool MUST be called before any of these protected tools:
- `create_health_context`
- `create_health_context_from_fhir`
- `evaluate_patient`
- `evaluate_all_cpgs`
- `evaluate_multiple_cpgs`
- `submit_attestation`
- `detect_care_gaps`

**Parameters:**
- `session_id` (string, required): Unique session identifier

**Returns:**
```json
{
  "status": "acknowledged",
  "session_id": "my-session",
  "acknowledged_at": "2024-01-15T10:30:00",
  "guidelines": "# CONCORD MANDATORY GUIDELINES...",
  "protected_tools_now_available": [
    "create_health_context",
    "create_health_context_from_fhir",
    "evaluate_patient",
    "evaluate_all_cpgs",
    "evaluate_multiple_cpgs",
    "submit_attestation",
    "detect_care_gaps"
  ]
}
```

**Key Guidelines Returned:**
1. **NEVER fabricate patient data** - Only use explicitly provided values
2. **Handle missing data correctly** - Ask user, don't assume
3. **Use exact variable IDs** - Case-sensitive, match CPG definition
4. **Format values correctly** - SNOMED codes for gender, OID for ethnicity
5. **Patient safety is paramount** - Always recommend consulting healthcare provider
6. **Do not interpret recommendations** - Present verbatim without reconciliation

---

### CPG Discovery

#### `list_cpgs`
List all available Clinical Practice Guidelines.

**Parameters:** None

**Returns:**
```json
{
  "available_cpgs": [
    {
      "identifier": "cholesterol",
      "title": "2019 Primary Prevention of ASCVD by Managing Blood Cholesterol",
      "publisher": "ACC/AHA",
      "variables_count": 32,
      "assessments_count": 18,
      "recommendations_count": 14
    },
    {
      "identifier": "uspstf_depression_screening",
      "title": "USPSTF Depression Screening in Adults",
      "publisher": "USPSTF",
      "variables_count": 17,
      "assessments_count": 12,
      "recommendations_count": 6
    }
  ],
  "total_count": 15
}
```

#### `get_cpg_info`
Get detailed information about a specific CPG.

**Parameters:**
- `cpg_id` (string, required): CPG identifier

**Returns:**
```json
{
  "identifier": "cholesterol",
  "title": "2019 Primary Prevention of ASCVD by Managing Blood Cholesterol",
  "publisher": "ACC/AHA",
  "variables": [
    {
      "id": "Age",
      "title": "Age",
      "required": true,
      "user_attestable": false,
      "code": "concord:Age"
    },
    {
      "id": "LDL",
      "title": "LDL Cholesterol",
      "required": false,
      "user_attestable": false,
      "code": "LOINC:18262-6"
    }
  ],
  "eligibility_criteria": [
    {
      "id": "age_criteria",
      "title": "Age between 20 and 75",
      "expression": "$Age >= 20 and $Age <= 75"
    }
  ],
  "assessments": [
    {
      "id": "ldl_over_190",
      "title": "Very High LDL",
      "expression": "$LDL >= 190"
    }
  ],
  "recommendations": [
    {
      "id": "high_intensity_statin",
      "title": "High-Intensity Statin Therapy",
      "type": "medication",
      "class_of_recommendation": "I",
      "level_of_evidence": "A"
    }
  ]
}
```

---

### Health Context Creation

#### `create_health_context`
Create patient context from variable/value pairs.

**Parameters:**
- `session_id` (string, required): Unique session identifier
- `persona` (string): "patient" or "provider" (default: "patient")
- `health_data` (array, required): Array of variable/value objects

**Example:**
```json
{
  "session_id": "patient-001",
  "persona": "patient",
  "health_data": [
    {"variable_id": "Age", "value": 55},
    {"variable_id": "LDL", "value": 160, "unit": "mg/dL", "date": "2024-01-15"},
    {"variable_id": "diabetesMellitus", "value": true}
  ]
}
```

**Returns:**
```json
{
  "session_id": "patient-001",
  "status": "created",
  "records_count": 3,
  "variables": ["Age", "LDL", "diabetesMellitus"]
}
```

#### `create_health_context_from_fhir`
Create patient context from FHIR R4 resources.

**Parameters:**
- `session_id` (string, required): Unique session identifier
- `fhir_data` (object, required): FHIR Bundle or array of resources
- `cpg_id` (string): Optional CPG to match FHIR codes against
- `persona` (string): "patient" or "provider"

**Returns:**
```json
{
  "session_id": "fhir-session",
  "status": "created",
  "records_count": 8,
  "variables": ["Age", "Gender", "LDL", "HDL", "diabetesMellitus"],
  "fhir_summary": {
    "Patient": 1,
    "Observation": 5,
    "Condition": 2,
    "MedicationRequest": 1
  }
}
```

---

### Evaluation

#### `evaluate_patient`
Evaluate patient against a specific CPG.

**Parameters:**
- `session_id` (string, required): Session with health context
- `cpg_id` (string, required): CPG to evaluate against
- `skip_eligibility` (boolean): Skip eligibility check (default: false)
- `include_confidence` (boolean): Include confidence scores (default: true)

**Returns:**
```json
{
  "session_id": "patient-001",
  "cpg_id": "cholesterol",
  "cpg_title": "2019 Primary Prevention of ASCVD...",
  "status": "evaluated",
  "eligibility": {
    "is_eligible": true
  },
  "sufficiency": {
    "is_executable": true,
    "missing_required": 0,
    "needs_attestation": 3
  },
  "assessments": [
    {
      "id": "ldl_over_190",
      "value": false,
      "narrative": "Your LDL is 160 mg/dL."
    },
    {
      "id": "intermediate_risk",
      "value": true,
      "narrative": "Your 10-year ASCVD risk is between 7.5% and 20%."
    }
  ],
  "recommendations": [
    {
      "id": "moderate_intensity_statin",
      "title": "Moderate-Intensity Statin Therapy",
      "applies": true,
      "narrative": "Based on your intermediate cardiovascular risk, moderate-intensity statin therapy is recommended."
    }
  ],
  "recommendations_count": 3,
  "is_complete": true,
  "confidence": {
    "data_completeness": 0.85,
    "data_freshness": 0.90,
    "validation_score": 1.0,
    "overall_score": 0.88
  }
}
```

**Status Values:**
- `evaluated` - Evaluation completed successfully
- `needs_attestation` - Missing data that can be provided by user
- `error` - Evaluation failed

#### `evaluate_all_cpgs`
Evaluate patient against ALL available CPGs.

**Parameters:**
- `session_id` (string, required): Session with health context
- `include_confidence` (boolean): Include confidence scores

**Returns:**
```json
{
  "session_id": "patient-001",
  "total_cpgs": 15,
  "eligible_cpgs": 8,
  "cpgs_with_recommendations": 5,
  "total_recommendations": 12,
  "results": [
    {
      "cpg_id": "cholesterol",
      "cpg_title": "2019 Primary Prevention of ASCVD...",
      "eligible": true,
      "status": "evaluated",
      "recommendations_count": 3
    },
    {
      "cpg_id": "uspstf_depression_screening",
      "cpg_title": "USPSTF Depression Screening in Adults",
      "eligible": true,
      "status": "evaluated",
      "recommendations_count": 1
    }
  ]
}
```

---

### Recommendations

#### `get_recommendations`
Get recommendations from a completed evaluation.

**Parameters:**
- `session_id` (string, required): Session with completed evaluation

**Returns:**
```json
{
  "session_id": "patient-001",
  "cpg_title": "2019 Primary Prevention of ASCVD...",
  "recommendations": [
    {
      "id": "moderate_intensity_statin",
      "title": "Moderate-Intensity Statin Therapy",
      "applies": true,
      "narrative": "Based on your intermediate cardiovascular risk...",
      "type": "medication",
      "citations_count": 2
    }
  ],
  "total_count": 3
}
```

#### `get_prioritized_recommendations`
Get recommendations ranked by evidence strength.

**Parameters:**
- `session_id` (string, required)
- `limit` (integer): Max recommendations to return (default: 10)
- `include_all_evaluated` (boolean): Include non-applicable recommendations

**Returns:**
```json
{
  "session_id": "patient-001",
  "cpg_title": "2019 Primary Prevention of ASCVD...",
  "prioritized_recommendations": [
    {
      "recommendation_id": "high_intensity_statin",
      "title": "High-Intensity Statin Therapy",
      "priority_score": 95,
      "priority_level": "CRITICAL",
      "class_of_recommendation": "I",
      "level_of_evidence": "A",
      "uspstf_grade": null,
      "rationale": "Class I recommendation with Level A evidence from multiple RCTs"
    },
    {
      "recommendation_id": "lifestyle_modification",
      "title": "Lifestyle Modifications",
      "priority_score": 72,
      "priority_level": "HIGH",
      "class_of_recommendation": "I",
      "level_of_evidence": "B-R",
      "rationale": "Class I with moderate quality evidence"
    }
  ],
  "summary": {
    "critical": 1,
    "high": 2,
    "moderate": 1,
    "low": 0
  }
}
```

**Priority Levels:**
- `CRITICAL` (score >= 80 with COR I)
- `HIGH` (score >= 70)
- `MODERATE` (score >= 50)
- `LOW` (score >= 30)
- `INFORMATIONAL` (score < 30)

**Priority Score Algorithm:**
```
score = (0.45 * COR_score) +      # I=100, IIa=75, IIb=50, III=25
        (0.35 * LOE_score) +      # A=100, B-R=80, B-NR=60, C-LD=40, C-EO=20
        (0.20 * USPSTF_score)     # A=100, B=75, C=50, D=25, I=10
```

#### `explain_recommendation`
Get detailed explanation of why a recommendation applies.

**Parameters:**
- `session_id` (string, required)
- `recommendation_id` (string, required)
- `persona` (string): "patient" or "provider" (default: "patient")

**Returns:**
```json
{
  "session_id": "patient-001",
  "recommendation_id": "moderate_intensity_statin",
  "title": "Moderate-Intensity Statin Therapy",
  "applies": true,
  "summary": "Based on your cardiovascular risk profile, you would benefit from moderate-intensity statin therapy to reduce your risk of heart attack and stroke.",
  "assessment_chain": [
    {
      "id": "age_40_75",
      "title": "Age 40-75 Years",
      "value": true,
      "expression": "$Age >= 40 and $Age <= 75",
      "contribution": "You are in the target age range for statin consideration."
    },
    {
      "id": "intermediate_risk",
      "title": "Intermediate 10-Year ASCVD Risk",
      "value": true,
      "expression": "$ASCVD_risk >= 7.5 and $ASCVD_risk < 20",
      "contribution": "Your calculated 10-year risk is 12.5%, placing you in the intermediate risk category."
    }
  ],
  "evidence": {
    "class_of_recommendation": "I (Strong)",
    "level_of_evidence": "A (High Quality)",
    "description": "Benefit >>> Risk. Recommendation should be performed."
  },
  "citations": [
    {
      "title": "2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease",
      "uri": "https://doi.org/10.1161/CIR.0000000000000678"
    }
  ],
  "source_data": [
    {"variable_id": "Age", "value": 55},
    {"variable_id": "LDL", "value": 160},
    {"variable_id": "systolic_bp", "value": 145}
  ]
}
```

---

### Data Quality

#### `get_confidence_scores`
Get confidence metrics for the evaluation.

**Parameters:**
- `session_id` (string, required)

**Returns:**
```json
{
  "session_id": "patient-001",
  "cpg_title": "2019 Primary Prevention of ASCVD...",
  "data_completeness": 0.85,
  "data_freshness": 0.90,
  "validation_score": 1.0,
  "attestation_burden": 0.15,
  "overall_confidence": 0.88,
  "details": {
    "total_variables": 20,
    "with_values": 17,
    "fresh_values": 15,
    "validated": 17,
    "from_attestation": 3
  }
}
```

**Confidence Score Algorithm:**
```
overall = (0.35 * completeness) +     # % required vars with data
          (0.25 * freshness) +        # data age scoring
          (0.25 * validation) +       # % passed plausibility checks
          (0.15 * (1 - attestation_burden))  # penalty for self-reported data

Freshness scoring by data age:
  <= 30 days:  1.0
  <= 90 days:  0.8
  <= 365 days: 0.5
  > 365 days:  0.2
```

#### `get_missing_data`
Identify missing data needed for complete evaluation.

**Parameters:**
- `session_id` (string, required)

**Returns:**
```json
{
  "session_id": "patient-001",
  "missing_required": [
    {
      "variable_id": "TotalCholesterol",
      "title": "Total Cholesterol",
      "required": true,
      "user_attestable": false
    }
  ],
  "needs_attestation": [
    {
      "variable_id": "FamilyHxPrematureASCVD",
      "title": "Family History of Premature ASCVD",
      "question": "Do you have a family history of early heart disease (heart attack, stroke) in a close relative?"
    },
    {
      "variable_id": "is_smoker",
      "title": "Current Smoker",
      "question": "Are you currently a smoker?"
    }
  ],
  "total_missing": 3
}
```

#### `submit_attestation`
Submit patient-attested values for missing data.

**Parameters:**
- `session_id` (string, required)
- `attestations` (array, required): Array of variable/value pairs

**Example:**
```json
{
  "session_id": "patient-001",
  "attestations": [
    {"variable_id": "FamilyHxPrematureASCVD", "value": true},
    {"variable_id": "is_smoker", "value": false}
  ]
}
```

**Returns:**
```json
{
  "session_id": "patient-001",
  "status": "attestations_added",
  "added_count": 2,
  "variables": ["FamilyHxPrematureASCVD", "is_smoker"],
  "message": "Call evaluate_patient again to re-evaluate with new data"
}
```

---

### Care Gap Detection

#### `detect_care_gaps`
Detect preventive care gaps by evaluating patient against all applicable CPGs.

**Parameters:**
- `session_id` (string, required): Session with health context
- `patient_id` (string): Optional patient identifier for the report (default: "unknown")
- `include_ineligible` (boolean): Include gaps for CPGs patient isn't eligible for (default: false)

**Returns:**
```json
{
  "session_id": "patient-001",
  "patient_id": "patient-123",
  "evaluation_date": "2024-01-15T10:30:00",
  "total_cpgs_evaluated": 15,
  "total_gaps": 5,
  "gaps_by_priority": {
    "critical": 1,
    "high": 2,
    "moderate": 1,
    "low": 1
  },
  "gaps_by_type": {
    "missing_screening": 2,
    "unmet_recommendation": 2,
    "missing_data": 1
  },
  "gaps": [
    {
      "id": "uspstf_scc_cervical_screening",
      "title": "Cervical Cancer Screening",
      "description": "Recommended screening for women aged 30-65",
      "gap_type": "missing_screening",
      "priority": "critical",
      "cpg_id": "scc",
      "cpg_title": "Screening for Cervical Cancer",
      "uspstf_grade": "A",
      "reason": "Recommendation applies based on patient data",
      "suggested_action": "Strongly recommended - schedule appointment",
      "evidence_summary": "USPSTF Grade A"
    },
    {
      "id": "uspstf_statinuse_moderate_statin",
      "title": "Moderate-Intensity Statin Therapy",
      "description": "Adults aged 40-75 with CVD risk factors and 10-year risk ≥10%",
      "gap_type": "unmet_recommendation",
      "priority": "high",
      "cpg_id": "uspstf_statinuse",
      "cpg_title": "Statin Use for Primary Prevention",
      "uspstf_grade": "B",
      "reason": "Recommendation applies based on patient data",
      "suggested_action": "Strongly recommended - schedule appointment",
      "evidence_summary": "USPSTF Grade B"
    }
  ],
  "_summary": "ATTENTION: 1 critical priority care gap(s) detected. Immediate action recommended."
}
```

**Gap Types:**
- `missing_screening` - Eligible for screening but not performed
- `overdue_screening` - Last performed beyond recommended interval
- `unmet_recommendation` - CPG recommends action not yet taken
- `missing_data` - Required data missing for complete evaluation

**Priority Levels (based on USPSTF Grade):**
- `critical` - Grade A recommendations (highest confidence benefit)
- `high` - Grade B recommendations (high confidence benefit)
- `moderate` - Grade C recommendations (selective recommendation)
- `low` - Missing data or insufficient evidence
- `informational` - Grade D (recommend against) or I (insufficient evidence)

**Use Cases:**
- Annual wellness visit preparation
- Population health gap closure
- Quality measure tracking (HEDIS, MIPS)
- Proactive patient outreach

---

## Resources

### Guidelines Resource

- `concord://guidelines` - **IMPORTANT**: Critical guidelines for using Concord tools. READ THIS FIRST before evaluating patients.

### CPG Resources

CPGs are available as MCP resources with URIs in the format `cpg://{identifier}`.

**Available Resources:**
- `cpg://cholesterol` - 2019 ACC/AHA Cholesterol Management
- `cpg://uspstf_statinuse` - USPSTF Statin Use
- `cpg://uspstf_depression_screening` - USPSTF Depression Screening
- `cpg://uspstf_diabetes_screening` - USPSTF Diabetes Screening
- `cpg://uspstf_colorectal_cancer_screening` - USPSTF Colorectal Cancer Screening
- `cpg://uspstf_hepatitis_b_screening` - USPSTF Hepatitis B Screening
- `cpg://uspstf_hepatitis_c_screening` - USPSTF Hepatitis C Screening
- `cpg://uspstf_hiv_screening` - USPSTF HIV Screening
- `cpg://uspstf_hypertension_screening` - USPSTF Hypertension Screening
- `cpg://scc` - Screening for Cervical Cancer

---

## Prompts

### `concord_guidelines`
**IMPORTANT**: Critical guidelines for using Concord tools safely.

**Arguments:** None

**Usage:** Read these guidelines before using any Concord tools. Contains critical rules about never fabricating patient data and how to handle missing information.

### `health_assessment`
Comprehensive health assessment workflow prompt.

**Arguments:**
- `patient_data` (required): JSON string of patient health data

**Usage:** Guides the AI through a complete assessment workflow:
1. Create health context
2. Evaluate against all CPGs
3. Get prioritized recommendations
4. Explain top recommendations
5. Summarize findings

### `explain_all_recommendations`
Explain all applicable recommendations.

**Arguments:**
- `session_id` (required): Session with completed evaluation

**Usage:** Guides the AI to explain each recommendation in patient-friendly terms.

---

## Example Workflows

### Workflow 1: Simple Patient Assessment

```
User: "I'm a 55-year-old male. My recent labs showed LDL 168, HDL 42,
       and total cholesterol 245. My blood pressure is 138/88.
       I have type 2 diabetes but don't smoke. What guidelines apply to me?"

AI Assistant actions:
1. create_health_context with the provided data
2. evaluate_all_cpgs to check all guidelines
3. get_prioritized_recommendations for actionable items
4. explain_recommendation for top recommendations

Response: "Based on your health data, several guidelines apply:
- Cholesterol Management: Your LDL of 168 mg/dL combined with diabetes
  qualifies you for statin therapy consideration (Class I, Level A evidence)
- Diabetes Screening: Already diagnosed, recommend ongoing monitoring
- Depression Screening: Recommended for all adults (Grade B)
- Blood Pressure: Your BP of 138/88 suggests hypertension management..."
```

### Workflow 2: FHIR-Based EHR Integration

For healthcare applications receiving FHIR data from EHR systems:

```python
import json
from mcp import ClientSession

async def process_patient_fhir(fhir_bundle: dict, session: ClientSession):
    """Process patient FHIR bundle through ConcordCore."""

    # Create unique session ID (e.g., from patient ID + timestamp)
    session_id = f"patient-{fhir_bundle['entry'][0]['resource']['id']}"

    # Step 1: Create health context from FHIR
    result = await session.call_tool('create_health_context_from_fhir', {
        'session_id': session_id,
        'persona': 'provider',
        'fhir_data': fhir_bundle
    })
    context_info = json.loads(result.content[0].text)
    print(f"Loaded {context_info['records_count']} health records from FHIR")

    # Step 2: Evaluate against all CPGs
    result = await session.call_tool('evaluate_all_cpgs', {
        'session_id': session_id,
        'include_confidence': True
    })
    eval_summary = json.loads(result.content[0].text)
    print(f"Eligible for {eval_summary['eligible_cpgs']} guidelines")
    print(f"Total recommendations: {eval_summary['total_recommendations']}")

    # Step 3: Get prioritized recommendations
    result = await session.call_tool('get_prioritized_recommendations', {
        'session_id': session_id,
        'limit': 10
    })
    recommendations = json.loads(result.content[0].text)

    # Step 4: Check for missing data
    result = await session.call_tool('get_missing_data', {
        'session_id': session_id
    })
    missing = json.loads(result.content[0].text)

    return {
        'session_id': session_id,
        'recommendations': recommendations['prioritized_recommendations'],
        'missing_data': missing['needs_attestation'],
        'confidence': eval_summary.get('confidence', {})
    }
```

### Workflow 3: Interactive Patient Questionnaire

For patient-facing applications that gather missing data:

```python
async def interactive_assessment(initial_data: list, session: ClientSession):
    """Run assessment with interactive data collection."""

    session_id = "interactive-session"

    # Step 1: Create initial context
    await session.call_tool('create_health_context', {
        'session_id': session_id,
        'persona': 'patient',
        'health_data': initial_data
    })

    # Step 2: Evaluate to identify missing data
    result = await session.call_tool('evaluate_patient', {
        'session_id': session_id,
        'cpg_id': 'cholesterol'
    })
    eval_result = json.loads(result.content[0].text)

    # Step 3: If needs attestation, get missing data list
    if eval_result['status'] == 'needs_attestation' or \
       eval_result['sufficiency']['needs_attestation'] > 0:

        result = await session.call_tool('get_missing_data', {
            'session_id': session_id
        })
        missing = json.loads(result.content[0].text)

        # Present questions to user (your UI logic here)
        attestations = []
        for item in missing['needs_attestation']:
            # Your UI: ask user the question
            user_answer = await ask_user(item['question'])
            attestations.append({
                'variable_id': item['variable_id'],
                'value': user_answer
            })

        # Step 4: Submit attestations
        await session.call_tool('submit_attestation', {
            'session_id': session_id,
            'attestations': attestations
        })

        # Step 5: Re-evaluate with complete data
        result = await session.call_tool('evaluate_patient', {
            'session_id': session_id,
            'cpg_id': 'cholesterol'
        })
        eval_result = json.loads(result.content[0].text)

    return eval_result
```

### Workflow 4: Clinical Notes Processing

For applications that receive clinical notes/encounter summaries:

```python
from ai.notes_extractor import ClinicalNotesExtractor, ExtractionConfig
from core.cpg import CPG
from core.healthcontext import HealthContext
from core.concord import Concord

def process_clinical_notes(notes_text: str, cpg_id: str = 'cholesterol'):
    """Extract data from clinical notes and evaluate against CPG."""

    # Load CPG
    cpg = CPG.load(f'cpgs/{cpg_id}.yaml')

    # Configure LLM extraction
    config = ExtractionConfig(
        provider='anthropic',
        model='claude-sonnet-4-20250514',
        min_confidence=0.7
    )

    # Extract variables from notes
    extractor = ClinicalNotesExtractor(config)
    records = extractor.extract_variables(notes_text, cpg.variables)

    # Log extraction results
    print(f"Extracted {len(records)} variables from clinical notes:")
    for record in records:
        source = record.value.source[0] if record.value.source else None
        confidence = source.confidence if source else "N/A"
        print(f"  {record.id}: {record.value.value} (confidence: {confidence})")

    # Create health context and evaluate
    health_context = HealthContext(records=records)
    concord = Concord(cpg=cpg, healthcontext=health_context)

    try:
        pipeline = concord.evaluate(ignore_attestations=True)

        return {
            'eligible': pipeline.eligibility.is_eligible if pipeline.eligibility else None,
            'recommendations': [
                {
                    'id': rec.recommendation.id,
                    'title': rec.recommendation.title,
                    'applies': rec.applies,
                    'narrative': rec.narrative
                }
                for rec in (pipeline.recommendations.applied or [])
            ],
            'extracted_variables': [
                {
                    'id': r.id,
                    'value': r.value.value,
                    'confidence': r.value.source[0].confidence if r.value.source else None
                }
                for r in records
            ]
        }
    except Exception as e:
        return {'error': str(e), 'extracted_variables': len(records)}
```

---

## Error Handling

All tools return JSON. On error, the response includes an `error` field:

```json
{
  "error": "Session not found: invalid-session-id"
}
```

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `Session not found` | Invalid session_id | Use a valid session_id from create_health_context |
| `CPG not found` | Invalid cpg_id | Check available CPGs with list_cpgs |
| `No health context for session` | Missing health context | Call create_health_context first |
| `No evaluation completed` | Missing evaluation | Call evaluate_patient first |
| `Value requires a value` | Null value in health_data | Don't include variables with null values |

---

## Server Architecture

```
mcp_server/
├── __init__.py          # Package exports
├── __main__.py          # Entry point (python -m mcp_server)
├── server.py            # Main MCP server, tool handlers
├── state.py             # Session state management, CPG loading
├── fhir_handler.py      # FHIR R4 resource parsing
├── confidence.py        # Confidence score calculation
├── priority.py          # Recommendation priority ranking
├── explanation.py       # Recommendation explanation generation
├── streaming.py         # Async streaming utilities
├── guidelines_handler.py # Mandatory guidelines enforcement
├── care_gaps.py         # Care gap detection
└── instructions_handler.py # LLM instruction scaffolding
```

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `ConcordState` | Manages CPG cache and session state |
| `EvaluationSession` | Stores health context, evaluations, attestations |
| `FHIRHandler` | Parses FHIR Bundle/resources to Records |
| `ConfidenceCalculator` | Computes data quality scores |
| `PriorityRanker` | Ranks recommendations by evidence |
| `ExplanationGenerator` | Builds assessment chains and summaries |
| `CareGapDetector` | Identifies preventive care gaps across CPGs |
| `PROTECTED_TOOLS` | Tools requiring guidelines acknowledgment |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONCORD_LLM_PROVIDER` | `anthropic` | LLM provider for notes extraction |
| `CONCORD_LLM_MODEL` | (provider default) | Specific model to use |
| `CONCORD_LLM_MIN_CONFIDENCE` | `0.7` | Minimum confidence threshold |
| `ANTHROPIC_API_KEY` | - | API key for Anthropic (if using) |
| `OPENAI_API_KEY` | - | API key for OpenAI (if using) |

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run MCP server-specific tests
pytest tests/unit/test_mcp_*.py -v

# Run with coverage
pytest tests/ --cov=mcp_server --cov-report=html
```

### Adding New Tools

1. Define tool schema in `list_tools()` in `server.py`
2. Create async handler function: `async def handle_<tool_name>(args: dict)`
3. Register in `call_tool()` handlers dict
4. Add tests in `tests/unit/test_mcp_server.py`

### Local Development

```bash
# Run server in development mode
python -m mcp_server

# Test with MCP inspector (if available)
npx @modelcontextprotocol/inspector python -m mcp_server
```

---

## Security Considerations

- **Session Isolation**: Each session_id maintains separate state
- **No Persistent Storage**: Sessions are in-memory only
- **API Key Security**: LLM API keys should be set via environment variables
- **Input Validation**: FHIR resources and health data are validated before processing
- **PHI Handling**: No patient data is logged or stored permanently

---

## Troubleshooting

### Server won't start

```bash
# Check Python version (3.10+ required)
python --version

# Verify MCP package is installed
pip show mcp

# Check for import errors
python -c "from mcp_server import serve; print('OK')"
```

### CPG not loading

```bash
# List available CPGs
python -c "from mcp_server.state import ConcordState; print([c['identifier'] for c in ConcordState().get_available_cpgs()])"
```

### FHIR parsing errors

- Ensure resources have valid LOINC/SNOMED codes
- Check that Observation resources include valueQuantity
- Verify Bundle structure follows FHIR R4 spec

---

## License

See main ConcordCore repository for license information.

---

## References

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [USPSTF Recommendations](https://www.uspreventiveservicestaskforce.org/)
- [ACC/AHA Clinical Practice Guidelines](https://www.acc.org/guidelines)