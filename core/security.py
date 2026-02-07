#!/usr/bin/env python3
"""Security utilities for ConcordCore.

Provides validation and sanitization for module loading and path operations
to prevent path traversal attacks and unauthorized code execution.
"""

import os
import re
import logging
from pathlib import Path
from typing import Tuple

from .errors import SecurityError

log = logging.getLogger(__name__)


# Allowlist of permitted directories for module loading (relative to project root)
ALLOWED_MODULE_DIRECTORIES = [
    'cpgs',
]


def sanitize_module_name(module_name: str) -> str | None:
    """Sanitize a module name to prevent injection attacks.

    Module names must contain only alphanumeric characters and underscores.

    Args:
        module_name: The module name to sanitize

    Returns:
        The sanitized module name if valid, None otherwise
    """
    if not module_name:
        return None

    # Module names should only contain alphanumeric characters and underscores
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    if re.match(pattern, module_name):
        return module_name

    log.warning(f"Invalid module name rejected: {module_name}")
    return None


def validate_module_path(base_directory: str, module_name: str) -> Tuple[bool, str | None]:
    """Validate that a module path is safe to load.

    Checks for:
    - Path traversal attempts (../)
    - Absolute paths
    - Symbolic link escapes
    - Module is within allowed directories

    Args:
        base_directory: The base directory where modules should reside
        module_name: The name of the module (without .py extension)

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    if not module_name:
        return False, "Module name is empty"

    if not base_directory:
        return False, "Base directory is empty"

    # Check for path traversal in module name
    if '..' in module_name or '/' in module_name or '\\' in module_name:
        return False, f"Path traversal detected in module name: {module_name}"

    # Resolve the base directory to absolute path
    try:
        base_path = Path(base_directory).resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid base directory: {e}"

    # Construct the full module path
    module_path = base_path / f"{module_name}.py"

    try:
        # Resolve the full path (follows symlinks)
        resolved_path = module_path.resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid module path: {e}"

    # Verify the resolved path is still within the base directory
    try:
        resolved_path.relative_to(base_path)
    except ValueError:
        return False, f"Module path escapes base directory: {resolved_path}"

    # Check if base directory is in allowed directories
    if ALLOWED_MODULE_DIRECTORIES:
        base_name = base_path.name
        if base_name not in ALLOWED_MODULE_DIRECTORIES:
            # Also check parent directories
            is_allowed = False
            for part in base_path.parts:
                if part in ALLOWED_MODULE_DIRECTORIES:
                    is_allowed = True
                    break
            if not is_allowed:
                return False, f"Module directory not in allowlist: {base_name}"

    # Verify the module file exists
    if not resolved_path.exists():
        # This is not a security error, just a missing file
        return True, None

    # Verify it's a regular file (not a directory, device, etc.)
    if not resolved_path.is_file():
        return False, f"Module path is not a regular file: {resolved_path}"

    log.debug(f"Module path validated: {resolved_path}")
    return True, None


def validate_cpg_filepath(filepath: str) -> Tuple[bool, str | None]:
    """Validate that a CPG file path is safe to load.

    Args:
        filepath: The path to the CPG YAML file

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    if not filepath:
        return False, "Filepath is empty"

    # Check for null bytes (common injection technique)
    if '\x00' in filepath:
        return False, "Null byte detected in filepath"

    try:
        path = Path(filepath)
        resolved = path.resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid filepath: {e}"

    # Verify it's a YAML file
    if resolved.suffix.lower() not in ['.yaml', '.yml']:
        return False, f"CPG file must be a YAML file, got: {resolved.suffix}"

    # Verify it exists and is a file
    if not resolved.exists():
        return False, f"CPG file does not exist: {resolved}"

    if not resolved.is_file():
        return False, f"CPG path is not a regular file: {resolved}"

    return True, None
