#!/usr/bin/env python3
"""CPG selection component - single column monotone."""

import streamlit as st
from apps.dashboard.config import AVAILABLE_CPGS, CPG_CATEGORIES
from apps.dashboard.services import CPGLoaderService
from apps.dashboard.styles import COLORS


def render_cpg_selector(loader: CPGLoaderService) -> list[str]:
    """Render CPG selection."""
    c = COLORS

    available = loader.get_available_cpgs()
    by_category = loader.get_cpgs_by_category()

    # Quick select buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("All", key="select_all", use_container_width=True):
            st.session_state.selected_cpgs = [cpg["id"] for cpg in available]
            st.rerun()

    with col2:
        if st.button("None", key="select_none", use_container_width=True):
            st.session_state.selected_cpgs = []
            st.rerun()

    with col3:
        if st.button("CV Only", key="select_cv", use_container_width=True):
            st.session_state.selected_cpgs = [
                cpg["id"] for cpg in available
                if cpg.get("category") == "Cardiovascular"
            ]
            st.rerun()

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    selected = st.session_state.get("selected_cpgs", [])

    for category in CPG_CATEGORIES:
        if category not in by_category:
            continue

        cpgs = by_category[category]

        with st.expander(f"{category} ({len(cpgs)})", expanded=True):
            for cpg in cpgs:
                is_selected = cpg["id"] in selected

                col1, col2 = st.columns([5, 1])

                with col1:
                    weight = "700" if is_selected else "400"
                    color = c['text_primary'] if is_selected else c['text_secondary']
                    st.markdown(
                        f'<p style="color: {color}; font-weight: {weight}; font-size: 1rem; margin: 0.5rem 0; line-height: 1.4;">{cpg["name"]}</p>',
                        unsafe_allow_html=True
                    )

                with col2:
                    if st.checkbox("", value=is_selected, key=f"cpg_{cpg['id']}", label_visibility="collapsed"):
                        if cpg["id"] not in selected:
                            selected.append(cpg["id"])
                    else:
                        if cpg["id"] in selected:
                            selected.remove(cpg["id"])

    st.session_state.selected_cpgs = selected

    st.markdown(
        f"""
        <div style="
            background: {c['accent_soft']};
            border: 1.5px solid {c['border']};
            border-radius: 6px;
            padding: 1rem;
            text-align: center;
            margin-top: 1.25rem;
        ">
            <span style="color: {c['text_primary']}; font-weight: 900; font-size: 1.125rem;">{len(selected)}</span>
            <span style="color: {c['text_muted']}; font-size: 1rem; margin-left: 0.5rem;">guidelines selected</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    return selected


def render_cpg_quick_select() -> list[str]:
    """Render quick select widget."""
    options = {cpg["id"]: cpg["name"] for cpg in AVAILABLE_CPGS}

    selected = st.multiselect(
        "Select Guidelines",
        options=list(options.keys()),
        default=st.session_state.get("selected_cpgs", []),
        format_func=lambda x: options.get(x, x),
    )

    st.session_state.selected_cpgs = selected
    return selected
