#!/usr/bin/env python3
"""Main view — sidebar patient navigation + clinical guideline evaluation."""

import re
import streamlit as st
from app_multicpg.services import MultiCPGService, PriorityRanker
from app_multicpg.styles import COLORS
from app_multicpg.data import get_patient_health_context, SAMPLE_PATIENTS

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from concordcore.primitives import Persona
from concordcore.core.cpg_registry import get_registry


def _html(text: str) -> None:
    """Render HTML via st.markdown, stripping blank lines to prevent parser breakage."""
    clean = re.sub(r'\n\s*\n', '\n', text.strip())
    st.markdown(clean, unsafe_allow_html=True)


def render_main_view():
    """Main render function."""
    _init_services()
    _render_sidebar()

    pid = st.session_state.get("active_patient")

    # Clear results when patient changes
    prev = st.session_state.get("_prev_patient")
    if pid != prev:
        st.session_state.pop("results", None)
        st.session_state.pop("show_results", None)
        st.session_state._prev_patient = pid

    if st.session_state.get("show_results") and "results" in st.session_state:
        _page_results()
    elif pid:
        _page_screening(pid)
    else:
        _page_welcome()


def _init_services():
    if "evaluator" not in st.session_state:
        st.session_state.evaluator = MultiCPGService(detect_conflicts=True)
    if "ranker" not in st.session_state:
        st.session_state.ranker = PriorityRanker()


# ─── Sidebar ─────────────────────────────────────────────────────────


def _render_sidebar():
    """Sidebar: brand + patient selection + patient context."""
    with st.sidebar:
        _html('<div class="sidebar-brand">concord</div>')
        _html('<p class="sidebar-section-label">Patients</p>')

        current = st.session_state.get("active_patient")

        for pid, p in SAMPLE_PATIENTS.items():
            is_active = pid == current
            if st.button(
                p["name"],
                key=f"pat_{pid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if pid != current:
                    st.session_state.active_patient = pid
                    st.rerun()

        # Patient context when a patient is selected
        if current and current in SAMPLE_PATIENTS:
            _render_sidebar_context(current)


def _render_sidebar_context(patient_id: str):
    """Render patient demographics + key metrics in sidebar."""
    p = SAMPLE_PATIENTS[patient_id]
    pdata = p["data"]

    _html('<div class="sidebar-divider"></div>')

    # Demographics
    parts = [f'{p["age"]}y {p["gender"]}']
    eth = pdata.get("Ethnicity")
    if eth:
        parts.append(eth)
    _html(f'<p class="sidebar-demo">{" · ".join(parts)}</p>')

    # Conditions
    conditions = []
    if pdata.get("htn"):
        conditions.append("HTN")
    if pdata.get("diabetesMellitus"):
        conditions.append("DM")
    if pdata.get("is_smoker"):
        conditions.append("Smoker")
    if pdata.get("former_smoker") and not pdata.get("is_smoker"):
        conditions.append("Former smoker")
    if pdata.get("FamilyHxPrematureASCVD"):
        conditions.append("FHx ASCVD")
    if conditions:
        _html(f'<p class="sidebar-conditions">{" · ".join(conditions)}</p>')

    # Medications
    meds = []
    if pdata.get("med_statins"):
        meds.append("Statins")
    if pdata.get("med_for_htn"):
        meds.append("Antihypertensives")
    if meds:
        _html(f'<p class="sidebar-meds">Rx: {", ".join(meds)}</p>')

    # Key metrics
    _html('<div class="sidebar-divider"></div>')
    _html('<p class="sidebar-section-label">Metrics</p>')

    metrics = _build_metrics(pdata)
    for label, value, cls in metrics:
        _html(f'''
            <div class="sidebar-metric-row">
                <span class="sidebar-metric-label">{label}</span>
                <span class="sidebar-metric-value {cls}">{value}</span>
            </div>
        ''')


def _build_metrics(pdata: dict) -> list[tuple[str, str, str]]:
    """Build key metric tuples (label, value, css_class)."""
    metrics = []

    ldl = pdata.get("LDL")
    if ldl:
        v = ldl[0] if isinstance(ldl, list) else ldl
        metrics.append(("LDL", f"{v} mg/dL", "high" if v > 160 else ("normal" if v < 130 else "")))

    hdl = pdata.get("HDL")
    if hdl is not None:
        metrics.append(("HDL", f"{hdl} mg/dL", "low" if hdl < 40 else "normal"))

    bp = pdata.get("bloodpressure")
    if bp and bp[0]:
        cls = "high" if bp[0] >= 140 or bp[1] >= 90 else "normal"
        metrics.append(("BP", f"{bp[0]}/{bp[1]}", cls))

    hba1c = pdata.get("HbA_one_c")
    if hba1c is not None:
        cls = "high" if hba1c >= 6.5 else ("low" if hba1c >= 5.7 else "normal")
        metrics.append(("A1c", f"{hba1c}%", cls))

    bmi = pdata.get("BMI")
    if bmi is not None:
        cls = "high" if bmi >= 30 else ("low" if bmi >= 25 else "normal")
        metrics.append(("BMI", str(bmi), cls))

    egfr = pdata.get("eGFR")
    if egfr is not None:
        metrics.append(("eGFR", str(egfr), "low" if egfr < 60 else "normal"))

    return metrics


# ─── Welcome Page ─────────────────────────────────────────────────────


def _page_welcome():
    """Welcome state — no patient selected."""
    _html('<div style="height: 25vh;"></div>')
    _, center, _ = st.columns([1, 2, 1])
    with center:
        _html('''
            <div style="text-align: center;">
                <div class="brand">concord</div>
                <p class="page-desc">Select a patient to begin clinical guideline evaluation.</p>
            </div>
        ''')


# ─── Screening Page ──────────────────────────────────────────────────


def _page_screening(patient_id: str):
    """Show applicable CPGs for the selected patient."""
    patient = SAMPLE_PATIENTS[patient_id]
    screening = _get_screening(patient_id)

    eligible = [s for s in screening if s["eligible"]]
    ineligible = [s for s in screening if not s["eligible"]]

    # Patient heading
    _html(f'<h1 class="page-patient-name">{patient["name"]}</h1>')
    _html(f'<p class="page-patient-desc">{patient["description"]}</p>')

    # Applicable guidelines
    _html(f'<p class="section-heading">Applicable Guidelines <span class="section-count">{len(eligible)}</span></p>')

    if not eligible:
        _html('<p class="empty-text">No guidelines are applicable to this patient.</p>')
    else:
        for cpg in eligible:
            desc = cpg["description"]
            if len(desc) > 150:
                desc = desc[:150].rsplit(" ", 1)[0] + "..."
            cat_html = f'<span class="cpg-card-category">{cpg["category"]}</span>' if cpg["category"] else ""
            _html(f'''
                <div class="cpg-card">
                    <div class="cpg-card-header">
                        <span class="cpg-card-name">{cpg["name"]}</span>
                        {cat_html}
                    </div>
                    <p class="cpg-card-desc">{desc}</p>
                </div>
            ''')

        # Evaluate button (centered)
        _html('<div style="height: 1rem;"></div>')
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            n = len(eligible)
            if st.button(
                f"Evaluate {n} guideline{'s' if n != 1 else ''}",
                type="primary",
                use_container_width=True,
            ):
                _evaluate(patient_id, [c["id"] for c in eligible])

    # Not applicable (collapsed)
    if ineligible:
        _html('<div style="height: 1.5rem;"></div>')
        with st.expander(f"Not applicable ({len(ineligible)})"):
            for cpg in ineligible:
                _html(f'<div class="cpg-na-row">{cpg["name"]}</div>')


def _get_screening(patient_id: str) -> list[dict]:
    """Get or compute eligibility screening for a patient (cached in session state)."""
    cache_key = f"screening_{patient_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    ctx = get_patient_health_context(patient_id, Persona.provider)
    if not ctx:
        return []

    results = [
        {
            "id": sr.cpg_identifier,
            "name": sr.cpg_title,
            "description": sr.description,
            "category": sr.category,
            "eligible": sr.is_eligible,
        }
        for sr in get_registry().screen(ctx)
    ]

    st.session_state[cache_key] = results
    return results


# ─── Evaluate ─────────────────────────────────────────────────────────


def _evaluate(patient_id: str, cpg_ids: list[str]):
    """Run full evaluation pipeline."""
    patient = SAMPLE_PATIENTS[patient_id]
    ctx = get_patient_health_context(patient_id, Persona.provider)

    if not ctx:
        st.error("Failed to load patient data")
        return

    with st.spinner("Evaluating..."):
        summary = st.session_state.evaluator.evaluate_multiple_cpgs(
            cpg_ids=cpg_ids,
            health_context=ctx,
            patient_id=patient_id,
            patient_name=patient["name"],
            persona=Persona.provider,
            parallel=True,
        )
        ranked = st.session_state.ranker.rank_recommendations(summary)

        st.session_state.results = {
            "summary": summary,
            "ranked": ranked,
            "patient": patient,
        }
        st.session_state.show_results = True
    st.rerun()


# ─── Results Page ─────────────────────────────────────────────────────


def _page_results():
    """Results page — recommendations + detail expanders."""
    data = st.session_state.results
    summary = data["summary"]
    ranked = data["ranked"]
    patient = data["patient"]

    # Patient heading
    _html(f'<h1 class="page-patient-name">{patient["name"]}</h1>')

    rec_count = len(ranked)
    _html(f'''
        <p class="results-summary">
            {summary.eligible_cpgs} of {summary.total_cpgs} guidelines evaluated
            · {rec_count} recommendation{"s" if rec_count != 1 else ""}
        </p>
    ''')

    # Conflict alert
    if summary.has_conflicts and summary.conflicts.conflicts:
        n = len(summary.conflicts.conflicts)
        descs = "; ".join(
            cf.description[:60] for cf in summary.conflicts.conflicts[:2]
        )
        _html(f'''
            <div class="alert-row">
                <span class="alert-icon">&#9888;</span>
                <span>{n} guideline conflict{"s" if n > 1 else ""} &#8212; {descs}</span>
            </div>
        ''')

    # Recommendations
    _html(f'<p class="section-heading">Recommendations <span class="section-count">{rec_count}</span></p>')

    if not ranked:
        _html('<p class="empty-text">No actionable recommendations at this time.</p>')
    else:
        for rec in ranked:
            _render_rec(rec)

    # Detail expanders
    _html('<div style="height: 1rem;"></div>')

    _render_assessments_expander(summary)

    if summary.has_conflicts and summary.conflicts.conflicts:
        _render_conflicts_expander(summary)

    if summary.errors:
        with st.expander(f"Errors ({len(summary.errors)})"):
            for err in summary.errors:
                st.markdown(f"`{err}`")

    # Back button
    _html('<div style="height: 1.5rem;"></div>')
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("Back to guidelines", type="secondary", use_container_width=True):
            st.session_state.pop("show_results", None)
            st.session_state.pop("results", None)
            st.rerun()


# ─── Shared Components ───────────────────────────────────────────────


def _render_rec(rec):
    """Render a single recommendation card."""
    var = rec.recommendation.recommendation
    title = getattr(var, "title", None) or getattr(var, "id", "Recommendation")
    narrative = getattr(rec.recommendation, "narrative", "") or ""

    grade = ""
    if g := getattr(var, "class_of_recommendation", None):
        grade = f"Class {g.value if hasattr(g, 'value') else g}"
    elif g := getattr(var, "uspstf_grade", None):
        grade = f"Grade {g.value if hasattr(g, 'value') else g}"

    priority_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MODERATE": "moderate",
        "LOW": "low",
        "INFORMATIONAL": "info",
    }
    priority_name = rec.priority.name if hasattr(rec.priority, "name") else str(rec.priority)
    priority_cls = priority_map.get(priority_name, "low")
    priority_label = priority_name.capitalize()

    if len(narrative) > 280:
        narrative = narrative[:280].rsplit(" ", 1)[0] + "..."

    grade_html = f'<span class="rec-grade">{grade}</span>' if grade else ""
    narrative_html = f'<p class="rec-narrative">{narrative}</p>' if narrative else ""

    _html(f'''
        <div class="rec-card priority-{priority_cls}">
            <div class="rec-top">
                <span class="rec-priority {priority_cls}">{priority_label}</span>
                {grade_html}
            </div>
            <p class="rec-title">{title}</p>
            {narrative_html}
            <span class="rec-source">{rec.cpg_title}</span>
        </div>
    ''')


def _render_assessments_expander(summary):
    """Render assessments inside an expander, grouped by CPG."""
    by_cpg = {}
    total = 0

    for cpg_id, result in summary.evaluations.items():
        if not result.assessments:
            continue
        rows = []
        for assessed in result.assessments:
            total += 1
            var_id = getattr(assessed, "id", "Unknown")
            title = var_id
            if hasattr(assessed, "record"):
                rec = assessed.record
                if hasattr(rec, "var") and hasattr(rec.var, "title"):
                    title = rec.var.title or var_id

            value = None
            if hasattr(assessed, "record") and hasattr(assessed.record, "value"):
                value = assessed.record.value

            eval_result = getattr(assessed, "evaluation_result", None)
            error = getattr(assessed, "error", None)

            if eval_result is not None:
                result_str = str(
                    eval_result.value if hasattr(eval_result, "value") else eval_result
                ).lower()
                dot_cls = "true" if "success" in result_str else "false"
            elif error:
                dot_cls = "error"
            else:
                dot_cls = "false"

            value_str = str(value) if value is not None else "—"
            if value_str.startswith("Val="):
                value_str = value_str[4:]
            if len(value_str) > 20:
                value_str = value_str[:17] + "..."

            if value_str == "True":
                val_cls = "v-true"
            elif value_str == "False":
                val_cls = "v-false"
            elif value_str == "—":
                val_cls = "v-missing"
            else:
                val_cls = "v-number"

            disp_title = title if len(title) <= 50 else title[:47] + "..."
            rows.append((dot_cls, disp_title, value_str, val_cls))

        if rows:
            by_cpg[result.cpg_title] = rows

    if not by_cpg:
        return

    with st.expander(f"Assessments ({total})"):
        for cpg_title, rows in by_cpg.items():
            _html(f'<p class="detail-cpg-title">{cpg_title}</p>')
            for dot, name, val, vcls in rows:
                _html(f'''
                    <div class="detail-row">
                        <span class="detail-dot {dot}"></span>
                        <span class="detail-label">{name}</span>
                        <span class="detail-value {vcls}">{val}</span>
                    </div>
                ''')


def _render_conflicts_expander(summary):
    """Render conflict details inside an expander."""
    conflicts = summary.conflicts.conflicts

    with st.expander(f"Conflicts ({len(conflicts)})"):
        for conflict in conflicts:
            severity = (
                conflict.severity.value
                if hasattr(conflict.severity, "value")
                else str(conflict.severity)
            )
            conflict_type = (
                conflict.conflict_type.value
                if hasattr(conflict.conflict_type, "value")
                else str(conflict.conflict_type)
            )

            cpg_list = " · ".join(
                inv.get("cpg_title", "")[:30] for inv in conflict.involved_cpgs
            )

            _html(f'''
                <div class="conflict-item">
                    <span class="conflict-severity-tag {severity.lower()}">{severity}</span>
                    <span class="conflict-type">{conflict_type.replace('_', ' ').title()}</span>
                </div>
            ''')
            _html(f'<p class="conflict-desc">{conflict.description}</p>')
            _html(f'<p class="conflict-cpgs">{cpg_list}</p>')

            if conflict.suggested_resolution:
                _html(f'<p class="conflict-resolution">{conflict.suggested_resolution}</p>')
