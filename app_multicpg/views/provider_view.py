#!/usr/bin/env python3
"""Provider view - single column centered layout."""

import streamlit as st

from app_multicpg.components import (
    render_cpg_selector,
    render_evaluation_card,
    render_recommendation_panel,
    render_conflict_panel,
    render_patient_selector,
)
from app_multicpg.services import (
    MultiCPGService,
    CPGLoaderService,
    PriorityRanker,
)
from app_multicpg.styles import COLORS
from app_multicpg.data import get_patient_health_context, SAMPLE_PATIENTS

# Keep COLORS import for grade badges that still need inline HTML

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from primitives import Persona


def render_provider_view():
    """Render the provider interface - single column."""
    c = COLORS

    # Initialize services
    if "cpg_loader" not in st.session_state:
        st.session_state.cpg_loader = CPGLoaderService()
    if "evaluator" not in st.session_state:
        st.session_state.evaluator = MultiCPGService(detect_conflicts=True)
    if "ranker" not in st.session_state:
        st.session_state.ranker = PriorityRanker()

    loader = st.session_state.cpg_loader
    evaluator = st.session_state.evaluator
    ranker = st.session_state.ranker

    # Header
    _render_header()

    # Navigation
    current_section = st.session_state.get("current_section", "overview")
    _render_nav(current_section)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Content
    if current_section == "overview":
        _render_overview(evaluator, ranker)
    elif current_section == "recommendations":
        _render_recommendations()
    elif current_section == "cpg_details":
        _render_cpg_details()
    elif current_section == "conflicts":
        _render_conflicts()
    elif current_section == "patient_data":
        _render_patient_data(loader)

    # Footer
    _render_footer()


def _render_header():
    """Render header."""
    c = COLORS

    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap;">
                <h1 style="
                    font-size: 2.5rem;
                    font-weight: 900;
                    color: {c['text_primary']};
                    margin: 0;
                    letter-spacing: -0.03em;
                    line-height: 1;
                ">ConcordCare</h1>
                <span style="
                    color: {c['text_muted']};
                    font-size: 1rem;
                    font-weight: 400;
                ">Clinical Decision Support</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        if st.button("Patient View", use_container_width=True):
            st.session_state.view_mode = "patient"
            st.rerun()


def _render_nav(current: str):
    """Render navigation."""
    c = COLORS

    sections = [
        ("overview", "Overview"),
        ("recommendations", "Recommendations"),
        ("cpg_details", "CPG Details"),
        ("conflicts", "Conflicts"),
        ("patient_data", "Data"),
    ]

    cols = st.columns(len(sections))

    for i, (section_id, label) in enumerate(sections):
        with cols[i]:
            is_current = current == section_id
            btn_type = "primary" if is_current else "secondary"
            if st.button(label, key=f"nav_{section_id}", use_container_width=True, type=btn_type):
                st.session_state.current_section = section_id
                st.rerun()


def _render_overview(evaluator: MultiCPGService, ranker: PriorityRanker):
    """Render overview."""
    c = COLORS

    if "evaluation_summary" not in st.session_state:
        _render_welcome()
        return

    summary = st.session_state.evaluation_summary
    ranked = st.session_state.ranked_recommendations

    # Patient name
    st.caption("PATIENT")
    st.markdown(f"## {summary.patient_name}")

    # Metrics using columns
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Guidelines", summary.total_cpgs)
    with col2:
        st.metric("Eligible", summary.eligible_cpgs)
    with col3:
        st.metric("Recommendations", summary.applied_recommendations)
    st.markdown("---")

    # Top recommendations
    if ranked:
        st.markdown("### Top Recommendations")

        for rec in ranked[:3]:
            _render_recommendation_card(rec)

        if len(ranked) > 3:
            st.caption(f"+ {len(ranked) - 3} more recommendations")
    else:
        st.info("No recommendations apply")

    # Conflicts
    if summary.has_conflicts:
        conflict_count = len(summary.conflicts.conflicts)
        st.warning(f"**{conflict_count} Potential Conflict{'s' if conflict_count != 1 else ''} Detected** - Review recommended before proceeding")


def _render_welcome():
    """Render welcome screen."""
    st.markdown("## Clinical Decision Support")
    st.caption("Evaluate clinical practice guidelines")

    st.markdown("")  # Spacer

    # Quick start
    quick_patient = st.selectbox(
        "Select patient",
        options=list(SAMPLE_PATIENTS.keys()),
        format_func=lambda x: f"{SAMPLE_PATIENTS[x]['name']} — {SAMPLE_PATIENTS[x]['description']}"
    )

    if st.button("Run Evaluation", type="primary", use_container_width=True):
        _run_evaluation(quick_patient, ["cholesterol", "statin", "hypertension", "diabetes"])


def _run_evaluation(patient_id: str, cpg_ids: list[str]):
    """Run evaluation."""
    evaluator = st.session_state.evaluator
    ranker = st.session_state.ranker

    patient = SAMPLE_PATIENTS.get(patient_id)
    patient_name = patient["name"] if patient else patient_id
    health_context = get_patient_health_context(patient_id, Persona.provider)

    if not health_context:
        st.error("Could not load patient data")
        return

    with st.spinner("Evaluating..."):
        summary = evaluator.evaluate_multiple_cpgs(
            cpg_ids=cpg_ids,
            health_context=health_context,
            patient_id=patient_id,
            patient_name=patient_name,
            persona=Persona.provider,
            parallel=True
        )
        ranked = ranker.rank_recommendations(summary)

        st.session_state.evaluation_summary = summary
        st.session_state.ranked_recommendations = ranked

    st.session_state.current_section = "overview"
    st.rerun()


def _render_recommendation_card(rec):
    """Render compact recommendation card."""
    c = COLORS

    rec_var = rec.recommendation.recommendation
    title = getattr(rec_var, 'title', None) or getattr(rec_var, 'id', 'Recommendation')
    narrative = getattr(rec.recommendation, 'narrative', '') or ''

    # Grade text
    class_of_rec = getattr(rec_var, 'class_of_recommendation', None)
    uspstf = getattr(rec_var, 'uspstf_grade', None)
    grade_text = ""
    if class_of_rec:
        grade = class_of_rec.value if hasattr(class_of_rec, 'value') else str(class_of_rec)
        grade_text = f"Class {grade}"
    elif uspstf:
        grade = uspstf.value if hasattr(uspstf, 'value') else str(uspstf)
        grade_text = f"Grade {grade}"

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**{title}**")
        with col2:
            if grade_text:
                st.markdown(
                    f"<span style='background:{c['text_primary']};color:{c['background']};padding:0.25rem 0.5rem;border-radius:4px;font-size:0.75rem;font-weight:700;'>{grade_text}</span>",
                    unsafe_allow_html=True
                )

        if narrative:
            display_narrative = narrative[:200] + '...' if len(narrative) > 200 else narrative
            st.markdown(display_narrative)

        st.markdown("---")


def _render_recommendations():
    """Render recommendations section."""
    st.markdown("## Recommendations")

    if "ranked_recommendations" not in st.session_state:
        st.info("Run an evaluation first.")
        return

    ranked = st.session_state.ranked_recommendations

    if not ranked:
        st.info("No recommendations apply")
        return

    render_recommendation_panel(ranked, view_mode="provider")


def _render_cpg_details():
    """Render CPG details section."""
    st.markdown("## CPG Details")

    if "evaluation_summary" not in st.session_state:
        st.info("Run an evaluation first.")
        return

    summary = st.session_state.evaluation_summary
    cpg_options = list(summary.evaluations.keys())

    if not cpg_options:
        st.info("No CPGs were evaluated.")
        return

    selected_cpg = st.selectbox(
        "Select guideline",
        options=cpg_options,
        format_func=lambda x: summary.evaluations[x].cpg_title
    )

    if selected_cpg:
        eval_result = summary.evaluations[selected_cpg]
        render_evaluation_card(selected_cpg, eval_result, view_mode="provider")


def _render_conflicts():
    """Render conflicts section."""
    st.markdown("## Conflicts")

    if "evaluation_summary" not in st.session_state:
        st.info("Run an evaluation first.")
        return

    summary = st.session_state.evaluation_summary
    render_conflict_panel(summary.conflicts, view_mode="provider")


def _render_patient_data(loader: CPGLoaderService):
    """Render patient data section."""
    st.markdown("## Patient & Guidelines")

    st.caption("PATIENT")
    patient_id = render_patient_selector()

    st.markdown("")  # Spacer

    st.caption("GUIDELINES")
    selected_cpgs = render_cpg_selector(loader)

    st.markdown("")  # Spacer

    if patient_id and selected_cpgs:
        if st.button("Run Evaluation", type="primary", use_container_width=True):
            _run_evaluation(patient_id, selected_cpgs)


def _render_footer():
    """Render footer."""
    st.markdown("---")
    st.caption("Powered by ConcordCore · Always consult your healthcare provider")
