#!/usr/bin/env python3
"""Evaluation result display - single column monotone."""

import streamlit as st


def render_evaluation_summary(summary, view_mode: str = "provider"):
    """Render the overall evaluation summary."""
    pass


def render_evaluation_card(cpg_id: str, eval_result, view_mode: str = "provider"):
    """Render a single CPG evaluation result."""
    # Status
    if eval_result.is_eligible:
        status = "Eligible"
    elif eval_result.is_eligible is False:
        status = "Not Eligible"
    else:
        status = "Unknown"

    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### {eval_result.cpg_title}")
        st.caption(eval_result.cpg_publisher)
    with col2:
        st.markdown(f"**{status}**")

    # Stats row using columns
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Assessments", len(eval_result.assessments))
    with col2:
        st.metric("Total", len(eval_result.all_recommendations))
    with col3:
        st.metric("Applied", len(eval_result.applied_recommendations))
    st.markdown("---")

    if eval_result.error:
        st.error(f"Evaluation error: {eval_result.error}")
        return

    # Tabs
    tabs = st.tabs(["Applied", "All Recommendations", "Assessments"])

    with tabs[0]:
        _render_applied_tab(eval_result)

    with tabs[1]:
        _render_all_recommendations_tab(eval_result)

    with tabs[2]:
        _render_assessments_tab(eval_result)


def _render_applied_tab(eval_result):
    """Render applied recommendations tab."""
    if not eval_result.applied_recommendations:
        st.info("No recommendations apply to this patient")
        return

    st.markdown(f"**{len(eval_result.applied_recommendations)} recommendation(s) apply**")

    for rec in eval_result.applied_recommendations:
        _render_recommendation(rec, show_status=False)


def _render_all_recommendations_tab(eval_result):
    """Render all recommendations tab."""
    if not eval_result.all_recommendations:
        st.info("No recommendations in this CPG")
        return

    st.caption(f"{len(eval_result.all_recommendations)} total recommendations")

    for rec in eval_result.all_recommendations:
        _render_recommendation(rec, show_status=True)


def _render_assessments_tab(eval_result):
    """Render assessments tab."""
    if not eval_result.assessments:
        st.info("No assessments available")
        return

    st.caption(f"{len(eval_result.assessments)} assessments")

    for assessment in eval_result.assessments:
        _render_assessment(assessment)


def _render_recommendation(rec, show_status: bool = False):
    """Render a single recommendation."""
    rec_var = getattr(rec, 'recommendation', rec)
    title = getattr(rec_var, 'title', None) or getattr(rec_var, 'id', 'Recommendation')
    narrative = getattr(rec, 'narrative', '') or ''
    expression = getattr(rec_var, 'expression', '') or ''
    applies = getattr(rec, 'applies', None)
    has_error = getattr(rec, 'error', None) is not None

    # Evidence grade
    class_of_rec = getattr(rec_var, 'class_of_recommendation', None)
    uspstf = getattr(rec_var, 'uspstf_grade', None)
    grade_text = ""
    if class_of_rec:
        grade = class_of_rec.value if hasattr(class_of_rec, 'value') else str(class_of_rec)
        grade_text = f"Class {grade}"
    elif uspstf:
        grade = uspstf.value if hasattr(uspstf, 'value') else str(uspstf)
        grade_text = f"Grade {grade}"

    # Status text
    status_text = ""
    if show_status:
        if applies is True:
            status_text = "● APPLIES"
        elif has_error:
            status_text = "⚠ ERROR"
        else:
            status_text = "○ Does not apply"

    with st.container():
        # Status and grade row
        col1, col2 = st.columns([3, 1])
        with col1:
            if status_text:
                if applies:
                    st.markdown(f"**{status_text}**")
                else:
                    st.caption(status_text)
        with col2:
            if grade_text:
                st.markdown(f"**{grade_text}**")

        # Title
        st.markdown(f"**{title}**")

        # Narrative
        if narrative:
            st.write(narrative)

        # Expression (if showing status)
        if show_status and expression:
            st.code(expression, language=None)

        st.markdown("---")


def _render_assessment(assessed_record):
    """Render a single assessment."""
    var_id = getattr(assessed_record, 'id', 'Unknown')

    # Title
    title = var_id
    if hasattr(assessed_record, 'record'):
        record = assessed_record.record
        if hasattr(record, 'var') and hasattr(record.var, 'title'):
            title = record.var.title or var_id

    # Value
    value = None
    if hasattr(assessed_record, 'record') and hasattr(assessed_record.record, 'value'):
        value = assessed_record.record.value

    # Result
    eval_result = getattr(assessed_record, 'evaluation_result', None)
    error = getattr(assessed_record, 'error', None)

    if eval_result is not None:
        result_str = str(eval_result.value if hasattr(eval_result, 'value') else eval_result).lower()
        if 'success' in result_str:
            indicator = "●"
        elif 'fail' in result_str:
            indicator = "○"
        else:
            indicator = "◐"
    elif error:
        indicator = "⚠"
    else:
        indicator = "○"

    # Format value
    value_str = str(value) if value is not None else "—"
    if value_str.startswith("Val="):
        value_str = value_str[4:]
    # Truncate long values
    if len(value_str) > 50:
        value_str = value_str[:47] + "..."

    # Use columns for layout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"{indicator} {title}")
    with col2:
        st.markdown(f"**{value_str}**")
