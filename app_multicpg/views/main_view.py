#!/usr/bin/env python3
"""Main view - clinical dashboard for providers."""

import re
import streamlit as st
from app_multicpg.services import MultiCPGService, CPGLoaderService, PriorityRanker
from app_multicpg.styles import COLORS
from app_multicpg.data import get_patient_health_context, SAMPLE_PATIENTS

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from primitives import Persona


def _html(text: str) -> None:
    """Render HTML via st.markdown, stripping blank lines to prevent parser breakage."""
    clean = re.sub(r'\n\s*\n', '\n', text.strip())
    st.markdown(clean, unsafe_allow_html=True)


def render_main_view():
    """Main render function."""
    _init_services()

    if "results" in st.session_state:
        _page_results()
    else:
        _page_setup()


def _init_services():
    if "loader" not in st.session_state:
        st.session_state.loader = CPGLoaderService()
    if "evaluator" not in st.session_state:
        st.session_state.evaluator = MultiCPGService(detect_conflicts=True)
    if "ranker" not in st.session_state:
        st.session_state.ranker = PriorityRanker()


# ─── Setup Page ────────────────────────────────────────────────────────


def _page_setup():
    """Setup page: select patient and guidelines, then evaluate."""
    c = COLORS
    loader = st.session_state.loader

    _html(f"""
        <div class="top-nav">
            <div class="top-nav-brand">Concord</div>
            <div class="top-nav-meta">Multi-guideline evaluation</div>
        </div>
    """)

    _html("""
        <div class="setup-header">
            <h1 class="setup-title">New Evaluation</h1>
            <p class="setup-subtitle">Select a patient and choose which clinical practice guidelines to evaluate against their health data.</p>
        </div>
    """)

    # ── Patient Selection ──
    _html('<p class="label">Patient</p>')

    patients = list(SAMPLE_PATIENTS.items())
    selected = st.session_state.get("_setup_patient", patients[0][0])

    cols = st.columns(len(patients))
    for i, (pid, p) in enumerate(patients):
        with cols[i]:
            is_sel = selected == pid
            sel_class = "selected" if is_sel else ""

            data = p["data"]
            ldl = data.get("LDL")
            if isinstance(ldl, list):
                ldl = ldl[0] if ldl else "—"
            bp = data.get("bloodpressure", ("—", "—"))

            conditions = []
            if data.get("htn"):
                conditions.append("HTN")
            if data.get("diabetesMellitus"):
                conditions.append("DM")
            if data.get("is_smoker"):
                conditions.append("Smoker")

            _html(f"""
                <div class="patient-select-card {sel_class}">
                    <p class="patient-card-name">{p['name']}</p>
                    <p class="patient-card-meta">{p['age']}y {p['gender']}</p>
                    <div class="patient-card-data">
                        <div class="patient-card-datum">
                            <span class="patient-card-datum-label">LDL</span>
                            <span class="patient-card-datum-value">{ldl}</span>
                        </div>
                        <div class="patient-card-datum">
                            <span class="patient-card-datum-label">BP</span>
                            <span class="patient-card-datum-value">{bp[0]}/{bp[1]}</span>
                        </div>
                        <div class="patient-card-datum">
                            <span class="patient-card-datum-label">Dx</span>
                            <span class="patient-card-datum-value">{', '.join(conditions) if conditions else '—'}</span>
                        </div>
                    </div>
                </div>
            """)
            if st.button(
                "Selected" if is_sel else "Select",
                key=f"sel_{pid}",
                type="primary" if is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state._setup_patient = pid
                st.rerun()

    # ── Guideline Selection ──
    _html('<div style="height: 1.5rem;"></div>')
    _html('<p class="label">Guidelines</p>')

    available = loader.get_available_cpgs()
    cpg_map = {cpg["id"]: cpg["name"] for cpg in available}
    defaults = [k for k in ["cholesterol", "statin"] if k in cpg_map]

    chosen = st.multiselect(
        "Select guidelines to evaluate",
        list(cpg_map.keys()),
        default=st.session_state.get("chosen_cpgs", defaults),
        format_func=lambda x: cpg_map.get(x, x),
        label_visibility="collapsed",
        key="chosen_cpgs",
    )

    col_a, col_b, col_c, col_rest = st.columns([1, 1, 1, 5])
    with col_a:
        if st.button("All", key="qa", use_container_width=True, type="secondary"):
            st.session_state.chosen_cpgs = list(cpg_map.keys())
            st.rerun()
    with col_b:
        if st.button("CV", key="qcv", use_container_width=True, type="secondary"):
            st.session_state.chosen_cpgs = [
                cpg["id"]
                for cpg in available
                if cpg.get("category") == "Cardiovascular"
            ]
            st.rerun()
    with col_c:
        if st.button("None", key="qn", use_container_width=True, type="secondary"):
            st.session_state.chosen_cpgs = []
            st.rerun()

    by_cat = loader.get_cpgs_by_category()
    chosen_set = set(chosen)

    for cat, cpgs_in_cat in by_cat.items():
        with st.expander(f"{cat} ({len(cpgs_in_cat)})", expanded=False):
            for cpg in cpgs_in_cat:
                is_in = cpg["id"] in chosen_set
                icon = "●" if is_in else "○"
                color = COLORS["accent"] if is_in else COLORS["text_muted"]
                _html(
                    f'<span style="color:{color};margin-right:6px;">{icon}</span>'
                    f'<span style="font-size:0.8125rem;font-weight:{"600" if is_in else "400"};color:{COLORS["text"] if is_in else COLORS["text_secondary"]};">'
                    f'{cpg["name"]}</span>'
                    f' <span style="font-size:0.6875rem;color:{COLORS["text_muted"]};">— {cpg.get("description", "")}</span>'
                )

    # ── Evaluate Footer ──
    _html('<div style="height: 1rem;"></div>')

    can_run = bool(selected and chosen)
    if can_run:
        summary_text = f"<strong>{SAMPLE_PATIENTS[selected]['name']}</strong> · {len(chosen)} guideline{'s' if len(chosen) != 1 else ''}"
    else:
        summary_text = "Select a patient and guidelines to begin"

    eval_l, eval_r = st.columns([4, 1])
    with eval_l:
        _html(f'<div class="eval-footer"><span class="eval-footer-text">{summary_text}</span></div>')
    with eval_r:
        if st.button(
            "Evaluate",
            type="primary",
            disabled=not can_run,
            use_container_width=True,
        ):
            _evaluate(selected, chosen)


# ─── Evaluate ──────────────────────────────────────────────────────────


def _evaluate(patient_id: str, cpg_ids: list[str]):
    """Run evaluation pipeline."""
    patient = SAMPLE_PATIENTS[patient_id]
    ctx = get_patient_health_context(patient_id, Persona.provider)

    if not ctx:
        st.error("Failed to load patient data")
        return

    with st.spinner("Evaluating guidelines..."):
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
    st.rerun()


# ─── Results Page ──────────────────────────────────────────────────────


def _page_results():
    """Results dashboard."""
    c = COLORS
    data = st.session_state.results
    summary = data["summary"]
    ranked = data["ranked"]
    patient = data["patient"]

    nav_l, nav_r = st.columns([1, 6])
    with nav_l:
        if st.button("\u2190 Back", type="secondary", use_container_width=True):
            del st.session_state.results
            st.rerun()
    with nav_r:
        _html("""
            <div class="top-nav" style="margin-bottom:0;border-bottom:none;">
                <div class="top-nav-brand">Concord</div>
                <div class="top-nav-meta">Evaluation Results</div>
            </div>
        """)
    _html('<div style="border-bottom:1px solid #E2E5EA;margin-bottom:0.75rem;"></div>')

    # ── Patient Banner ──
    pdata = patient["data"]
    conditions = []
    if pdata.get("htn"):
        conditions.append(("Hypertension", ""))
    if pdata.get("diabetesMellitus"):
        conditions.append(("Diabetes", ""))
    if pdata.get("is_smoker"):
        conditions.append(("Current Smoker", ""))
    if pdata.get("former_smoker") and not pdata.get("is_smoker"):
        conditions.append(("Former Smoker", ""))
    if pdata.get("FamilyHxPrematureASCVD"):
        conditions.append(("FHx ASCVD", ""))

    meds = []
    if pdata.get("med_statins"):
        meds.append("Statins")
    if pdata.get("med_for_htn"):
        meds.append("Antihypertensives")
    if pdata.get("med_nonstatins_chol"):
        meds.append("Non-statin lipid Rx")

    cond_chips = "".join(
        f'<span class="condition-chip">{name}</span>' for name, _ in conditions
    )
    med_chips = "".join(
        f'<span class="condition-chip med">{m}</span>' for m in meds
    )

    initials = "".join(w[0] for w in patient["name"].split()[:2]).upper()

    # Calculate risk level from findings
    risk_factors = sum([
        bool(pdata.get("htn")),
        bool(pdata.get("diabetesMellitus")),
        bool(pdata.get("is_smoker")),
        bool(pdata.get("FamilyHxPrematureASCVD")),
        (pdata.get("LDL", [0])[0] if isinstance(pdata.get("LDL"), list) else pdata.get("LDL", 0)) > 160,
        pdata.get("HDL", 100) < 40,
    ])
    if risk_factors >= 3:
        risk_cls, risk_text = "risk-high", "High Risk"
    elif risk_factors >= 1:
        risk_cls, risk_text = "risk-moderate", "Moderate Risk"
    else:
        risk_cls, risk_text = "risk-low", "Low Risk"

    _html(f"""
        <div class="patient-banner">
            <div class="patient-avatar">{initials}</div>
            <div class="patient-info">
                <p class="patient-name">{patient['name']} <span class="risk-badge {risk_cls}">{risk_text}</span></p>
                <p class="patient-demo">{patient['age']} years · {patient['gender']} · {pdata.get('Ethnicity', '')}</p>
            </div>
            <div class="patient-conditions">
                {cond_chips}
                {med_chips}
                {f'<span class="condition-chip ok">No active conditions</span>' if not conditions else ''}
            </div>
        </div>
    """)

    # ── Stats Row ──
    conflict_count = len(summary.conflicts.conflicts) if summary.has_conflicts else 0
    conflict_class = "error" if conflict_count > 0 else "success"
    total_assessments = sum(len(r.assessments) for r in summary.evaluations.values())

    rec_label = "Recommendation" if len(ranked) == 1 else "Recommendations"
    conflict_label = "Conflict" if conflict_count == 1 else "Conflicts"

    _html(f"""
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-card-value accent">{summary.eligible_cpgs}<span style="font-size:0.875rem;font-weight:500;color:#94A3B8;">/{summary.total_cpgs}</span></div>
                <div class="stat-card-label">Eligible Guidelines</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-value {'success' if ranked else ''}">{len(ranked)}</div>
                <div class="stat-card-label">{rec_label}</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-value">{total_assessments}</div>
                <div class="stat-card-label">Assessments</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-value {conflict_class}">{conflict_count}</div>
                <div class="stat-card-label">{conflict_label}</div>
            </div>
        </div>
    """)

    # ── Conflict Alert ──
    if summary.has_conflicts and summary.conflicts.conflicts:
        n = len(summary.conflicts.conflicts)
        descs = "; ".join(
            cf.description[:80] for cf in summary.conflicts.conflicts[:2]
        )
        _html(f"""
            <div class="conflict-banner">
                <div class="conflict-banner-icon">&#9888;</div>
                <div class="conflict-banner-text">
                    <p class="conflict-banner-title">{n} inter-guideline conflict{'s' if n > 1 else ''} detected</p>
                    <p class="conflict-banner-desc">{descs}</p>
                </div>
            </div>
        """)

    # ── Main two-column layout: Recs + Health Data ──
    col_main, col_side = st.columns([7, 5], gap="large")

    with col_main:
        _render_recommendations(ranked)
        _render_key_findings(patient, summary)
        _render_assessments(summary)
        _render_guideline_overview(summary)

    with col_side:
        _render_health_data(patient)

    # ── Conflicts Detail ──
    if summary.has_conflicts and summary.conflicts.conflicts:
        _render_conflicts_detail(summary)

    # ── Errors ──
    if summary.errors:
        with st.expander(f"Errors ({len(summary.errors)})"):
            for err in summary.errors:
                st.markdown(f"- `{err}`")


# ─── Result Sub-Sections ──────────────────────────────────────────────


def _render_key_findings(patient, summary):
    """Render auto-generated key clinical findings."""
    pdata = patient["data"]
    findings = []

    # Lipid findings
    ldl = pdata.get("LDL")
    if ldl:
        ldl_val = ldl[0] if isinstance(ldl, list) else ldl
        if ldl_val > 190:
            findings.append(("LDL critically elevated", f"{ldl_val} mg/dL (>190)", "critical"))
        elif ldl_val > 160:
            findings.append(("LDL elevated", f"{ldl_val} mg/dL (>160)", "high"))

    hdl = pdata.get("HDL")
    if hdl and hdl < 40:
        findings.append(("Low HDL", f"{hdl} mg/dL (<40)", "high"))

    # BP
    bp = pdata.get("bloodpressure", (None, None))
    if bp and bp[0]:
        if bp[0] >= 140 or bp[1] >= 90:
            findings.append(("Hypertension", f"{bp[0]}/{bp[1]} mmHg", "high"))

    # Metabolic
    hba1c = pdata.get("HbA_one_c")
    if hba1c:
        if hba1c >= 6.5:
            findings.append(("HbA1c in diabetic range", f"{hba1c}%", "critical"))
        elif hba1c >= 5.7:
            findings.append(("HbA1c pre-diabetic", f"{hba1c}%", "moderate"))

    bmi = pdata.get("BMI")
    if bmi:
        if bmi >= 30:
            findings.append(("Obesity", f"BMI {bmi}", "high"))
        elif bmi >= 25:
            findings.append(("Overweight", f"BMI {bmi}", "moderate"))

    # Triglycerides
    tg = pdata.get("triglycerides")
    if tg and tg > 200:
        findings.append(("Elevated triglycerides", f"{tg} mg/dL", "high"))

    # Kidney
    egfr = pdata.get("eGFR")
    if egfr and egfr < 60:
        findings.append(("Reduced eGFR", f"{egfr} mL/min", "high"))

    # Risk factors
    if pdata.get("FamilyHxPrematureASCVD"):
        findings.append(("Family history of premature ASCVD", "", "moderate"))

    if pdata.get("is_smoker"):
        findings.append(("Active smoker", "", "critical"))

    if not findings:
        return

    _html('<div style="height: 1rem;"></div>')
    _html(f"""
        <div class="section-header">
            <p class="section-title">Key Findings</p>
            <span class="section-count">{len(findings)} flagged</span>
        </div>
    """)

    findings_html = "".join(
        f'<div class="finding-row">'
        f'<span class="finding-dot {sev}"></span>'
        f'<span class="finding-label">{label}</span>'
        f'<span class="finding-value">{value}</span>'
        f'</div>'
        for label, value, sev in findings
    )
    _html(f'<div class="findings-panel">{findings_html}</div>')


def _render_recommendations(ranked):
    """Render priority-ranked recommendation cards."""
    _html(f"""
        <div class="section-header">
            <p class="section-title">Recommendations</p>
            <span class="section-count">{len(ranked)} total</span>
        </div>
    """)

    if not ranked:
        _html('<div class="empty-state positive">No actionable recommendations at this time. Continue monitoring per guideline protocols.</div>')
        return

    for rec in ranked:
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

        if len(narrative) > 200:
            narrative = narrative[:200].rsplit(" ", 1)[0] + "..."

        conflict_html = ""
        if rec.conflicts_with:
            conflict_html = '<span class="rec-card-conflict">&#9888; Conflict</span>'

        evidence_html = ""
        if grade:
            evidence_html = f'<span class="rec-evidence">{grade}</span>'

        narrative_html = f'<p class="rec-card-narrative">{narrative}</p>' if narrative else ""

        _html(f"""
            <div class="rec-card priority-{priority_cls}">
                <div class="rec-card-top">
                    <div class="rec-card-meta">
                        <span class="rec-priority-tag {priority_cls}">{priority_label}</span>
                        <span class="rec-category-tag">{rec.category}</span>
                        {conflict_html}
                    </div>
                    {evidence_html}
                </div>
                <p class="rec-card-title">{title}</p>
                {narrative_html}
                <span class="rec-card-source">{rec.cpg_title}</span>
            </div>
        """)


def _render_assessments(summary):
    """Render assessment results grouped by CPG in a compact table."""
    # Collect assessments by CPG
    by_cpg = {}
    total = 0
    counts = {"positive": 0, "negative": 0, "unavailable": 0, "error": 0}

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
                if "success" in result_str:
                    dot_cls = "true"
                    counts["positive"] += 1
                else:
                    dot_cls = "false"
                    counts["negative"] += 1
            elif error:
                dot_cls = "error"
                counts["error"] += 1
            else:
                dot_cls = "false"
                counts["negative"] += 1

            # Format value with color class
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
                counts["unavailable"] += 1
                counts["negative"] -= 1  # correct the count
            else:
                val_cls = "v-number"

            disp_title = title if len(title) <= 45 else title[:42] + "..."
            rows.append((dot_cls, disp_title, value_str, val_cls))

        if rows:
            by_cpg[result.cpg_title] = rows

    if not by_cpg:
        return

    _html('<div style="height: 1.5rem;"></div>')
    _html(f"""
        <div class="section-header">
            <p class="section-title">Assessments</p>
            <span class="section-count">{total} evaluated</span>
        </div>
    """)

    # Summary bar
    summary_items = []
    if counts["positive"]:
        summary_items.append(f'<span class="assess-summary-item"><span class="assess-summary-dot positive"></span>{counts["positive"]} positive</span>')
    if counts["negative"]:
        summary_items.append(f'<span class="assess-summary-item"><span class="assess-summary-dot negative"></span>{counts["negative"]} negative</span>')
    if counts["unavailable"]:
        summary_items.append(f'<span class="assess-summary-item"><span class="assess-summary-dot unavailable"></span>{counts["unavailable"]} unavailable</span>')
    if counts["error"]:
        summary_items.append(f'<span class="assess-summary-item"><span class="assess-summary-dot error"></span>{counts["error"]} errors</span>')
    _html('<div class="assess-summary">' + "".join(summary_items) + "</div>")

    # Table per CPG - collapsed inside an expander
    for cpg_title, rows in by_cpg.items():
        with st.expander(f"{cpg_title} ({len(rows)} assessments)", expanded=False):
            table_rows = "".join(
                f'<div class="assess-row">'
                f'<span class="assess-dot {dot}"></span>'
                f'<span class="assess-name">{name}</span>'
                f'<span class="assess-val {vcls}">{val}</span>'
                f'</div>'
                for dot, name, val, vcls in rows
            )
            header = (
                '<div class="assess-table-header">'
                '<span></span>'
                '<span>Assessment</span>'
                '<span style="text-align:right;">Value</span>'
                '</div>'
            )
            _html(f'<div class="assess-table">{header}{table_rows}</div>')


def _render_health_data(patient):
    """Render comprehensive patient health data panels."""
    pdata = patient["data"]

    # Vitals
    bp = pdata.get("bloodpressure", (None, None))
    bmi = pdata.get("BMI")
    vitals_rows = []
    if bp and bp[0]:
        bp_cls = "high" if bp[0] >= 140 or bp[1] >= 90 else "normal"
        vitals_rows.append(("Blood Pressure", f"{bp[0]}/{bp[1]} mmHg", bp_cls))
    if bmi:
        bmi_cls = "high" if bmi >= 30 else ("low" if bmi >= 25 else "normal")
        vitals_rows.append(("BMI", f"{bmi}", bmi_cls))
    _health_panel("Vitals", vitals_rows)

    # Lipids
    lipid_rows = []
    ldl = pdata.get("LDL")
    if ldl is not None:
        if isinstance(ldl, list):
            ldl_display = ", ".join(str(v) for v in ldl)
            ldl_val = ldl[0]
        else:
            ldl_display = str(ldl)
            ldl_val = ldl
        ldl_cls = "high" if ldl_val > 160 else ("normal" if ldl_val < 130 else "")
        lipid_rows.append(("LDL Cholesterol", f"{ldl_display} mg/dL", ldl_cls))

    hdl = pdata.get("HDL")
    if hdl is not None:
        hdl_cls = "low" if hdl < 40 else "normal"
        lipid_rows.append(("HDL Cholesterol", f"{hdl} mg/dL", hdl_cls))

    tg = pdata.get("triglycerides")
    if tg is not None:
        tg_cls = "high" if tg > 200 else "normal"
        lipid_rows.append(("Triglycerides", f"{tg} mg/dL", tg_cls))

    chol = pdata.get("Chol")
    if chol is not None:
        chol_cls = "high" if chol > 240 else ("normal" if chol < 200 else "")
        lipid_rows.append(("Total Cholesterol", f"{chol} mg/dL", chol_cls))
    _health_panel("Lipid Panel", lipid_rows)

    # Metabolic
    metabolic_rows = []
    hba1c = pdata.get("HbA_one_c")
    if hba1c is not None:
        hba1c_cls = "high" if hba1c >= 6.5 else ("low" if hba1c >= 5.7 else "normal")
        metabolic_rows.append(("HbA1c", f"{hba1c}%", hba1c_cls))

    glu = pdata.get("glu")
    if glu is not None:
        glu_cls = "high" if glu >= 126 else ("low" if glu >= 100 else "normal")
        metabolic_rows.append(("Fasting Glucose", f"{glu} mg/dL", glu_cls))

    egfr = pdata.get("eGFR")
    if egfr is not None:
        egfr_cls = "low" if egfr < 60 else "normal"
        metabolic_rows.append(("eGFR", f"{egfr} mL/min", egfr_cls))
    _health_panel("Metabolic", metabolic_rows)

    # Demographics
    demo_rows = [
        ("Age", f"{pdata.get('Age', '—')} years", ""),
        ("Gender", pdata.get("Gender", "—"), ""),
    ]
    ethnicity = pdata.get("Ethnicity")
    if ethnicity:
        demo_rows.append(("Ethnicity", ethnicity, ""))
    _health_panel("Demographics", demo_rows)

    # Conditions
    condition_rows = []
    bool_labels = {
        "diabetesMellitus": "Diabetes Mellitus",
        "htn": "Hypertension",
        "is_smoker": "Current Smoker",
        "former_smoker": "Former Smoker",
        "ckd": "Chronic Kidney Disease",
        "elevated_tg": "Elevated Triglycerides",
        "FamilyHxPrematureASCVD": "Family Hx Premature ASCVD",
    }
    for key, label in bool_labels.items():
        val = pdata.get(key)
        if val is not None:
            display = "Yes" if val else "No"
            cls = "high" if val and key not in ("former_smoker",) else ("normal" if not val else "")
            if key == "former_smoker" and val:
                cls = ""
            condition_rows.append((label, display, cls))
    _health_panel("Conditions & Risk Factors", condition_rows)

    # Medications
    med_rows = []
    med_labels = {
        "med_statins": "Statin Therapy",
        "med_for_htn": "Antihypertensive",
        "med_nonstatins_chol": "Non-statin Lipid Rx",
    }
    for key, label in med_labels.items():
        val = pdata.get(key)
        if val is not None:
            display = "Active" if val else "None"
            cls = "normal" if val else ""
            med_rows.append((label, display, cls))
    _health_panel("Medications", med_rows)

    # Smoking History
    smoking_rows = []
    pack_years = pdata.get("pack_years")
    if pack_years is not None:
        py_cls = "high" if pack_years >= 20 else ""
        smoking_rows.append(("Pack-years", str(pack_years), py_cls))

    years_quit = pdata.get("years_since_quit")
    if years_quit is not None:
        smoking_rows.append(("Years Since Quit", str(years_quit), ""))

    ever_smoked = pdata.get("ever_smoked")
    if ever_smoked is not None:
        smoking_rows.append(("Ever Smoked", "Yes" if ever_smoked else "No", "high" if ever_smoked else "normal"))

    if smoking_rows:
        _health_panel("Smoking History", smoking_rows)


_PANEL_ICONS = {
    "Vitals": "vitals",
    "Lipid Panel": "lipids",
    "Metabolic": "metabolic",
    "Demographics": "demo",
    "Conditions & Risk Factors": "conditions",
    "Medications": "meds",
    "Smoking History": "smoking",
}


def _health_panel(title: str, rows: list[tuple[str, str, str]]):
    """Render a health data panel with title and rows of (label, value, status_class)."""
    if not rows:
        return

    icon_cls = _PANEL_ICONS.get(title, "demo")

    rows_html = "".join(
        f'<div class="health-row"><span class="health-row-label">{label}</span><span class="health-row-value {cls}">{value}</span></div>'
        for label, value, cls in rows
    )

    _html(f'<div class="health-panel"><div class="health-panel-header"><span class="panel-icon {icon_cls}"></span>{title}</div><div class="health-panel-body">{rows_html}</div></div>')


def _render_guideline_overview(summary):
    """Render guideline status overview."""
    loader = st.session_state.loader
    available_map = {cpg["id"]: cpg for cpg in loader.get_available_cpgs()}

    _html('<div style="height: 1.5rem;"></div>')
    _html(f"""
        <div class="section-header">
            <p class="section-title">Guideline Overview</p>
            <span class="section-count">{summary.total_cpgs} evaluated</span>
        </div>
    """)

    # Render guideline cards side by side
    gl_items = list(summary.evaluations.items())
    if gl_items:
        cols = st.columns(len(gl_items))
        for i, (cpg_id, result) in enumerate(gl_items):
            with cols[i]:
                meta = available_map.get(cpg_id, {})
                eligible = result.is_eligible
                status_cls = "eligible" if eligible else "not-eligible"
                status_text = "Eligible" if eligible else "Not Eligible"
                card_cls = "eligible" if eligible else ""
                n_applied = len(result.applied_recommendations)
                n_assessments = len(result.assessments)

                _html(f"""
                    <div class="gl-card {card_cls}">
                        <div class="gl-card-top">
                            <span class="gl-card-category">{meta.get('category', 'General')}</span>
                            <span class="gl-status {status_cls}">{status_text}</span>
                        </div>
                        <p class="gl-card-title">{result.cpg_title}</p>
                        <div class="gl-card-stats">
                            <div class="gl-card-stat">
                                <span class="gl-card-stat-value">{n_applied}</span>
                                <span class="gl-card-stat-label">Recs Applied</span>
                            </div>
                            <div class="gl-card-stat">
                                <span class="gl-card-stat-value">{n_assessments}</span>
                                <span class="gl-card-stat-label">Assessments</span>
                            </div>
                        </div>
                    </div>
                """)

    with st.expander("Detailed Guideline Results"):
        for cpg_id, result in summary.evaluations.items():
            st.markdown(f"**{result.cpg_title}** — {'Eligible' if result.is_eligible else 'Not Eligible'}")
            if result.error:
                st.error(f"Error: {result.error}")
                continue

            if result.applied_recommendations:
                for rec in result.applied_recommendations:
                    var = rec.recommendation
                    title = getattr(var, "title", None) or getattr(var, "id", "—")
                    narrative = getattr(rec, "narrative", "") or ""
                    if len(narrative) > 120:
                        narrative = narrative[:120] + "..."
                    st.markdown(f"- **{title}**: {narrative}" if narrative else f"- **{title}**")
            else:
                st.caption("No recommendations apply")

            st.markdown("---")


def _render_conflicts_detail(summary):
    """Render detailed conflict section."""
    c = COLORS

    _html('<div style="height: 1rem;"></div>')
    _html(f"""
        <div class="section-header">
            <p class="section-title">Conflict Details</p>
            <span class="section-count">{len(summary.conflicts.conflicts)} detected</span>
        </div>
    """)

    for conflict in summary.conflicts.conflicts:
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
        severity_cls = severity.lower()

        cpg_list = " · ".join(
            inv.get("cpg_title", "")[:25] for inv in conflict.involved_cpgs
        )

        _html(f"""
            <div class="conflict-card">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span class="conflict-severity {severity_cls}">{severity}</span>
                    <span style="font-size:0.8125rem;color:{c['text_muted']};">{conflict_type.replace('_', ' ').title()}</span>
                </div>
                <p style="font-size:0.9375rem;color:{c['text_secondary']};margin:0 0 8px 0;line-height:1.6;">{conflict.description}</p>
                <span style="font-size:0.6875rem;color:{c['text_muted']};">{cpg_list}</span>
            </div>
        """)

        if conflict.suggested_resolution:
            with st.expander("Suggested Resolution"):
                st.write(conflict.suggested_resolution)
