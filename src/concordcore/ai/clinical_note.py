#!/usr/bin/env python3
"""Clinical note source tracking for LLM-extracted values.

This module provides the ClinicalNote class for storing metadata about
clinical note snippets used as the source for extracted variable values.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class ClinicalNote:
    """Represents a clinical note snippet used as the source for an extracted value.

    This class stores the relevant portion of clinical notes that was used to
    extract a variable value, along with metadata about the extraction process.

    Attributes:
        snippet: The relevant text excerpt from the clinical notes
        variable_id: ID of the variable that was extracted
        confidence: Confidence score from 0.0 to 1.0
        provider: LLM provider used for extraction (e.g., 'anthropic', 'openai')
        model: Specific model used (e.g., 'claude-sonnet-4-20250514')
        extraction_timestamp: When the extraction was performed
        full_notes_hash: Optional hash of the full clinical notes for reference
        raw_llm_response: Optional raw response from the LLM
        prompt_used: Optional prompt that was used for extraction

    Example:
        source = ClinicalNote(
            snippet="Mother had colon cancer at age 62.",
            variable_id="family_history_crc",
            confidence=0.95,
            provider="anthropic",
            model="claude-sonnet-4-20250514"
        )
        value = Value(True, source=[source])
    """

    snippet: str
    variable_id: str
    confidence: float = 0.0
    provider: str = None
    model: str = None
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    full_notes_hash: str = None
    raw_llm_response: Any = None
    prompt_used: str = None

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            object.__setattr__(self, 'confidence', max(0.0, min(1.0, self.confidence)))

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return "clinical_notes"

    @property
    def source_string(self) -> str:
        """Return a standardized source string for logging/display.

        Format: clinical_notes:llm:<provider>:<model>
        """
        parts = ["clinical_notes", "llm"]
        if self.provider:
            parts.append(self.provider)
        if self.model:
            parts.append(self.model)
        return ":".join(parts)

    def __repr__(self) -> str:
        snippet_preview = self.snippet[:50] + "..." if len(self.snippet) > 50 else self.snippet
        return (
            f"ClinicalNote(var={self.variable_id}, "
            f"confidence={self.confidence:.2f}, "
            f"snippet='{snippet_preview}')"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "source_type": self.source_type,
            "snippet": self.snippet,
            "variable_id": self.variable_id,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "extraction_timestamp": self.extraction_timestamp.isoformat() if self.extraction_timestamp else None,
            "full_notes_hash": self.full_notes_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ClinicalNote':
        """Create ClinicalNote from dictionary."""
        timestamp = data.get("extraction_timestamp")
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            snippet=data.get("snippet", ""),
            variable_id=data.get("variable_id", ""),
            confidence=data.get("confidence", 0.0),
            provider=data.get("provider"),
            model=data.get("model"),
            extraction_timestamp=timestamp,
            full_notes_hash=data.get("full_notes_hash"),
        )
