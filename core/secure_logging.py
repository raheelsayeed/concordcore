#!/usr/bin/env python3
"""Secure logging utilities for ConcordCore.

Provides a logging wrapper that masks sensitive patient data including:
- Social Security Numbers (SSN)
- Medical Record Numbers (MRN)
- Dates of birth
- Other PII identifiers

This module helps ensure HIPAA compliance by preventing sensitive data
from appearing in log files.
"""

import logging
import re
from functools import lru_cache
from typing import Any


# Patterns for sensitive data that should be masked
SENSITIVE_PATTERNS = {
    # SSN patterns: XXX-XX-XXXX or XXXXXXXXX
    'ssn': re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),

    # Date of birth patterns: YYYY-MM-DD, MM/DD/YYYY, MM-DD-YYYY
    'dob': re.compile(r'\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b'),

    # MRN patterns: typically 6-10 digit numbers prefixed with MRN
    'mrn': re.compile(r'\bMRN[:\s]?\d{6,10}\b', re.IGNORECASE),

    # Email addresses
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),

    # Phone numbers
    'phone': re.compile(r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
}

# Variable IDs that contain sensitive demographic data
SENSITIVE_VARIABLE_IDS = frozenset({
    'Age',
    'Gender',
    'Sex',
    'Ethnicity',
    'Race',
    'DateOfBirth',
    'DOB',
    'SSN',
    'MRN',
    'Name',
    'Address',
    'Phone',
    'Email',
})


def mask_sensitive_data(message: str) -> str:
    """Mask sensitive data in a log message.

    Args:
        message: The log message to sanitize

    Returns:
        The sanitized message with sensitive data masked
    """
    if not isinstance(message, str):
        message = str(message)

    result = message

    for pattern_name, pattern in SENSITIVE_PATTERNS.items():
        result = pattern.sub(f'[{pattern_name.upper()}_MASKED]', result)

    return result


def mask_sensitive_dict(data: dict[str, Any], mask_value: str = '[MASKED]') -> dict[str, Any]:
    """Mask sensitive values in a dictionary.

    Args:
        data: Dictionary potentially containing sensitive data
        mask_value: The string to use for masking

    Returns:
        A new dictionary with sensitive values masked
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        # Check if key matches sensitive variable IDs
        key_upper = key.upper() if isinstance(key, str) else str(key).upper()
        is_sensitive = any(
            sensitive_id.upper() in key_upper
            for sensitive_id in SENSITIVE_VARIABLE_IDS
        )

        if is_sensitive:
            result[key] = mask_value
        elif isinstance(value, dict):
            result[key] = mask_sensitive_dict(value, mask_value)
        elif isinstance(value, str):
            result[key] = mask_sensitive_data(value)
        else:
            result[key] = value

    return result


class SecureLogFilter(logging.Filter):
    """Logging filter that masks sensitive data in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and sanitize the log record.

        Args:
            record: The log record to filter

        Returns:
            True (always allows the record through after sanitization)
        """
        if record.msg:
            if isinstance(record.msg, str):
                record.msg = mask_sensitive_data(record.msg)

        # Also sanitize args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = mask_sensitive_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True


class SecureLogger:
    """A logging wrapper that automatically masks sensitive data.

    Usage:
        logger = SecureLogger(__name__)
        logger.info(f"Processing patient SSN: 123-45-6789")
        # Logs: "Processing patient SSN: [SSN_MASKED]"
    """

    def __init__(self, name: str, level: int = logging.DEBUG):
        """Initialize the secure logger.

        Args:
            name: The logger name (typically __name__)
            level: The logging level
        """
        self._logger = logging.getLogger(name)
        self._logger.addFilter(SecureLogFilter())

    def _sanitize_message(self, msg: Any) -> str:
        """Sanitize a log message."""
        return mask_sensitive_data(str(msg))

    def debug(self, msg: Any, *args, **kwargs) -> None:
        """Log a debug message with sensitive data masked."""
        self._logger.debug(self._sanitize_message(msg), *args, **kwargs)

    def info(self, msg: Any, *args, **kwargs) -> None:
        """Log an info message with sensitive data masked."""
        self._logger.info(self._sanitize_message(msg), *args, **kwargs)

    def warning(self, msg: Any, *args, **kwargs) -> None:
        """Log a warning message with sensitive data masked."""
        self._logger.warning(self._sanitize_message(msg), *args, **kwargs)

    def error(self, msg: Any, *args, **kwargs) -> None:
        """Log an error message with sensitive data masked."""
        self._logger.error(self._sanitize_message(msg), *args, **kwargs)

    def critical(self, msg: Any, *args, **kwargs) -> None:
        """Log a critical message with sensitive data masked."""
        self._logger.critical(self._sanitize_message(msg), *args, **kwargs)

    def exception(self, msg: Any, *args, **kwargs) -> None:
        """Log an exception message with sensitive data masked."""
        self._logger.exception(self._sanitize_message(msg), *args, **kwargs)

    def setLevel(self, level: int) -> None:
        """Set the logging level."""
        self._logger.setLevel(level)


def get_secure_logger(name: str) -> SecureLogger:
    """Get a secure logger instance.

    This is the recommended way to get a logger in ConcordCore modules.

    Args:
        name: The logger name (typically __name__)

    Returns:
        A SecureLogger instance
    """
    return SecureLogger(name)
