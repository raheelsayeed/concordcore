#!/usr/bin/env python3
"""ConcordCore API Server.

Complete REST API for CPG discovery, evaluation, screening,
reproducibility verification, and FHIR data ingestion.

Run with: uvicorn apps.api.server:app --reload --port 8080
"""

import time
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

from concordcore.core.cpg import CPG
from concordcore.core.cpg_registry import get_registry
from concordcore.core.concord import Concord
from concordcore.core.healthcontext import HealthContext
from concordcore.core.batch_processor import MultiCPGEvaluator, PatientScreener
from concordcore.core.reproducibility import compute_output_hash, ReproducibilityVerifier
from concordcore.formats.fhir_adapter import FHIRAdapter
from concordcore.primitives.types import Persona

log = logging.getLogger(__name__)

app = FastAPI(
    title="ConcordCore API",
    description="Clinical Practice Guideline evaluation engine",
    version="1.0.0",
)

_registry = get_registry()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class HealthDataInput(BaseModel):
    health_data: list[dict] = Field(
        default_factory=list,
        description="List of {variable_id, value, unit?, date?} dicts",
    )
    persona: str = Field(
        default="provider",
        description="Narrative persona: patient | provider | guardian",
    )


class EvaluateRequest(HealthDataInput):
    cpg_id: str


class MultiEvaluateRequest(HealthDataInput):
    cpg_ids: list[str]
    parallel: bool = True


class VerifyRequest(HealthDataInput):
    cpg_id: str
    verification_record: dict


class FHIRRequest(BaseModel):
    cpg_id: str
    fhir_bundle: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_cpg(cpg_id: str) -> CPG:
    try:
        return _registry.get(cpg_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"CPG not found: {cpg_id}")


def _build_context(req: HealthDataInput) -> HealthContext:
    data: dict[str, Any] = {}
    for item in req.health_data:
        vid = item.get("variable_id")
        val = item.get("value")
        if vid is not None and val is not None:
            # Accumulate multiple values for the same variable as a list
            if vid in data:
                existing = data[vid]
                if isinstance(existing, list):
                    existing.append(val)
                else:
                    data[vid] = [existing, val]
            else:
                data[vid] = val
    persona = Persona(req.persona) if req.persona in ("patient", "provider", "guardian") else Persona.provider
    return HealthContext.from_dict(data, persona=persona)


def _format_var(v) -> dict:
    """Serialize a Var to a dict."""
    codes = []
    if v.code:
        for c in v.code:
            codes.append({"system": c.system.value if hasattr(c.system, "value") else str(c.system),
                          "code": c.code, "display": c.display})
    return {
        "id": v.id,
        "title": v.title,
        "description": v.description,
        "type": str(v.type) if v.type else None,
        "category": str(v.category) if v.category else None,
        "required": v.required,
        "user_attestable": v.user_attestable,
        "question": v.question,
        "llm_prompt": getattr(v, "llm_prompt", None),
        "codes": codes if codes else None,
    }


def _format_eligibility_var(ev) -> dict:
    d = _format_var(ev)
    d["expression"] = ev.expression
    d["criteria_type"] = str(ev.criteria_type) if ev.criteria_type else None
    return d


def _format_assessment_var(av) -> dict:
    d = _format_var(av)
    d["expression"] = av.expression
    d["show_if_negative"] = av.show_if_negative
    return d


def _format_recommendation_var(rv) -> dict:
    d = _format_var(rv)
    d["expression"] = rv.expression
    d["class_of_recommendation"] = str(rv.class_of_recommendation) if rv.class_of_recommendation else None
    d["level_of_evidence"] = str(rv.level_of_evidence) if rv.level_of_evidence else None
    d["uspstf_grade"] = rv.uspstf_grade.value if rv.uspstf_grade else None
    d["compliance_expression"] = rv.compliance_expression
    return d


def _format_cpg(cpg: CPG) -> dict:
    """Full CPG detail."""
    return {
        "identifier": cpg.identifier,
        "title": cpg.title,
        "description": cpg.description,
        "publisher": cpg.publisher,
        "version": cpg.version,
        "doi": cpg.doi,
        "source_url": cpg.source_url,
        "last_updated": cpg.last_updated,
        "category": cpg.category,
        "variables": [_format_var(v) for v in (cpg.variables or [])],
        "eligibility_criteria": [_format_eligibility_var(ev) for ev in (cpg.eligibility_variables or [])],
        "assessments": [_format_assessment_var(av) for av in (cpg.assessment_variables or [])],
        "recommendations": [_format_recommendation_var(rv) for rv in (cpg.recommendation_variables or [])],
    }


def _format_pipeline(pipeline, cpg: CPG) -> dict:
    """Serialize a PipelineResult into a JSON-safe dict."""
    result: dict[str, Any] = {
        "cpg_id": cpg.identifier,
        "cpg_title": cpg.title,
        "is_complete": pipeline.is_complete,
        "is_eligible": pipeline.is_eligible,
        "is_executable": pipeline.is_executable,
    }

    # Eligibility
    if pipeline.eligibility:
        elig = pipeline.eligibility
        result["eligibility"] = {
            "is_eligible": elig.is_eligible,
            "criteria": [
                {
                    "variable_id": ev.record.id,
                    "title": ev.record.var.title,
                    "result": str(ev.evaluation_result.name),
                    "has_value": ev.record.has_value,
                }
                for ev in elig.context.evaluation_list
            ],
        }

    # Sufficiency
    if pipeline.sufficiency:
        suff = pipeline.sufficiency
        missing = []
        attestable = []
        for ev in suff.context.evaluation_list:
            if not ev.record.has_value:
                entry = {"variable_id": ev.record.id, "title": ev.record.var.title,
                         "required": ev.record.var.required}
                if ev.record.var.user_attestable:
                    attestable.append(entry)
                else:
                    missing.append(entry)
        result["sufficiency"] = {
            "is_executable": suff.is_executable,
            "status": suff.result.name,
            "missing_variables": missing,
            "attestable_variables": attestable,
        }

    # Assessments
    if pipeline.assessment:
        result["assessments"] = [
            {
                "variable_id": a.id,
                "title": a.var.title,
                "expression": a.var.expression,
                "value": _safe_value(a.value),
                "result": a.evaluation_result.name,
                "narrative": a.narrative,
            }
            for a in pipeline.assessment.assessments
        ]

    # Recommendations
    if pipeline.recommendations:
        result["recommendations"] = [
            {
                "id": r.recommendation.id,
                "title": r.recommendation.title,
                "description": r.recommendation.description,
                "applies": r.applies,
                "compliant": r.compliant,
                "narrative": r.narrative,
                "compliance_narrative": r.compliance_narrative,
                "class_of_recommendation": str(r.recommendation.class_of_recommendation) if r.recommendation.class_of_recommendation else None,
                "level_of_evidence": str(r.recommendation.level_of_evidence) if r.recommendation.level_of_evidence else None,
                "uspstf_grade": r.recommendation.uspstf_grade.value if r.recommendation.uspstf_grade else None,
            }
            for r in pipeline.recommendations.recommendations
        ]

    # Metadata
    if pipeline.metadata:
        result["metadata"] = pipeline.metadata.to_dict()

    # Errors
    if pipeline.errors:
        result["errors"] = [str(e) for e in pipeline.errors]

    return result


def _safe_value(v) -> Any:
    """Convert a Value object to a JSON-safe primitive."""
    if v is None:
        return None
    val = v.value if hasattr(v, "value") else v
    if isinstance(val, (bool, int, float, str)):
        return val
    return str(val)


# ---------------------------------------------------------------------------
# GET — Discovery endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>ConcordCore API</h1><p>index.html not found</p>")


@app.get("/api/cpgs")
async def list_cpgs(
    code: str | None = Query(default=None, description="Filter by variable code. Format: code or system|code (e.g. 18262-6 or http://loinc.org|18262-6)"),
):
    """List all CPGs grouped by category. Optionally filter by variable code."""
    if code:
        # Parse system|code format
        if "|" in code:
            system, code_value = code.split("|", 1)
        else:
            system, code_value = None, code

        # Find CPGs whose variables match the code
        all_vars = _registry.variables()
        # Collect matching cpg identifiers (deduplicated, preserving order)
        matched_cpg_ids: dict[str, list[dict]] = {}  # cpg_id -> [variable matches]
        for cpg_var in all_vars:
            v = cpg_var.var
            if not v.code:
                continue
            for c in v.code:
                if c.code == code_value and (system is None or c.system == system):
                    for cpg_id in cpg_var.cpg_identifiers:
                        matched_cpg_ids.setdefault(cpg_id, []).append({
                            "variable_id": v.id,
                            "variable_title": v.title,
                            "code": c.code,
                            "system": c.system,
                            "display": c.display,
                        })
                    break

        cpgs = []
        for cpg_id, variables in matched_cpg_ids.items():
            entry = _registry.entry(cpg_id)
            cpg_dict = entry.as_dict()
            cpg_dict["matched_variables"] = variables
            cpgs.append(cpg_dict)

        return {"code": code, "cpgs": cpgs, "count": len(cpgs)}

    # Default: list all grouped by category
    by_cat = _registry.list_by_category()
    categories = {}
    for cat, entries in by_cat.items():
        categories[cat] = [e.as_dict() for e in entries]
    return {"categories": categories, "total_count": sum(len(v) for v in categories.values())}


@app.get("/api/cpgs/{cpg_id}")
async def get_cpg_detail(cpg_id: str):
    """Full CPG detail: variables, eligibility, assessments, recommendations."""
    cpg = _load_cpg(cpg_id)
    return _format_cpg(cpg)


@app.get("/api/variables")
async def list_variables(cpg_ids: str | None = Query(default=None, description="Comma-separated CPG identifiers")):
    """Cross-CPG variable index."""
    ids = [s.strip() for s in cpg_ids.split(",") if s.strip()] if cpg_ids else None
    try:
        variables = _registry.variables(ids)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"variables": [v.as_dict() for v in variables], "count": len(variables)}


# ---------------------------------------------------------------------------
# POST — Evaluation endpoints
# ---------------------------------------------------------------------------

@app.post("/api/screen")
async def screen_patient(req: HealthDataInput):
    """Screen patient against all CPGs."""
    ctx = _build_context(req)
    screener = PatientScreener()
    result = screener.screen(health_context=ctx)

    cpg_results = []
    for r in result.results:
        entry: dict[str, Any] = {
            "cpg_id": r.cpg_id,
            "cpg_title": r.cpg_title,
            "is_eligible": r.is_eligible,
            "is_executable": r.is_executable,
            "error": r.error,
        }
        cpg_results.append(entry)

    coverage = {
        "total_unique_variables": result.coverage.total_unique_variables,
        "provided_variables": result.coverage.provided_variables,
        "missing_variables": result.coverage.missing_variables,
        "gaps": [
            {
                "variable_id": g.variable_id,
                "variable_title": g.variable_title,
                "cpg_ids": list(g.cpg_ids),
                "is_required": g.is_required,
                "is_attestable": g.is_attestable,
                "impact_score": g.impact_score,
            }
            for g in result.coverage.gaps
        ],
    }

    return {
        "eligible_count": result.eligible_count,
        "executable_count": result.executable_count,
        "total_cpgs": result.total_cpgs,
        "elapsed_ms": round(result.elapsed_ms, 2),
        "results": cpg_results,
        "coverage": coverage,
    }


@app.post("/api/evaluate")
async def evaluate_cpg(req: EvaluateRequest):
    """Full single-CPG pipeline evaluation."""
    cpg = _load_cpg(req.cpg_id)
    ctx = _build_context(req)

    start = time.perf_counter()
    concord = Concord(cpg=cpg, healthcontext=ctx)
    pipeline = concord.evaluate(ignore_attestations=True)
    elapsed_ms = (time.perf_counter() - start) * 1000

    output_hash = compute_output_hash(pipeline)

    # Build verification record for later use
    verifier = ReproducibilityVerifier(cpg)
    verification_record = verifier.create_verification_record(pipeline, ctx)

    result = _format_pipeline(pipeline, cpg)
    result["elapsed_ms"] = round(elapsed_ms, 2)
    result["output_hash"] = output_hash
    result["verification_record"] = verification_record
    return result


@app.post("/api/evaluate/multi")
async def evaluate_multi_cpg(req: MultiEvaluateRequest):
    """Multi-CPG parallel evaluation with conflict detection."""
    if not req.cpg_ids:
        raise HTTPException(status_code=400, detail="No CPG IDs specified")

    cpgs = [_load_cpg(cid) for cid in req.cpg_ids]
    ctx = _build_context(req)

    evaluator = MultiCPGEvaluator(cpgs=cpgs, detect_conflicts=True)

    start = time.perf_counter()
    result = evaluator.evaluate(
        patient_id="api_patient",
        healthcontext=ctx,
        parallel=req.parallel,
        ignore_attestations=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    evaluations = {}
    for cpg_id, pipeline in result.evaluations.items():
        cpg = _load_cpg(cpg_id)
        evaluations[cpg_id] = _format_pipeline(pipeline, cpg)

    conflicts = result.conflicts.to_dict() if result.conflicts else None

    return {
        "cpgs_evaluated": len(req.cpg_ids),
        "parallel": req.parallel,
        "elapsed_ms": round(elapsed_ms, 2),
        "evaluations": evaluations,
        "conflicts": conflicts,
    }


@app.post("/api/verify")
async def verify_evaluation(req: VerifyRequest):
    """Reproducibility verification."""
    cpg = _load_cpg(req.cpg_id)
    ctx = _build_context(req)

    verifier = ReproducibilityVerifier(cpg)
    vresult = verifier.verify(
        original_record=req.verification_record,
        healthcontext=ctx,
        ignore_attestations=True,
    )
    return vresult.to_dict()


@app.post("/api/fhir/to-records")
async def fhir_to_records(req: FHIRRequest):
    """Parse FHIR bundle into CPG variable records."""
    cpg = _load_cpg(req.cpg_id)
    adapter = FHIRAdapter()
    records = adapter.parse_bundle_to_records(req.fhir_bundle, cpg.variables or [])

    return {
        "cpg_id": cpg.identifier,
        "records": [
            {
                "variable_id": r.id,
                "title": r.var.title,
                "values": [
                    {
                        "value": _safe_value(v),
                        "date": str(v.date) if v.date else None,
                        "code": v.code.as_string if hasattr(v, "code") and v.code else None,
                    }
                    for v in (r.values or [])
                ],
            }
            for r in records
        ],
        "count": len(records),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
