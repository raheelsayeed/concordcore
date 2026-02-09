#!/usr/bin/env python3
"""Consolidated error classes for ConcordCore.

This module defines all exception types used across the Concord framework.
All exceptions inherit from ConcordError for consistent error handling.
"""

import logging

log = logging.getLogger(__name__)


class ConcordError(Exception):
    """Base exception for all Concord errors."""
    pass


class ExpressionError(ConcordError):
    """Error in expression parsing or evaluation.

    Attributes:
        expression: The expression that caused the error.
    """

    def __init__(self, expression: str, message: str):
        message = message + f' expression={expression}'
        super().__init__(message)
        self.expression = expression


class ExpressionEvaluationError(ExpressionError):
    """Error during expression evaluation.

    Attributes:
        expression: The expression that failed.
        values: The values used during evaluation.
    """

    def __init__(self, expression: str, values, message: str = None):
        msg = f'ExpressionEvaluationError for values={values} message={message}'
        super().__init__(expression, msg)
        self.values = values


class ExpressionVariableNotFound(ExpressionError):
    """Variable referenced in expression not found.

    Attributes:
        expression_var: The variable ID that was not found.
        expression: The expression containing the reference.
    """

    def __init__(self, expression_var: str, expression: str):
        msg = f'var_id={expression_var} not found or undefined'
        super().__init__(expression, msg)
        self.expression_var = expression_var


class VarError(ConcordError):
    """Error related to variable definition or usage.

    Attributes:
        variable_id: The ID of the variable that caused the error.
        var_title: Human-readable variable title.
        actual_value: The value that caused the error (if applicable).
        constraint: The constraint that was violated (if applicable).
        user_friendly_message: Message suitable for display to end users.
    """

    def __init__(self, message: str, variable_id: str,
                 var_title: str | None = None,
                 actual_value=None,
                 constraint: str | None = None,
                 user_friendly_message: str | None = None):
        message = message + f' variable_id={variable_id}'
        super().__init__(message)
        self.variable_id = variable_id
        self.var_title = var_title
        self.actual_value = actual_value
        self.constraint = constraint
        self.user_friendly_message = user_friendly_message or message
        log.error(f'{self.__class__.__name__}: {message}')


class VariableEvaluationError(ConcordError):
    """Aggregated errors during variable evaluation.

    Attributes:
        errors: List of errors that occurred during evaluation.
        variable_id: The ID of the variable being evaluated.
    """

    def __init__(self, errors: list, variable_id: str):
        msgs = "\n  ".join([str(e).replace("\n", "\n  ") for e in errors])
        message = "{}:\n  {}".format(variable_id or "{root}", msgs)
        super().__init__(message)
        self.errors = errors
        self.variable_id = variable_id
        log.error(f'VariableEvaluationError variable_id={self.variable_id} error={message}')


class SecurityError(ConcordError):
    """Security-related error (e.g., invalid module path)."""
    pass


class NeedAttestationError(ConcordError):
    """User attestation required to continue evaluation.

    This exception is raised during assessment when required variables are
    missing values but are configured as user-attestable. The calling code
    should handle this by collecting the required data from the user.

    Attributes:
        records: List of EvaluatedRecord objects that need user attestation.
    """

    def __init__(self, records: list):
        self.records = records
        super().__init__(str(self))

    def __str__(self) -> str:
        return f'Need user attestation for records={[ev.record.var.id for ev in self.records]}'


class CPGDefinitionError(ConcordError):
    """Error in CPG definition (missing variables, invalid structure)."""
    pass


class PipelineError(ConcordError):
    """Error in evaluation pipeline execution (prerequisite not met)."""
    pass


class FHIRParseError(ConcordError):
    """Error parsing FHIR resources."""
    pass
