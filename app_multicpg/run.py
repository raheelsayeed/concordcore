#!/usr/bin/env python3
"""Concord - Clinical Guideline Evaluation App.

A streamlined provider-focused interface for evaluating patients
against clinical practice guidelines.

Run with: streamlit run app_multicpg/run.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from app_multicpg.styles import get_custom_css
from app_multicpg.views.main_view import render_main_view


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Concord — Clinical Guidelines",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(get_custom_css(), unsafe_allow_html=True)

    if "selected_cpgs" not in st.session_state:
        st.session_state.selected_cpgs = []

    if "selected_patient" not in st.session_state:
        st.session_state.selected_patient = None

    render_main_view()


if __name__ == "__main__":
    main()
