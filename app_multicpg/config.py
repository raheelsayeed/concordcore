#!/usr/bin/env python3
"""Configuration for the Multi-CPG Evaluation App."""

from pathlib import Path
from dataclasses import dataclass, field

# Paths
APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parent
CPGS_DIR = PROJECT_ROOT / "cpgs"

# Available CPGs for evaluation
AVAILABLE_CPGS = [
    {
        "id": "cholesterol",
        "file": "cholesterol.yaml",
        "name": "Cholesterol Management (ACC/AHA 2019)",
        "category": "Cardiovascular",
        "description": "Primary prevention of atherosclerotic cardiovascular disease through lipid management",
    },
    {
        "id": "statin",
        "file": "uspstf_statinuse.yaml",
        "name": "Statin Use (USPSTF)",
        "category": "Cardiovascular",
        "description": "Statin use for primary prevention of cardiovascular disease",
    },
    {
        "id": "lung_cancer",
        "file": "screeninglungcancer.yaml",
        "name": "Lung Cancer Screening (USPSTF)",
        "category": "Cancer Screening",
        "description": "Lung cancer screening recommendations for high-risk individuals",
    },
    {
        "id": "hypertension",
        "file": "uspstf_hypertension_screening.yaml",
        "name": "Hypertension Screening (USPSTF)",
        "category": "Cardiovascular",
        "description": "Screening for high blood pressure in adults",
    },
    {
        "id": "diabetes",
        "file": "uspstf_diabetes_screening.yaml",
        "name": "Diabetes Screening (USPSTF)",
        "category": "Metabolic",
        "description": "Screening for prediabetes and type 2 diabetes",
    },
    {
        "id": "hiv",
        "file": "uspstf_hiv_screening.yaml",
        "name": "HIV Screening (USPSTF)",
        "category": "Infectious Disease",
        "description": "HIV screening recommendations for adolescents and adults",
    },
    {
        "id": "hepatitis_c",
        "file": "uspstf_hepatitis_c_screening.yaml",
        "name": "Hepatitis C Screening (USPSTF)",
        "category": "Infectious Disease",
        "description": "Hepatitis C virus infection screening",
    },
    {
        "id": "hepatitis_b",
        "file": "uspstf_hepatitis_b_screening.yaml",
        "name": "Hepatitis B Screening (USPSTF)",
        "category": "Infectious Disease",
        "description": "Hepatitis B virus infection screening",
    },
    {
        "id": "depression",
        "file": "uspstf_depression_screening.yaml",
        "name": "Depression Screening (USPSTF)",
        "category": "Mental Health",
        "description": "Screening for depression in adults",
    },
    {
        "id": "colorectal",
        "file": "uspstf_colorectal_cancer_screening.yaml",
        "name": "Colorectal Cancer Screening (USPSTF)",
        "category": "Cancer Screening",
        "description": "Colorectal cancer screening recommendations",
    },
    {
        "id": "cervical",
        "file": "scc.yaml",
        "name": "Cervical Cancer Screening",
        "category": "Cancer Screening",
        "description": "Cervical cancer screening for women",
    },
]

# CPG Categories
CPG_CATEGORIES = [
    "Cardiovascular",
    "Cancer Screening",
    "Metabolic",
    "Infectious Disease",
    "Mental Health",
]

# Evidence grade colors and descriptions
EVIDENCE_COLORS = {
    # Class of Recommendation (ACC/AHA)
    "I": {"color": "#28a745", "label": "Strong", "description": "Benefit >>> Risk"},
    "IIa": {"color": "#5cb85c", "label": "Moderate", "description": "Benefit >> Risk"},
    "IIb": {"color": "#f0ad4e", "label": "Weak", "description": "Benefit >= Risk"},
    "III": {"color": "#d9534f", "label": "Harmful", "description": "Risk > Benefit"},
    # USPSTF Grades
    "A": {"color": "#28a745", "label": "Strongly Recommended", "description": "High certainty of substantial benefit"},
    "B": {"color": "#5cb85c", "label": "Recommended", "description": "High certainty of moderate benefit"},
    "C": {"color": "#f0ad4e", "label": "Selective", "description": "Offer based on individual circumstances"},
    "D": {"color": "#d9534f", "label": "Not Recommended", "description": "No benefit or harms outweigh benefits"},
    "I_statement": {"color": "#6c757d", "label": "Insufficient Evidence", "description": "Cannot determine benefit/harm balance"},
}

# Conflict severity colors
CONFLICT_COLORS = {
    "LOW": "#17a2b8",
    "MEDIUM": "#ffc107",
    "HIGH": "#fd7e14",
    "CRITICAL": "#dc3545",
}

# UI Configuration
@dataclass
class UIConfig:
    """UI configuration settings."""

    # Page settings
    page_title: str = "ConcordCare - Multi-CPG Health Evaluation"
    page_icon: str = "🏥"
    layout: str = "wide"

    # Theme colors
    primary_color: str = "#0066cc"
    secondary_color: str = "#6c757d"
    success_color: str = "#28a745"
    warning_color: str = "#ffc107"
    danger_color: str = "#dc3545"

    # Provider view settings
    show_evidence_details: bool = True
    show_citations: bool = True
    show_expression_details: bool = False
    enable_conflict_resolution: bool = True

    # Patient view settings
    simplify_language: bool = True
    show_action_items: bool = True
    show_questions_for_doctor: bool = True
    enable_education_links: bool = True


UI_CONFIG = UIConfig()
