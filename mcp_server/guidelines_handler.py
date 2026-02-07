#!/usr/bin/env python3
"""Mandatory guidelines acknowledgment for Concord MCP server.

This module enforces that LLMs read and acknowledge critical guidelines
before using tools that handle patient health data.

RATIONALE:
LLMs may skip reading instructions and fabricate health data, which is
dangerous for clinical decision support. This module ensures:
1. Guidelines are explicitly acknowledged before data tools are used
2. Full instructions are delivered when acknowledged
3. Critical tools are blocked until acknowledgment
"""

import json
import logging
from datetime import datetime
from typing import Any

from mcp.types import Tool, TextContent

from .state import ConcordState, EvaluationSession

log = logging.getLogger(__name__)


# Tools that require guidelines acknowledgment before use
PROTECTED_TOOLS = {
    "create_health_context",
    "create_health_context_from_fhir",
    "evaluate_patient",
    "evaluate_all_cpgs",
    "evaluate_multiple_cpgs",
    "submit_attestation",
    "detect_care_gaps",
}

# Full guidelines text that MUST be read
MANDATORY_GUIDELINES = """
# CONCORD MANDATORY GUIDELINES

You MUST follow these rules when using Concord tools. Failure to comply
may result in incorrect clinical recommendations that could harm patients.

## RULE 1: NEVER FABRICATE PATIENT DATA

You must NEVER fabricate, estimate, assume, or fill in any health data
that the user has not EXPLICITLY provided in the conversation.

FORBIDDEN ACTIONS:
- Adding values the user didn't mention
- Using "typical" or "average" values as substitutes
- Assuming default values for missing fields
- Inferring values from general statements (e.g., "I'm healthy" ≠ normal labs)
- Guessing based on demographics or common patterns

REQUIRED ACTION:
If you need data that wasn't provided, you MUST ask the user for it.

## RULE 2: HANDLE MISSING DATA CORRECTLY

When evaluate_patient returns missing_required_variables or needs_attestation_variables:

1. STOP - Do not interpret partial results
2. PRESENT the missing variables list to the user clearly
3. EXPLAIN what each variable means in plain language
4. ASK the user to provide each missing value
5. WAIT for user response before proceeding
6. Call create_health_context again with the new data
7. Re-run evaluate_patient

NEVER proceed with recommendations based on incomplete data.

## RULE 3: USE EXACT VARIABLE IDs

Variable IDs are CASE-SENSITIVE and must match the CPG definition exactly.

ALWAYS call get_cpg_info FIRST to see the exact variable IDs required.

Examples of correct vs incorrect:
- CORRECT: 'Age'           WRONG: 'age', 'AGE', 'patient_age'
- CORRECT: 'LDL'           WRONG: 'ldl', 'ldl_cholesterol', 'LDL-C'
- CORRECT: 'bloodpressure' WRONG: 'blood_pressure', 'BP', 'systolic'
- CORRECT: 'diabetesMellitus' WRONG: 'diabetes', 'DM', 'has_diabetes'

## RULE 4: FORMAT VALUES CORRECTLY

Different variable types require specific formats:

GENDER (use SNOMED codes):
- Male: "http://snomed.info/sct|248153007"
- Female: "http://snomed.info/sct|248152002"

ETHNICITY (use OID codes):
- White: "urn:oid:2.16.840.1.113883.6.238|2106-3"
- Black/African American: "urn:oid:2.16.840.1.113883.6.238|2054-5"
- Asian: "urn:oid:2.16.840.1.113883.6.238|2028-9"
- Hispanic/Latino: "urn:oid:2.16.840.1.113883.6.238|2135-2"

BLOOD PRESSURE:
- Use tuple format: (systolic, diastolic)
- Example: (142, 90) for 142/90 mmHg

BOOLEAN VALUES:
- Use: true/false or 1/0
- Example: diabetesMellitus: true

NUMERIC VALUES:
- Include units when specified
- Example: {"value": 165, "unit": "mg/dL"}

## RULE 5: PATIENT SAFETY IS PARAMOUNT

Clinical decision support affects patient care. Inaccurate data leads to
inappropriate recommendations. When in doubt:

- ASK the user for clarification
- DO NOT guess or assume
- EXPLAIN when data is insufficient
- RECOMMEND consulting a healthcare provider

## RULE 6: DO NOT INTERPRET OR RECONCILE RECOMMENDATIONS

When multiple recommendations are returned from Concord, present them
EXACTLY as provided. Do not attempt to interpret or reconcile them.

FORBIDDEN ACTIONS:
- Interpreting why different recommendations exist
- Reconciling or merging seemingly conflicting recommendations
- Explaining the logical paths that led to each recommendation
- Adding editorial commentary about the recommendations
- Speculating about clinical reasoning behind recommendations

REQUIRED ACTIONS:
- Display each recommendation VERBATIM as returned by Concord
- Present all recommendations without modification or interpretation
- If asked about recommendation logic, direct user to their healthcare provider

WHY THIS MATTERS:
Different recommendations may appear to have "conflicting paths" but lead to
the same clinical action. For example:
- Path A: No diabetes, but 10-year risk > 10% → Statin recommended
- Path B: Diabetes present, but 10-year risk < 10% → Statin recommended

Both paths recommend statins through different clinical logic. Concord has
already evaluated the complete clinical picture. Your role is to PRESENT
the results faithfully, not to RE-INTERPRET or RECONCILE them.

The clinical reasoning is encoded in evidence-based guidelines. Do not
substitute your interpretation for established medical logic.

## ACKNOWLEDGMENT

By calling acknowledge_guidelines, you confirm that you have read and
understood these rules and will follow them strictly.
"""


def get_guidelines_tool() -> Tool:
    """Return the acknowledge_guidelines tool definition."""
    return Tool(
        name="acknowledge_guidelines",
        description="""REQUIRED FIRST STEP: Acknowledge Concord usage guidelines.

You MUST call this tool before using any of these tools:
- create_health_context
- create_health_context_from_fhir
- evaluate_patient
- evaluate_all_cpgs
- evaluate_multiple_cpgs
- submit_attestation
- detect_care_gaps

This tool returns the mandatory guidelines that you MUST follow.
Read them carefully - they contain critical rules about:
- Never fabricating patient data
- How to handle missing data
- Correct variable ID and value formats
- Patient safety requirements

Calling this tool is NOT optional. Protected tools will be blocked
until you acknowledge the guidelines.""",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Unique session identifier for this conversation"
                }
            },
            "required": ["session_id"]
        }
    )


async def handle_acknowledge_guidelines(
    args: dict,
    state: ConcordState
) -> list[TextContent]:
    """Handle acknowledge_guidelines tool call.

    Returns the full guidelines and marks the session as acknowledged.
    """
    session_id = args.get("session_id")
    if not session_id:
        return [TextContent(type="text", text=json.dumps({
            "error": "session_id is required"
        }))]

    # Get or create session
    session = state.get_session(session_id, create=True)

    # Mark as acknowledged
    session.acknowledge_guidelines()

    # Return full guidelines
    result = {
        "status": "acknowledged",
        "session_id": session_id,
        "acknowledged_at": session.guidelines_acknowledged_at.isoformat(),
        "guidelines": MANDATORY_GUIDELINES,
        "protected_tools_now_available": list(PROTECTED_TOOLS),
        "_instructions": (
            "You have acknowledged the guidelines. You may now use the protected tools. "
            "Remember: NEVER fabricate data, always ask for missing values, use exact variable IDs."
        )
    }

    log.info(f"Guidelines acknowledged for session {session_id}")
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def check_guidelines_acknowledged(
    session: EvaluationSession | None,
    tool_name: str
) -> dict | None:
    """Check if guidelines have been acknowledged for a protected tool.

    Args:
        session: The evaluation session (may be None)
        tool_name: Name of the tool being called

    Returns:
        None if acknowledged (proceed with tool)
        Error dict if not acknowledged (return this to LLM)
    """
    if tool_name not in PROTECTED_TOOLS:
        return None  # Not a protected tool, proceed

    if session is None:
        return {
            "error": "GUIDELINES_NOT_ACKNOWLEDGED",
            "message": (
                f"You must call 'acknowledge_guidelines' before using '{tool_name}'. "
                "This is a patient safety requirement."
            ),
            "required_action": {
                "tool": "acknowledge_guidelines",
                "args": {"session_id": "<your_session_id>"}
            },
            "reason": (
                "Clinical decision support requires strict adherence to data handling rules. "
                "The guidelines ensure you never fabricate patient data."
            )
        }

    if not session.guidelines_acknowledged:
        return {
            "error": "GUIDELINES_NOT_ACKNOWLEDGED",
            "message": (
                f"You must call 'acknowledge_guidelines' before using '{tool_name}'. "
                "This is a patient safety requirement."
            ),
            "required_action": {
                "tool": "acknowledge_guidelines",
                "args": {"session_id": session.session_id}
            },
            "reason": (
                "Clinical decision support requires strict adherence to data handling rules. "
                "The guidelines ensure you never fabricate patient data."
            )
        }

    return None  # Acknowledged, proceed


def get_guidelines_error_response(
    session_id: str | None,
    tool_name: str
) -> list[TextContent]:
    """Generate error response for unacknowledged guidelines."""
    error = {
        "error": "GUIDELINES_NOT_ACKNOWLEDGED",
        "blocked_tool": tool_name,
        "message": (
            "STOP: You must acknowledge the guidelines before using this tool. "
            "Call 'acknowledge_guidelines' first with a session_id."
        ),
        "required_action": {
            "tool": "acknowledge_guidelines",
            "args": {"session_id": session_id or "<create_a_session_id>"}
        },
        "why": (
            "This tool handles patient health data. Incorrect usage can lead to "
            "wrong clinical recommendations. The guidelines ensure patient safety."
        )
    }
    return [TextContent(type="text", text=json.dumps(error, indent=2))]
