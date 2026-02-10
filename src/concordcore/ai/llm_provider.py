#!/usr/bin/env python3
"""LLM Provider protocols and extraction result types.

This module defines protocols for LLM providers:
- ExtractionProvider: For clinical notes variable extraction
- ConversationProvider: For copilot conversation generation
- LLMProvider: Alias for ExtractionProvider (backwards compatibility)
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ExtractionResult:
    """Result of extracting a variable from clinical notes.

    Attributes:
        variable_id: The ID of the variable being extracted
        found: Whether the variable was found in the notes
        raw_value: The raw extracted value from the LLM
        parsed_value: The value converted to the expected type
        confidence: Confidence score from 0.0 to 1.0
        source_text: The relevant excerpt from the notes
        error: Error message if extraction failed
    """

    variable_id: str
    found: bool
    raw_value: Any = None
    parsed_value: Any = None
    confidence: float = 0.0
    source_text: str = None
    error: str = None

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


class ExtractionProvider(Protocol):
    """Protocol for LLM providers used in clinical notes extraction.

    Implement this protocol to add support for different LLM providers
    (e.g., Anthropic, OpenAI, local models) for extracting variable values
    from clinical notes.

    Example implementation:
        class MyLLMAdapter:
            def extract_value(
                self,
                prompt: str,
                clinical_notes: str,
                expected_type: str,
                variable_id: str
            ) -> ExtractionResult:
                # Call your LLM and parse the response
                ...
    """

    def extract_value(
        self,
        prompt: str,
        clinical_notes: str,
        expected_type: str,
        variable_id: str
    ) -> ExtractionResult:
        """Extract a variable value from clinical notes using the prompt.

        Args:
            prompt: The extraction prompt for this variable
            clinical_notes: The clinical notes text to extract from
            expected_type: Expected value type ('boolean', 'integer', 'decimal', 'string')
            variable_id: The ID of the variable being extracted

        Returns:
            ExtractionResult with the extracted value and metadata
        """
        ...

    def extract_batch(
        self,
        extractions: list[tuple[str, str, str]],
        clinical_notes: str
    ) -> list[ExtractionResult]:
        """Batch extraction for efficiency.

        This is an optional optimization. The default implementation
        calls extract_value for each item.

        Args:
            extractions: List of (prompt, expected_type, variable_id) tuples
            clinical_notes: The clinical notes text to extract from

        Returns:
            List of ExtractionResult objects
        """
        ...


class ConversationProvider(Protocol):
    """Protocol for LLM providers used in copilot conversations.

    Implement this protocol for LLM providers that generate conversational
    responses in the HealthCopilot system.

    Example implementation:
        class MyConversationLLM:
            def generate(self, prompt: str, system: str = None) -> str:
                # Call your LLM and return the response
                ...
    """

    def generate(self, prompt: str, system: str = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt to respond to
            system: Optional system prompt for context

        Returns:
            The generated response text
        """
        ...


# Backwards compatibility alias
LLMProvider = ExtractionProvider
