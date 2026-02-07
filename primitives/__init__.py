#!/usr/bin/env python3
"""Primitives module for ConcordCore.

This module provides basic types, codes, and utilities used throughout
the Concord framework.

Note: The `vlist` module is intentionally not imported here to maintain
backwards compatibility with code that imports it as a module
(e.g., `from primitives import vlist` then uses `vlist.vlist`).
"""

from .types import YMLStrEnum, Persona, ValueType
from .code import Code
from .varstring import VarString

__all__ = [
    # Types
    'YMLStrEnum',
    'Persona',
    'ValueType',
    # Code
    'Code',
    # Utilities
    'VarString',
]
