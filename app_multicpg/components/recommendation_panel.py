#!/usr/bin/env python3
"""Recommendation display - crisp monotone design."""

import streamlit as st
from app_multicpg.services import RankedRecommendation, PriorityLevel
from app_multicpg.styles import COLORS


PRIORITY_LABELS = {
    PriorityLevel.CRITICAL: "Critical",
    PriorityLevel.HIGH: "High",
    PriorityLevel.MODERATE: "Moderate",
    PriorityLevel.LOW: "Low",
    PriorityLevel.INFORMATIONAL: "Info",
}


def render_recommendation_panel(
    ranked_recommendations: list[RankedRecommendation],
    view_mode: str = "provider"
):
    """Render the recommendation panel."""
    if not ranked_recommendations:
        st.info("No recommendations to display")
        return

    # Filter controls
    if view_mode == "provider":
        categories = list(set(r.category for r in ranked_recommendations))

        col1, col2 = st.columns([3, 1])
        with col1:
            filter_category = st.multiselect(
                "Filter by category",
                options=categories,
                default=[],
            )
        with col2:
            show_conflicts = st.checkbox("Conflicts only")

        filtered = ranked_recommendations
        if filter_category:
            filtered = [r for r in filtered if r.category in filter_category]
        if show_conflicts:
            filtered = [r for r in filtered if r.conflicts_with]
    else:
        filtered = ranked_recommendations

    # Display
    for rec in filtered:
        _render_card(rec)


def _render_card(rec: RankedRecommendation):
    """Render a recommendation card."""
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

    priority_label = PRIORITY_LABELS.get(rec.priority, "")
    conflict_marker = " · Conflict" if rec.conflicts_with else ""

    st.markdown(
        f"""
        <div style="padding: 1.25rem 0; border-bottom: 1.5px solid {c['border']};">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                <span style="font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: {c['text_muted']};">
                    {priority_label} · {rec.category}{conflict_marker}
                </span>
                {"<span style='background:" + c['text_primary'] + ";color:" + c['background'] + ";padding:0.375rem 0.625rem;border-radius:4px;font-size:0.75rem;font-weight:700;'>" + grade_text + "</span>" if grade_text else ""}
            </div>
            <div style="font-weight: 700; font-size: 1rem; color: {c['text_primary']}; margin-bottom: 0.375rem;">{title}</div>
            {"<div style='font-size: 1rem; color: " + c['text_secondary'] + "; line-height: 1.7; margin-bottom: 0.5rem;'>" + (narrative[:200] + '...' if len(narrative) > 200 else narrative) + "</div>" if narrative else ""}
            <div style="font-size: 0.875rem; color: {c['text_muted']};">{rec.cpg_title}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_recommendation_summary_stats(recommendations: list[RankedRecommendation]):
    """Render summary stats."""
    if not recommendations:
        return

    by_priority = {}
    for rec in recommendations:
        by_priority[rec.priority] = by_priority.get(rec.priority, 0) + 1

    stats = []
    for priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH, PriorityLevel.MODERATE, PriorityLevel.LOW]:
        if priority in by_priority:
            stats.append(f"{by_priority[priority]} {PRIORITY_LABELS[priority]}")

    if stats:
        st.caption(" · ".join(stats))
