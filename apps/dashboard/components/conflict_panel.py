#!/usr/bin/env python3
"""Conflict display - crisp monotone design."""

import streamlit as st
from apps.dashboard.styles import COLORS


def render_conflict_panel(conflicts, view_mode: str = "provider"):
    """Render conflict panel."""
    c = COLORS
    if not conflicts or not conflicts.conflicts:
        st.markdown(
            f"""
            <div style="padding: 1.25rem; background: {c['accent_soft']}; border-radius: 6px; border-left: 3px solid {c['text_muted']};">
                <span style="font-size: 1rem; color: {c['text_secondary']};">No conflicts detected — Guidelines are consistent</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    if view_mode == "provider":
        _render_provider_conflicts(conflicts)
    else:
        _render_patient_conflicts(conflicts)


def _render_provider_conflicts(conflicts):
    """Render provider-facing conflicts."""
    c = COLORS
    by_severity = {}
    for conflict in conflicts.conflicts:
        severity = conflict.severity.value if hasattr(conflict.severity, 'value') else str(conflict.severity)
        by_severity[severity] = by_severity.get(severity, 0) + 1

    severity_text = " · ".join([f"{count} {sev}" for sev, count in by_severity.items()])

    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem;">
            <span style="font-weight: 700; font-size: 1rem; color: {c['text_primary']};">{len(conflicts.conflicts)} conflict(s) detected</span>
            <span style="font-size: 0.875rem; color: {c['text_muted']}; margin-left: 0.5rem;">{severity_text}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    for conflict in conflicts.conflicts:
        _render_conflict_card(conflict)


def _render_conflict_card(conflict):
    """Render a conflict card."""
    c = COLORS
    severity = conflict.severity.value if hasattr(conflict.severity, 'value') else str(conflict.severity)
    conflict_type = conflict.conflict_type.value if hasattr(conflict.conflict_type, 'value') else str(conflict.conflict_type)

    cpg_list = []
    for involved in conflict.involved_cpgs:
        cpg_title = involved.get('cpg_title', involved.get('cpg_id', 'Unknown'))
        cpg_list.append(cpg_title)

    st.markdown(
        f"""
        <div style="padding: 1.25rem 0; border-bottom: 1.5px solid {c['border']};">
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.625rem;">
                <span style="background: {c['text_primary']}; color: {c['background']}; padding: 0.375rem 0.625rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">{severity}</span>
                <span style="font-size: 0.875rem; color: {c['text_muted']};">{conflict_type.replace('_', ' ').title()}</span>
            </div>
            <p style="font-size: 1rem; color: {c['text_secondary']}; margin: 0 0 0.625rem 0; line-height: 1.7;">{conflict.description}</p>
            <span style="font-size: 0.875rem; color: {c['text_muted']};">Involves: {' · '.join(cpg_list)}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Resolution
    if conflict.suggested_resolution:
        with st.expander("Suggested Resolution"):
            st.write(conflict.suggested_resolution)


def _render_patient_conflicts(conflicts):
    """Render patient-facing conflicts."""
    c = COLORS

    st.markdown(
        f"""
        <div style="padding: 1.25rem; background: {c['accent_soft']}; border-radius: 6px; border-left: 3px solid {c['text_muted']}; margin-bottom: 2rem;">
            <div style="font-weight: 700; font-size: 1rem; color: {c['text_primary']}; margin-bottom: 0.375rem;">Some Guidelines Have Different Recommendations</div>
            <p style="font-size: 1rem; color: {c['text_secondary']}; margin: 0; line-height: 1.6;">This is normal. Your doctor can help you understand what's best for your specific situation.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    for conflict in conflicts.conflicts:
        conflict_type = conflict.conflict_type.value if hasattr(conflict.conflict_type, 'value') else str(conflict.conflict_type)

        explanations = {
            "DIRECT_CONTRADICTION": "Different guidelines have opposite recommendations. Your doctor can explain which approach is best for you.",
            "TARGET_VALUE_MISMATCH": "Different guidelines suggest different target values. Your doctor can help set the right goals for you.",
            "DRUG_INTERACTION": "Some recommended medications may interact. Make sure to tell your doctor about all medications you take.",
        }
        explanation = explanations.get(conflict_type, "There are some differences between guidelines. Discuss with your doctor which options are best.")

        cpg_list = [inv.get('cpg_title', inv.get('cpg_id', 'Unknown'))[:40] for inv in conflict.involved_cpgs]

        st.markdown(
            f"""
            <div style="padding: 1rem 0; border-bottom: 1.5px solid {c['border']};">
                <p style="font-size: 1rem; color: {c['text_secondary']}; margin: 0 0 0.375rem 0; line-height: 1.7;">{explanation}</p>
                <span style="font-size: 0.875rem; color: {c['text_muted']};">Guidelines: {', '.join(cpg_list)}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
