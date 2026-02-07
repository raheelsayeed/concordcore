# Why LLMs Cannot Replace Concord: The Unavoidable Clinical Arguments

## The Core Problem

LLMs can *sound* clinically competent. They can recite guidelines, discuss risk factors, and generate plausible recommendations.

**But they have fundamental limitations that make them unsuitable for clinical decision support without a verified computation layer.**

---

## The 6 Unavoidable Arguments

### 1. LLMs HALLUCINATE. CONCORD CANNOT.

**The Problem:**
LLMs fabricate medical facts. They invent drug interactions that don't exist. They misremember thresholds. They cite studies that were never published.

**Real Examples:**
- LLM says "ASCVD risk threshold is 7.5%" (it's 10% for Grade B)
- LLM invents a drug interaction between metformin and lisinopril (doesn't exist)
- LLM cites "Smith et al. 2019" for a guideline published in 2022

**Why It Happens:**
LLMs are statistical pattern matchers. They generate text that *looks* correct based on training data. They have no ground truth.

**Concord's Solution:**
```yaml
# Ground truth in validated YAML
recommendations:
  - id: MED_B
    expression: "$ascvd_ten_year_risk_score > 9.9"  # Exact threshold
    class_of_recommendation: B
    citation: "USPSTF 2022, JAMA. doi:10.1001/jama.2022.13044"
```

Concord evaluates against **validated CPG definitions**. It cannot hallucinate because it doesn't generate - it computes.

---

### 2. LLMs CAN'T SHOW THEIR WORK. CONCORD SHOWS EVERYTHING.

**The Problem:**
When an LLM says "Your ASCVD risk is approximately 30%", you cannot verify:
- What formula was used?
- What coefficients were applied?
- What intermediate values were calculated?
- Is this the published Pooled Cohort Equations or an approximation?

**Why It Matters:**
Clinical trust requires transparency. Shared decision-making requires explainability. Liability requires documentation.

**Concord's Solution:**
```
## How We Calculated Your ASCVD 10-Year Risk Score

**Result: 30.5%**

Step-by-step calculation:

1. Calculate natural log of age
   Formula: ln(age)
   Input: age=55
   Result: 4.0073

2. Calculate natural log of total cholesterol
   Formula: ln(total_cholesterol)
   Input: total_cholesterol=220
   Result: 5.3936

3. Apply White Male coefficients:
   - ln_age coefficient: 12.344
   - ln_total_chol coefficient: 11.853
   - ln_hdl coefficient: -7.99
   ...

4. Final calculation:
   Formula: 1 - S₀^exp(coefficient_sum - mean)
   Result: 30.5%

Source: 2013 ACC/AHA Guideline, Goff et al. Circulation 2014
```

**Every coefficient. Every intermediate value. Every step. Verifiable.**

---

### 3. LLMs CAN'T DO COUNTER-FACTUALS. CONCORD CAN.

**The Problem:**
Patient asks: *"What if I quit smoking? How much would my risk go down?"*

LLM response: *"Quitting smoking would significantly reduce your cardiovascular risk, possibly by 20-30% over time..."*

This is vague, unquantified, and potentially wrong.

**Why It Matters:**
Counter-factual analysis is essential for:
- Motivating behavior change ("Quitting smoking reduces your risk from 30.5% to 25.0%")
- Shared decision-making ("If we add a statin, your risk drops from 15% to 8%")
- Treatment planning ("Which intervention has the biggest impact?")

**Concord's Solution:**
```python
# Exact counter-factual calculation
result = engine.run_counterfactual(
    base_context={'is_smoker': True, 'ldl': 145, ...},
    variable_id='is_smoker',
    hypothetical_value=False,
    evaluator=ascvd_calculator
)

# Result:
{
  "original_value": True (smoking),
  "hypothetical_value": False (quit),
  "original_result": "30.5%",
  "hypothetical_result": "25.0%",
  "difference": "-5.5 percentage points",
  "clinical_significance": "Significant clinical impact"
}
```

**Concord re-runs the exact calculation with modified inputs. Not a guess.**

---

### 4. LLMs HAVE STALE KNOWLEDGE. CONCORD IS ALWAYS CURRENT.

**The Problem:**
LLMs have training cutoffs. GPT-4 was trained on data up to April 2023. Claude's knowledge has a similar cutoff.

**What This Means:**
- USPSTF updated statin guidelines in August 2024 → LLM doesn't know
- New drug interaction discovered in 2024 → LLM doesn't know
- Threshold changed based on new evidence → LLM uses old threshold

**Real Risk:**
A patient evaluated by an LLM in 2025 might receive a recommendation based on 2022 guidelines, missing 2+ years of updates.

**Concord's Solution:**
```yaml
# CPG YAML is updated when guidelines change
CPG:
  identifier: uspstfStatinUse
  version: "1.0.0"
  last_updated: "2024-08-22"  # Updated immediately
  source_url: https://jamanetwork.com/journals/jama/fullarticle/2795193
```

Concord provides **proof of currency**:
```json
{
  "cpg_id": "uspstfStatinUse",
  "cpg_version": "1.0.0",
  "last_updated": "2024-08-22",
  "verified_at": "2025-02-06T10:30:00Z",
  "is_current": true,
  "currency_statement": "This evaluation uses the current published version."
}
```

**When guidelines update, Concord updates. No retraining required.**

---

### 5. LLMs CAN'T TRACE EVIDENCE CHAINS. CONCORD CAN.

**The Problem:**
When an LLM recommends a statin, can it show:
- Exactly which patient data points triggered the recommendation?
- Which assessments were evaluated?
- Which expression was satisfied?
- What's the citation for this logic?

LLMs can *rationalize* their recommendations, but they can't *trace* them.

**Why It Matters:**
- Clinical accountability: "Why did we recommend this?"
- Quality improvement: "What's driving our statin prescribing?"
- Patient education: "Here's exactly why this applies to you"

**Concord's Solution:**
```
Evidence Chain for: Start statin therapy (Grade B)
============================================================

[Level 0: RAW DATA]
  Age: 55
  Gender: Male (SNOMED: 248153007)
  LDL: 145 mg/dL
  Total Cholesterol: 220 mg/dL
  Systolic BP: 142 mmHg
  Diabetes: Yes
  Smoking: Yes

[Level 1: ASSESSMENTS]
  ascvd_ten_year_risk_score: 30.5%
    Formula: Pooled Cohort Equations (White Male)
    Uses: Age, Gender, LDL, HDL, BP, Diabetes, Smoking

  risk_factors: True
    Formula: $has_diabetes OR $has_dyslipidemia OR $htn OR $is_smoker
    Uses: diabetesMellitus, has_dyslipidemia, htn, is_smoker

[Level 2: RECOMMENDATION]
  MED_B: True (Recommend statin)
    Formula: $ascvd_ten_year_risk_score > 9.9 AND $risk_factors
    Citation: USPSTF 2022, Grade B

============================================================
Source: uspstfStatinUse v1.0.0
```

**Complete traceability from raw data to recommendation.**

---

### 6. LLMs CAN'T ENFORCE EVIDENCE HIERARCHY. CONCORD CAN.

**The Problem:**
LLMs treat all information equally. A Reddit post about statins and a Cochrane systematic review get similar weight in training.

When generating recommendations, LLMs don't systematically apply:
- Class of Recommendation (I, IIa, IIb, III)
- Level of Evidence (A, B, C)
- USPSTF Grades (A, B, C, D, I)

**Why It Matters:**
Not all recommendations are equal:
- Class I, Level A = "Do this, strong evidence"
- Class IIb, Level C = "Might consider, weak evidence"

Clinical decision-making requires understanding this hierarchy.

**Concord's Solution:**
```yaml
recommendations:
  - id: MED_B
    title: "Statin for patients with 10-year risk ≥10%"
    class_of_recommendation: B  # USPSTF Grade
    level_of_evidence: moderate
    expression: "$ascvd_ten_year_risk_score > 9.9"

  - id: MED_C
    title: "Consider statin for 7.5-10% risk"
    class_of_recommendation: C  # Weaker recommendation
    level_of_evidence: low
    expression: "$ascvd_ten_year_risk_score > 7.4 and $ascvd_ten_year_risk_score < 10"
```

**Concord explicitly encodes and enforces evidence hierarchy.**

---

## Summary: What LLMs Cannot Do

| Capability | LLM | Concord |
|------------|-----|---------|
| Guarantee no hallucinations | ❌ | ✅ |
| Show exact calculation steps | ❌ | ✅ |
| Run precise counter-factuals | ❌ | ✅ |
| Prove guideline currency | ❌ | ✅ |
| Trace evidence chains | ❌ | ✅ |
| Enforce evidence hierarchy | ❌ | ✅ |

---

## The Unavoidable Conclusion

LLMs are excellent at:
- Natural language understanding
- Conversational interfaces
- Explaining concepts to patients
- General medical knowledge

LLMs are fundamentally incapable of:
- Guaranteeing clinical accuracy
- Providing verifiable calculations
- Updating instantly when guidelines change
- Tracing decisions to evidence

**Concord provides what LLMs cannot. Together, they create clinical AI that is both conversational AND trustworthy.**

---

## The Integration Model

```
┌────────────────────────────────────────────────────────────┐
│                       PATIENT                               │
│            "What's my heart disease risk?"                  │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                         LLM                                 │
│  • Understands the question                                │
│  • Gathers patient context conversationally                │
│  • Explains results in patient-friendly terms              │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                     CONCORD MCP                            │
│  • Runs exact ASCVD calculation (no hallucination)         │
│  • Uses current guideline (2024, not 2022)                 │
│  • Shows all coefficients and steps                        │
│  • Traces recommendation to evidence                       │
│  • Computes counter-factuals precisely                     │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                    VERIFIED RESULT                          │
│  "Your 10-year risk is 30.5% (USPSTF 2024, Grade B)        │
│   If you quit smoking, it drops to 25.0%                   │
│   Recommendation: Start moderate-intensity statin"         │
└────────────────────────────────────────────────────────────┘
```

**LLMs provide the interface. Concord provides the truth.**
