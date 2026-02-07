#!/usr/bin/env python3
"""Conflict display - single column monotone."""

import streamlit as st


def render_conflict_panel(conflicts, view_mode: str = "provider"):
    """Render conflict panel."""
    if not conflicts or not conflicts.conflicts:
        st.success("● No conflicts detected - Guidelines are consistent")
        return

    if view_mode == "provider":
        _render_provider_conflicts(conflicts)
    else:
        _render_patient_conflicts(conflicts)


def _render_provider_conflicts(conflicts):
    """Render provider-facing conflicts."""
    by_severity = {}
    for conflict in conflicts.conflicts:
        severity = conflict.severity.value if hasattr(conflict.severity, 'value') else str(conflict.severity)
        by_severity[severity] = by_severity.get(severity, 0) + 1

    severity_text = " · ".join([f"{count} {sev}" for sev, count in by_severity.items()])

    st.markdown(f"**{len(conflicts.conflicts)} conflict(s) detected**")
    st.caption(severity_text)

    for conflict in conflicts.conflicts:
        _render_conflict_card(conflict)


def _render_conflict_card(conflict):
    """Render a conflict card."""
    severity = conflict.severity.value if hasattr(conflict.severity, 'value') else str(conflict.severity)
    conflict_type = conflict.conflict_type.value if hasattr(conflict.conflict_type, 'value') else str(conflict.conflict_type)

    cpg_list = []
    for involved in conflict.involved_cpgs:
        cpg_title = involved.get('cpg_title', involved.get('cpg_id', 'Unknown'))
        cpg_list.append(cpg_title)

    with st.container():
        # Header
        st.markdown(f"**{severity.upper()}** · {conflict_type.replace('_', ' ')}")

        # Description
        st.write(conflict.description)

        # Involved CPGs
        st.caption(f"Involves: {' · '.join(cpg_list)}")

        # Resolution
        if conflict.suggested_resolution:
            with st.expander("Suggested Resolution"):
                st.write(conflict.suggested_resolution)

        st.markdown("---")


def _render_patient_conflicts(conflicts):
    """Render patient-facing conflicts."""
    st.info("**Some Guidelines Have Different Recommendations** - This is normal and your doctor can help you understand what's best for your specific situation.")

    for conflict in conflicts.conflicts:
        conflict_type = conflict.conflict_type.value if hasattr(conflict.conflict_type, 'value') else str(conflict.conflict_type)

        explanations = {
            "DIRECT_CONTRADICTION": "Different guidelines have opposite recommendations. Your doctor can explain which approach is best for you.",
            "TARGET_VALUE_MISMATCH": "Different guidelines suggest different target values. Your doctor can help set the right goals for you.",
            "DRUG_INTERACTION": "Some recommended medications may interact. Make sure to tell your doctor about all medications you take.",
        }
        explanation = explanations.get(conflict_type, "There are some differences between guidelines. Discuss with your doctor which options are best.")

        cpg_list = [inv.get('cpg_title', inv.get('cpg_id', 'Unknown'))[:40] for inv in conflict.involved_cpgs]

        st.markdown(explanation)
        st.caption(f"Guidelines: {', '.join(cpg_list)}")
        st.markdown("---")
