#!/usr/bin/env python3
"""Main entry point for the Multi-CPG Evaluation App.

Run with: streamlit run app_multicpg/run.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from app_multicpg.styles import get_custom_css
from app_multicpg.views import render_provider_view, render_patient_view


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="ConcordCare",
        page_icon="⚕️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Apply custom styling
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # Initialize session state
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "provider"

    if "current_section" not in st.session_state:
        st.session_state.current_section = "overview"

    if "selected_cpgs" not in st.session_state:
        st.session_state.selected_cpgs = []

    # Render view
    if st.session_state.view_mode == "provider":
        render_provider_view()
    else:
        render_patient_view()


if __name__ == "__main__":
    main()
