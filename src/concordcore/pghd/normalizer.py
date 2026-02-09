"""Normalization of raw patient input into typed values."""

import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any

from concordcore.primitives.types import ValueType
from concordcore.variables.var import Var
from .input_source import InputSource, InputMetadata

log = logging.getLogger(__name__)

# Boolean truthy/falsy string values
_BOOL_TRUE = frozenset({'yes', 'y', 'true', '1', 'on'})
_BOOL_FALSE = frozenset({'no', 'n', 'false', '0', 'off'})


class PGHDNormalizer:
    """Normalizes raw patient input based on variable type definitions.

    Handles type coercion (string→int, "yes"→True, etc.) and
    attaches InputMetadata for source tracking.
    """

    def normalize(self, raw_value: Any, var: Var,
                  source: InputSource = InputSource.patient_reported,
                  session_id: str | None = None) -> tuple[Any, InputMetadata]:
        """Normalize a raw input value based on the variable's value_type.

        Args:
            raw_value: The raw input (typically a string from user input)
            var: The variable definition with type information
            source: Where this data came from
            session_id: Optional session ID for traceability

        Returns:
            Tuple of (normalized_value, InputMetadata)

        Raises:
            ValueError: If the value cannot be coerced to the expected type
        """
        metadata = InputMetadata(
            source=source,
            session_id=session_id,
            raw_input=raw_value,
        )

        value_type = var.value_type
        if value_type is None:
            return raw_value, metadata

        normalized = self._coerce(raw_value, value_type)
        return normalized, metadata

    def _coerce(self, raw_value: Any, value_type: ValueType) -> Any:
        """Coerce a raw value to the expected ValueType."""
        if raw_value is None:
            raise ValueError('Cannot normalize None value')

        if value_type == ValueType.boolean:
            return self._to_bool(raw_value)
        elif value_type == ValueType.integer:
            return self._to_int(raw_value)
        elif value_type == ValueType.decimal:
            return self._to_decimal(raw_value)
        elif value_type == ValueType.date:
            return self._to_date(raw_value)
        elif value_type == ValueType.string:
            return str(raw_value)
        else:
            return raw_value

    def _to_bool(self, raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(raw, str):
            lower = raw.strip().lower()
            if lower in _BOOL_TRUE:
                return True
            if lower in _BOOL_FALSE:
                return False
            raise ValueError(f'Cannot parse "{raw}" as boolean. Use yes/no, true/false, or 1/0.')
        raise ValueError(f'Cannot convert {type(raw).__name__} to boolean')

    def _to_int(self, raw: Any) -> int:
        if isinstance(raw, bool):
            return int(raw)
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)
        if isinstance(raw, str):
            try:
                return int(raw.strip())
            except ValueError:
                try:
                    return int(float(raw.strip()))
                except ValueError:
                    raise ValueError(f'Cannot parse "{raw}" as integer')
        raise ValueError(f'Cannot convert {type(raw).__name__} to integer')

    def _to_decimal(self, raw: Any) -> float:
        if isinstance(raw, bool):
            return float(raw)
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            try:
                return float(raw.strip())
            except ValueError:
                raise ValueError(f'Cannot parse "{raw}" as decimal')
        raise ValueError(f'Cannot convert {type(raw).__name__} to decimal')

    def _to_date(self, raw: Any) -> date:
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        if isinstance(raw, str):
            raw = raw.strip()
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d'):
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(raw).date()
            except ValueError:
                raise ValueError(f'Cannot parse "{raw}" as date. Use YYYY-MM-DD format.')
        raise ValueError(f'Cannot convert {type(raw).__name__} to date')
