"""Input source tracking for patient-generated health data."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class InputSource(StrEnum):
    """Source of patient-generated health data."""
    patient_reported = 'patient-reported'
    device = 'device'
    survey = 'survey'
    caregiver = 'caregiver'
    attestation = 'attestation'
    mcp_conversation = 'mcp-conversation'


@dataclass(frozen=True)
class InputMetadata:
    """Metadata about a patient-generated data input.

    Attributes:
        source: Where the data came from
        timestamp: When the data was captured
        session_id: Optional session identifier for traceability
        confidence: Data confidence level (0.0-1.0)
        raw_input: The original unprocessed input value
    """
    source: InputSource
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str | None = None
    confidence: float | None = None
    raw_input: Any = None

    def __post_init__(self):
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f'confidence must be between 0.0 and 1.0, got {self.confidence}')
