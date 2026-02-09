#!/usr/bin/env python3
"""Deprecated: Error classes have moved to core.errors.

This module re-exports error classes from core.errors for backwards compatibility.
Import directly from core.errors instead:

    from concordcore.core.errors import ExpressionError, VarError, VariableEvaluationError
"""

import warnings

# Re-export all error classes from core.errors for backwards compatibility
from concordcore.core.errors import (
    ConcordError,
    ExpressionError,
    ExpressionEvaluationError,
    ExpressionVariableNotFound,
    VarError,
    VariableEvaluationError,
    SecurityError,
    NeedAttestationError,
    FHIRParseError,
)

__all__ = [
    'ConcordError',
    'ExpressionError',
    'ExpressionEvaluationError',
    'ExpressionVariableNotFound',
    'VarError',
    'VariableEvaluationError',
    'SecurityError',
    'NeedAttestationError',
    'FHIRParseError',
]

# Issue deprecation warning when this module is imported directly
warnings.warn(
    "primitives.errors is deprecated. Import from core.errors instead.",
    DeprecationWarning,
    stacklevel=2
)
