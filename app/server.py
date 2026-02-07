#!/usr/bin/env python3
"""Multi-CPG Demo Application Server.

A FastAPI-based web application demonstrating Concord's multi-CPG evaluation
capabilities including:
- Parallel evaluation against multiple CPGs
- Conflict detection
- Performance benchmarking
- Reproducibility verification

Run with: uvicorn app.server:app --reload --port 8080
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from core.cpg import CPG
from core.concord import Concord
from core.healthcontext import HealthContext
from core.batch_processor import MultiCPGEvaluator, BatchProcessor, ProcessingMode
from core.reproducibility import compute_output_hash
from core.benchmarks import BenchmarkRunner, estimate_llm_cost
from primitives.types import Persona
from variables.value import Value
from misc import sample_healthcontext

app = FastAPI(
    title="Concord Multi-CPG Demo",
    description="Demonstration of parallel multi-CPG evaluation",
    version="1.0.0",
)

# CPG cache
_cpg_cache: dict[str, CPG] = {}
_cpg_dir = Path(__file__).parent.parent / "cpgs"


def get_cpg(cpg_id: str) -> CPG:
    """Get or load a CPG by ID."""
    if cpg_id not in _cpg_cache:
        cpg_path = _cpg_dir / f"{cpg_id}.yaml"
        if not cpg_path.exists():
            raise HTTPException(status_code=404, detail=f"CPG not found: {cpg_id}")
        _cpg_cache[cpg_id] = CPG.from_document_path(str(cpg_path))
    return _cpg_cache[cpg_id]


def get_available_cpgs() -> list[dict]:
    """Get list of available CPGs."""
    cpgs = []
    for path in sorted(_cpg_dir.glob("*.yaml")):
        try:
            cpg = get_cpg(path.stem)
            cpgs.append({
                "id": cpg.identifier,
                "title": cpg.title,
                "version": cpg.version,
                "variables_count": len(cpg.variables or []),
                "assessments_count": len(cpg.assessment_variables or []),
                "recommendations_count": len(cpg.recommendation_variables or []),
            })
        except Exception:
            pass
    return cpgs


# Request/Response models
class PatientData(BaseModel):
    age: int = 55
    gender: str = "male"
    ldl: float = 145
    hdl: float = 38
    total_cholesterol: float = 220
    triglycerides: float = 185
    systolic_bp: int = 142
    diastolic_bp: int = 90
    has_diabetes: bool = True
    has_hypertension: bool = True
    is_smoker: bool = True
    on_statin: bool = False


class MultiCPGRequest(BaseModel):
    cpg_ids: list[str]
    patient: PatientData
    parallel: bool = True


class BenchmarkRequest(BaseModel):
    cpg_ids: list[str] = None
    iterations: int = 20
    patient_counts: list[int] = [10, 50, 100]


# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the demo UI."""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>Multi-CPG Demo</h1><p>index.html not found</p>")


@app.get("/api/cpgs")
async def list_cpgs():
    """List all available CPGs."""
    return {"cpgs": get_available_cpgs()}


@app.get("/api/cpg/{cpg_id}")
async def get_cpg_details(cpg_id: str):
    """Get details of a specific CPG."""
    cpg = get_cpg(cpg_id)
    return {
        "id": cpg.identifier,
        "title": cpg.title,
        "version": cpg.version,
        "publisher": cpg.publisher,
        "variables": [{"id": v.id, "title": v.title} for v in (cpg.variables or [])],
        "assessments": [{"id": v.id, "title": v.title} for v in (cpg.assessment_variables or [])],
        "recommendations": [{"id": v.id, "title": v.title} for v in (cpg.recommendation_variables or [])],
    }


@app.post("/api/evaluate/single")
async def evaluate_single_cpg(cpg_id: str, patient: PatientData):
    """Evaluate a single CPG."""
    cpg = get_cpg(cpg_id)
    hc = _create_health_context(patient)

    start = time.perf_counter()
    concord = Concord(cpg=cpg, healthcontext=hc)
    result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "cpg_id": cpg_id,
        "cpg_title": cpg.title,
        "elapsed_ms": round(elapsed_ms, 2),
        "is_complete": result.is_complete,
        "is_eligible": result.is_eligible,
        "recommendations": _format_recommendations(result),
        "output_hash": compute_output_hash(result),
    }


@app.post("/api/evaluate/multi")
async def evaluate_multi_cpg(request: MultiCPGRequest):
    """Evaluate multiple CPGs in parallel."""
    if not request.cpg_ids:
        raise HTTPException(status_code=400, detail="No CPGs specified")

    cpgs = [get_cpg(cpg_id) for cpg_id in request.cpg_ids]
    hc = _create_health_context(request.patient)

    evaluator = MultiCPGEvaluator(cpgs=cpgs, detect_conflicts=True)

    start = time.perf_counter()
    result = evaluator.evaluate(
        patient_id="demo_patient",
        healthcontext=hc,
        parallel=request.parallel,
        workers=4,
        skip_eligibility=True,
        ignore_attestations=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Format results
    evaluations = {}
    all_recommendations = []

    for cpg_id, eval_result in result.evaluations.items():
        cpg = get_cpg(cpg_id)
        recs = _format_recommendations(eval_result)
        evaluations[cpg_id] = {
            "title": cpg.title,
            "is_complete": eval_result.is_complete,
            "is_eligible": eval_result.is_eligible,
            "recommendations": recs,
            "recommendations_count": len(recs),
        }
        for rec in recs:
            rec["cpg_id"] = cpg_id
            rec["cpg_title"] = cpg.title
            all_recommendations.append(rec)

    conflicts = None
    if result.conflicts and result.conflicts.conflicts:
        conflicts = [c.to_dict() for c in result.conflicts.conflicts]

    # Compare with LLM estimate
    llm_cost, llm_time = estimate_llm_cost("claude_sonnet", len(request.cpg_ids))

    return {
        "cpgs_evaluated": len(request.cpg_ids),
        "parallel_mode": request.parallel,
        "elapsed_ms": round(elapsed_ms, 2),
        "evaluations": evaluations,
        "all_recommendations": all_recommendations,
        "conflicts": conflicts,
        "comparison": {
            "concord_time_ms": round(elapsed_ms, 2),
            "llm_estimated_time_ms": llm_time,
            "speedup": round(llm_time / elapsed_ms, 1) if elapsed_ms > 0 else 0,
            "llm_estimated_cost_usd": round(llm_cost, 4),
        },
    }


@app.post("/api/benchmark")
async def run_benchmark(request: BenchmarkRequest):
    """Run performance benchmarks."""
    runner = BenchmarkRunner(cpg_dir=str(_cpg_dir))

    cpg_ids = request.cpg_ids
    if not cpg_ids:
        cpg_ids = [c["id"] for c in get_available_cpgs()[:3]]

    results = {
        "timestamp": datetime.now().isoformat(),
        "single_cpg": [],
        "batch": [],
        "multi_cpg": [],
    }

    # Single CPG benchmarks
    for cpg_id in cpg_ids:
        try:
            bench = runner.benchmark_single_cpg(cpg_id, iterations=request.iterations)
            results["single_cpg"].append({
                "cpg_id": cpg_id,
                "iterations": bench.iterations,
                "avg_ms": round(bench.avg_ms, 3),
                "p95_ms": round(bench.p95_ms, 3),
                "p99_ms": round(bench.p99_ms, 3),
                "evaluations_per_second": round(bench.evaluations_per_second, 1),
            })
        except Exception as e:
            results["single_cpg"].append({"cpg_id": cpg_id, "error": str(e)})

    # Batch benchmarks
    if cpg_ids:
        try:
            batch_results = runner.benchmark_batch_processing(
                cpg_ids[0],
                patient_counts=request.patient_counts,
                modes=["sequential", "thread_pool"],
            )
            for br in batch_results:
                results["batch"].append({
                    "patient_count": br.patient_count,
                    "mode": br.mode,
                    "total_ms": round(br.total_ms, 2),
                    "patients_per_second": round(br.patients_per_second, 1),
                })
        except Exception as e:
            results["batch"].append({"error": str(e)})

    # Multi-CPG benchmarks
    if len(cpg_ids) >= 2:
        try:
            for parallel in [True, False]:
                multi_result = runner.benchmark_multi_cpg(cpg_ids, parallel=parallel)
                results["multi_cpg"].append({
                    "cpg_count": multi_result.cpg_count,
                    "parallel": multi_result.parallel,
                    "total_ms": round(multi_result.total_ms, 2),
                    "cpgs_per_second": round(multi_result.cpgs_per_second, 1),
                })
        except Exception as e:
            results["multi_cpg"].append({"error": str(e)})

    return results


@app.get("/api/sample-patient")
async def get_sample_patient():
    """Get sample patient data."""
    return PatientData().dict()


def _create_health_context(patient: PatientData) -> HealthContext:
    """Create a health context from patient data."""
    hc = sample_healthcontext()

    # Update with provided values
    def set_value(var_id: str, value: Any):
        for record in hc.records:
            if record.var.id == var_id:
                record._values = [Value(value=value)]
                return

    set_value("Age", patient.age)
    set_value("LDL", patient.ldl)
    set_value("HDL", patient.hdl)
    set_value("Chol", patient.total_cholesterol)
    set_value("Trig", patient.triglycerides)
    set_value("diabetesMellitus", 1 if patient.has_diabetes else 0)
    set_value("htn", 1 if patient.has_hypertension else 0)
    set_value("is_smoker", 1 if patient.is_smoker else 0)
    set_value("on_statin", 1 if patient.on_statin else 0)

    return hc


def _format_recommendations(result) -> list[dict]:
    """Format recommendations from evaluation result."""
    recs = []
    for rec in (result.applied_recommendations or []):
        if rec.applies:
            rec_var = rec.recommendation
            recs.append({
                "id": rec_var.id if rec_var else None,
                "title": rec_var.title if rec_var else None,
                "applies": rec.applies,
            })
    return recs


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
