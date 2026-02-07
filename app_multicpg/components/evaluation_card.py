#!/usr/bin/env python3
"""Evaluation result display - crisp monotone design."""

import streamlit as st
from app_multicpg.styles import COLORS


def render_evaluation_summary(summary, view_mode: str = "provider"):
    """Render the overall evaluation summary."""
    pass


def render_evaluation_card(cpg_id: str, eval_result, view_mode: str = "provider"):
    """Render a single CPG evaluation result."""
    c = COLORS

    # Status
    if eval_result.is_eligible:
        status = "Eligible"
    elif eval_result.is_eligible is False:
        status = "Not Eligible"
    else:
        status = "Unknown"

    # Header
    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h3 style="font-size: 1.25rem; font-weight: 700; color: {c['text_primary']}; margin: 0 0 0.375rem 0;">{eval_result.cpg_title}</h3>
                    <span style="font-size: 0.875rem; color: {c['text_muted']};">{eval_result.cpg_publisher}</span>
                </div>
                <span style="background: {c['text_primary']}; color: {c['background']}; padding: 0.375rem 0.75rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;">{status}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    c = COLORS
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

    # Status
    if show_status:
        if applies is True:
            status_text = "Applies"
            status_style = f"background: {c['text_primary']}; color: {c['surface']};"
        elif has_error:
            status_text = "Error"
            status_style = f"background: {c['text_muted']}; color: {c['surface']};"
        else:
            status_text = "No"
            status_style = f"background: {c['border']}; color: {c['text_secondary']};"

    st.markdown(
        f"""
        <div style="padding: 1rem 0; border-bottom: 1.5px solid {c['border']};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem;">
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 1rem; color: {c['text_primary']};">{title}</div>
                    {"<div style='font-size: 0.9375rem; color: " + c['text_secondary'] + "; line-height: 1.6; margin-top: 0.375rem;'>" + narrative[:180] + ('...' if len(narrative) > 180 else '') + "</div>" if narrative else ""}
                </div>
                <div style="display: flex; gap: 0.5rem; flex-shrink: 0;">
                    {"<span style='" + status_style + " padding: 0.375rem 0.625rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;'>" + status_text + "</span>" if show_status else ""}
                    {"<span style='background: " + c['text_primary'] + "; color: " + c['background'] + "; padding: 0.375rem 0.625rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;'>" + grade_text + "</span>" if grade_text else ""}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Expression (if showing status - use streamlit code block)
    if show_status and expression:
        st.code(expression, language=None)


def _render_assessment(assessed_record):
    """Render a single assessment."""
    c = COLORS
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
        indicator = "!"
    else:
        indicator = "○"

    # Format value
    value_str = str(value) if value is not None else "—"
    if value_str.startswith("Val="):
        value_str = value_str[4:]
    # Truncate long values
    if len(value_str) > 40:
        value_str = value_str[:37] + "..."

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.625rem 0; border-bottom: 1.5px solid {c['accent_soft']};">
            <span style="font-size: 0.9375rem; color: {c['text_secondary']};">{indicator} {title}</span>
            <span style="font-size: 0.9375rem; font-weight: 700; color: {c['text_primary']};">{value_str}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
