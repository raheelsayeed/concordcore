#!/usr/bin/env python3
"""LLM configuration management for ConcordCore.

This module provides configuration classes for LLM-based extraction,
supporting environment variables and programmatic configuration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """Configuration for LLM extraction.

    Attributes:
        provider: LLM provider name ('anthropic', 'openai')
        model: Optional model override
        api_key: Optional API key (falls back to environment)
        min_confidence: Minimum confidence threshold (0.0-1.0)
        include_low_confidence: Include low-confidence values as attestable
        batch_size: Number of variables per batch
    """

    provider: str = "anthropic"
    model: Optional[str] = None
    api_key: Optional[str] = None
    min_confidence: float = 0.7
    include_low_confidence: bool = False
    batch_size: int = 10

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Create configuration from environment variables.

        Environment variables:
            CONCORD_LLM_PROVIDER: LLM provider name (default: 'anthropic')
            CONCORD_LLM_MODEL: Model override
            CONCORD_LLM_MIN_CONFIDENCE: Minimum confidence threshold
            CONCORD_LLM_INCLUDE_LOW_CONFIDENCE: Include low-confidence values ('true'/'false')
            CONCORD_LLM_BATCH_SIZE: Batch size for extraction

        Returns:
            LLMConfig instance configured from environment.
        """
        provider = os.getenv('CONCORD_LLM_PROVIDER', 'anthropic')
        model = os.getenv('CONCORD_LLM_MODEL')
        min_confidence = float(os.getenv('CONCORD_LLM_MIN_CONFIDENCE', '0.7'))
        include_low = os.getenv('CONCORD_LLM_INCLUDE_LOW_CONFIDENCE', 'false').lower() == 'true'
        batch_size = int(os.getenv('CONCORD_LLM_BATCH_SIZE', '10'))

        return cls(
            provider=provider,
            model=model,
            min_confidence=min_confidence,
            include_low_confidence=include_low,
            batch_size=batch_size
        )

    def to_extraction_config(self) -> 'ExtractionConfig':
        """Convert to ExtractionConfig for use with ClinicalNotesExtractor.

        Returns:
            ExtractionConfig instance with these settings.
        """
        from concordcore.ai.notes_extractor import ExtractionConfig

        return ExtractionConfig(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
            batch_size=self.batch_size,
            min_confidence=self.min_confidence,
            include_low_confidence=self.include_low_confidence
        )


# Default configuration instance (can be modified at runtime)
default_config = LLMConfig()


def get_default_config() -> LLMConfig:
    """Get the default LLM configuration.

    Returns:
        The current default LLMConfig instance.
    """
    return default_config


def set_default_config(config: LLMConfig) -> None:
    """Set the default LLM configuration.

    Args:
        config: The new default configuration.
    """
    global default_config
    default_config = config
