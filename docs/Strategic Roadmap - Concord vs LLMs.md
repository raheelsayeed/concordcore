# Strategic Roadmap: Concord's Competitive Edge vs Frontier LLMs

*Created: 2026-02-06*

## Context

Frontier LLMs (e.g., ChatGPT 5.2, Claude Opus) can now reason through clinical practice guidelines, calculate risk scores like ASCVD, and provide recommendations. In testing, ChatGPT 5.2 correctly calculated a 30.5% 10-year ASCVD risk and provided the correct USPSTF Grade B statin recommendation.

**The question: What is Concord's proprietary edge over these frontier models?**

---

## The Problem with LLM-Only Clinical Reasoning

| Issue | LLM Approach | Concord Approach |
|-------|--------------|------------------|
| **Verifiability** | "Trust me, I calculated ~30.5%" - How do you verify the coefficients used? | Explicit code path, auditable calculation |
| **Reproducibility** | May vary between runs | Same input = same output, always |
| **Regulatory** | Not certifiable for clinical use | Can be validated for FDA/CE compliance |
| **Liability** | Who's responsible for wrong advice? | Clear audit trail, traceable logic |
| **Updates** | Training cutoff - may use outdated guidelines | YAML updated when USPSTF publishes new recs |
| **Customization** | Generic guidelines only | Institution-specific rule modifications |

---

## Concord's Proprietary Edge

### 1. Source of Truth Layer

Position Concord not as a replacement for LLMs, but as the **authoritative clinical logic layer** that LLMs call:

```
User → LLM (natural language interface) → Concord MCP (verified clinical logic) → Response
```

The LLM handles conversation; Concord handles **certified clinical decisions**.

### 2. Audit Trail & Explainability

For healthcare settings, you need to show:
- Exactly which data points were used
- Which assessment expressions evaluated to what
- Which recommendation criteria were satisfied
- Version of the guideline used
- Timestamp of evaluation

LLMs can't provide this. Concord can.

### 3. Multi-Guideline Orchestration

A patient may be eligible for 15+ CPGs simultaneously. Concord can:
- Evaluate all at once
- Identify conflicts between recommendations
- Prioritize by evidence strength
- Show gaps in preventive care

### 4. Institutional Customization

Healthcare systems have local protocols:
- "Our cardiology dept uses 7.5% threshold, not 10%"
- "We require LDL < 100 for diabetics before considering moderate-intensity"
- "Add local formulary constraints"

Concord YAML files can be customized per institution.

### 5. FHIR/EHR Integration

Concord already parses FHIR R4. This means:
- Direct integration with Epic, Cerner, etc.
- No manual data entry
- Real-time evaluation as new labs come in

### 6. Regulatory Pathway

For clinical decision support to be deployed in healthcare:
- FDA Class II medical device clearance (510(k))
- CE marking for EU
- Requires deterministic, validated logic

**LLMs cannot be certified.** Concord can.

---

## Architecture: LLM + Concord

**Don't compete with LLMs on natural language. Use them as the interface layer.**

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│         (ChatGPT, Claude, Custom App, EHR Portal)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONCORD MCP SERVER                       │
│  • Certified clinical logic                                 │
│  • Auditable calculations                                   │
│  • Institution-specific rules                               │
│  • FHIR integration                                         │
│  • Version-controlled CPGs                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    VERIFIED RESPONSE                        │
│  • Recommendation with audit trail                          │
│  • Citation to specific guideline version                   │
│  • Liability-ready documentation                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Roadmap: What to Build Next

### Phase 1: Foundation (Current)
- [x] Core evaluation pipeline
- [x] MCP server for LLM integration
- [x] FHIR R4 parsing
- [x] Missing data detection and user prompting
- [x] ASCVD risk score calculation

### Phase 2: Audit & Compliance
- [ ] **Certification Documentation** - Prepare for FDA 510(k) / CE marking
- [ ] **Audit Log Storage** - Every evaluation stored with full trace
- [ ] **Evaluation Versioning** - Track CPG version, timestamp, input hash

### Phase 3: Enterprise Features
- [ ] **Institutional Config Layer** - Allow per-hospital rule overrides
- [ ] **Conflict Detection** - When multiple CPGs give conflicting advice
- [ ] **Gap Analysis** - "This patient is missing these screenings"

### Phase 4: Outcomes & Analytics
- [ ] **Outcome Tracking** - Link recommendations to patient outcomes
- [ ] **Population Health** - Aggregate analytics across patient populations
- [ ] **Quality Measures** - Track guideline adherence rates

---

## Value Proposition

> "Your LLM can chat, but Concord ensures the clinical logic is certified, auditable, and legally defensible."

**For Healthcare Systems:**
- Reduce liability with traceable recommendations
- Meet regulatory requirements for clinical decision support
- Customize guidelines to institutional protocols

**For LLM Providers:**
- Offer verified clinical tools via MCP
- Avoid liability for medical advice
- Differentiate with healthcare-grade accuracy

**For Patients:**
- Consistent, evidence-based recommendations
- Transparent reasoning they can understand
- Confidence that advice follows current guidelines

---

## Competitive Moat

1. **CPG Library** - Curated, validated YAML definitions for major guidelines
2. **Regulatory Expertise** - FDA/CE pathway knowledge
3. **Healthcare Integrations** - FHIR, HL7, EHR connectors
4. **Audit Infrastructure** - Compliance-ready logging
5. **Institutional Relationships** - Per-hospital customizations

---

## Next Steps

See task list for specific implementation items.
