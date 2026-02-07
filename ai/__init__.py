#!/usr/bin/env python3
"""AI integration module for Concord.

Provides LLM-ready interfaces for clinical guideline evaluation
and clinical notes extraction.
"""

from .copilot import HealthCopilot, CopilotContext, ConversationTurn
from .prompts import PromptBuilder
from .llm_provider import LLMProvider, ExtractionProvider, ConversationProvider, ExtractionResult
from .clinical_note import ClinicalNote
from .notes_extractor import ClinicalNotesExtractor, ExtractionConfig, ExtractionSummary
from .config import LLMConfig, get_default_config, set_default_config

# Import instruction scaffolding
from .instructions import (
    InstructionManager,
    LLMProviderType,
    InstructionContext,
    FormattingStyle,
    ProviderInstructions,
)

__all__ = [
    # Copilot
    'HealthCopilot',
    'CopilotContext',
    'ConversationTurn',
    'PromptBuilder',
    # LLM Providers
    'LLMProvider',  # Alias for ExtractionProvider (backwards compatibility)
    'ExtractionProvider',
    'ConversationProvider',
    'ExtractionResult',
    # Clinical Note Source
    'ClinicalNote',
    # Notes Extraction
    'ClinicalNotesExtractor',
    'ExtractionConfig',
    'ExtractionSummary',
    # Configuration
    'LLMConfig',
    'get_default_config',
    'set_default_config',
    # Instruction Scaffolding
    'InstructionManager',
    'LLMProviderType',
    'InstructionContext',
    'FormattingStyle',
    'ProviderInstructions',
]
