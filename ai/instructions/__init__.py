#!/usr/bin/env python3
"""LLM instruction scaffolding for provider-specific prompts.

This package provides a layered instruction system for different LLM providers:
- System-level defaults
- CPG-level customizations
- Institution-level overrides

Example usage:
    ```python
    from ai.instructions import InstructionManager, LLMProviderType, InstructionContext

    # System-only instructions
    manager = InstructionManager.system_only()

    # Build a prompt for Claude extraction
    prompt = manager.build_prompt(
        context=InstructionContext.EXTRACTION,
        provider=LLMProviderType.CLAUDE,
        user_content="Extract LDL from: LDL-C: 145 mg/dL"
    )
    print(prompt['system'])  # Claude-optimized system prompt with XML tags

    # With CPG context
    from core.cpg import CPG
    cpg = CPG.from_document_path('cpgs/cholesterol.yaml')
    manager = InstructionManager.for_cpg(cpg)

    # Get instructions for conversation
    instructions = manager.get_instructions(
        context=InstructionContext.CONVERSATION,
        provider=LLMProviderType.OPENAI
    )
    print(instructions.formatting_style)  # FormattingStyle.MARKDOWN
    ```
"""

from .models import (
    # Enums
    LLMProviderType,
    InstructionContext,
    FormattingStyle,
    # Dataclasses
    FewShotExample,
    ProviderInstructions,
    ContextInstructions,
    LLMInstructionSet,
)

from .loader import (
    InstructionLoader,
    get_merged_instructions,
    get_system_instructions,
)

from .api import (
    InstructionManager,
)


__all__ = [
    # Enums
    'LLMProviderType',
    'InstructionContext',
    'FormattingStyle',
    # Dataclasses
    'FewShotExample',
    'ProviderInstructions',
    'ContextInstructions',
    'LLMInstructionSet',
    # Loader
    'InstructionLoader',
    'get_merged_instructions',
    'get_system_instructions',
    # API
    'InstructionManager',
]
