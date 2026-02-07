#!/usr/bin/env python3
"""Sample patient data for demonstrating multi-CPG evaluation."""

import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.healthcontext import HealthContext
from primitives import Persona


# Sample patient profiles
# Note: Variable names match CPG definitions (e.g., cholesterol.yaml uses 'Chol', 'triglycerides', etc.)
# Also includes common aliases for broader CPG compatibility
SAMPLE_PATIENTS = {
    "patient_1": {
        "id": "patient_1",
        "name": "John Smith",
        "age": 55,
        "gender": "Male",
        "description": "Middle-aged male with cardiovascular risk factors",
        "data": {
            # Demographics
            "Age": 55,
            "Gender": "Male",
            "Ethnicity": "White",
            # Lipids (using CPG variable names)
            # LDL > 190 triggers high LDL recommendation
            "LDL": [195, 188, 192],  # Historical values showing very elevated LDL
            "HDL": 38,  # Lower HDL increases risk
            "triglycerides": 210,
            "Chol": 275,  # Total cholesterol
            # Metabolic
            "HbA_one_c": 5.9,
            "glu": 108,  # Fasting glucose
            "BMI": 29.5,
            # Vitals
            "bloodpressure": (145, 92),  # Higher BP
            # Conditions
            "diabetesMellitus": False,
            "htn": True,
            "is_smoker": False,
            # Medications
            "med_for_htn": True,
            "med_statins": False,
            "med_nonstatins_chol": False,
            # Risk factors
            "FamilyHxPrematureASCVD": True,
            "eGFR": 78,
            # Smoking history
            "pack_years": 15,
            "former_smoker": True,
            # USPSTF screening variables
            "ever_smoked": True,
            "years_since_quit": 5,
        },
    },
    "patient_2": {
        "id": "patient_2",
        "name": "Maria Garcia",
        "age": 48,
        "gender": "Female",
        "description": "Woman with metabolic syndrome indicators",
        "data": {
            # Demographics
            "Age": 48,
            "Gender": "Female",
            "Ethnicity": "Hispanic",
            # Lipids
            "LDL": [142, 138, 145],
            "HDL": 38,
            "triglycerides": 220,
            "Chol": 218,
            "elevated_tg": True,
            # Metabolic
            "HbA_one_c": 6.2,
            "glu": 118,
            "BMI": 32.1,
            # Vitals
            "bloodpressure": (142, 92),
            # Conditions
            "diabetesMellitus": False,
            "htn": True,
            "is_smoker": False,
            # Medications
            "med_for_htn": False,
            "med_statins": False,
            "med_nonstatins_chol": False,
            # Risk factors
            "FamilyHxPrematureASCVD": False,
            "eGFR": 92,
            # Smoking
            "pack_years": 0,
            "former_smoker": False,
            "ever_smoked": False,
        },
    },
    "patient_3": {
        "id": "patient_3",
        "name": "Robert Johnson",
        "age": 62,
        "gender": "Male",
        "description": "Older male with multiple risk factors, current smoker",
        "data": {
            # Demographics
            "Age": 62,
            "Gender": "Male",
            "Ethnicity": "African American",
            # Lipids
            "LDL": [185, 192, 178],
            "HDL": 35,
            "triglycerides": 195,
            "Chol": 268,
            # Metabolic
            "HbA_one_c": 6.8,
            "glu": 132,
            "BMI": 28.3,
            # Vitals
            "bloodpressure": (155, 98),
            # Conditions
            "diabetesMellitus": True,
            "htn": True,
            "is_smoker": True,
            # Medications
            "med_for_htn": True,
            "med_statins": False,
            "med_nonstatins_chol": False,
            # Risk factors
            "FamilyHxPrematureASCVD": True,
            "eGFR": 65,
            "ckd": False,
            # Smoking
            "pack_years": 40,
            "former_smoker": False,
            "ever_smoked": True,
            "current_smoker": True,
        },
    },
    "patient_4": {
        "id": "patient_4",
        "name": "Sarah Williams",
        "age": 35,
        "gender": "Female",
        "description": "Young woman, generally healthy",
        "data": {
            # Demographics
            "Age": 35,
            "Gender": "Female",
            "Ethnicity": "White",
            # Lipids
            "LDL": [95, 92],
            "HDL": 62,
            "triglycerides": 85,
            "Chol": 172,
            # Metabolic
            "HbA_one_c": 5.2,
            "glu": 88,
            "BMI": 23.5,
            # Vitals
            "bloodpressure": (118, 72),
            # Conditions
            "diabetesMellitus": False,
            "htn": False,
            "is_smoker": False,
            # Medications
            "med_for_htn": False,
            "med_statins": False,
            "med_nonstatins_chol": False,
            # Risk factors
            "FamilyHxPrematureASCVD": False,
            "eGFR": 105,
            # Smoking
            "pack_years": 0,
            "former_smoker": False,
            "ever_smoked": False,
        },
    },
    "patient_5": {
        "id": "patient_5",
        "name": "David Chen",
        "age": 70,
        "gender": "Male",
        "description": "Elderly male with controlled conditions",
        "data": {
            # Demographics
            "Age": 70,
            "Gender": "Male",
            "Ethnicity": "Asian",
            # Lipids
            "LDL": [88, 92, 85],
            "HDL": 48,
            "triglycerides": 145,
            "Chol": 165,
            # Metabolic
            "HbA_one_c": 6.4,
            "glu": 112,
            "BMI": 25.8,
            # Vitals
            "bloodpressure": (128, 78),
            # Conditions
            "diabetesMellitus": True,
            "htn": True,
            "is_smoker": False,
            # Medications
            "med_for_htn": True,
            "med_statins": True,
            "med_nonstatins_chol": False,
            # Risk factors
            "FamilyHxPrematureASCVD": False,
            "eGFR": 58,
            "ckd": True,
            # Smoking
            "pack_years": 25,
            "former_smoker": True,
            "ever_smoked": True,
            "years_since_quit": 20,
        },
    },
}


def get_sample_patient(patient_id: str) -> dict | None:
    """Get a sample patient by ID."""
    return SAMPLE_PATIENTS.get(patient_id)


def get_patient_health_context(
    patient_id: str,
    persona: Persona = Persona.patient
) -> HealthContext | None:
    """Get a HealthContext for a sample patient.

    Args:
        patient_id: The patient ID to look up
        persona: The persona for rendering (patient or provider)

    Returns:
        HealthContext if patient found, None otherwise
    """
    patient = get_sample_patient(patient_id)
    if not patient:
        return None

    return HealthContext.from_dict(patient["data"], persona=persona)


def create_custom_patient(
    data: dict[str, Any],
    name: str = "Custom Patient",
    persona: Persona = Persona.patient
) -> tuple[dict, HealthContext]:
    """Create a custom patient from provided data.

    Args:
        data: Dictionary of health data (Age, LDL, etc.)
        name: Display name for the patient
        persona: The persona for rendering

    Returns:
        Tuple of (patient_info_dict, HealthContext)
    """
    patient_info = {
        "id": "custom",
        "name": name,
        "age": data.get("Age", "Unknown"),
        "gender": data.get("Gender", "Unknown"),
        "description": "Custom patient data",
        "data": data,
    }

    context = HealthContext.from_dict(data, persona=persona)

    return patient_info, context
