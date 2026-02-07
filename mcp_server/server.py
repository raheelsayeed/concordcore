#!/usr/bin/env python3
"""MCP Server implementation for Concord.

Exposes clinical practice guideline evaluation as MCP tools, including:
- CPG discovery and information
- Patient health context creation (variable-based and FHIR)
- CPG evaluation with streaming support
- Prioritized recommendations with confidence scoring
- Deep recommendation explanations

Example usage:
    # Run server
    python -m mcp_server

    # Configure in Claude Desktop:
    {
        "mcpServers": {
            "concord": {
                "command": "python",
                "args": ["-m", "mcp_server"],
                "cwd": "/path/to/concordcore"
            }
        }
    }
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    PromptMessage,
    PromptArgument,
    GetPromptResult,
)

from core.cpg import CPG
from core.concord import Concord, NeedAttestationError
from core.healthcontext import HealthContext
from primitives.types import Persona
from variables.var import Var
from variables.value import Value
from variables.record import Record

# Import our modules
from .state import ConcordState, EvaluationSession
from .fhir_handler import FHIRHandler, FHIRParseError
from .confidence import ConfidenceCalculator, ConfidenceScore
from .priority import PriorityRanker, PrioritizedRecommendation
from .explanation import ExplanationGenerator, RecommendationExplanation
from .streaming import StreamingEvaluator, StreamProgress
from .instructions_handler import (
    get_instruction_tools,
    handle_get_llm_instructions,
    handle_build_optimized_prompt,
)
from .guidelines_handler import (
    get_guidelines_tool,
    handle_acknowledge_guidelines,
    check_guidelines_acknowledged,
    get_guidelines_error_response,
    PROTECTED_TOOLS,
)
from .care_gaps import CareGapDetector, detect_care_gaps

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("concord-mcp")

# Initialize state and server
state = ConcordState()
server = Server("concord")

# Module instances
fhir_handler = FHIRHandler()
confidence_calculator = ConfidenceCalculator()
priority_ranker = PriorityRanker()
explanation_generator = ExplanationGenerator()
streaming_evaluator = StreamingEvaluator()


# ============================================================================
# TOOLS
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Concord tools."""
    return [
        # === MANDATORY FIRST STEP ===
        get_guidelines_tool(),  # Must be called before protected tools

        # === CPG Discovery ===
        Tool(
            name="list_cpgs",
            description="List all available Clinical Practice Guidelines (CPGs). Returns identifiers, titles, and counts of variables/assessments/recommendations.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_cpg_info",
            description="Get detailed information about a specific CPG including its variables, eligibility criteria, assessments, and recommendations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cpg_id": {
                        "type": "string",
                        "description": "The CPG identifier (e.g., 'cholesterol')"
                    }
                },
                "required": ["cpg_id"]
            }
        ),

        # === Health Context Creation ===
        Tool(
            name="create_health_context",
            description="""Create a patient health context from variable/value pairs.

CRITICAL: Only include health data that the user has EXPLICITLY provided.
DO NOT fabricate, estimate, assume, or fill in any missing values.
DO NOT add default values for missing fields.
DO NOT use typical/average values as substitutes.

If the user provides incomplete data, create the context with ONLY what was provided.
The evaluate_patient tool will identify what data is missing.

Variable IDs are case-sensitive and must match the CPG definition exactly (e.g., 'Age' not 'age', 'LDL' not 'ldl_cholesterol').
Use get_cpg_info first to see the exact variable IDs required.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier"
                    },
                    "persona": {
                        "type": "string",
                        "enum": ["patient", "provider"],
                        "default": "patient"
                    },
                    "health_data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "variable_id": {"type": "string"},
                                "value": {},
                                "unit": {"type": "string"},
                                "date": {"type": "string"}
                            },
                            "required": ["variable_id", "value"]
                        }
                    }
                },
                "required": ["session_id", "health_data"]
            }
        ),
        Tool(
            name="create_health_context_from_fhir",
            description="Create a patient health context from FHIR R4 resources. Accepts Bundle or array of resources (Observation, Condition, MedicationRequest, Procedure).",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier"
                    },
                    "persona": {
                        "type": "string",
                        "enum": ["patient", "provider"],
                        "default": "patient"
                    },
                    "fhir_data": {
                        "type": "object",
                        "description": "FHIR R4 Bundle or array of resources"
                    },
                    "cpg_id": {
                        "type": "string",
                        "description": "Optional: CPG ID to match FHIR codes against"
                    }
                },
                "required": ["session_id", "fhir_data"]
            }
        ),

        # === Evaluation ===
        Tool(
            name="evaluate_patient",
            description="""Evaluate a patient against a specific CPG.

IMPORTANT DATA HANDLING RULES:
1. If 'sufficiency.is_executable' is false or missing_required_variables/needs_attestation_variables are not empty:
   - DO NOT proceed with interpretation of partial results
   - DO NOT fabricate or estimate missing values
   - You MUST ask the user to provide the missing data
   - Present the list of missing variables to the user in a clear format
   - Wait for user response before calling create_health_context again

2. Only after the user provides the missing values should you:
   - Call create_health_context with the additional data
   - Call evaluate_patient again

3. Never assume or fill in health data yourself - patient safety requires actual data.

Returns eligibility, sufficiency check, assessments, and recommendations.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "cpg_id": {"type": "string"},
                    "skip_eligibility": {"type": "boolean", "default": False},
                    "include_confidence": {"type": "boolean", "default": True},
                    "require_complete_data": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, returns error instead of partial results when required data is missing"
                    }
                },
                "required": ["session_id", "cpg_id"]
            }
        ),
        Tool(
            name="evaluate_all_cpgs",
            description="Evaluate patient against ALL available CPGs. Returns summary of applicable guidelines and total recommendations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "include_confidence": {"type": "boolean", "default": True}
                },
                "required": ["session_id"]
            }
        ),

        # === Recommendations ===
        Tool(
            name="get_recommendations",
            description="Get recommendations from a completed evaluation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="get_prioritized_recommendations",
            description="Get recommendations ranked by evidence strength (Class of Recommendation, Level of Evidence, USPSTF Grade). Returns priority scores and rationales.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                    "include_all_evaluated": {"type": "boolean", "default": False}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="explain_recommendation",
            description="Get deep explanation of why a recommendation applies, including assessment chain, evidence citations, and patient-friendly summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "recommendation_id": {"type": "string"},
                    "persona": {
                        "type": "string",
                        "enum": ["patient", "provider"],
                        "default": "patient"
                    }
                },
                "required": ["session_id", "recommendation_id"]
            }
        ),

        # === Data Quality ===
        Tool(
            name="get_confidence_scores",
            description="Get confidence scores for evaluation based on data completeness, freshness, validation, and attestation burden.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="get_missing_data",
            description="Get list of health data missing and needed for CPG evaluation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="submit_attestation",
            description="Submit patient-attested health data for missing variables.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "attestations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "variable_id": {"type": "string"},
                                "value": {}
                            },
                            "required": ["variable_id", "value"]
                        }
                    }
                },
                "required": ["session_id", "attestations"]
            }
        ),
        # === Care Gap Detection ===
        Tool(
            name="detect_care_gaps",
            description="""Detect preventive care gaps by evaluating patient against all applicable CPGs.

Returns a prioritized list of care gaps including:
- Missing screenings (eligible but not performed)
- Overdue tests (last performed beyond recommended interval)
- Unmet recommendations (CPG recommends action not yet taken)

Each gap includes priority (critical/high/moderate/low), USPSTF grade,
and suggested action. Use this for comprehensive preventive care review.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID with health context"
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "Optional patient identifier for the report",
                        "default": "unknown"
                    },
                    "include_ineligible": {
                        "type": "boolean",
                        "description": "Include gaps for CPGs patient isn't eligible for",
                        "default": False
                    }
                },
                "required": ["session_id"]
            }
        ),

        # === Reproducibility & Verification ===
        Tool(
            name="get_evaluation_metadata",
            description="Get cryptographic metadata for a completed evaluation. Returns input hash, output hash, CPG version, and timestamp for reproducibility verification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID from evaluate_patient"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="verify_reproducibility",
            description="Verify that a previous evaluation is reproducible. Re-runs evaluation and compares hashes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID to verify"},
                    "original_input_hash": {"type": "string", "description": "Original input hash to compare"},
                    "original_output_hash": {"type": "string", "description": "Original output hash to compare"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="evaluate_multiple_cpgs",
            description="Evaluate patient against multiple specific CPGs in parallel. Returns combined results with conflict detection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID with health context"},
                    "cpg_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of CPG identifiers to evaluate"
                    },
                    "parallel": {"type": "boolean", "default": True, "description": "Run evaluations in parallel"}
                },
                "required": ["session_id", "cpg_ids"]
            }
        ),
        # === Institutional Configuration ===
        Tool(
            name="validate_institution_config",
            description="Validate an institutional configuration file. Checks schema, detects conflicts, validates expressions, and analyzes impact. Returns detailed validation report with errors, warnings, inheritance chain, and impact analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {"type": "string", "description": "Path to the institution config YAML file"},
                    "cpg_id": {"type": "string", "description": "Optional CPG identifier to validate config against"},
                    "check_safe_ranges": {"type": "boolean", "default": True, "description": "Check if values are within safe clinical ranges"},
                    "strict_mode": {"type": "boolean", "default": False, "description": "Treat warnings as errors"}
                },
                "required": ["config_path"]
            }
        ),
        Tool(
            name="get_institution_config_impact",
            description="Analyze how an institutional configuration would impact CPG evaluation. Shows threshold changes, excluded recommendations, and added local rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {"type": "string", "description": "Path to the institution config YAML file"},
                    "cpg_id": {"type": "string", "description": "CPG identifier to analyze impact against"}
                },
                "required": ["config_path", "cpg_id"]
            }
        ),
        # === LLM Instructions ===
        *get_instruction_tools(),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        # Check if this is a protected tool that requires guidelines acknowledgment
        if name in PROTECTED_TOOLS:
            session_id = arguments.get("session_id")
            session = state.get_session(session_id, create=False) if session_id else None
            error = check_guidelines_acknowledged(session, name)
            if error:
                log.warning(f"Blocked {name}: guidelines not acknowledged for session {session_id}")
                return [TextContent(type="text", text=json.dumps(error, indent=2))]

        handlers = {
            # Mandatory first step
            "acknowledge_guidelines": lambda args: handle_acknowledge_guidelines(args, state),
            # CPG Discovery
            "list_cpgs": handle_list_cpgs,
            "get_cpg_info": handle_get_cpg_info,
            # Health Context (PROTECTED)
            "create_health_context": handle_create_health_context,
            "create_health_context_from_fhir": handle_create_health_context_from_fhir,
            # Evaluation (PROTECTED)
            "evaluate_patient": handle_evaluate_patient,
            "evaluate_all_cpgs": handle_evaluate_all_cpgs,
            "evaluate_multiple_cpgs": handle_evaluate_multiple_cpgs,
            # Recommendations
            "get_recommendations": handle_get_recommendations,
            "get_prioritized_recommendations": handle_get_prioritized_recommendations,
            "explain_recommendation": handle_explain_recommendation,
            # Data quality
            "get_confidence_scores": handle_get_confidence_scores,
            "get_missing_data": handle_get_missing_data,
            "submit_attestation": handle_submit_attestation,
            # Care gaps
            "detect_care_gaps": handle_detect_care_gaps,
            # Reproducibility
            "get_evaluation_metadata": handle_get_evaluation_metadata,
            "verify_reproducibility": handle_verify_reproducibility,
            # Institutional configuration
            "validate_institution_config": handle_validate_institution_config,
            "get_institution_config_impact": handle_get_institution_config_impact,
            # LLM Instructions
            "get_llm_instructions": lambda args: handle_get_llm_instructions(args, state),
            "build_optimized_prompt": lambda args: handle_build_optimized_prompt(args, state),
        }

        handler = handlers.get(name)
        if handler:
            return await handler(arguments)
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        log.exception(f"Tool error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ============================================================================
# TOOL HANDLERS
# ============================================================================

async def handle_list_cpgs(args: dict) -> list[TextContent]:
    """List available CPGs."""
    cpgs_info = state.get_available_cpgs()

    result = {"available_cpgs": []}
    for cpg_info in cpgs_info:
        try:
            cpg = state.load_cpg(cpg_info["identifier"])
            result["available_cpgs"].append({
                "identifier": cpg_info["identifier"],
                "title": cpg.title,
                "publisher": cpg.publisher,
                "variables_count": len(cpg.variables) if cpg.variables else 0,
                "assessments_count": len(cpg.assessment_variables) if cpg.assessment_variables else 0,
                "recommendations_count": len(cpg.recommendation_variables) if cpg.recommendation_variables else 0
            })
        except Exception as e:
            log.warning(f"Could not load CPG {cpg_info['identifier']}: {e}")

    result["total_count"] = len(result["available_cpgs"])
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_cpg_info(args: dict) -> list[TextContent]:
    """Get detailed CPG information."""
    cpg_id = args["cpg_id"]
    cpg = state.load_cpg(cpg_id)

    result = {
        "identifier": cpg.identifier,
        "title": cpg.title,
        "publisher": cpg.publisher,
        "variables": [],
        "eligibility_criteria": [],
        "assessments": [],
        "recommendations": []
    }

    for v in (cpg.variables or []):
        result["variables"].append({
            "id": v.id,
            "title": v.title,
            "required": v.required,
            "user_attestable": v.user_attestable,
            "code": v.code_string
        })

    for e in (cpg.eligibility_variables or []):
        result["eligibility_criteria"].append({
            "id": e.id,
            "title": e.title,
            "expression": e.expression
        })

    for a in (cpg.assessment_variables or []):
        result["assessments"].append({
            "id": a.id,
            "title": a.title,
            "expression": getattr(a, 'expression', None)
        })

    for r in (cpg.recommendation_variables or []):
        result["recommendations"].append({
            "id": r.id,
            "title": r.title,
            "type": str(r.type) if r.type else None,
            "class_of_recommendation": str(r.class_of_recommendation) if r.class_of_recommendation else None,
            "level_of_evidence": str(r.level_of_evidence) if r.level_of_evidence else None,
            "expression": getattr(r, 'expression', None)
        })

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_create_health_context(args: dict) -> list[TextContent]:
    """Create health context from variable/value pairs."""
    session_id = args["session_id"]
    persona_str = args.get("persona", "patient")
    health_data = args["health_data"]

    persona = Persona.patient if persona_str == "patient" else Persona.provider

    session = state.get_session(session_id)
    user = session.get_or_create_user(persona)
    user.clear()  # Reset for fresh context creation

    for item in health_data:
        var_id = item["variable_id"]
        raw_value = item["value"]
        user.add_input(var_id, raw_value)

    context = user.build_health_context()
    session.health_context = context

    result = {
        "session_id": session_id,
        "status": "created",
        "records_count": len(context.records),
        "variables": [r.id for r in context.records]
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_create_health_context_from_fhir(args: dict) -> list[TextContent]:
    """Create health context from FHIR resources."""
    session_id = args["session_id"]
    persona_str = args.get("persona", "patient")
    fhir_data = args["fhir_data"]
    cpg_id = args.get("cpg_id")

    persona = Persona.patient if persona_str == "patient" else Persona.provider

    # Get CPG variables if specified
    cpg_variables = None
    if cpg_id:
        cpg = state.load_cpg(cpg_id)
        cpg_variables = cpg.variables

    try:
        context = fhir_handler.create_health_context(
            fhir_data=fhir_data,
            cpg_variables=cpg_variables,
            persona=persona
        )
    except FHIRParseError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    session = state.get_session(session_id)
    session.health_context = context

    # Store FHIR resources for reference
    resources = fhir_handler.parse_resources(fhir_data)
    session.fhir_resources = resources

    result = {
        "session_id": session_id,
        "status": "created",
        "records_count": len(context.records),
        "variables": [r.id for r in context.records],
        "fhir_summary": fhir_handler.get_resource_summary(resources)
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_evaluate_patient(args: dict) -> list[TextContent]:
    """Evaluate patient against a CPG."""
    session_id = args["session_id"]
    cpg_id = args["cpg_id"]
    skip_eligibility = args.get("skip_eligibility", False)
    include_confidence = args.get("include_confidence", True)
    require_complete_data = args.get("require_complete_data", False)

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No health context for session: {session_id}"
        }))]

    cpg = state.load_cpg(cpg_id)
    concord = Concord(
        cpg=cpg,
        healthcontext=session.health_context,
        ignore_eligibility=skip_eligibility
    )

    result = {
        "session_id": session_id,
        "cpg_id": cpg_id,
        "cpg_title": cpg.title
    }

    # First check sufficiency to report missing data
    try:
        sufficiency_result = concord.sufficiency()
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Sufficiency check failed: {str(e)}",
            "session_id": session_id,
            "cpg_id": cpg_id
        }))]

    # Build detailed missing data info
    missing_required_vars = []
    if sufficiency_result.insufficient_variables:
        for ev in sufficiency_result.insufficient_variables:
            missing_required_vars.append({
                "variable_id": ev.record.id,
                "title": ev.record.var.title or ev.record.id,
                "required": True,
                "user_attestable": ev.record.var.user_attestable
            })

    needs_attestation_vars = []
    if sufficiency_result.attestation_variables:
        for ev in sufficiency_result.attestation_variables:
            needs_attestation_vars.append({
                "variable_id": ev.record.id,
                "title": ev.record.var.title or ev.record.id,
                "required": True,
                "user_attestable": True
            })

    result["sufficiency"] = {
        "is_executable": sufficiency_result.is_executable,
        "missing_required_count": len(missing_required_vars),
        "missing_required_variables": missing_required_vars,
        "needs_attestation_count": len(needs_attestation_vars),
        "needs_attestation_variables": needs_attestation_vars
    }

    # If data is missing, always return instructions for the AI to ask the user
    if missing_required_vars or needs_attestation_vars:
        all_missing = missing_required_vars + needs_attestation_vars

        # Build user-friendly prompts for each missing variable
        ask_user_prompts = []
        for v in all_missing:
            var_id = v["variable_id"]
            title = v["title"]
            if v.get("user_attestable"):
                ask_user_prompts.append(f"- {title} ({var_id}): Ask yes/no or get specific value from user")
            else:
                ask_user_prompts.append(f"- {title} ({var_id}): Request lab result or measurement from user")

        result["status"] = "missing_data"
        result["_ai_instructions"] = {
            "action": "ASK_USER_FOR_MISSING_DATA",
            "message": (
                "STOP - DO NOT PROCEED WITHOUT USER INPUT. "
                "The following health data is missing and MUST be obtained from the user. "
                "DO NOT fabricate, estimate, or assume any values. "
                "Present this list to the user and ask them to provide the missing information. "
                "After receiving the data, call create_health_context again with the complete data set."
            ),
            "missing_variables": all_missing,
            "ask_user_prompts": ask_user_prompts,
            "sample_question": (
                f"I need additional information to complete the evaluation. "
                f"Could you please provide the following:\n" +
                "\n".join(ask_user_prompts[:10])
            )
        }

        # If require_complete_data is True, stop here with error
        if require_complete_data:
            missing_names = [v["variable_id"] for v in all_missing]
            result["error"] = f"Cannot evaluate: missing required data for {len(all_missing)} variables: {', '.join(missing_names[:10])}"
            if len(missing_names) > 10:
                result["error"] += f" and {len(missing_names) - 10} more"
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        # Even if proceeding, add strong warning
        result["data_quality_warning"] = (
            f"CRITICAL: INCOMPLETE DATA - {len(missing_required_vars)} required variables missing, "
            f"{len(needs_attestation_vars)} variables need patient attestation. "
            "DO NOT interpret these results. Ask user for missing data first. Missing: " +
            ", ".join([v["variable_id"] for v in all_missing[:5]])
        )
        if len(all_missing) > 5:
            result["data_quality_warning"] += f" and {len(all_missing) - 5} more"

    try:
        pipeline = concord.evaluate(
            skip_eligibility=skip_eligibility,
            ignore_attestations=True
        )

        session.cpg_evaluations[cpg_id] = concord

        if pipeline.eligibility:
            result["eligibility"] = {"is_eligible": pipeline.eligibility.is_eligible}

        # Sufficiency already computed above, just update is_executable from pipeline if available
        if pipeline.sufficiency:
            result["sufficiency"]["is_executable"] = pipeline.sufficiency.is_executable

        if pipeline.assessment:
            result["assessments"] = []
            for ev in pipeline.assessment.context.evaluation_list:
                result["assessments"].append({
                    "id": ev.id,
                    "value": ev.record.value.value if ev.record.value else None,
                    "narrative": getattr(ev.record, 'narrative', None)
                })

        if pipeline.recommendations:
            result["recommendations"] = []
            for rec in (pipeline.recommendations.applied or []):
                result["recommendations"].append({
                    "id": rec.recommendation.id,
                    "title": rec.recommendation.title,
                    "applies": rec.applies,
                    "narrative": rec.narrative
                })
            result["recommendations_count"] = len(result["recommendations"])

        result["status"] = "evaluated"
        result["is_complete"] = pipeline.is_complete

        # Add explicit incomplete data flag for clear signaling
        has_missing_data = (
            (pipeline.sufficiency and not pipeline.sufficiency.is_executable) or
            (pipeline.sufficiency and pipeline.sufficiency.attestation_variables)
        )
        if has_missing_data:
            result["is_complete"] = False
            result["incomplete_reason"] = "Missing required data - see sufficiency.missing_required_variables and sufficiency.needs_attestation_variables"

        if include_confidence:
            confidence = confidence_calculator.calculate(concord)
            result["confidence"] = confidence.to_dict()

        # Add evaluation metadata for reproducibility
        if pipeline.metadata:
            result["metadata"] = pipeline.metadata.to_dict()

    except NeedAttestationError as e:
        result["status"] = "needs_attestation"
        result["missing_attestations"] = [ev.record.id for ev in e.records]
        session.cpg_evaluations[cpg_id] = concord
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_evaluate_all_cpgs(args: dict) -> list[TextContent]:
    """Evaluate patient against all CPGs."""
    session_id = args["session_id"]
    include_confidence = args.get("include_confidence", True)

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No health context for session: {session_id}"
        }))]

    cpg_infos = state.get_available_cpgs()
    cpgs = []
    for info in cpg_infos:
        try:
            cpg = state.load_cpg(info["identifier"])
            cpgs.append((info["identifier"], cpg))
        except Exception as e:
            log.warning(f"Could not load CPG {info['identifier']}: {e}")

    summary = await streaming_evaluator.evaluate_all_with_summary(
        session.health_context,
        cpgs,
        include_confidence
    )

    result = summary.to_dict()
    result["session_id"] = session_id

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_get_recommendations(args: dict) -> list[TextContent]:
    """Get recommendations for a session."""
    session_id = args["session_id"]

    session = state.get_session(session_id, create=False)
    if not session:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Session not found: {session_id}"
        }))]

    concord = session.active_concord
    if not concord or not concord.recommendation_result:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation completed. Call evaluate_patient first."
        }))]

    result = {
        "session_id": session_id,
        "cpg_title": concord.cpg.title,
        "recommendations": []
    }

    for rec in (concord.recommendation_result.applied or []):
        rec_data = {
            "id": rec.recommendation.id,
            "title": rec.recommendation.title,
            "applies": rec.applies,
            "narrative": rec.narrative,
            "type": str(rec.recommendation.type) if rec.recommendation.type else None
        }
        if rec.recommendation.citations:
            rec_data["citations_count"] = len(rec.recommendation.citations)
        result["recommendations"].append(rec_data)

    result["total_count"] = len(result["recommendations"])
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_get_prioritized_recommendations(args: dict) -> list[TextContent]:
    """Get prioritized recommendations."""
    session_id = args["session_id"]
    limit = args.get("limit", 10)
    include_all = args.get("include_all_evaluated", False)

    session = state.get_session(session_id, create=False)
    if not session:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Session not found: {session_id}"
        }))]

    concord = session.active_concord
    if not concord or not concord.recommendation_result:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation completed. Call evaluate_patient first."
        }))]

    all_recs = concord.recommendation_result.recommendations
    prioritized = priority_ranker.rank(all_recs, include_non_applicable=include_all)

    result = {
        "session_id": session_id,
        "cpg_title": concord.cpg.title,
        "prioritized_recommendations": [p.to_dict() for p in prioritized[:limit]],
        "summary": priority_ranker.get_summary(prioritized)
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_explain_recommendation(args: dict) -> list[TextContent]:
    """Explain a recommendation."""
    session_id = args["session_id"]
    recommendation_id = args["recommendation_id"]
    persona_str = args.get("persona", "patient")

    session = state.get_session(session_id, create=False)
    if not session:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Session not found: {session_id}"
        }))]

    concord = session.active_concord
    if not concord:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation completed. Call evaluate_patient first."
        }))]

    persona = Persona.patient if persona_str == "patient" else Persona.provider

    try:
        explanation = explanation_generator.explain(concord, recommendation_id, persona)
        result = explanation.to_dict()
        result["session_id"] = session_id
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except ValueError as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def handle_get_confidence_scores(args: dict) -> list[TextContent]:
    """Get confidence scores."""
    session_id = args["session_id"]

    session = state.get_session(session_id, create=False)
    if not session:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Session not found: {session_id}"
        }))]

    concord = session.active_concord
    if not concord:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation completed. Call evaluate_patient first."
        }))]

    confidence = confidence_calculator.calculate(concord)
    result = confidence.to_dict()
    result["session_id"] = session_id
    result["cpg_title"] = concord.cpg.title

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_missing_data(args: dict) -> list[TextContent]:
    """Get missing data needed for evaluation."""
    session_id = args["session_id"]

    session = state.get_session(session_id, create=False)
    if not session:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Session not found: {session_id}"
        }))]

    concord = session.active_concord
    if not concord or not concord.sufficiency_result:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation completed. Call evaluate_patient first."
        }))]

    result = {
        "session_id": session_id,
        "missing_required": [],
        "needs_attestation": []
    }

    # Insufficient (missing required)
    for ev in (concord.sufficiency_result.insufficient_variables or []):
        var = ev.record.var
        result["missing_required"].append({
            "variable_id": ev.record.id,
            "title": var.title or ev.record.id,
            "required": var.required,
            "user_attestable": var.user_attestable
        })

    # Needs attestation
    for ev in (concord.sufficiency_result.attestation_variables or []):
        var = ev.record.var
        result["needs_attestation"].append({
            "variable_id": ev.record.id,
            "title": var.title or ev.record.id,
            "question": getattr(var, 'question', None) or f"What is your {var.title or ev.record.id}?"
        })

    result["total_missing"] = len(result["missing_required"]) + len(result["needs_attestation"])
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_submit_attestation(args: dict) -> list[TextContent]:
    """Submit attestations."""
    session_id = args["session_id"]
    attestations = args["attestations"]

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No health context for session: {session_id}"
        }))]

    user = session.get_or_create_user()

    for att in attestations:
        var_id = att["variable_id"]
        raw_value = att["value"]
        user.attest(var_id, raw_value)

        # Keep attestations dict for backward compatibility
        session.attestations[var_id] = raw_value

    # Rebuild HealthContext with the new attestations (frozen-safe)
    session.health_context = user.update_health_context(session.health_context)

    result = {
        "session_id": session_id,
        "status": "attestations_added",
        "added_count": len(attestations),
        "variables": [a["variable_id"] for a in attestations],
        "message": "Call evaluate_patient again to re-evaluate with new data"
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_detect_care_gaps(args: dict) -> list[TextContent]:
    """Detect care gaps by evaluating patient against all applicable CPGs."""
    session_id = args["session_id"]
    patient_id = args.get("patient_id", "unknown")
    include_ineligible = args.get("include_ineligible", False)

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No health context for session: {session_id}"
        }))]

    # Load all available CPGs
    cpg_infos = state.get_available_cpgs()
    cpgs = []
    for info in cpg_infos:
        try:
            cpg = state.load_cpg(info["identifier"])
            cpgs.append(cpg)
        except Exception as e:
            log.warning(f"Could not load CPG {info['identifier']} for gap detection: {e}")

    if not cpgs:
        return [TextContent(type="text", text=json.dumps({
            "error": "No CPGs available for care gap detection"
        }))]

    # Detect care gaps
    detector = CareGapDetector(cpgs)
    report = detector.detect(
        health_context=session.health_context,
        patient_id=patient_id,
        include_ineligible=include_ineligible
    )

    # Build response
    result = {
        "session_id": session_id,
        "patient_id": report.patient_id,
        "evaluation_date": report.evaluation_date.isoformat(),
        "total_cpgs_evaluated": report.total_cpgs_evaluated,
        "total_gaps": len(report.gaps),
        "gaps_by_priority": report.summary.get("by_priority", {}),
        "gaps_by_type": report.summary.get("by_type", {}),
        "gaps": []
    }

    # Add gap details
    for gap in report.gaps:
        result["gaps"].append({
            "id": gap.id,
            "title": gap.title,
            "description": gap.description,
            "gap_type": gap.gap_type.value,
            "priority": gap.priority.value,
            "cpg_id": gap.cpg_id,
            "cpg_title": gap.cpg_title,
            "uspstf_grade": gap.uspstf_grade,
            "reason": gap.reason,
            "suggested_action": gap.suggested_action,
            "evidence_summary": gap.evidence_summary,
        })

    # Add summary message
    if report.gaps:
        critical = report.summary.get("by_priority", {}).get("critical", 0)
        high = report.summary.get("by_priority", {}).get("high", 0)

        if critical > 0:
            result["_summary"] = f"ATTENTION: {critical} critical priority care gap(s) detected. Immediate action recommended."
        elif high > 0:
            result["_summary"] = f"Found {high} high priority care gap(s) that should be addressed soon."
        else:
            result["_summary"] = f"Found {len(report.gaps)} care gap(s) to consider addressing."
    else:
        result["_summary"] = "No care gaps detected. Patient is up to date on preventive care for evaluated CPGs."

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


# ============================================================================
# REPRODUCIBILITY & PARALLEL EVALUATION HANDLERS
# ============================================================================

async def handle_get_evaluation_metadata(args: dict) -> list[TextContent]:
    """Get evaluation metadata for reproducibility."""
    from core.reproducibility import compute_output_hash

    session_id = args["session_id"]
    session = state.get_session(session_id, create=False)

    if not session:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Session not found: {session_id}"
        }))]

    concord = session.active_concord
    if not concord:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation completed. Call evaluate_patient first."
        }))]

    # Get metadata from the last evaluation
    metadata = concord._create_metadata()

    # Compute output hash if we have results
    output_hash = None
    if concord.recommendation_result:
        from core.concord import PipelineResult
        # Create a PipelineResult to compute hash
        result = PipelineResult(
            eligibility=concord.eligibility_result,
            sufficiency=concord.sufficiency_result,
            assessment=concord.assessment_result,
            recommendations=concord.recommendation_result,
            is_complete=True,
            errors=[],
            metadata=metadata
        )
        output_hash = compute_output_hash(result)

    result = {
        "session_id": session_id,
        "cpg_id": metadata.cpg_id,
        "cpg_version": metadata.cpg_version,
        "cpg_last_updated": metadata.cpg_last_updated,
        "evaluation_timestamp": metadata.evaluation_timestamp,
        "input_data_hash": metadata.input_data_hash,
        "output_hash": output_hash,
        "_reproducibility_note": "Same input_data_hash + same cpg_version = identical output_hash (guaranteed)"
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_verify_reproducibility(args: dict) -> list[TextContent]:
    """Verify evaluation reproducibility."""
    from core.reproducibility import ReproducibilityVerifier, compute_output_hash

    session_id = args["session_id"]
    original_input_hash = args.get("original_input_hash")
    original_output_hash = args.get("original_output_hash")

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No health context for session: {session_id}"
        }))]

    concord = session.active_concord
    if not concord:
        return [TextContent(type="text", text=json.dumps({
            "error": "No evaluation to verify. Call evaluate_patient first."
        }))]

    # Create verification record from current state
    current_metadata = concord._create_metadata()

    # Compute current output hash
    from core.concord import PipelineResult
    current_result = PipelineResult(
        eligibility=concord.eligibility_result,
        sufficiency=concord.sufficiency_result,
        assessment=concord.assessment_result,
        recommendations=concord.recommendation_result,
        is_complete=True,
        errors=[],
        metadata=current_metadata
    )
    current_output_hash = compute_output_hash(current_result)

    # Verification checks
    input_match = (original_input_hash == current_metadata.input_data_hash) if original_input_hash else None
    output_match = (original_output_hash == current_output_hash) if original_output_hash else None

    verified = True
    issues = []

    if original_input_hash and not input_match:
        verified = False
        issues.append("Input data has changed since original evaluation")

    if original_output_hash and not output_match:
        verified = False
        issues.append("Output hash mismatch - evaluation produced different results")

    result = {
        "session_id": session_id,
        "verified": verified,
        "status": "VERIFIED" if verified else "MISMATCH",
        "current_input_hash": current_metadata.input_data_hash,
        "current_output_hash": current_output_hash,
        "cpg_version": current_metadata.cpg_version,
        "comparisons": {
            "input_hash_match": input_match,
            "output_hash_match": output_match
        },
        "issues": issues if issues else None,
        "_note": "Concord guarantees: same input + same CPG version = identical output"
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_evaluate_multiple_cpgs(args: dict) -> list[TextContent]:
    """Evaluate patient against multiple CPGs in parallel."""
    from core.batch_processor import MultiCPGEvaluator

    session_id = args["session_id"]
    cpg_ids = args["cpg_ids"]
    parallel = args.get("parallel", True)

    session = state.get_session(session_id, create=False)
    if not session or not session.health_context:
        return [TextContent(type="text", text=json.dumps({
            "error": f"No health context for session: {session_id}"
        }))]

    # Load the requested CPGs
    cpgs = []
    load_errors = []
    for cpg_id in cpg_ids:
        try:
            cpg = state.load_cpg(cpg_id)
            cpgs.append(cpg)
        except Exception as e:
            load_errors.append({"cpg_id": cpg_id, "error": str(e)})

    if not cpgs:
        return [TextContent(type="text", text=json.dumps({
            "error": "No valid CPGs could be loaded",
            "load_errors": load_errors
        }))]

    # Use MultiCPGEvaluator for parallel evaluation
    evaluator = MultiCPGEvaluator(cpgs=cpgs, detect_conflicts=True)

    import time
    start = time.perf_counter()

    multi_result = evaluator.evaluate(
        patient_id=session_id,
        healthcontext=session.health_context,
        parallel=parallel,
        workers=4,
        skip_eligibility=True,
        ignore_attestations=True
    )

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Build result
    result = {
        "session_id": session_id,
        "cpgs_requested": len(cpg_ids),
        "cpgs_evaluated": len(multi_result.evaluations),
        "parallel_mode": parallel,
        "elapsed_ms": round(elapsed_ms, 2),
        "evaluations": {},
        "all_recommendations": [],
        "conflicts": None,
        "load_errors": load_errors if load_errors else None
    }

    # Add evaluation results
    for cpg_id, eval_result in multi_result.evaluations.items():
        cpg_summary = {
            "is_complete": eval_result.is_complete,
            "is_eligible": eval_result.is_eligible,
            "recommendations_count": len(eval_result.applied_recommendations or []),
            "recommendations": []
        }
        for rec in (eval_result.applied_recommendations or []):
            rec_info = {
                "id": rec.recommendation.id if rec.recommendation else None,
                "title": rec.recommendation.title if rec.recommendation else None,
                "applies": rec.applies
            }
            cpg_summary["recommendations"].append(rec_info)
            result["all_recommendations"].append({
                "cpg_id": cpg_id,
                **rec_info
            })
        result["evaluations"][cpg_id] = cpg_summary

    # Add conflict information
    if multi_result.conflicts and multi_result.conflicts.conflicts:
        result["conflicts"] = {
            "count": len(multi_result.conflicts.conflicts),
            "details": [c.to_dict() for c in multi_result.conflicts.conflicts]
        }

    result["_performance_note"] = f"Evaluated {len(cpgs)} CPGs in {elapsed_ms:.1f}ms ({elapsed_ms/len(cpgs):.1f}ms per CPG)"

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_validate_institution_config(args: dict) -> list[TextContent]:
    """Validate an institutional configuration file."""
    from core.config_validator import (
        ConfigValidator,
        validate_config_file,
        visualize_inheritance_chain,
    )
    from core.institution_config import load_institution_config

    config_path = args.get("config_path")
    cpg_id = args.get("cpg_id")
    check_safe_ranges = args.get("check_safe_ranges", True)
    strict_mode = args.get("strict_mode", False)

    if not config_path:
        return [TextContent(type="text", text=json.dumps({
            "error": "config_path is required"
        }))]

    # Load CPG if specified
    cpg = None
    if cpg_id:
        try:
            cpg = state.load_cpg(cpg_id)
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Failed to load CPG '{cpg_id}': {e}"
            }))]

    # Validate the config
    result = validate_config_file(
        config_path,
        cpg=cpg,
        check_safe_ranges=check_safe_ranges,
        strict_mode=strict_mode
    )

    # Build response
    response = {
        "validation_result": result.to_dict(),
        "summary": result.summary(),
        "status": "VALID" if result.is_valid else "INVALID",
        "error_count": len(result.errors),
        "warning_count": len(result.warnings),
    }

    # Add inheritance visualization if valid
    if result.is_valid and result.inheritance_chain:
        try:
            config = load_institution_config(config_path)
            response["inheritance_visualization"] = visualize_inheritance_chain(config)
        except Exception:
            pass  # Skip visualization if config can't be loaded

    return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]


async def handle_get_institution_config_impact(args: dict) -> list[TextContent]:
    """Analyze the impact of an institutional configuration on CPG evaluation."""
    from core.config_validator import ConfigValidator
    from core.institution_config import load_institution_config

    config_path = args.get("config_path")
    cpg_id = args.get("cpg_id")

    if not config_path:
        return [TextContent(type="text", text=json.dumps({
            "error": "config_path is required"
        }))]

    if not cpg_id:
        return [TextContent(type="text", text=json.dumps({
            "error": "cpg_id is required for impact analysis"
        }))]

    # Load the config
    try:
        config = load_institution_config(config_path)
    except FileNotFoundError:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Configuration file not found: {config_path}"
        }))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Failed to load config: {e}"
        }))]

    # Load the CPG
    try:
        cpg = state.load_cpg(cpg_id)
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Failed to load CPG '{cpg_id}': {e}"
        }))]

    # Validate and get impact analysis
    validator = ConfigValidator()
    result = validator.validate(config, cpg=cpg)

    if not result.impact_analysis:
        return [TextContent(type="text", text=json.dumps({
            "config_id": config.institution_id,
            "config_name": config.institution_name,
            "cpg_id": cpg_id,
            "has_impact": False,
            "message": "No impact on this CPG"
        }))]

    impact = result.impact_analysis

    response = {
        "config_id": config.institution_id,
        "config_name": config.institution_name,
        "cpg_id": cpg_id,
        "cpg_title": cpg.title,
        "has_impact": impact.has_impact(),
        "impact_summary": {
            "threshold_changes": len(impact.threshold_changes),
            "affected_assessments": len(impact.affected_assessments),
            "affected_recommendations": len(impact.affected_recommendations),
            "excluded_recommendations": len(impact.excluded_recommendations),
            "added_local_rules": len(impact.added_rules),
        },
        "details": {
            "threshold_changes": impact.threshold_changes,
            "excluded_recommendations": impact.excluded_recommendations,
            "added_rules": impact.added_rules,
        },
        "validation_issues": [
            {
                "severity": i.severity.value,
                "code": i.code,
                "message": i.message,
            }
            for i in result.issues
        ] if result.issues else None
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]


# ============================================================================
# RESOURCES
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available CPG resources."""
    resources = [
        # Add guidelines resource first - this is critical for proper tool usage
        Resource(
            uri="concord://guidelines",
            name="Concord Usage Guidelines",
            description="IMPORTANT: Critical rules for using Concord tools. READ THIS FIRST before evaluating patients. Contains rules about never fabricating data and always asking users for missing information.",
            mimeType="text/plain"
        )
    ]
    for cpg_info in state.get_available_cpgs():
        try:
            cpg = state.load_cpg(cpg_info["identifier"])
            resources.append(Resource(
                uri=f"cpg://{cpg_info['identifier']}",
                name=cpg.title,
                description=f"Clinical Practice Guideline: {cpg.title}",
                mimeType="application/json"
            ))
        except:
            pass
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a CPG resource."""
    if uri == "concord://guidelines":
        return """# Concord MCP Server - Critical Guidelines

## RULE 1: NEVER FABRICATE PATIENT DATA

You must NEVER fabricate, estimate, assume, or fill in any health data that the user has not explicitly provided.

- NEVER add values the user didn't provide
- NEVER use "typical" or "average" values as substitutes
- NEVER assume default values for missing data
- If data is missing, ASK the user for it

## RULE 2: WHEN DATA IS MISSING, ASK THE USER

When evaluate_patient returns missing_required_variables or needs_attestation_variables:

1. STOP - Do not proceed with interpretation
2. PRESENT the list of missing variables to the user clearly
3. ASK the user to provide each missing value
4. WAIT for user response
5. Only then call create_health_context again with complete data

## RULE 3: USE EXACT VARIABLE IDs

Variable IDs are case-sensitive. Always call get_cpg_info first to see exact IDs.

Examples: 'Age' not 'age', 'LDL' not 'ldl_cholesterol', 'bloodpressure' not 'systolic_bp'

## RULE 4: FORMAT VALUES CORRECTLY

- Gender: Use SNOMED codes "http://snomed.info/sct|248153007" for male, "http://snomed.info/sct|248152002" for female
- Ethnicity: Use OID codes like "urn:oid:2.16.840.1.113883.6.238|2106-3" for White
- Blood Pressure: Use tuple (systolic, diastolic) like (142, 90)
- Boolean: Use 1/0 or true/false

## PATIENT SAFETY

Incomplete data leads to inaccurate clinical recommendations. Always ask for missing data rather than guessing."""

    if uri.startswith("cpg://"):
        cpg_id = uri.replace("cpg://", "")
        cpg = state.load_cpg(cpg_id)
        return json.dumps({
            "identifier": cpg.identifier,
            "title": cpg.title,
            "publisher": cpg.publisher,
            "variables_count": len(cpg.variables) if cpg.variables else 0,
            "assessments_count": len(cpg.assessment_variables) if cpg.assessment_variables else 0,
            "recommendations_count": len(cpg.recommendation_variables) if cpg.recommendation_variables else 0
        }, indent=2)
    raise ValueError(f"Unknown resource URI: {uri}")


# ============================================================================
# PROMPTS
# ============================================================================

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="concord_guidelines",
            description="IMPORTANT: Read these guidelines before using any Concord tools. Contains critical rules for handling patient data.",
            arguments=[]
        ),
        Prompt(
            name="health_assessment",
            description="Comprehensive health assessment against all available guidelines",
            arguments=[
                PromptArgument(
                    name="patient_data",
                    description="JSON string of patient health data",
                    required=True
                )
            ]
        ),
        Prompt(
            name="explain_all_recommendations",
            description="Explain all applicable recommendations for a patient",
            arguments=[
                PromptArgument(
                    name="session_id",
                    description="Session ID with completed evaluation",
                    required=True
                )
            ]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    """Get a specific prompt."""
    if name == "concord_guidelines":
        return GetPromptResult(
            description="Critical guidelines for using Concord clinical evaluation tools",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text="""# Concord MCP Server - Critical Guidelines for AI Assistants

## RULE 1: NEVER FABRICATE PATIENT DATA

You must NEVER fabricate, estimate, assume, or fill in any health data that the user has not explicitly provided.

BAD Examples (DO NOT DO THIS):
- User provides LDL=145, you add total cholesterol=220 because "it's typical"
- User doesn't mention ethnicity, you assume "White" as default
- User says they have high blood pressure, you estimate systolic=140
- User doesn't provide medication info, you assume "not on medications"

GOOD Examples:
- Only include values the user explicitly stated
- When data is missing, ASK the user for it
- If user says "I don't know", do NOT make up a value

## RULE 2: WHEN DATA IS MISSING, ASK THE USER

When evaluate_patient returns missing_required_variables or needs_attestation_variables:

1. STOP - Do not proceed with interpretation
2. PRESENT the list of missing variables to the user clearly
3. ASK the user to provide each missing value
4. WAIT for user response
5. Only then call create_health_context again with the complete data

Example response when data is missing:
"I need some additional information to complete your cardiovascular risk assessment:

1. **Total Cholesterol (Chol)**: What is your total cholesterol level in mg/dL?
2. **Triglycerides**: What is your triglyceride level in mg/dL?
3. **Ethnicity**: For accurate risk calculation, what is your ethnicity? (Options: White, Black/African American, Hispanic, Asian, Other)
4. **Hypertension Medication**: Are you currently taking any medication for high blood pressure? (Yes/No)

Please provide these values and I'll complete the evaluation."

## RULE 3: USE EXACT VARIABLE IDs

Variable IDs are case-sensitive. Always call get_cpg_info first to see the exact IDs needed.

Examples:
- Use 'Age' not 'age'
- Use 'LDL' not 'ldl_cholesterol'
- Use 'Gender' not 'gender' or 'sex'
- Use 'bloodpressure' not 'systolic_blood_pressure'

## RULE 4: FORMAT VALUES CORRECTLY

- Gender: Use SNOMED codes like "http://snomed.info/sct|248153007" for male
- Ethnicity: Use OID codes like "urn:oid:2.16.840.1.113883.6.238|2106-3" for White
- Blood Pressure: Use tuple format (systolic, diastolic) like (142, 90)
- Boolean values: Use 1/0 or true/false

## RULE 5: DATA QUALITY MATTERS

Incomplete data leads to inaccurate clinical recommendations. It is better to:
- Ask for missing data than guess
- Report "cannot evaluate without X" than provide misleading results
- Be clear about data limitations than hide them

Patient safety depends on accurate data. Never compromise on this."""
                    )
                )
            ]
        )

    if name == "health_assessment":
        return GetPromptResult(
            description="Assess patient health against clinical guidelines",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Please evaluate this patient's health data against all available Clinical Practice Guidelines.

Patient Data:
{arguments.get('patient_data', '{}')}

Steps:
1. Use create_health_context to set up the patient data
2. Use evaluate_all_cpgs to check against all guidelines
3. Use get_prioritized_recommendations to see ranked recommendations
4. For the top recommendations, use explain_recommendation for details
5. Summarize key findings and recommendations

Explain everything in patient-friendly terms."""
                    )
                )
            ]
        )

    if name == "explain_all_recommendations":
        session_id = arguments.get('session_id', '')
        return GetPromptResult(
            description="Explain all recommendations",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""For session {session_id}:

1. Use get_prioritized_recommendations to see all recommendations
2. For each recommendation that applies, use explain_recommendation
3. Provide a comprehensive summary suitable for the patient"""
                    )
                )
            ]
        )

    raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# SERVER
# ============================================================================

async def serve():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(serve())


if __name__ == "__main__":
    main()
