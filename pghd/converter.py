"""Converts raw patient input into Concord Values and Records."""

import logging
from datetime import datetime
from typing import Any

from variables.var import Var
from variables.value import Value
from variables.record import Record
from .input_source import InputSource, InputMetadata
from .normalizer import PGHDNormalizer
from .validator import PGHDValidator, PGHDValidationError

log = logging.getLogger(__name__)


class PGHDConverter:
    """Main entry point for converting patient-generated data.

    Combines normalization and validation to produce type-safe
    Records and Values from raw patient input.

    Example:
        converter = PGHDConverter()
        record = converter.to_record(var, "yes")
        records = converter.to_records({"DM": True, "Smoker": "no"}, var_lookup)
    """

    def __init__(self, normalizer: PGHDNormalizer | None = None,
                 validator: PGHDValidator | None = None):
        self._normalizer = normalizer or PGHDNormalizer()
        self._validator = validator or PGHDValidator()

    def to_value(self, var: Var, raw_value: Any,
                 source: InputSource = InputSource.patient_reported,
                 session_id: str | None = None,
                 date: datetime | None = None) -> Value:
        """Convert a raw input into a validated Value.

        Args:
            var: The variable definition
            raw_value: Raw input from the user
            source: Data source type
            session_id: Optional session ID
            date: Optional timestamp for the value

        Returns:
            A validated Value object with source metadata

        Raises:
            PGHDValidationError: If validation fails
        """
        self._validator.validate_raw(raw_value, var)

        normalized, metadata = self._normalizer.normalize(
            raw_value, var, source=source, session_id=session_id
        )

        value = Value(
            value=normalized,
            date=date,
            source=[metadata.source.value],
        )

        self._validator.validate_normalized(value, var, strict=False)

        return value

    def to_record(self, var: Var, raw_value: Any,
                  source: InputSource = InputSource.patient_reported,
                  session_id: str | None = None,
                  date: datetime | None = None) -> Record:
        """Convert a raw input into a validated Record.

        Args:
            var: The variable definition
            raw_value: Raw input from the user
            source: Data source type
            session_id: Optional session ID
            date: Optional timestamp for the value

        Returns:
            A Record containing the validated Value

        Raises:
            PGHDValidationError: If validation fails
        """
        value = self.to_value(var, raw_value, source=source,
                              session_id=session_id, date=date)
        return Record(var=var, initial_values=[value])

    def to_records(self, data: dict[str, Any],
                   var_lookup: dict[str, Var],
                   source: InputSource = InputSource.patient_reported,
                   session_id: str | None = None) -> list[Record]:
        """Convert a dict of var_id→raw_value into Records.

        Skips entries where the var_id is not found in var_lookup.
        Collects validation errors without stopping; raises a combined
        PGHDValidationError listing all failures if any occur.

        Args:
            data: Dict mapping variable IDs to raw values
            var_lookup: Dict mapping variable IDs to Var definitions
            source: Data source type
            session_id: Optional session ID

        Returns:
            List of validated Records

        Raises:
            PGHDValidationError: If any value fails validation (aggregated)
        """
        records = []
        errors = []

        for var_id, raw_value in data.items():
            var = var_lookup.get(var_id)
            if var is None:
                log.warning(f'PGHD: skipping unknown var_id={var_id}')
                continue

            try:
                record = self.to_record(var, raw_value, source=source,
                                        session_id=session_id)
                records.append(record)
            except PGHDValidationError as e:
                errors.append(e)

        if errors:
            var_ids = [e.var_id for e in errors]
            reasons = '; '.join(str(e) for e in errors)
            raise PGHDValidationError(
                var_id=', '.join(var_ids),
                value=None,
                reason=f'{len(errors)} validation error(s): {reasons}',
                user_message=f'Could not process {len(errors)} value(s): {", ".join(var_ids)}'
            )

        return records

    def attest(self, record: Record, raw_value: Any,
               source: InputSource = InputSource.attestation,
               session_id: str | None = None) -> None:
        """Apply a user attestation to an existing Record.

        Normalizes and validates the value, then sets it as the
        attested value on the record.

        Args:
            record: The record to attest
            raw_value: The raw attestation value
            source: Data source (defaults to attestation)
            session_id: Optional session ID

        Raises:
            PGHDValidationError: If validation fails
        """
        normalized, metadata = self._normalizer.normalize(
            raw_value, record.var, source=source, session_id=session_id
        )

        value = Value(
            value=normalized,
            source=[metadata.source.value],
        )

        try:
            record.attested_value = value
        except ValueError as e:
            raise PGHDValidationError(
                var_id=record.var.id,
                value=raw_value,
                reason=str(e),
                user_message=f'Cannot attest {record.var.title or record.var.id}: {e}'
            )
