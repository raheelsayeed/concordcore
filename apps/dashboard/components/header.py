#!/usr/bin/env python3
"""Header and navigation components - Artistic UI (concor.ai inspired)."""

import streamlit as st
from apps.dashboard.styles import COLORS


def render_header(view_mode: str = "provider"):
    """Render the app header."""
    c = COLORS

    col1, col2, col3 = st.columns([2, 4, 2])

    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center;">
                <span style="
                    font-size: 1.375rem;
                    font-weight: 900;
                    color: {c['text_primary']};
                    letter-spacing: -0.02em;
                ">ConcordCare</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        subtitle = "Clinical Decision Support" if view_mode == "provider" else "Your Health Recommendations"
        st.markdown(
            f'''
            <p style="
                text-align: center;
                color: {c['text_muted']};
                margin: 0;
                font-size: 1rem;
            ">{subtitle}</p>
            ''',
            unsafe_allow_html=True
        )

    with col3:
        col_a, col_b = st.columns([1, 1])
        with col_b:
            if view_mode == "provider":
                if st.button("Patient View", key="switch_to_patient", use_container_width=True):
                    st.session_state.view_mode = "patient"
                    st.rerun()
            else:
                if st.button("Provider View", key="switch_to_provider", use_container_width=True):
                    st.session_state.view_mode = "provider"
                    st.rerun()

    st.markdown(f"<hr style='margin: 1.5rem 0; border-color: {c['border']};'>", unsafe_allow_html=True)


def render_sidebar_navigation(view_mode: str = "provider"):
    """Render sidebar navigation."""
    c = COLORS

    with st.sidebar:
        # Logo/Brand - minimal
        st.markdown(
            f"""
            <div style="
                padding: 1rem 0 2.5rem 0;
                border-bottom: 1px solid {c['border']};
                margin-bottom: 2rem;
            ">
                <div style="
                    font-size: 1.375rem;
                    font-weight: 900;
                    color: {c['text_primary']};
                    letter-spacing: -0.02em;
                    margin-bottom: 0.25rem;
                ">ConcordCare</div>
                <div style="
                    font-size: 0.8125rem;
                    color: {c['text_muted']};
                    letter-spacing: 0.1em;
                    text-transform: uppercase;
                ">Multi-CPG</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if view_mode == "provider":
            sections = [
                ("overview", "Overview"),
                ("recommendations", "Recommendations"),
                ("cpg_details", "CPG Details"),
                ("conflicts", "Conflicts"),
                ("patient_data", "Patient Data"),
            ]
        else:
            sections = [
                ("summary", "My Summary"),
                ("actions", "What I Can Do"),
                ("questions", "Questions"),
                ("learn", "Learn More"),
            ]

        selected = st.session_state.get("current_section", sections[0][0])

        st.markdown(
            f'''
            <p style="
                color: {c['text_muted']};
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.15em;
                margin-bottom: 1rem;
            ">Navigation</p>
            ''',
            unsafe_allow_html=True
        )

        for section_id, label in sections:
            is_selected = selected == section_id
            button_style = "primary" if is_selected else "secondary"

            if st.button(
                label,
                key=f"nav_{section_id}",
                use_container_width=True,
                type=button_style
            ):
                st.session_state.current_section = section_id
                st.rerun()

        # Stats section
        if "evaluation_summary" in st.session_state:
            st.markdown(f"<hr style='margin: 2.5rem 0; border-color: {c['border']};'>", unsafe_allow_html=True)

            summary = st.session_state.evaluation_summary

            st.markdown(
                f'''
                <p style="
                    color: {c['text_muted']};
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    letter-spacing: 0.15em;
                    margin-bottom: 1rem;
                ">Quick Stats</p>
                ''',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"""
                    <div>
                        <div style="
                            font-size: 2rem;
                            font-weight: 900;
                            color: {c['text_primary']};
                            letter-spacing: -0.02em;
                        ">{summary.total_cpgs}</div>
                        <div style="
                            color: {c['text_muted']};
                            font-size: 0.75rem;
                            text-transform: uppercase;
                            letter-spacing: 0.1em;
                        ">CPGs</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(
                    f"""
                    <div>
                        <div style="
                            font-size: 2rem;
                            font-weight: 900;
                            color: {c['text_primary']};
                            letter-spacing: -0.02em;
                        ">{summary.applied_recommendations}</div>
                        <div style="
                            color: {c['text_muted']};
                            font-size: 0.75rem;
                            text-transform: uppercase;
                            letter-spacing: 0.1em;
                        ">Recs</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if summary.has_conflicts:
                st.markdown(
                    f"""
                    <div style="
                        background: {c['accent_soft']};
                        border: 1px solid {c['border']};
                        border-left: 3px solid {c['text_primary']};
                        border-radius: 8px;
                        padding: 1rem;
                        margin-top: 1.5rem;
                    ">
                        <div style="
                            color: {c['text_primary']};
                            font-size: 1rem;
                            font-weight: 700;
                        ">{len(summary.conflicts.conflicts)} Conflicts</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


def render_footer():
    """Render the app footer."""
    c = COLORS

    st.markdown(
        f"""
        <div style="
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid {c['border']};
            text-align: center;
        ">
            <p style="
                color: {c['text_muted']};
                font-size: 0.9375rem;
                margin: 0;
                line-height: 1.6;
            ">
                Powered by ConcordCore · Evidence-based clinical guidelines · Always consult your healthcare provider
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
