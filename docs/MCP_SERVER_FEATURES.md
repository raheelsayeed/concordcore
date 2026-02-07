# ConcordCore MCP Server Features

This document outlines the current MCP server capabilities and proposed future features.

---

## Current Features (18 Tools)

### CPG Discovery

| Tool | Description |
|------|-------------|
| `list_cpgs` | List all available Clinical Practice Guidelines with metadata (variable count, assessments, recommendations) |
| `get_cpg_info` | Get detailed information about a specific CPG including variables, eligibility criteria, assessments, and recommendations |

### Health Context Creation

| Tool | Description |
|------|-------------|
| `create_health_context` | Create patient health context from variable/value pairs with strict rules against fabricating data |
| `create_health_context_from_fhir` | Create health context from FHIR R4 resources (Bundle or array). Supports Observation, Condition, MedicationRequest, and Procedure resources |

### Evaluation

| Tool | Description |
|------|-------------|
| `evaluate_patient` | Evaluate a patient against a specific CPG with missing data detection and reporting |
| `evaluate_all_cpgs` | Evaluate patient against ALL available CPGs with streaming support |
| `evaluate_multiple_cpgs` | Evaluate patient against multiple specific CPGs in parallel with conflict detection |

### Recommendations

| Tool | Description |
|------|-------------|
| `get_recommendations` | Retrieve recommendations from a completed evaluation |
| `get_prioritized_recommendations` | Get recommendations ranked by evidence strength (Class of Recommendation, Level of Evidence, USPSTF Grade) |
| `explain_recommendation` | Generate deep explanations with assessment chains, evidence citations, and persona-appropriate summaries (patient/provider) |

### Data Quality

| Tool | Description |
|------|-------------|
| `get_confidence_scores` | Calculate confidence scores based on data completeness, freshness, validation status, and attestation burden |
| `get_missing_data` | Identify health data missing and needed for CPG evaluation |
| `submit_attestation` | Submit patient-attested health data for missing variables |

### Reproducibility & Verification

| Tool | Description |
|------|-------------|
| `get_evaluation_metadata` | Get cryptographic metadata (input hash, output hash, CPG version, timestamp) for reproducibility verification |
| `verify_reproducibility` | Verify that a previous evaluation is reproducible by re-running and comparing hashes |

### Institutional Configuration

| Tool | Description |
|------|-------------|
| `validate_institution_config` | Validate institutional configuration files with schema checking, conflict detection, and impact analysis |
| `get_institution_config_impact` | Analyze how institutional configuration would impact CPG evaluation |

### LLM Instructions

| Tool | Description |
|------|-------------|
| `get_llm_instructions` | Get provider-specific LLM instructions optimized for Claude, OpenAI, or Gemini |
| `build_optimized_prompt` | Build prompts optimized for specific LLM providers with system prompts and few-shot examples |

---

## Current Resources

| Resource URI | Description |
|--------------|-------------|
| `concord://guidelines` | Critical usage guidelines - enforces data integrity rules (never fabricate patient data) |
| `cpg://[identifier]` | Individual CPG resources with metadata for each available guideline |

---

## Current Prompts

| Prompt | Description |
|--------|-------------|
| `concord_guidelines` | Critical rules for using Concord tools (no data fabrication) |
| `health_assessment` | Comprehensive health assessment workflow template |
| `explain_all_recommendations` | Template for explaining all applicable recommendations |

---

## Proposed Features

### 1. Temporal/Trend Analysis

| Tool | Description | Priority |
|------|-------------|----------|
| `get_value_trends` | Analyze trends over time (LDL trajectory, BP patterns) | High |
| `predict_trajectory` | Project future values based on trends | Medium |
| `compare_visits` | Compare health data between visits | Medium |
| `get_timeline` | Chronological view of patient data and evaluations | Low |

### 2. Care Gap Detection

| Tool | Description | Priority |
|------|-------------|----------|
| `detect_care_gaps` | Find missing screenings, overdue tests | High |
| `get_preventive_services_due` | List age/risk-appropriate preventive care | High |
| `suggest_next_actions` | Prioritized list of clinical actions | Medium |
| `get_quality_measures` | HEDIS/CMS quality measure compliance | Medium |

### 3. Medication Intelligence

| Tool | Description | Priority |
|------|-------------|----------|
| `check_drug_interactions` | Interactions between current/recommended medications | High |
| `check_contraindications` | Patient-specific contraindications | High |
| `suggest_alternatives` | Alternative medications when primary contraindicated | Medium |
| `get_medication_adjustments` | Dosing adjustments based on labs/conditions | Medium |

### 4. Risk Calculators

| Tool | Description | Priority |
|------|-------------|----------|
| `calculate_risk_score` | Named risk calculators (ASCVD, CHA₂DS₂-VASc, Wells, etc.) | High |
| `list_risk_calculators` | Available calculators for patient's conditions | Medium |
| `compare_risk_scenarios` | "What-if" risk with/without intervention | Medium |
| `get_risk_factors` | Modifiable vs non-modifiable risk breakdown | Low |

### 5. Goal Setting & Progress

| Tool | Description | Priority |
|------|-------------|----------|
| `set_patient_goals` | Define therapeutic targets (LDL <70, A1c <7) | Medium |
| `get_goal_progress` | Current progress toward goals | Medium |
| `estimate_time_to_goal` | Based on current trajectory | Low |
| `celebrate_achievements` | Patient-friendly progress acknowledgments | Low |

### 6. Patient Communication

| Tool | Description | Priority |
|------|-------------|----------|
| `generate_patient_summary` | Plain-language health summary | High |
| `generate_after_visit_summary` | Post-visit instructions | Medium |
| `create_shared_decision_aid` | Pros/cons for treatment decisions | Medium |
| `translate_clinical_terms` | Medical jargon to plain language | Medium |
| `get_educational_resources` | Relevant patient education materials | Low |

### 7. Provider Decision Support

| Tool | Description | Priority |
|------|-------------|----------|
| `get_clinical_pearls` | Key clinical insights for the case | Medium |
| `suggest_differential` | Conditions to consider | Medium |
| `get_evidence_summary` | Quick evidence summary for a recommendation | High |
| `compare_guidelines` | When guidelines conflict, show differences | High |
| `get_specialty_referrals` | When to refer and to whom | Low |

### 8. Population Health

| Tool | Description | Priority |
|------|-------------|----------|
| `get_cohort_statistics` | Aggregate stats for patient population | Medium |
| `identify_high_risk_patients` | Panel management queries | High |
| `get_population_gaps` | Care gaps across patient panel | Medium |
| `benchmark_performance` | Compare to regional/national benchmarks | Low |

### 9. FHIR Integration Enhancements

| Tool | Description | Priority |
|------|-------------|----------|
| `fetch_from_fhir_server` | Pull patient data from FHIR endpoint | High |
| `write_care_plan` | Generate FHIR CarePlan resource | Medium |
| `create_order_suggestion` | FHIR ServiceRequest for recommended tests | Medium |
| `generate_cds_hooks_card` | CDS Hooks-compatible response | High |

### 10. Audit & Compliance

| Tool | Description | Priority |
|------|-------------|----------|
| `get_audit_log` | Evaluation history for a session | Medium |
| `explain_deviation` | Why a guideline wasn't followed | Medium |
| `generate_compliance_report` | Guideline adherence report | Low |
| `get_regulatory_requirements` | Applicable regulatory considerations | Low |

### 11. Workflow Integration

| Tool | Description | Priority |
|------|-------------|----------|
| `get_order_sets` | Pre-built order sets for recommendations | Medium |
| `create_reminder` | Schedule follow-up reminders | Low |
| `assign_task` | Create tasks for care team members | Low |
| `update_problem_list` | Suggest problem list updates | Medium |

### 12. Cost/Value Considerations

| Tool | Description | Priority |
|------|-------------|----------|
| `estimate_intervention_cost` | Cost estimates for recommendations | Low |
| `get_value_based_options` | Cost-effective alternatives | Low |
| `check_coverage` | Insurance coverage considerations | Low |
| `calculate_qaly_impact` | Quality-adjusted life year estimates | Low |

### 13. Multi-Patient/Batch Operations

| Tool | Description | Priority |
|------|-------------|----------|
| `batch_evaluate` | Evaluate multiple patients at once | Medium |
| `schedule_batch_job` | Schedule recurring evaluations | Low |
| `get_batch_results` | Retrieve batch evaluation results | Medium |

### 14. Guideline Authoring (for CPG developers)

| Tool | Description | Priority |
|------|-------------|----------|
| `validate_cpg_yaml` | Validate CPG definition syntax | High |
| `test_cpg_with_cases` | Run CPG against test cases | High |
| `generate_cpg_documentation` | Auto-generate CPG docs | Medium |
| `compare_cpg_versions` | Diff between CPG versions | Low |

---

## Implementation Priority Matrix

### High Value / Lower Complexity (Recommended First)

1. **`calculate_risk_score`** - Wrap existing ASCVD calculator, add more standard calculators
2. **`detect_care_gaps`** - High clinical utility, builds on existing evaluation
3. **`generate_patient_summary`** - Great for patient engagement, leverages existing narratives
4. **`check_drug_interactions`** - Safety critical, can integrate external databases
5. **`validate_cpg_yaml`** - Useful for CPG authors, validates existing loader

### High Value / Higher Complexity

1. **`get_value_trends`** - Requires temporal data modeling
2. **`fetch_from_fhir_server`** - Requires authentication/connectivity handling
3. **`compare_guidelines`** - Conflict resolution logic is complex
4. **`generate_cds_hooks_card`** - Requires CDS Hooks spec compliance

### Quick Wins

1. **`list_risk_calculators`** - Simple enumeration
2. **`get_evidence_summary`** - Extract from existing recommendation data
3. **`translate_clinical_terms`** - Leverage existing narrative system

---

## Architecture Considerations

### For New Tools

- Follow existing patterns in `mcp_server/server.py`
- Create dedicated handler modules for complex features (like `confidence.py`, `priority.py`)
- Use frozen dataclasses for return types
- Include `_ai_instructions` for guiding LLM behavior
- Add corresponding resources/prompts where appropriate

### Data Requirements

| Feature Category | Data Needs |
|------------------|------------|
| Temporal Analysis | Historical values with timestamps |
| Care Gaps | Age, sex, condition history, procedure dates |
| Drug Interactions | Current medications, allergies |
| Risk Calculators | Calculator-specific variables |
| Population Health | Multi-patient dataset access |

### External Integrations

| Feature | External Dependency |
|---------|---------------------|
| Drug Interactions | RxNorm, DrugBank, or similar |
| FHIR Server | OAuth2, SMART on FHIR |
| CDS Hooks | CDS Hooks specification compliance |
| Cost Estimation | Pricing databases, formularies |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-02 | Initial feature inventory and roadmap |
