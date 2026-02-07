#!/usr/bin/env python3
"""Patient view - single column centered layout."""

import streamlit as st

from app_multicpg.components import render_conflict_panel
from app_multicpg.services import (
    MultiCPGService,
    CPGLoaderService,
    PriorityRanker,
    ExplanationService,
    PriorityLevel,
)
from app_multicpg.data import get_patient_health_context, SAMPLE_PATIENTS

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from primitives import Persona


def render_patient_view():
    """Render the patient interface - single column."""
    c = COLORS

    # Initialize services
    if "cpg_loader" not in st.session_state:
        st.session_state.cpg_loader = CPGLoaderService()
    if "evaluator" not in st.session_state:
        st.session_state.evaluator = MultiCPGService(detect_conflicts=True)
    if "ranker" not in st.session_state:
        st.session_state.ranker = PriorityRanker()
    if "explanation_service" not in st.session_state:
        st.session_state.explanation_service = ExplanationService()

    explanation_service = st.session_state.explanation_service

    # Header
    _render_header()

    # Navigation
    current_section = st.session_state.get("current_section", "summary")
    _render_nav(current_section)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Content
    if current_section == "summary":
        _render_summary(explanation_service)
    elif current_section == "actions":
        _render_actions(explanation_service)
    elif current_section == "questions":
        _render_questions(explanation_service)
    elif current_section == "learn":
        _render_learn()

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
                ">Your Health Recommendations</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        if st.button("Provider View", use_container_width=True):
            st.session_state.view_mode = "provider"
            st.rerun()


def _render_nav(current: str):
    """Render navigation."""
    sections = [
        ("summary", "Summary"),
        ("actions", "Actions"),
        ("questions", "Questions"),
        ("learn", "Learn"),
    ]

    cols = st.columns(len(sections))

    for i, (section_id, label) in enumerate(sections):
        with cols[i]:
            is_current = current == section_id
            btn_type = "primary" if is_current else "secondary"
            if st.button(label, key=f"nav_{section_id}", use_container_width=True, type=btn_type):
                st.session_state.current_section = section_id
                st.rerun()


def _render_summary(explanation_service: ExplanationService):
    """Render summary section."""
    if "evaluation_summary" not in st.session_state:
        _render_welcome()
        return

    summary = st.session_state.evaluation_summary
    ranked = st.session_state.ranked_recommendations

    health_summary = explanation_service.generate_health_summary(summary, ranked)

    # Summary
    st.markdown("### Your Health Summary")
    st.write(health_summary.overall_status)

    # Metrics using columns
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Guidelines", summary.total_cpgs)
    with col2:
        st.metric("Recommendations", summary.applied_recommendations)
    st.markdown("---")

    # Key findings
    if health_summary.key_findings:
        st.markdown("### Key Findings")
        for finding in health_summary.key_findings[:5]:
            st.markdown(f"- {finding}")

    # Conflicts
    if summary.has_conflicts:
        render_conflict_panel(summary.conflicts, view_mode="patient")


def _render_welcome():
    """Render welcome screen."""
    st.markdown("## Your Health Recommendations")
    st.caption("Understand what guidelines recommend for you")

    st.markdown("")  # Spacer

    demo_patient = st.selectbox(
        "Select sample patient",
        options=list(SAMPLE_PATIENTS.keys()),
        format_func=lambda x: SAMPLE_PATIENTS[x]['name']
    )

    if st.button("Show Recommendations", type="primary", use_container_width=True):
        _run_demo(demo_patient)


def _run_demo(patient_id: str):
    """Run demo evaluation."""
    evaluator = st.session_state.evaluator
    ranker = st.session_state.ranker

    patient = SAMPLE_PATIENTS.get(patient_id)
    patient_name = patient["name"] if patient else patient_id
    health_context = get_patient_health_context(patient_id, Persona.patient)

    if not health_context:
        st.error("Could not load patient data")
        return

    with st.spinner("Checking recommendations..."):
        summary = evaluator.evaluate_multiple_cpgs(
            cpg_ids=["cholesterol", "statin", "hypertension", "diabetes"],
            health_context=health_context,
            patient_id=patient_id,
            patient_name=patient_name,
            persona=Persona.patient,
            parallel=True
        )
        ranked = ranker.rank_recommendations(summary)

        st.session_state.evaluation_summary = summary
        st.session_state.ranked_recommendations = ranked

    st.rerun()


def _render_actions(explanation_service: ExplanationService):
    """Render actions section."""
    st.markdown("## What You Can Do")

    if "ranked_recommendations" not in st.session_state:
        st.info("Run a health check first.")
        return

    ranked = st.session_state.ranked_recommendations

    if not ranked:
        st.success("● No specific actions needed")
        return

    urgent = [r for r in ranked if r.priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]]
    routine = [r for r in ranked if r.priority not in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]]

    if urgent:
        st.markdown("### Talk to Your Doctor Soon")
        for rec in urgent:
            explanation = explanation_service.explain_recommendation(rec)
            _render_action_card(explanation, urgent=True)

    if routine:
        st.markdown("### At Your Next Appointment")
        for rec in routine[:5]:
            explanation = explanation_service.explain_recommendation(rec)
            _render_action_card(explanation, urgent=False)


def _render_action_card(explanation, urgent: bool = False):
    """Render action card."""
    with st.container():
        st.markdown(f"**{explanation.title}**")
        st.write(explanation.summary)

        if explanation.what_you_can_do:
            for action in explanation.what_you_can_do[:3]:
                st.markdown(f"- {action}")

        st.markdown("---")


def _render_questions(explanation_service: ExplanationService):
    """Render questions section."""
    st.markdown("## Questions for Your Doctor")

    if "ranked_recommendations" not in st.session_state:
        st.info("Run a health check first.")
        return

    ranked = st.session_state.ranked_recommendations

    all_questions = []
    seen = set()

    for rec in ranked:
        explanation = explanation_service.explain_recommendation(rec)
        for q in explanation.questions_for_doctor:
            if q not in seen:
                all_questions.append({"question": q, "category": rec.category})
                seen.add(q)

    by_category = {}
    for item in all_questions:
        cat = item["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item["question"])

    for category, questions in by_category.items():
        st.markdown(f"### {category}")
        for q in questions:
            st.checkbox(q, key=f"q_{hash(q)}")

    st.markdown("### General Questions")

    general = [
        "What are the most important things I should focus on?",
        "Are there any lifestyle changes that could help me?",
        "How often should I follow up with you?",
    ]
    for q in general:
        st.checkbox(q, key=f"gen_{hash(q)}")

    st.caption("Tip: Print this page to bring to your appointment")


def _render_learn():
    """Render learn section."""
    st.markdown("## Learn More")

    resources = {
        "Heart Health": [
            "American Heart Association (heart.org)",
            "CDC Heart Disease Prevention",
        ],
        "Diabetes": [
            "American Diabetes Association (diabetes.org)",
            "CDC Diabetes Prevention",
        ],
        "General Health": [
            "MedlinePlus (medlineplus.gov)",
            "CDC (cdc.gov)",
            "NIH Health Information (nih.gov)",
        ],
    }

    for category, links in resources.items():
        with st.expander(category, expanded=True):
            for link in links:
                st.markdown(f"- {link}")

    st.info("**Remember:** These resources are for general information. Always discuss your specific health questions with your healthcare provider.")


def _render_footer():
    """Render footer."""
    st.markdown("---")
    st.caption("Powered by ConcordCore · Always consult your healthcare provider")
