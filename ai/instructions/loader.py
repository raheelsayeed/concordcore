#!/usr/bin/env python3
"""YAML loader for LLM instruction files.

This module handles loading and parsing instruction YAML files,
with support for caching and hierarchical merging.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .models import (
    LLMProviderType,
    InstructionContext,
    FormattingStyle,
    FewShotExample,
    ProviderInstructions,
    ContextInstructions,
    LLMInstructionSet,
)

log = logging.getLogger(__name__)

# Default path for system instructions
SYSTEM_INSTRUCTIONS_PATH = Path(__file__).parent / "system_instructions.yaml"


class InstructionLoader:
    """Loader for LLM instruction YAML files.

    Handles parsing of instruction YAML files and provides caching
    for efficient repeated access.
    """

    def __init__(self):
        self._cache: dict[str, LLMInstructionSet] = {}

    def load(self, path: str | Path) -> LLMInstructionSet:
        """Load instruction set from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            Parsed LLMInstructionSet

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If required fields are missing
        """
        path = Path(path)
        cache_key = str(path.resolve())

        if cache_key in self._cache:
            return self._cache[cache_key]

        if not path.exists():
            raise FileNotFoundError(f"Instruction file not found: {path}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        instruction_set = self._parse_instruction_set(data)
        self._cache[cache_key] = instruction_set
        return instruction_set

    def load_system_instructions(self) -> LLMInstructionSet:
        """Load the system-level default instructions."""
        return self.load(SYSTEM_INSTRUCTIONS_PATH)

    def load_from_cpg_yaml(self, cpg_data: dict) -> LLMInstructionSet | None:
        """Extract and parse LLM instructions from CPG YAML data.

        Args:
            cpg_data: Parsed CPG YAML dictionary

        Returns:
            LLMInstructionSet if llm_instructions section exists, None otherwise
        """
        llm_instructions = cpg_data.get('llm_instructions')
        if not llm_instructions:
            return None

        return self._parse_instruction_set({'llm_instructions': llm_instructions})

    def clear_cache(self):
        """Clear the instruction cache."""
        self._cache.clear()

    def _parse_instruction_set(self, data: dict) -> LLMInstructionSet:
        """Parse a complete instruction set from YAML data."""
        inst_data = data.get('llm_instructions', data)

        instruction_id = inst_data.get('id', 'unnamed')
        name = inst_data.get('name', instruction_id)
        version = inst_data.get('version', '1.0')

        # Parse global constraints
        global_constraints = tuple(inst_data.get('global_constraints', []))

        # Parse context instructions
        context_instructions = {}
        contexts_data = inst_data.get('contexts', {})

        for context_name, context_data in contexts_data.items():
            try:
                context = InstructionContext.YAML(context_name)
                if context:
                    context_instructions[context] = self._parse_context_instructions(
                        context, context_data
                    )
            except ValueError:
                log.warning(f"Unknown instruction context: {context_name}")

        return LLMInstructionSet(
            id=instruction_id,
            name=name,
            version=version,
            context_instructions=context_instructions,
            global_constraints=global_constraints,
        )

    def _parse_context_instructions(
        self,
        context: InstructionContext,
        data: dict
    ) -> ContextInstructions:
        """Parse instructions for a specific context."""
        provider_instructions = {}
        default_instructions = None

        for provider_name, provider_data in data.items():
            if provider_name == 'default':
                default_instructions = self._parse_provider_instructions(
                    LLMProviderType.DEFAULT, provider_data
                )
            else:
                try:
                    provider = LLMProviderType.YAML(provider_name)
                    if provider:
                        provider_instructions[provider] = self._parse_provider_instructions(
                            provider, provider_data
                        )
                except ValueError:
                    log.warning(f"Unknown LLM provider: {provider_name}")

        return ContextInstructions(
            context=context,
            provider_instructions=provider_instructions,
            default_instructions=default_instructions,
        )

    def _parse_provider_instructions(
        self,
        provider: LLMProviderType,
        data: dict
    ) -> ProviderInstructions:
        """Parse instructions for a specific provider."""
        # Parse formatting style
        formatting_style = FormattingStyle.PLAIN
        if 'formatting_style' in data:
            try:
                formatting_style = FormattingStyle.YAML(data['formatting_style'])
            except ValueError:
                log.warning(f"Unknown formatting style: {data['formatting_style']}")

        # Parse few-shot examples
        few_shot_examples = []
        for ex_data in data.get('few_shot_examples', []):
            example = FewShotExample(
                input=ex_data.get('input', ''),
                output=ex_data.get('output', ''),
                explanation=ex_data.get('explanation'),
            )
            few_shot_examples.append(example)

        # Parse custom tags
        custom_tags = data.get('custom_tags', {})
        if isinstance(custom_tags, dict):
            custom_tags = {str(k): str(v) for k, v in custom_tags.items()}
        else:
            custom_tags = {}

        # Parse constraints
        constraints = tuple(data.get('constraints', []))

        # Parse response format
        response_format = data.get('response_format')
        if response_format and not isinstance(response_format, dict):
            response_format = None

        # Parse metadata
        metadata = data.get('metadata', {})
        if not isinstance(metadata, dict):
            metadata = {}

        return ProviderInstructions(
            provider=provider,
            system_prompt=data.get('system_prompt'),
            formatting_style=formatting_style,
            temperature_hint=data.get('temperature_hint'),
            few_shot_examples=tuple(few_shot_examples),
            custom_tags=custom_tags,
            constraints=constraints,
            response_format=response_format,
            metadata=metadata,
        )


def get_merged_instructions(
    cpg_data: dict = None,
    institution_config: dict = None,
    loader: InstructionLoader = None
) -> LLMInstructionSet:
    """Get merged instructions from all layers.

    Merges instructions in priority order:
    1. System defaults (lowest priority)
    2. CPG-level instructions
    3. Institution-level instructions (highest priority)

    Args:
        cpg_data: Optional CPG YAML data with llm_instructions section
        institution_config: Optional institution config with llm_instructions
        loader: Optional InstructionLoader instance (creates new if None)

    Returns:
        Merged LLMInstructionSet
    """
    if loader is None:
        loader = InstructionLoader()

    # Start with system instructions
    try:
        result = loader.load_system_instructions()
    except FileNotFoundError:
        log.warning("System instructions not found, using empty defaults")
        result = LLMInstructionSet(
            id='empty_default',
            name='Empty Default',
            version='1.0',
        )

    # Merge CPG instructions if provided
    if cpg_data:
        cpg_instructions = loader.load_from_cpg_yaml(cpg_data)
        if cpg_instructions:
            result = result.merge(cpg_instructions)

    # Merge institution instructions if provided
    if institution_config:
        inst_instructions = institution_config.get('llm_instructions')
        if inst_instructions:
            parsed = loader._parse_instruction_set({'llm_instructions': inst_instructions})
            result = result.merge(parsed)

    return result


@lru_cache(maxsize=1)
def get_system_instructions() -> LLMInstructionSet:
    """Get cached system instructions singleton.

    Returns:
        The system-level LLMInstructionSet
    """
    loader = InstructionLoader()
    try:
        return loader.load_system_instructions()
    except FileNotFoundError:
        log.warning("System instructions not found, using empty defaults")
        return LLMInstructionSet(
            id='empty_default',
            name='Empty Default',
            version='1.0',
        )
