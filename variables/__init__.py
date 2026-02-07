#!/usr/bin/env python3
"""Variables module for ConcordCore.

This module provides the data model for CPG variables, values, and records.
"""

from .var import Var
from .value import Value
from .record import Record

__all__ = [
    'Var',
    'Value',
    'Record',
]
