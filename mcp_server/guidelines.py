"""Mandatory guidelines and access control for Concord MCP server v2."""

from __future__ import annotations

PROTECTED_TOOLS = {
    "create_health_context",
    "create_health_context_from_fhir",
    "evaluate_patient",
    "evaluate_all_cpgs",
    "evaluate_multiple_cpgs",
    "submit_attestation",
    "collect_attestation",
    "detect_care_gaps",
}

MANDATORY_GUIDELINES = """
# CONCORD MANDATORY GUIDELINES

You MUST follow these rules when using Concord tools. Failure to comply
may result in incorrect clinical recommendations that could harm patients.

## RULE 1: NEVER FABRICATE PATIENT DATA

You must NEVER fabricate, estimate, assume, or fill in any health data
that the user has not EXPLICITLY provided in the conversation.

FORBIDDEN:
- Adding values the user didn't mention
- Using "typical" or "average" values as substitutes
- Assuming default values for missing fields
- Inferring values from general statements (e.g., "I'm healthy" != normal labs)
- Guessing based on demographics or common patterns

If you need data that wasn't provided, you MUST ask the user for it.

## RULE 2: HANDLE MISSING DATA — USE collect_attestation

When evaluate_patient returns missing_required_variables or needs_attestation_variables:

1. STOP — do not interpret partial results
2. Call collect_attestation with the session_id and cpg_id
3. collect_attestation renders an INTERACTIVE FORM directly in the conversation.
   The user fills it in and clicks Submit — you do NOT need to ask questions yourself.
4. DO NOT create your own UI, picker, or conversational questions for missing data.
   The form handles all data collection automatically.
5. After the form loads, say ONLY: "Please fill in and submit the form above."
   DO NOT list, describe, or enumerate the form fields — the form already shows them.
6. After the user submits the form, call evaluate_patient again with the same
   session_id and cpg_id.

FORBIDDEN after calling collect_attestation:
- Listing the form fields (e.g., "The form asks about: Ethnicity, Diabetes...")
- Describing what each field does or what type of input it expects
- Restating any information that is already visible in the form

NEVER proceed with recommendations based on incomplete data.

## RULE 3: USE EXACT VARIABLE IDs

Variable IDs are CASE-SENSITIVE and must match the CPG definition exactly.
ALWAYS call get_cpg_info FIRST to see the exact variable IDs required.

Examples:
- CORRECT: 'Age'              WRONG: 'age', 'AGE', 'patient_age'
- CORRECT: 'LDL'              WRONG: 'ldl', 'ldl_cholesterol', 'LDL-C'
- CORRECT: 'bloodpressure'    WRONG: 'blood_pressure', 'BP', 'systolic'
- CORRECT: 'diabetesMellitus' WRONG: 'diabetes', 'DM', 'has_diabetes'

## RULE 4: FORMAT VALUES CORRECTLY

GENDER (SNOMED codes):
- Male: "http://snomed.info/sct|248153007"
- Female: "http://snomed.info/sct|248152002"

ETHNICITY (OID codes):
- White: "urn:oid:2.16.840.1.113883.6.238|2106-3"
- Black/African American: "urn:oid:2.16.840.1.113883.6.238|2054-5"
- Asian: "urn:oid:2.16.840.1.113883.6.238|2028-9"
- Hispanic/Latino: "urn:oid:2.16.840.1.113883.6.238|2135-2"

BLOOD PRESSURE: tuple format — (142, 90) for 142/90 mmHg
BOOLEAN: true/false or 1/0
NUMERIC: include units when specified — {"value": 165, "unit": "mg/dL"}

## RULE 5: PATIENT SAFETY IS PARAMOUNT

When in doubt: ASK for clarification, DO NOT guess, EXPLAIN when data is
insufficient, RECOMMEND consulting a healthcare provider.

## RULE 6: VERBATIM QUOTE RECOMMENDATIONS ONLY

You do NOT need to recall or restate the patient's data or assessment results.
Only present each recommendation as a verbatim quote using this exact format:

### Guideline Supported Recommendation:
<recommendation text exactly as returned by Concord>

FORBIDDEN:
- Summarizing, paraphrasing, or rewording any recommendation text
- Combining or merging multiple recommendations into one
- Restating patient data or assessment values alongside recommendations
- Interpreting, reconciling, or explaining clinical logic behind recommendations
- Adding editorial commentary about the recommendations

REQUIRED:
- VERBATIM QUOTE each recommendation exactly as returned by Concord
- Use the heading "### Guideline Supported Recommendation:" before each quote
- Preserve the original wording and order of each recommendation
- If asked about recommendation logic, direct user to their healthcare provider

## ACKNOWLEDGMENT

By calling acknowledge_guidelines, you confirm that you have read and
understood these rules and will follow them strictly.
"""


def check_guidelines_acknowledged(session, tool_name: str) -> dict | None:
    """Return error dict if guidelines not acknowledged for a protected tool, else None."""
    if tool_name not in PROTECTED_TOOLS:
        return None
    if session and session.guidelines_acknowledged:
        return None
    return {
        "error": "GUIDELINES_NOT_ACKNOWLEDGED",
        "message": (
            f"You must call 'acknowledge_guidelines' before using '{tool_name}'. "
            "This is a patient safety requirement."
        ),
        "required_action": {
            "tool": "acknowledge_guidelines",
            "args": {
                "session_id": getattr(session, "session_id", "<your_session_id>"),
            },
        },
    }
