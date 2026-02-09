"""FastMCP server for Concord with MCP Apps UI support (v2).

7 tools: acknowledge_guidelines, list_cpgs, get_cpg_info, create_health_context,
evaluate_patient, collect_attestation, submit_attestation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from core.concord import Concord, NeedAttestationError
from primitives.types import Persona
from variables.var import Var

from .state import ConcordState
from .guidelines import MANDATORY_GUIDELINES, PROTECTED_TOOLS
from .form_builder import FormBuilder
from .html_renderer import get_attestation_app_html

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("concord-mcp-v2")

ATTESTATION_UI_URI = "ui://concord/attestation-form"
MCP_APP_MIME = "text/html;profile=mcp-app"

mcp = FastMCP("concord-ui")
state = ConcordState()
form_builder = FormBuilder()


@mcp.resource(ATTESTATION_UI_URI, mime_type=MCP_APP_MIME)
def attestation_form_resource() -> str:
    """Serve the attestation form MCP App HTML."""
    return get_attestation_app_html()


def _check_guidelines(session_id: str, tool_name: str) -> dict | None:
    if tool_name not in PROTECTED_TOOLS:
        return None
    session = state.get_session(session_id, create=False)
    if session and session.guidelines_acknowledged:
        return None
    return {
        "error": "GUIDELINES_NOT_ACKNOWLEDGED",
        "message": f"You must call 'acknowledge_guidelines' before using '{tool_name}'.",
        "required_action": {
            "tool": "acknowledge_guidelines",
            "args": {"session_id": session_id or "<your_session_id>"},
        },
    }


def _var_info(ev) -> dict:
    """Extract variable metadata from an evaluation result."""
    var = ev.record.var
    return {
        "variable_id": ev.record.id,
        "title": var.title or ev.record.id,
        "required": True,
        "user_attestable": var.user_attestable,
        "type": var.type.value if var.type else None,
        "llm_prompt": var.llm_prompt,
        "question": var.question,
    }


def _missing_var_dict(ev, attestable: bool = False) -> dict:
    """Lighter version for collect_attestation — no user_attestable field."""
    var = ev.record.var
    return {
        "variable_id": ev.record.id,
        "title": var.title or ev.record.id,
        "required": True,
        "type": var.type.value if var.type else None,
        "llm_prompt": var.llm_prompt,
        "question": var.question,
    }


# --- Tool 1 ---

@mcp.tool()
def acknowledge_guidelines(session_id: str) -> str:
    """REQUIRED FIRST STEP: Acknowledge Concord usage guidelines.

    You MUST call this before using create_health_context, evaluate_patient,
    collect_attestation, or submit_attestation.
    """
    session = state.get_session(session_id, create=True)
    session.acknowledge_guidelines()
    return json.dumps({
        "status": "acknowledged",
        "session_id": session_id,
        "acknowledged_at": session.guidelines_acknowledged_at.isoformat(),
        "guidelines": MANDATORY_GUIDELINES,
        "protected_tools_now_available": sorted(PROTECTED_TOOLS),
        "_instructions": (
            "You have acknowledged the guidelines. You may now use the protected tools. "
            "Remember: NEVER fabricate data, always ask for missing values, use exact variable IDs."
        ),
    }, indent=2)


# --- Tool 2 ---

@mcp.tool()
def list_cpgs() -> str:
    """List all available Clinical Practice Guidelines (CPGs)."""
    cpgs = []
    for info in state.get_available_cpgs():
        try:
            cpg = state.load_cpg(info["identifier"])
            cpgs.append({
                "identifier": info["identifier"],
                "title": cpg.title,
                "publisher": cpg.publisher,
                "variables_count": len(cpg.variables or []),
                "assessments_count": len(cpg.assessment_variables or []),
                "recommendations_count": len(cpg.recommendation_variables or []),
            })
        except Exception as e:
            log.warning(f"Could not load CPG {info['identifier']}: {e}")
    return json.dumps({"available_cpgs": cpgs, "total_count": len(cpgs)}, indent=2)


# --- Tool 3 ---

@mcp.tool()
def get_cpg_info(cpg_id: str) -> str:
    """Get detailed variable, eligibility, assessment, and recommendation info for a CPG.

    Variable IDs are case-sensitive — use them exactly as shown.
    """
    cpg = state.load_cpg(cpg_id)
    return json.dumps({
        "identifier": cpg.identifier,
        "title": cpg.title,
        "publisher": cpg.publisher,
        "variables": [
            {"id": v.id, "title": v.title, "required": v.required,
             "user_attestable": v.user_attestable, "code": v.code_string}
            for v in (cpg.variables or [])
        ],
        "eligibility_criteria": [
            {"id": e.id, "title": e.title, "expression": e.expression}
            for e in (cpg.eligibility_variables or [])
        ],
        "assessments": [
            {"id": a.id, "title": a.title, "expression": getattr(a, "expression", None)}
            for a in (cpg.assessment_variables or [])
        ],
        "recommendations": [
            {"id": r.id, "title": r.title,
             "type": str(r.type) if r.type else None,
             "class_of_recommendation": str(r.class_of_recommendation) if r.class_of_recommendation else None,
             "level_of_evidence": str(r.level_of_evidence) if r.level_of_evidence else None,
             "expression": getattr(r, "expression", None)}
            for r in (cpg.recommendation_variables or [])
        ],
    }, indent=2)


# --- Tool 4 ---

@mcp.tool()
def create_health_context(
    session_id: str,
    health_data: list[dict[str, Any]],
    persona: str = "patient",
) -> str:
    """Create a patient health context from variable/value pairs.

    CRITICAL: Only include data the user EXPLICITLY provided.
    health_data: array of {variable_id, value, unit?, date?}
    """
    error = _check_guidelines(session_id, "create_health_context")
    if error:
        return json.dumps(error, indent=2)

    persona_enum = Persona.patient if persona == "patient" else Persona.provider
    session = state.get_session(session_id)
    user = session.get_or_create_user(persona_enum)
    user.clear()
    for item in health_data:
        user.add_input(item["variable_id"], item["value"])

    context = user.build_health_context()
    session.health_context = context
    return json.dumps({
        "session_id": session_id,
        "status": "created",
        "records_count": len(context.records),
        "variables": [r.id for r in context.records],
    }, indent=2)


# --- Tool 5 ---

@mcp.tool()
def evaluate_patient(session_id: str, cpg_id: str) -> str:
    """Evaluate a patient against a CPG.

    If the result contains missing data, you MUST call collect_attestation next.
    DO NOT fabricate values or proceed with partial results.
    """
    error = _check_guidelines(session_id, "evaluate_patient")
    if error:
        return json.dumps(error, indent=2)

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return json.dumps({"error": f"No health context for session: {session_id}"})

    cpg = state.load_cpg(cpg_id)
    concord = Concord(cpg=cpg, healthcontext=session.health_context)

    result: dict[str, Any] = {
        "session_id": session_id,
        "cpg_id": cpg_id,
        "cpg_title": cpg.title,
    }

    try:
        suff = concord.sufficiency()
    except Exception as e:
        return json.dumps({"error": f"Sufficiency check failed: {e}",
                           "session_id": session_id, "cpg_id": cpg_id})

    missing_required = [_var_info(ev) for ev in (suff.insufficient_variables or [])]
    needs_attestation = [
        {**_var_info(ev), "user_attestable": True}
        for ev in (suff.attestation_variables or [])
    ]

    result["sufficiency"] = {
        "is_executable": suff.is_executable,
        "missing_required_count": len(missing_required),
        "missing_required_variables": missing_required,
        "needs_attestation_count": len(needs_attestation),
        "needs_attestation_variables": needs_attestation,
    }

    if missing_required or needs_attestation:
        all_missing = missing_required + needs_attestation
        result["status"] = "missing_data"
        result["_ai_instructions"] = {
            "action": "CALL_COLLECT_ATTESTATION",
            "message": (
                "STOP. Data is missing. "
                "Immediately call collect_attestation to get an interactive form. "
                "Do NOT proceed until all missing data has been collected."
            ),
            "next_tool": "collect_attestation",
            "next_tool_args": {"session_id": session_id, "cpg_id": cpg_id},
            "missing_count": len(all_missing),
            "missing_variable_ids": [v["variable_id"] for v in all_missing],
        }

    try:
        pipeline = concord.evaluate(skip_eligibility=False, ignore_attestations=True)
        session.cpg_evaluations[cpg_id] = concord

        if pipeline.eligibility:
            result["eligibility"] = {"is_eligible": pipeline.eligibility.is_eligible}

        if pipeline.assessment:
            result["assessments"] = [
                {"id": a.id, "value": a.value.value if a.value else None, "narrative": a.narrative}
                for a in pipeline.assessment.assessments
            ]

        if pipeline.recommendations:
            result["recommendations"] = [
                {"id": r.recommendation.id, "title": r.recommendation.title,
                 "applies": r.applies, "narrative": r.narrative}
                for r in (pipeline.recommendations.applied or [])
            ]
            result["recommendations_count"] = len(result["recommendations"])

        if "status" not in result:
            result["status"] = "evaluated"
        result["is_complete"] = pipeline.is_complete

    except NeedAttestationError as e:
        result["status"] = "needs_attestation"
        result["missing_attestations"] = [ev.record.id for ev in e.records]
        session.cpg_evaluations[cpg_id] = concord
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return json.dumps(result, indent=2, default=str)


# --- Tool 6 ---

@mcp.tool(meta={"ui": {"resourceUri": ATTESTATION_UI_URI}})
def collect_attestation(session_id: str, cpg_id: str) -> str:
    """Collect missing health data via an interactive form.

    IMPORTANT: This tool renders an interactive HTML form in the conversation.
    DO NOT ask the user questions yourself — the form handles data collection.
    DO NOT list or describe the form fields — the form already shows them.
    After the form loads, say ONLY: "Please fill in and submit the form above."
    Wait for the user to submit the form, then call evaluate_patient again.
    """
    error = _check_guidelines(session_id, "collect_attestation")
    if error:
        return json.dumps(error, indent=2)

    session = state.get_session(session_id, create=False)
    if not session:
        return json.dumps({"error": f"Session not found: {session_id}"})

    cpg = state.load_cpg(cpg_id)
    concord = session.get_evaluation(cpg_id)

    missing_vars: list[dict] = []
    if concord and concord.sufficiency_result:
        for ev in (concord.sufficiency_result.insufficient_variables or []):
            missing_vars.append(_missing_var_dict(ev))
        for ev in (concord.sufficiency_result.attestation_variables or []):
            missing_vars.append(_missing_var_dict(ev))

    if not missing_vars:
        missing_vars = [
            {"variable_id": v.id, "title": v.title or v.id, "required": v.required,
             "type": v.type.value if v.type else None,
             "llm_prompt": v.llm_prompt, "question": v.question}
            for v in (cpg.variables or []) if v.user_attestable
        ]

    fields = form_builder.build_fields(missing_vars, cpg.variables or [])

    var_lookup = {v.id: v for v in (cpg.variables or [])}
    fields_json = []
    for f in fields:
        entry = f.to_dict()
        var_obj = var_lookup.get(f.variable_id)
        if var_obj and getattr(var_obj, "category", None):
            entry["category"] = (var_obj.category.value
                                 if hasattr(var_obj.category, "value")
                                 else str(var_obj.category))
        fields_json.append(entry)

    log.info(f"collect_attestation: {len(fields_json)} fields for {cpg_id}")
    return json.dumps({
        "session_id": session_id,
        "cpg_id": cpg_id,
        "cpg_title": cpg.title,
        "fields_count": len(fields_json),
        "fields": fields_json,
    }, indent=2)


# --- Tool 7 ---

@mcp.tool()
def submit_attestation(
    session_id: str,
    attestations: list[dict[str, Any]],
    cpg_id: str = "",
) -> str:
    """Submit patient-attested health data collected from the form.

    attestations: array of {variable_id, value}.
    After submitting, call evaluate_patient again.
    """
    error = _check_guidelines(session_id, "submit_attestation")
    if error:
        return json.dumps(error, indent=2)

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return json.dumps({"error": f"No health context for session: {session_id}"})

    var_lookup: dict[str, Var] = {}
    if cpg_id:
        try:
            var_lookup = {v.id: v for v in state.load_cpg(cpg_id).variables}
        except Exception:
            pass
    elif session.active_concord:
        var_lookup = {v.id: v for v in session.active_concord.cpg.variables}

    user = session.get_or_create_user()
    errors_list, added = [], []

    for att in attestations:
        var_id, raw_value = att["variable_id"], att["value"]
        try:
            user.attest(var_id, raw_value, var=var_lookup.get(var_id))
            added.append(var_id)
            session.attestations[var_id] = raw_value
        except Exception as e:
            errors_list.append({"variable_id": var_id, "error": str(e)})

    session.health_context = user.update_health_context(session.health_context)
    return json.dumps({
        "session_id": session_id,
        "status": "attestations_added",
        "added_count": len(added),
        "variables": added,
        "errors": errors_list or None,
        "message": "Call evaluate_patient again to re-evaluate with new data",
    }, indent=2)


# --- Prompt ---

@mcp.prompt()
def test_attestation_ui(
    cpg_id: str = "uspstfStatinUse",
    age: str = "55",
    gender: str = "female",
) -> str:
    """Test the interactive attestation UI flow end-to-end."""
    gender_code = (
        "http://snomed.info/sct|248152002" if gender.lower().startswith("f")
        else "http://snomed.info/sct|248153007"
    )
    return f"""Test the Concord attestation UI — follow these steps exactly,
showing the tool result after each.

1. Call acknowledge_guidelines with session_id "test-ui"
2. Call get_cpg_info with cpg_id "{cpg_id}"
3. Call create_health_context with session_id "test-ui", health_data:
   [{{"variable_id": "Age", "value": {age}}}, {{"variable_id": "Gender", "value": "{gender_code}"}}]
4. Call evaluate_patient with session_id "test-ui", cpg_id "{cpg_id}"
5. Call collect_attestation with session_id "test-ui", cpg_id "{cpg_id}"
6. After I submit the form, call submit_attestation
7. Call evaluate_patient again and show the final recommendations

Begin with step 1."""


# --- Entry points ---

async def serve():
    await mcp.run_stdio_async()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Concord MCP Server v2")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()

    if args.transport == "streamable-http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        log.info(f"Starting on http://{args.host}:{args.port}/mcp")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
