#!/usr/bin/env python3
"""Patient selection and data input components - Monotone UI."""

import streamlit as st
from apps.dashboard.data import SAMPLE_PATIENTS, get_sample_patient
from apps.dashboard.styles import COLORS


def render_patient_selector() -> str | None:
    """Render patient selection interface.

    Returns:
        Selected patient ID or None
    """
    c = COLORS

    # Tabs for sample vs custom
    tab1, tab2 = st.tabs(["Sample Patients", "Custom"])

    with tab1:
        selected = st.session_state.get("selected_patient")

        for patient_id, patient in SAMPLE_PATIENTS.items():
            is_selected = selected == patient_id

            # Patient card - monotone style
            border_color = c['text_primary'] if is_selected else c['border']
            bg_color = c['accent_soft'] if is_selected else c['surface']

            col1, col2 = st.columns([4, 1])

            with col1:
                weight = "700" if is_selected else "400"
                st.markdown(
                    f"""
                    <div style="background: {bg_color}; border: 1.5px solid {border_color}; border-radius: 6px; padding: 1rem; margin-bottom: 0.5rem;">
                        <div style="font-weight: {weight}; color: {c['text_primary']}; margin-bottom: 0.25rem; font-size: 1rem;">{patient['name']}</div>
                        <div style="color: {c['text_muted']}; font-size: 0.875rem;">Age {patient['age']} · {patient['gender']}</div>
                        <div style="color: {c['text_secondary']}; font-size: 0.875rem; margin-top: 0.25rem; line-height: 1.5;">{patient['description']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                if st.button(
                    "✓" if is_selected else "Select",
                    key=f"select_{patient_id}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True
                ):
                    st.session_state.selected_patient = patient_id
                    st.session_state.custom_patient_data = None
                    st.rerun()

        return st.session_state.get("selected_patient")

    with tab2:
        return render_custom_patient_form()


def render_custom_patient_form() -> str | None:
    """Render custom patient data entry form.

    Returns:
        "custom" if custom data entered, None otherwise
    """
    c = COLORS

    with st.form("custom_patient_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f'<p style="color: {c["text_muted"]}; font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.375rem;">Demographics</p>', unsafe_allow_html=True)
            age = st.number_input("Age", min_value=18, max_value=100, value=55)
            gender = st.selectbox("Gender", ["Male", "Female"])

            st.markdown(f'<p style="color: {c["text_muted"]}; font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0.75rem 0 0.375rem 0;">Lipids</p>', unsafe_allow_html=True)
            ldl = st.number_input("LDL (mg/dL)", min_value=30, max_value=400, value=150)
            hdl = st.number_input("HDL (mg/dL)", min_value=20, max_value=150, value=45)
            total_chol = st.number_input("Total Cholesterol", min_value=100, max_value=500, value=220)

        with col2:
            st.markdown(f'<p style="color: {c["text_muted"]}; font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.375rem;">Vitals</p>', unsafe_allow_html=True)
            systolic = st.number_input("Systolic BP", min_value=80, max_value=220, value=130)
            diastolic = st.number_input("Diastolic BP", min_value=50, max_value=140, value=85)
            bmi = st.number_input("BMI", min_value=15.0, max_value=60.0, value=27.0, step=0.1)

            st.markdown(f'<p style="color: {c["text_muted"]}; font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0.75rem 0 0.375rem 0;">Conditions</p>', unsafe_allow_html=True)
            diabetes = st.checkbox("Diabetes")
            hypertension = st.checkbox("Hypertension")
            smoker = st.checkbox("Current Smoker")

        submitted = st.form_submit_button("Use Custom Data", use_container_width=True)

        if submitted:
            patient_data = {
                "Age": age,
                "Gender": gender,
                "LDL": ldl,
                "HDL": hdl,
                "Chol": total_chol,
                "bloodpressure": (systolic, diastolic),
                "BMI": bmi,
                "diabetesMellitus": diabetes,
                "htn": hypertension,
                "is_smoker": smoker,
                "med_statins": False,
            }

            st.session_state.custom_patient_data = patient_data
            st.session_state.selected_patient = "custom"
            return "custom"

    return st.session_state.get("selected_patient") if st.session_state.get("custom_patient_data") else None


def render_patient_info(patient_id: str):
    """Render patient information card.

    Args:
        patient_id: The patient ID to display
    """
    c = COLORS

    if patient_id == "custom":
        data = st.session_state.get("custom_patient_data", {})
        name = "Custom Patient"
        age = data.get("Age", "Unknown")
        gender = data.get("Gender", "Unknown")
    else:
        patient = get_sample_patient(patient_id)
        if not patient:
            return
        data = patient["data"]
        name = patient["name"]
        age = patient["age"]
        gender = patient["gender"]

    # Get LDL value
    ldl = data.get('LDL', 'N/A')
    if isinstance(ldl, list):
        ldl = ldl[0] if ldl else 'N/A'

    # Get conditions
    conditions = []
    if data.get('diabetesMellitus'):
        conditions.append("Diabetes")
    if data.get('htn'):
        conditions.append("HTN")
    if data.get('is_smoker'):
        conditions.append("Smoker")

    st.markdown(
        f"""
        <div style="background: {c['surface']}; border: 1.5px solid {c['border']}; border-radius: 6px; padding: 1.25rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <div style="font-size: 1.0625rem; font-weight: 700; color: {c['text_primary']};">{name}</div>
                    <div style="color: {c['text_muted']}; font-size: 0.9375rem;">{age} years · {gender}</div>
                </div>
                <div style="display: flex; gap: 1.5rem;">
                    <div style="text-align: center;">
                        <div style="color: {c['text_muted']}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">LDL</div>
                        <div style="color: {c['text_primary']}; font-weight: 900; font-size: 1rem;">{ldl}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="color: {c['text_muted']}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">Conditions</div>
                        <div style="color: {c['text_primary']}; font-weight: 900; font-size: 1rem;">{', '.join(conditions) if conditions else 'None'}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
