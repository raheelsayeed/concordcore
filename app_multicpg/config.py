#!/usr/bin/env python3
"""Configuration for the Multi-CPG Evaluation App."""

from pathlib import Path
from dataclasses import dataclass, field

# Paths
APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parent
CPGS_DIR = PROJECT_ROOT / "cpgs"

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
