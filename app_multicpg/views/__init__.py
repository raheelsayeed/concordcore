#!/usr/bin/env python3
"""View modules for the Multi-CPG app."""

from .provider_view import render_provider_view
from .patient_view import render_patient_view

__all__ = [
    "render_provider_view",
    "render_patient_view",
]
