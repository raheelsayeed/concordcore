# Concord: Unavoidable Technical Advantages Over LLMs

These are fundamental technical limitations of transformer-based LLMs that Concord solves.

---

## 1. DETERMINISTIC EXECUTION (Cryptographically Verifiable)

**LLM Reality:**
- Temperature, top-p sampling, context window position all affect output
- Same prompt can produce different answers
- Model updates change behavior without notice
- Cannot guarantee reproducibility

**Concord Reality:**
```python
# Every evaluation is cryptographically verifiable
{
  "input_hash": "sha256:7f8a9b2c4d...",  # Hash of patient data
  "cpg_version": "1.0.0",
  "result": 30.5,
  "output_hash": "sha256:3e4f5a6b..."   # Hash of complete output
}

# Same input + same CPG version = identical output, provable
```

**Why It Matters:**
- Quality reporting requires reproducibility
- Clinical audits require verifiable calculations
- Research requires deterministic results

---

## 2. COST: 100-1000x CHEAPER AT SCALE

**LLM Cost Model:**
```
GPT-4 Turbo: ~$0.01-0.03 per evaluation (input + output tokens)
Claude Opus: ~$0.015-0.075 per evaluation

10,000 patients × $0.02 = $200 per batch
1 million patients × $0.02 = $20,000 per batch
Daily population health = $600,000/month
```

**Concord Cost Model:**
```
Concord: $0 per evaluation (local computation)

10,000 patients = $0 (runs in seconds)
1 million patients = $0 (runs in minutes)
Daily population health = $0/month (just compute costs)
```

**Real Numbers:**
| Scale | LLM Cost | Concord Cost | Savings |
|-------|----------|--------------|---------|
| 1,000 evals/day | $600/month | ~$0 | 100% |
| 10,000 evals/day | $6,000/month | ~$0 | 100% |
| 100,000 evals/day | $60,000/month | ~$0 | 100% |

**The LLM is still used for conversation - but clinical logic runs locally.**

---

## 3. SPEED: 50-100x FASTER

**LLM Latency:**
```
GPT-4: 2-8 seconds per request
Claude: 1-5 seconds per request
Network latency + inference time + token generation
```

**Concord Latency:**
```
CPG evaluation: 10-50 milliseconds
ASCVD calculation: <5 milliseconds
Full pipeline (eligibility → sufficiency → assessment → recommendation): <100ms
```

**Benchmark:**
```python
# Evaluate 1000 patients
LLM: 1000 × 3 seconds = 50 minutes (sequential)
Concord: 1000 × 50ms = 50 seconds (and can parallelize)
```

**Why It Matters:**
- Real-time clinical decision support needs sub-second response
- Batch processing for population health
- EHR integration requires speed

---

## 4. BATCH & POPULATION HEALTH PROCESSING

**LLM Limitation:**
- Sequential API calls (or expensive parallel calls)
- Rate limits (tokens per minute, requests per minute)
- Cost scales linearly with population size
- Hours to process large populations

**Concord Capability:**
```python
# Evaluate entire patient population in parallel
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=16) as executor:
    results = executor.map(evaluate_patient, all_patients)

# 100,000 patients in minutes, not hours
# Zero API costs
# No rate limits
```

**Use Cases Enabled:**
- Daily gap analysis for entire clinic
- Monthly quality measure computation
- Real-time population health dashboards
- Predictive analytics at scale

---

## 5. NO MODEL DRIFT - STABLE, CONTROLLABLE BEHAVIOR

**LLM Reality:**
- OpenAI/Anthropic update models without notice
- GPT-4 behavior changes between versions
- "Same" model can behave differently over time
- You don't control the model

**Concord Reality:**
```yaml
# CPG version is explicit and controlled
CPG:
  version: "1.0.0"
  last_updated: "2024-08-22"

# You control when logic changes
# Version 1.0.0 behaves identically forever
# Upgrade to 1.1.0 is your decision
```

**Why It Matters:**
- Clinical protocols must be stable
- Changes require review and approval
- Unexpected behavior changes are dangerous

---

## 6. TESTABILITY - CI/CD FOR CLINICAL LOGIC

**LLM Reality:**
- Cannot unit test LLM outputs
- Cannot guarantee behavior after model update
- No regression testing possible
- "Testing" = hoping it still works

**Concord Reality:**
```python
# Unit tests for every CPG expression
def test_ascvd_high_risk():
    result = evaluate(age=55, ldl=145, diabetes=True, smoking=True)
    assert result.risk == 30.5
    assert result.recommendation == "MED_B"

def test_ascvd_threshold():
    result = evaluate(age=55, risk_score=9.9)
    assert result.recommendation is None  # Below threshold

    result = evaluate(age=55, risk_score=10.1)
    assert result.recommendation == "MED_B"  # Above threshold

# Run in CI/CD pipeline
# Every CPG change is tested before deployment
# Regression testing catches errors
```

**Why It Matters:**
- Healthcare requires validated software
- Changes must be tested before deployment
- Errors must be caught before reaching patients

---

## 7. INSTITUTIONAL CONTROL - YOU OWN THE LOGIC

**LLM Reality:**
- Logic lives in OpenAI/Anthropic's model
- You cannot inspect or modify it
- You cannot guarantee what it will do
- Provider can change behavior anytime

**Concord Reality:**
```yaml
# You own the CPG definition
# You can inspect every expression
# You control updates
# You can customize for your institution

recommendations:
  - id: MED_B
    expression: "$ascvd_ten_year_risk_score > 9.9"  # You can read this
    # Change to 7.5 for your cardiology protocol? Your choice.
```

**Why It Matters:**
- Healthcare systems need control
- Institutional protocols differ
- Liability requires ownership

---

## 8. OFFLINE CAPABILITY

**LLM Reality:**
- Requires internet connection
- Requires API availability
- Outages = no clinical decision support
- Latency depends on network

**Concord Reality:**
```bash
# Runs completely offline
# No network dependency for clinical logic
# Works in air-gapped environments
# Disaster recovery capable
```

**Use Cases:**
- Remote clinics with poor connectivity
- Military/disaster medicine
- High-security environments
- Network outage resilience

---

## 9. PARALLEL MULTI-CPG EVALUATION

**LLM Approach:**
```
Evaluate patient against CPG 1: 3 seconds
Evaluate patient against CPG 2: 3 seconds
...
Evaluate patient against CPG 20: 3 seconds
Total: 60 seconds (sequential)
```

**Concord Approach:**
```python
# Parallel evaluation against all CPGs
results = parallel_evaluate(patient, all_20_cpgs)
# Total: <1 second

# Plus conflict detection across all CPGs
conflicts = detect_conflicts(results)
```

---

## 10. SEMANTIC VERSIONING & CHANGE CONTROL

**LLM Reality:**
- Model "GPT-4" changes opaquely
- No changelog for behavior changes
- Cannot pin to specific behavior version
- Cannot diff between versions

**Concord Reality:**
```
CPG Changelog:
v1.0.0 (2024-01-01): Initial release
v1.0.1 (2024-03-15): Fixed threshold typo (9.9 not 9.99)
v1.1.0 (2024-08-22): Added new risk factor per updated guideline
v2.0.0 (2025-01-01): Major revision with new evidence categories

# Git diff shows exactly what changed
# Semantic versioning communicates impact
# Rollback is trivial
```

---

## Summary: The Technical Moat

| Capability | LLM | Concord |
|------------|-----|---------|
| Deterministic output | ❌ Probabilistic | ✅ Guaranteed |
| Cost at scale | $$$$ | ✅ Near zero |
| Latency | 1-5 seconds | ✅ <100ms |
| Batch processing | Rate limited | ✅ Unlimited |
| Model stability | ❌ Drifts | ✅ Controlled |
| Unit testable | ❌ No | ✅ Full CI/CD |
| Institutional control | ❌ Vendor owned | ✅ You own it |
| Offline capable | ❌ No | ✅ Yes |
| Parallel CPGs | Sequential | ✅ Parallel |
| Version control | ❌ Opaque | ✅ Semantic |

---

## The Integration Model

**Use LLMs for what they're good at:**
- Natural language understanding
- Conversational interface
- Patient communication
- General knowledge Q&A

**Use Concord for what it's good at:**
- Deterministic clinical calculations
- High-volume batch processing
- Reproducible, auditable results
- Version-controlled logic
- Cost-efficient evaluation

```
┌─────────────────────────────────────────────────────────────────┐
│  LLM Layer: Conversation & Understanding ($0.02/interaction)   │
├─────────────────────────────────────────────────────────────────┤
│  Concord Layer: Clinical Logic ($0/evaluation)                 │
│    • ASCVD calculation: 5ms                                     │
│    • 20-CPG evaluation: 100ms                                   │
│    • 10,000 patient batch: 30 seconds                           │
│    • Fully deterministic & testable                             │
└─────────────────────────────────────────────────────────────────┘
```

**Bottom Line:** LLMs are expensive, slow, non-deterministic, and uncontrollable for clinical logic. Concord is cheap, fast, deterministic, and fully controlled. Use both where they excel.

---

# How These Features Actually Work

This section explains the implementation details of Concord's key technical advantages in plain language, with diagrams to illustrate the concepts.

---

## Reproducibility Verification: Proving Results Are Consistent

### What Problem Does It Solve?

Imagine you evaluate a patient's cardiovascular risk today and get a recommendation. Six months later, during a clinical audit, someone asks: "How do we know the system gave the same recommendation back then?" With traditional software or LLMs, you can't prove it. With Concord, you can.

### How It Works

Every evaluation creates a "digital fingerprint" of both the inputs (patient data) and outputs (recommendations). This fingerprint is called a **hash** - think of it like a unique serial number that represents the entire evaluation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EVALUATION FINGERPRINTING                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   PATIENT DATA                    HASH FUNCTION                     │
│   ┌─────────────────┐            ┌─────────────┐                   │
│   │ Age: 55         │            │             │                   │
│   │ LDL: 145        │  ───────►  │  SHA-256    │  ───────►  INPUT  │
│   │ Smoker: Yes     │            │  Algorithm  │           HASH    │
│   │ Diabetic: Yes   │            │             │           7f8a9b2c│
│   └─────────────────┘            └─────────────┘                   │
│                                                                     │
│   EVALUATION RESULTS                                                │
│   ┌─────────────────┐            ┌─────────────┐                   │
│   │ Risk: 30.5%     │            │             │                   │
│   │ Eligible: Yes   │  ───────►  │  SHA-256    │  ───────►  OUTPUT │
│   │ Rec: Statin     │            │  Algorithm  │           HASH    │
│   │ Grade: B        │            │             │           3e4f5a6b│
│   └─────────────────┘            └─────────────┘                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Verification Process

When you want to verify a past evaluation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VERIFICATION WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Step 1: Save the Original Evaluation                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Original Evaluation (January 15, 2024)                     │  │
│   │  • Input Hash:  7f8a9b2c4d...                               │  │
│   │  • Output Hash: 3e4f5a6b7c...                               │  │
│   │  • CPG Version: 1.0.0                                       │  │
│   │  • Result: 30.5% risk, Statin recommended                   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   Step 2: Run the Same Evaluation Again (July 20, 2024)            │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Re-evaluation with Same Patient Data                       │  │
│   │  • New Input Hash:  7f8a9b2c4d...  ←── Same!               │  │
│   │  • New Output Hash: 3e4f5a6b7c...  ←── Same!               │  │
│   │  • CPG Version: 1.0.0              ←── Same!               │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   Step 3: Compare Hashes                                            │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  ✅ VERIFIED: All hashes match                              │  │
│   │                                                             │  │
│   │  This proves the evaluation is reproducible:                │  │
│   │  • Same patient data was used (input hash matches)         │  │
│   │  • Same result was produced (output hash matches)          │  │
│   │  • Same guideline version was used (version matches)       │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### What If Something Changed?

The system detects four types of verification results:

| Status | What It Means |
|--------|---------------|
| ✅ VERIFIED | Everything matches - the evaluation is reproducible |
| ⚠️ CPG_VERSION_CHANGED | The guideline was updated since the original evaluation |
| ❌ INPUT_HASH_MISMATCH | Different patient data was provided |
| ❌ MISMATCH | Same inputs produced different outputs (should never happen with Concord) |

### Why This Matters for Healthcare

1. **Clinical Audits**: Prove that a recommendation was generated correctly at the time
2. **Quality Reporting**: Demonstrate consistent application of guidelines
3. **Research**: Verify that study results can be reproduced
4. **Legal Protection**: Document exactly how clinical decisions were made

---

## Batch Processing: Evaluating Thousands of Patients Quickly

### What Problem Does It Solve?

A hospital system might have 100,000 patients. Running a cardiovascular risk assessment on each one using an LLM would take:
- 100,000 patients × 3 seconds each = 83 hours
- 100,000 patients × $0.02 each = $2,000

With Concord's batch processing:
- 100,000 patients × 50ms each = 83 minutes (parallelized: ~5 minutes)
- Cost: $0

### How It Works

The batch processor uses your computer's multiple CPU cores to evaluate many patients simultaneously:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BATCH PROCESSING MODES                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   SEQUENTIAL (One at a time):                                       │
│   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐                            │
│   │ P1  │──►│ P2  │──►│ P3  │──►│ P4  │──►  ...                    │
│   └─────┘   └─────┘   └─────┘   └─────┘                            │
│   Time: 4 × 50ms = 200ms                                           │
│                                                                     │
│   PARALLEL (Multiple at once):                                      │
│   ┌─────┐                                                          │
│   │ P1  │────┐                                                     │
│   └─────┘    │                                                     │
│   ┌─────┐    │                                                     │
│   │ P2  │────┼────►  All complete in ~50ms                         │
│   └─────┘    │                                                     │
│   ┌─────┐    │                                                     │
│   │ P3  │────┤                                                     │
│   └─────┘    │                                                     │
│   ┌─────┐    │                                                     │
│   │ P4  │────┘                                                     │
│   └─────┘                                                          │
│   Time: ~50ms (4 workers)                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BATCH PROCESSING FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   INPUT: List of Patients                                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Patient 1: John, 55, LDL: 145, Smoker                      │  │
│   │  Patient 2: Mary, 62, LDL: 120, Diabetic                    │  │
│   │  Patient 3: Bob, 48, LDL: 180, Healthy                      │  │
│   │  ... (thousands more)                                        │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   PROCESSING: Parallel Workers                                      │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                  │
│   │Worker 1 │ │Worker 2 │ │Worker 3 │ │Worker 4 │                  │
│   │John ✓   │ │Mary ✓   │ │Bob ✓    │ │Sue ✓    │                  │
│   │Tom ✓    │ │Lisa ✓   │ │Jim ✓    │ │Ann ✓    │                  │
│   │...      │ │...      │ │...      │ │...      │                  │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘                  │
│                              │                                      │
│                              ▼                                      │
│   OUTPUT: Aggregated Results                                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  BATCH REPORT                                                │  │
│   │  ─────────────────────────────────────────────────────────  │  │
│   │  Total patients: 10,000                                      │  │
│   │  Successfully processed: 9,850                               │  │
│   │  Failed: 150 (missing data)                                  │  │
│   │  Total time: 2.3 seconds                                     │  │
│   │  Patients per second: 4,348                                  │  │
│   │                                                              │  │
│   │  RECOMMENDATIONS SUMMARY:                                    │  │
│   │  • 3,200 patients need statin therapy                        │  │
│   │  • 1,500 patients have high ASCVD risk (>20%)               │  │
│   │  • 4,850 patients meet diabetes screening criteria          │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Real-World Use Cases

| Use Case | Description |
|----------|-------------|
| **Daily Gap Analysis** | Find all patients due for preventive care |
| **Quality Measures** | Calculate HEDIS/CMS scores for entire population |
| **Risk Stratification** | Identify high-risk patients for care management |
| **Panel Management** | Help providers manage their patient panels |

---

## Parallel Multi-CPG Evaluation: Checking All Guidelines at Once

### What Problem Does It Solve?

A primary care visit might need to check 20 different preventive care guidelines. With an LLM, that's:
- 20 guidelines × 3 seconds = 60 seconds of waiting
- 20 guidelines × $0.02 = $0.40 per visit

With Concord:
- 20 guidelines in parallel = <100 milliseconds
- Cost: $0

### How It Works

Instead of checking guidelines one by one, Concord checks them all simultaneously:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PARALLEL CPG EVALUATION                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   PATIENT DATA                                                      │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Age: 55, Male, LDL: 145, Smoker, Diabetic                  │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│              ┌───────────────┼───────────────┐                     │
│              │               │               │                      │
│              ▼               ▼               ▼                      │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│   │ Statin CPG      │ │ Diabetes CPG    │ │ Hypertension    │      │
│   │                 │ │                 │ │ CPG             │      │
│   │ Risk: 30.5%     │ │ Screen: Yes     │ │ Screen: Yes     │      │
│   │ Rec: Statin     │ │ Rec: A1c test   │ │ Rec: BP check   │      │
│   │ Grade: B        │ │ Grade: B        │ │ Grade: A        │      │
│   └─────────────────┘ └─────────────────┘ └─────────────────┘      │
│              │               │               │                      │
│              └───────────────┼───────────────┘                     │
│                              ▼                                      │
│   COMBINED RESULTS                                                  │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  EVALUATION COMPLETE (2.16 milliseconds)                    │  │
│   │                                                              │  │
│   │  Recommendations:                                            │  │
│   │  1. [Grade B] Start statin therapy - ASCVD risk 30.5%       │  │
│   │  2. [Grade B] Order A1c test - Diabetes screening            │  │
│   │  3. [Grade A] Check blood pressure - Hypertension screening │  │
│   │                                                              │  │
│   │  Conflicts Detected: None                                    │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Conflict Detection

When guidelines might give conflicting advice, Concord detects and reports it:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONFLICT DETECTION EXAMPLE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   CPG 1: Cholesterol Management                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Recommendation: Start high-intensity statin                 │  │
│   │  Reason: LDL > 190 mg/dL                                     │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   CPG 2: Older Adult Care                                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Recommendation: Use moderate-intensity statin               │  │
│   │  Reason: Age > 75, increased side effect risk               │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   ⚠️ CONFLICT DETECTED                                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Both guidelines recommend statins but differ on intensity: │  │
│   │  • Cholesterol CPG: High-intensity                          │  │
│   │  • Older Adult CPG: Moderate-intensity                      │  │
│   │                                                              │  │
│   │  Clinical Decision: Provider review recommended              │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## CI/CD Templates: Testing Guidelines Before Deployment

### What Problem Does It Solve?

Clinical guidelines are critical - a typo could cause harm. With LLMs, you can't test that the output will be correct. With Concord, you can test every guideline before it goes live, just like software developers test their code.

### How It Works

Every time someone changes a guideline, automated tests run to make sure nothing broke:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE FOR CPGs                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   STEP 1: Developer Makes a Change                                  │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  File: cpgs/uspstf_statinuse.yaml                           │  │
│   │  Change: Update risk threshold from 10.0 to 7.5             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   STEP 2: Pre-commit Hooks Run Locally                             │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  ✅ YAML syntax valid                                        │  │
│   │  ✅ Required fields present (identifier, title)             │  │
│   │  ✅ All variable references exist                            │  │
│   │  ✅ No trailing whitespace                                   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   STEP 3: GitHub Actions Run on Push                               │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Job 1: Lint (10 sec)                                        │  │
│   │  ✅ Code style checks passed                                 │  │
│   │                                                              │  │
│   │  Job 2: Unit Tests (30 sec)                                  │  │
│   │  ✅ 166 tests passed                                         │  │
│   │                                                              │  │
│   │  Job 3: Integration Tests (45 sec)                           │  │
│   │  ✅ CPG evaluation tests passed                              │  │
│   │                                                              │  │
│   │  Job 4: Reproducibility Check (20 sec)                       │  │
│   │  ✅ All evaluations are reproducible                         │  │
│   │                                                              │  │
│   │  Job 5: CPG Diff Report (15 sec)                             │  │
│   │  📋 Changes detected in uspstf_statinuse.yaml               │  │
│   │     - Risk threshold: 10.0 → 7.5                            │  │
│   │     - Affected patients: ~15% increase in recommendations   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   STEP 4: Pull Request Review                                       │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Reviewer sees:                                              │  │
│   │  • All tests passing ✅                                      │  │
│   │  • Exactly what changed in the guideline                    │  │
│   │  • Impact analysis (how many patients affected)             │  │
│   │  • Approval required before merge                            │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Testing Pyramid

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TESTING LEVELS                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                         ┌───────────────┐                          │
│                        /  INTEGRATION    \                         │
│                       /   Tests (20)      \                        │
│                      /   Full pipeline     \                       │
│                     /   evaluations         \                      │
│                    ├────────────────────────┤                      │
│                   /      UNIT TESTS          \                     │
│                  /       (140+)               \                    │
│                 /   Individual functions       \                   │
│                /   Expression evaluation        \                  │
│               /   Variable processing            \                 │
│              ├───────────────────────────────────┤                 │
│             /        STATIC VALIDATION            \                │
│            /         (Pre-commit)                  \               │
│           /   YAML syntax                           \              │
│          /   Required fields                         \             │
│         /   Variable reference checks                 \            │
│        └───────────────────────────────────────────────┘           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Matters

| Without CI/CD | With CI/CD |
|---------------|------------|
| Typos reach production | Caught before merge |
| Manual testing only | Automated verification |
| Hope nothing broke | Know nothing broke |
| Changes are scary | Changes are safe |

---

## MCP Server Integration: Connecting AI Assistants to Clinical Logic

### What Problem Does It Solve?

AI assistants (like Claude) are great at conversation but shouldn't make up clinical recommendations. The MCP (Model Context Protocol) server lets AI assistants use Concord for accurate clinical evaluations while handling the conversation naturally.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   USER                                                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  "What's my cardiovascular risk? I'm 55, male, smoker,      │  │
│   │   diabetic, LDL is 145, HDL is 38"                          │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   CLAUDE (AI ASSISTANT)                                             │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  I'll evaluate this using clinical guidelines...             │  │
│   │                                                              │  │
│   │  [Calls MCP Tool: create_health_context]                    │  │
│   │  [Calls MCP Tool: evaluate_patient]                         │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   MCP SERVER (CONCORD)                                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Tools Available:                                            │  │
│   │  • list_cpgs - List available guidelines                    │  │
│   │  • create_health_context - Store patient data               │  │
│   │  • evaluate_patient - Run guideline evaluation              │  │
│   │  • get_evaluation_metadata - Get hashes for verification   │  │
│   │  • verify_reproducibility - Verify past evaluation          │  │
│   │  • evaluate_multiple_cpgs - Check multiple guidelines       │  │
│   │                                                              │  │
│   │  Evaluation Result:                                          │  │
│   │  {                                                           │  │
│   │    "risk_score": 30.5,                                       │  │
│   │    "recommendation": "Statin therapy recommended",          │  │
│   │    "grade": "B",                                             │  │
│   │    "input_hash": "7f8a9b2c...",                             │  │
│   │    "output_hash": "3e4f5a6b..."                             │  │
│   │  }                                                           │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   CLAUDE'S RESPONSE TO USER                                         │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Based on the USPSTF guidelines, your 10-year cardiovascular│  │
│   │  risk is 30.5%. This is considered high risk.               │  │
│   │                                                              │  │
│   │  The guidelines recommend starting statin therapy (Grade B  │  │
│   │  recommendation from USPSTF).                               │  │
│   │                                                              │  │
│   │  Would you like me to explain what this means or discuss    │  │
│   │  this with your doctor?                                     │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Key Insight

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SEPARATION OF CONCERNS                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                     AI ASSISTANT (Claude)                    │  │
│   │                                                              │  │
│   │  Good at:                    Not good at:                    │  │
│   │  • Understanding questions   • Precise calculations          │  │
│   │  • Natural conversation      • Consistent results            │  │
│   │  • Explaining results        • Following exact protocols    │  │
│   │  • Asking for missing data   • Reproducibility              │  │
│   │  • Patient communication     • Audit trails                 │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                     CONCORD (MCP Server)                    │  │
│   │                                                              │  │
│   │  Good at:                    Not good at:                    │  │
│   │  • Precise calculations      • Natural conversation          │  │
│   │  • Consistent results        • Understanding context         │  │
│   │  • Following exact protocols • Explaining in plain language │  │
│   │  • Reproducibility           • Asking follow-up questions   │  │
│   │  • Audit trails              • Adapting to patient needs    │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   TOGETHER: The best of both worlds                                │
│   • Natural conversation WITH accurate clinical logic              │
│   • Patient-friendly explanations WITH reproducible results        │
│   • Flexible interaction WITH deterministic calculations           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Available MCP Tools

| Tool | Purpose |
|------|---------|
| `list_cpgs` | Show available clinical guidelines |
| `get_cpg_details` | Get detailed info about a specific guideline |
| `create_health_context` | Store patient data for evaluation |
| `evaluate_patient` | Run a guideline against patient data |
| `get_recommendations` | Get prioritized recommendations |
| `get_evaluation_metadata` | Get cryptographic hashes for verification |
| `verify_reproducibility` | Verify a past evaluation can be reproduced |
| `evaluate_multiple_cpgs` | Check multiple guidelines in parallel |

---

## Summary: The Complete Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONCORD FEATURE SUMMARY                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   REPRODUCIBILITY                                                   │
│   ├── Every evaluation gets input/output hashes                    │
│   ├── Verify any past evaluation was correct                       │
│   └── Cryptographic proof of consistency                           │
│                                                                     │
│   BATCH PROCESSING                                                  │
│   ├── Evaluate thousands of patients in seconds                    │
│   ├── Parallel processing across CPU cores                         │
│   └── Population health at zero marginal cost                      │
│                                                                     │
│   MULTI-CPG EVALUATION                                              │
│   ├── Check all guidelines simultaneously                          │
│   ├── Detect conflicts between recommendations                     │
│   └── Complete in milliseconds, not minutes                        │
│                                                                     │
│   CI/CD INTEGRATION                                                 │
│   ├── Test every guideline change automatically                    │
│   ├── Pre-commit hooks catch errors locally                        │
│   └── GitHub Actions verify on every push                          │
│                                                                     │
│   MCP SERVER                                                        │
│   ├── Connect AI assistants to accurate clinical logic             │
│   ├── Natural conversation + deterministic calculations            │
│   └── Best of both worlds: AI flexibility + medical accuracy       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**The Bottom Line:** These features work together to provide clinical decision support that is:
- **Accurate** - Based on published guidelines, not AI hallucination
- **Fast** - Milliseconds, not seconds
- **Cheap** - Local computation, no per-evaluation API costs
- **Verifiable** - Cryptographic proof of reproducibility
- **Testable** - Full CI/CD like professional software
- **Scalable** - From one patient to millions

---

## Institutional Configuration Validation Tool

Healthcare institutions often need to customize clinical guidelines for their specific needs - different risk thresholds, local protocols, or formulary constraints. The Institutional Config Validation Tool ensures these customizations are safe, consistent, and properly documented.

### What Problem Does It Solve?

When institutions modify clinical guidelines:
- Typos can change thresholds dangerously (e.g., "7.5" vs "75")
- Conflicting rules can slip through (include AND exclude the same recommendation)
- Expression syntax errors can break evaluation
- Changes can affect more patients than intended

The validation tool catches these issues BEFORE they reach production.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONFIG VALIDATION PIPELINE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   INPUT: Institutional Configuration YAML                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  institution_config:                                         │  │
│   │    institution_id: hospital_abc                              │  │
│   │    threshold_overrides:                                      │  │
│   │      - target_id: MED_B                                      │  │
│   │        parameter: risk_threshold                             │  │
│   │        override_value: 7.5    # Changed from 10.0           │  │
│   │    local_rules:                                              │  │
│   │      - id: cardiology_referral                               │  │
│   │        expression: "$ascvd_risk > 20"                        │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   VALIDATION CHECKS                                                 │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  1. SCHEMA VALIDATION                                        │  │
│   │     ✅ Required fields present (institution_id, target_id)  │  │
│   │     ✅ Correct types (string, number, etc.)                 │  │
│   │     ✅ Valid enum values (include/exclude, assessment/rec)  │  │
│   │                                                              │  │
│   │  2. CONFLICT DETECTION                                       │  │
│   │     ✅ No duplicate overrides for same target               │  │
│   │     ✅ No conflicting filters (include AND exclude)         │  │
│   │     ✅ No circular inheritance                               │  │
│   │                                                              │  │
│   │  3. EXPRESSION VALIDATION                                    │  │
│   │     ✅ Valid syntax (no "and and" or unbalanced parens)     │  │
│   │     ✅ Variable references exist in CPG                     │  │
│   │                                                              │  │
│   │  4. SAFE RANGE CHECKS                                        │  │
│   │     ⚠️ LDL threshold 500 above typical max (300)            │  │
│   │     ⚠️ Negative risk threshold unusual                      │  │
│   │                                                              │  │
│   │  5. CPG COMPATIBILITY                                        │  │
│   │     ✅ Override targets exist in CPG                        │  │
│   │     ✅ Recommendation filters match CPG recommendations     │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   OUTPUT: Validation Report                                         │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  STATUS: VALID (or INVALID)                                  │  │
│   │  Errors: 0                                                   │  │
│   │  Warnings: 2                                                 │  │
│   │                                                              │  │
│   │  INHERITANCE CHAIN:                                          │  │
│   │  └─ ABC Medical Center (ID: hospital_abc)                   │  │
│   │       2 threshold overrides, 1 local rule                   │  │
│   │                                                              │  │
│   │  IMPACT ANALYSIS:                                            │  │
│   │  • Threshold Changes: risk_threshold 10.0 → 7.5             │  │
│   │  • Added Rules: cardiology_referral                          │  │
│   │  • Affected Patients: ~15% more will receive recommendations│  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Types of Validation Checks

| Check Type | Severity | Example Issue |
|------------|----------|---------------|
| Missing required field | ERROR | No target_id on threshold override |
| Duplicate override | ERROR | Two overrides for same target.parameter |
| Conflicting filters | ERROR | Both include AND exclude same recommendation |
| Invalid expression syntax | ERROR | Expression with syntax errors |
| Value outside safe range | WARNING | LDL threshold of 500 (typical max is 300) |
| Undefined variable reference | WARNING | Expression uses $unknown_var |
| Missing audit reason | WARNING | Override without documented reason |

### Inheritance Chain Visualization

Configurations can inherit from parent configs. The validator shows the full chain:

```
Configuration Inheritance Chain
========================================
┌─ Cardiology Department
   ID: cardio_dept
   Threshold overrides: 2
   Local rules: 3
   │
   ▼ inherits from
└─ ABC Medical Center
   ID: hospital_abc
   Threshold overrides: 5
   Local rules: 1
   │
   ▼ inherits from
└─ Health System Default
   ID: system_default
   Threshold overrides: 0
   Local rules: 0
```

### Impact Analysis

The validator analyzes how your configuration changes affect CPG evaluation:

```
IMPACT ANALYSIS
===============
Threshold Changes:
  • MED_B.risk_threshold: 10.0 → 7.5 (more aggressive)
  • highLDL.ldl_threshold: 140 → 100 (stricter target)

Excluded Recommendations:
  • SOME_MED (reason: not on formulary)

Added Local Rules:
  • cardiology_referral: "Consider Cardiology Referral"
  • high_complexity_patient: "High Complexity Patient Flag"

Estimated Impact:
  • ~15% more patients will receive statin recommendations
  • ~5% of patients will trigger cardiology referral
```

### MCP Server Tools

Two tools are available for AI assistants:

| Tool | Purpose |
|------|---------|
| `validate_institution_config` | Validate a config file with full reporting |
| `get_institution_config_impact` | Analyze how config affects a specific CPG |

### Why This Matters

1. **Safety** - Catch dangerous typos before they affect patients
2. **Compliance** - Ensure all changes are documented with reasons
3. **Visibility** - Understand the full impact before deploying changes
4. **Auditability** - Clear record of what changed and why
5. **Control** - Institutions own their customizations, validated before deployment

---

## Benchmarking Suite: Proving the Performance Claims

### What Problem Does It Solve?

When we say Concord is "100-1000x cheaper" and "<100ms", how do we prove it? The benchmarking suite provides hard numbers that can be independently verified.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BENCHMARKING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   BENCHMARK TYPES                                                   │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                                                             │  │
│   │  1. SINGLE CPG EVALUATION                                   │  │
│   │     - Run same evaluation N times                           │  │
│   │     - Measure: avg, min, max, p95, p99                     │  │
│   │     - Track memory usage                                    │  │
│   │     - Calculate evaluations/second                          │  │
│   │                                                             │  │
│   │  2. BATCH PROCESSING                                        │  │
│   │     - Evaluate 10, 100, 1000+ patients                     │  │
│   │     - Compare sequential vs parallel                        │  │
│   │     - Measure throughput (patients/second)                  │  │
│   │                                                             │  │
│   │  3. MULTI-CPG EVALUATION                                    │  │
│   │     - Evaluate 5, 10, 20 CPGs simultaneously               │  │
│   │     - Compare parallel vs sequential                        │  │
│   │     - Measure CPGs/second                                   │  │
│   │                                                             │  │
│   │  4. LLM COST COMPARISON                                     │  │
│   │     - Calculate Concord time/cost                           │  │
│   │     - Estimate LLM time/cost                                │  │
│   │     - Show speedup factor and savings                       │  │
│   │                                                             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│   SAMPLE OUTPUT                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  CONCORD BENCHMARK REPORT                                    │  │
│   │  ════════════════════════════════════════════════════════   │  │
│   │                                                              │  │
│   │  SINGLE CPG EVALUATION                                       │  │
│   │  CPG                     Avg (ms)   P95 (ms)   Evals/sec    │  │
│   │  ──────────────────────────────────────────────────────────  │  │
│   │  cholesterol             3.45       5.21       290          │  │
│   │  uspstf_statinuse        4.12       6.33       243          │  │
│   │                                                              │  │
│   │  BATCH PROCESSING                                            │  │
│   │  Patients   Mode          Total (ms)   Pat/sec              │  │
│   │  ──────────────────────────────────────────────────────────  │  │
│   │  100        sequential    412          243                   │  │
│   │  100        thread_pool   198          505                   │  │
│   │  1000       thread_pool   1,845        542                   │  │
│   │                                                              │  │
│   │  COST COMPARISON                                             │  │
│   │  Scenario            Concord      LLM Est.     Savings      │  │
│   │  ──────────────────────────────────────────────────────────  │  │
│   │  100 evals/day       $0.00        $2.00        100%         │  │
│   │  10,000 evals/day    $0.00        $200.00      100%         │  │
│   │                                                              │  │
│   │  KEY METRICS                                                 │  │
│   │  Average evaluation time: 3.78ms (<100ms target: PASS)      │  │
│   │  Max batch throughput: 542 patients/second                  │  │
│   │  ════════════════════════════════════════════════════════   │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Running Benchmarks

```bash
# Quick benchmark
python -m core.benchmarks --quick

# Full benchmark with output
python -m core.benchmarks --iterations 100 -o benchmark_report.json
```

---

## CPG Changelog Generation: Tracking What Changed

### What Problem Does It Solve?

When a clinical guideline is updated, stakeholders need to know:
- What exactly changed?
- Is this a breaking change?
- Will it affect existing patients?
- Do we need to notify anyone?

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CPG CHANGELOG GENERATION                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   INPUTS                                                            │
│   ┌──────────────────────┐    ┌──────────────────────┐             │
│   │  OLD VERSION         │    │  NEW VERSION         │             │
│   │  cholesterol v1.0.0  │    │  cholesterol v1.1.0  │             │
│   └──────────────────────┘    └──────────────────────┘             │
│              │                           │                          │
│              └───────────┬───────────────┘                          │
│                          ▼                                          │
│   DIFF ANALYSIS                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                                                             │  │
│   │  METADATA CHANGES:                                          │  │
│   │  ~ version: "1.0.0" → "1.1.0"                              │  │
│   │  ~ last_updated: "2024-01-01" → "2024-06-15"              │  │
│   │                                                             │  │
│   │  VARIABLE CHANGES:                                          │  │
│   │  + high_risk_age (assessment) - ADDED                       │  │
│   │  ~ MED_B.expression - MODIFIED ⚠️ BREAKING                  │  │
│   │    "$risk > 10" → "$risk > 7.5"                            │  │
│   │  - legacy_threshold (variable) - REMOVED ⚠️ BREAKING        │  │
│   │                                                             │  │
│   │  SEVERITY ANALYSIS:                                         │  │
│   │  • Breaking changes: 2                                      │  │
│   │  • Significant changes: 1                                   │  │
│   │  • Minor changes: 1                                         │  │
│   │                                                             │  │
│   │  RECOMMENDED VERSION BUMP: MAJOR (due to breaking changes) │  │
│   │                                                             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   CHANGELOG OUTPUT (Markdown)                                       │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  ## [1.1.0] - 2024-06-15                                    │  │
│   │                                                              │  │
│   │  ### ⚠️ Breaking Changes                                    │  │
│   │  - **MED_B** (recommendation): expression changed           │  │
│   │    - `$risk > 10` → `$risk > 7.5`                          │  │
│   │  - **legacy_threshold** (variable): removed                 │  │
│   │                                                              │  │
│   │  ### Added                                                   │  │
│   │  - **high_risk_age** (assessment)                           │  │
│   │                                                              │  │
│   │  ### Changed                                                 │  │
│   │  - Risk threshold lowered from 10% to 7.5%                  │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Expression Diff Analysis

The tool also provides detailed analysis of expression changes:

```
EXPRESSION DIFF ANALYSIS
========================
Old: $has_diabetes == True or $htn == True
New: $has_diabetes == True or $htn == True or $Age > 55

Variables:
  Added: Age
  Removed: (none)
  Unchanged: has_diabetes, htn

Potential Impact:
  - New variable required ($Age)
  - Logic expanded (OR condition added)
  - More patients may qualify
```

---

## Multi-CPG Demo Application

### What It Is

A web-based demonstration application that shows Concord's multi-CPG evaluation capabilities in action.

### Features

1. **Patient Data Input** - Enter patient demographics and clinical values
2. **CPG Selection** - Choose multiple CPGs to evaluate
3. **Parallel Evaluation** - See all CPGs evaluated in milliseconds
4. **Conflict Detection** - View any conflicts between recommendations
5. **LLM Comparison** - Real-time comparison with estimated LLM costs/time
6. **Benchmarking** - Run performance benchmarks directly in the UI

### Running the Demo

```bash
# Start the server
cd concordcore
uvicorn app.server:app --reload --port 8080

# Open in browser
open http://localhost:8080
```

### Screenshot Description

```
┌─────────────────────────────────────────────────────────────────────┐
│  Concord Multi-CPG Demo                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────────────────────────────┐  │
│  │ PATIENT DATA    │  │ RESULTS                                 │  │
│  │                 │  │                                         │  │
│  │ Age: [55    ]   │  │  ┌────────┐ ┌────────┐ ┌────────┐     │  │
│  │ LDL: [145   ]   │  │  │ 2.3ms  │ │ 3 CPGs │ │ 5 Recs │     │  │
│  │ HDL: [38    ]   │  │  └────────┘ └────────┘ └────────┘     │  │
│  │ SBP: [142   ]   │  │                                         │  │
│  │                 │  │  Mode: Parallel  Speedup: 1300x faster │  │
│  │ [x] Diabetes    │  │                                         │  │
│  │ [x] Hypertension│  │  RECOMMENDATIONS                        │  │
│  │ [x] Smoker      │  │  ┌─────────────────────────────────┐   │  │
│  │                 │  │  │ Rx │ Initiate statin therapy    │   │  │
│  ├─────────────────┤  │  │    │ (cholesterol)              │   │  │
│  │ SELECT CPGs     │  │  ├─────────────────────────────────┤   │  │
│  │                 │  │  │ Rx │ ASCVD risk counseling      │   │  │
│  │ [x] cholesterol │  │  │    │ (uspstf_statinuse)         │   │  │
│  │ [x] statinuse   │  │  └─────────────────────────────────┘   │  │
│  │ [ ] diabetes    │  │                                         │  │
│  │ [ ] hypertension│  │  LLM COMPARISON                         │  │
│  │                 │  │  ┌─────────────────────────────────┐   │  │
│  │ [EVALUATE]      │  │  │ Metric     Concord   LLM Est.  │   │  │
│  └─────────────────┘  │  │ Time       2.3ms     3000ms    │   │  │
│                       │  │ Cost       $0.00     $0.04     │   │  │
│                       │  └─────────────────────────────────┘   │  │
│                       └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```
