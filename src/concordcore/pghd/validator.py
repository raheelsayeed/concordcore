"""Validation of patient-generated health data before conversion."""

import logging
from dataclasses import dataclass
from typing import Any

from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.variables.record import Record

log = logging.getLogger(__name__)


@dataclass
class PGHDValidationError(Exception):
    """Validation error for patient-generated data.

    Provides structured error information including a user-friendly message.

    Attributes:
        var_id: The variable ID that failed validation
        value: The value that was rejected
        reason: Technical reason for the failure
        user_message: Human-readable message suitable for display
    """
    var_id: str
    value: Any
    reason: str
    user_message: str

    def __str__(self) -> str:
        return f'PGHDValidationError({self.var_id}): {self.reason}'


class PGHDValidator:
    """Validates patient-generated data before conversion to Records/Values.

    Performs pre-normalization checks (null, type compatibility) and
    delegates to Record.validate() for plausible/panel validation.
    """

    def validate_raw(self, raw_value: Any, var: Var) -> None:
        """Validate a raw value before normalization.

        Args:
            raw_value: The raw input value
            var: The variable definition

        Raises:
            PGHDValidationError: If validation fails
        """
        if raw_value is None:
            raise PGHDValidationError(
                var_id=var.id,
                value=None,
                reason='Value is None',
                user_message=f'A value is required for {var.title or var.id}.'
            )

        if not var.user_attestable:
            raise PGHDValidationError(
                var_id=var.id,
                value=raw_value,
                reason='Variable is not user-attestable',
                user_message=f'{var.title or var.id} cannot be provided by the patient and must come from clinical data.'
            )

    def validate_normalized(self, value: Value, var: Var,
                            records: list[Record] | None = None,
                            strict: bool = False) -> None:
        """Validate a normalized Value using Record validation logic.

        Creates a temporary Record and runs its validate() method, which
        checks plausible and panel validators.

        Args:
            value: The normalized Value object
            var: The variable definition
            records: Optional context records for panel validation
            strict: If True, raise on plausibility/panel failures

        Raises:
            PGHDValidationError: If validation fails
        """
        temp_record = Record(var=var, initial_values=[value])
        try:
            temp_record.validate(value=value, records=records, strict=strict)
        except Exception as e:
            raise PGHDValidationError(
                var_id=var.id,
                value=value.value,
                reason=str(e),
                user_message=f'The value {value.value} for {var.title or var.id} is not valid: {e}'
            )
