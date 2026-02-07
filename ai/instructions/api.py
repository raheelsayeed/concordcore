#!/usr/bin/env python3
"""High-level API for LLM instruction management.

The InstructionManager provides a simple interface for:
- Getting provider-specific instructions for different contexts
- Building optimized prompts with proper formatting
- Managing instruction hierarchy (system → CPG → institution)
"""

from typing import TYPE_CHECKING

from .models import (
    LLMProviderType,
    InstructionContext,
    FormattingStyle,
    ProviderInstructions,
    LLMInstructionSet,
)
from .loader import (
    InstructionLoader,
    get_merged_instructions,
    get_system_instructions,
)

if TYPE_CHECKING:
    from core.cpg import CPG
    from core.institution_config import InstitutionConfig


class InstructionManager:
    """High-level manager for LLM instructions.

    Provides a unified interface for accessing provider-specific
    instructions across different contexts.

    Example:
        ```python
        # System-only instructions
        manager = InstructionManager.system_only()
        prompt = manager.build_prompt(
            context=InstructionContext.EXTRACTION,
            provider=LLMProviderType.CLAUDE,
            user_content="Extract LDL from: LDL-C: 145 mg/dL"
        )

        # With CPG context
        manager = InstructionManager.for_cpg(cpg)
        instructions = manager.get_instructions(
            context=InstructionContext.CONVERSATION,
            provider=LLMProviderType.OPENAI
        )
        ```
    """

    def __init__(
        self,
        instruction_set: LLMInstructionSet,
        cpg: 'CPG | None' = None,
        institution_config: 'InstitutionConfig | None' = None,
    ):
        """Initialize the InstructionManager.

        Args:
            instruction_set: The merged instruction set to use
            cpg: Optional CPG for context
            institution_config: Optional institution config
        """
        self._instruction_set = instruction_set
        self._cpg = cpg
        self._institution_config = institution_config
        self._loader = InstructionLoader()

    @classmethod
    def system_only(cls) -> 'InstructionManager':
        """Create an InstructionManager with only system instructions.

        Returns:
            InstructionManager with system-level defaults only
        """
        return cls(instruction_set=get_system_instructions())

    @classmethod
    def for_cpg(
        cls,
        cpg: 'CPG',
        institution_config: 'InstitutionConfig | None' = None,
    ) -> 'InstructionManager':
        """Create an InstructionManager for a specific CPG.

        Merges system defaults with CPG-level and optional institution
        instructions.

        Args:
            cpg: The CPG to get instructions for
            institution_config: Optional institution configuration

        Returns:
            InstructionManager with merged instructions
        """
        # Get CPG's raw YAML data if available
        cpg_data = None
        if hasattr(cpg, '_raw_yaml'):
            cpg_data = cpg._raw_yaml
        elif hasattr(cpg, 'llm_instructions'):
            cpg_data = {'llm_instructions': cpg.llm_instructions}

        # Get institution config data if available
        inst_data = None
        if institution_config:
            inst_data = institution_config.to_dict() if hasattr(institution_config, 'to_dict') else {}

        instruction_set = get_merged_instructions(
            cpg_data=cpg_data,
            institution_config=inst_data,
        )

        return cls(
            instruction_set=instruction_set,
            cpg=cpg,
            institution_config=institution_config,
        )

    def get_instructions(
        self,
        context: InstructionContext,
        provider: LLMProviderType,
    ) -> ProviderInstructions:
        """Get provider-specific instructions for a context.

        Args:
            context: The instruction context (extraction, conversation, etc.)
            provider: The LLM provider (claude, openai, gemini)

        Returns:
            ProviderInstructions optimized for the provider and context
        """
        return self._instruction_set.get_instructions(context, provider)

    def build_prompt(
        self,
        context: InstructionContext,
        provider: LLMProviderType,
        user_content: str,
        include_examples: bool = True,
        additional_context: str | None = None,
    ) -> dict[str, str]:
        """Build a complete prompt optimized for a provider.

        Args:
            context: The instruction context
            provider: The target LLM provider
            user_content: The user's message/content
            include_examples: Whether to include few-shot examples
            additional_context: Optional additional context to inject

        Returns:
            Dict with 'system' and 'user' prompt strings
        """
        instructions = self.get_instructions(context, provider)

        # Build base prompt
        prompt = instructions.build_full_prompt(user_content, include_examples)

        # Add additional context if provided
        if additional_context:
            if instructions.formatting_style == FormattingStyle.XML_TAGS:
                prompt['system'] = (
                    prompt['system'] +
                    f"\n\n<additional_context>\n{additional_context}\n</additional_context>"
                )
            elif instructions.formatting_style == FormattingStyle.MARKDOWN:
                prompt['system'] = (
                    prompt['system'] +
                    f"\n\n## Additional Context\n\n{additional_context}"
                )
            else:
                prompt['system'] = (
                    prompt['system'] +
                    f"\n\nAdditional Context:\n{additional_context}"
                )

        # Add CPG-specific context if available
        if self._cpg and context in (InstructionContext.CONVERSATION, InstructionContext.EXPLANATION):
            cpg_context = self._format_cpg_context(instructions.formatting_style)
            if cpg_context:
                prompt['system'] = prompt['system'] + "\n\n" + cpg_context

        return prompt

    def get_temperature(
        self,
        context: InstructionContext,
        provider: LLMProviderType,
    ) -> float | None:
        """Get suggested temperature for a context/provider combination.

        Args:
            context: The instruction context
            provider: The LLM provider

        Returns:
            Suggested temperature, or None if not specified
        """
        instructions = self.get_instructions(context, provider)
        return instructions.temperature_hint

    def get_response_format(
        self,
        context: InstructionContext,
        provider: LLMProviderType,
    ) -> dict | None:
        """Get response format specification for a context/provider.

        Args:
            context: The instruction context
            provider: The LLM provider

        Returns:
            Response format dict, or None if not specified
        """
        instructions = self.get_instructions(context, provider)
        return instructions.response_format

    def get_formatting_style(
        self,
        context: InstructionContext,
        provider: LLMProviderType,
    ) -> FormattingStyle:
        """Get formatting style for a context/provider.

        Args:
            context: The instruction context
            provider: The LLM provider

        Returns:
            The FormattingStyle for this context/provider
        """
        instructions = self.get_instructions(context, provider)
        return instructions.formatting_style

    def _format_cpg_context(self, style: FormattingStyle) -> str:
        """Format CPG context information for prompts."""
        if not self._cpg:
            return ""

        title = getattr(self._cpg, 'title', 'Unknown CPG')
        publisher = getattr(self._cpg, 'publisher', None)

        if style == FormattingStyle.XML_TAGS:
            parts = [f"<cpg_context>", f"<title>{title}</title>"]
            if publisher:
                parts.append(f"<publisher>{publisher}</publisher>")
            parts.append("</cpg_context>")
            return "\n".join(parts)
        elif style == FormattingStyle.MARKDOWN:
            parts = [f"## CPG Context", f"**Title:** {title}"]
            if publisher:
                parts.append(f"**Publisher:** {publisher}")
            return "\n".join(parts)
        else:
            parts = [f"CPG: {title}"]
            if publisher:
                parts.append(f"Publisher: {publisher}")
            return "\n".join(parts)

    @property
    def instruction_set(self) -> LLMInstructionSet:
        """Get the underlying instruction set."""
        return self._instruction_set

    @property
    def cpg(self) -> 'CPG | None':
        """Get the associated CPG, if any."""
        return self._cpg

    @property
    def institution_config(self) -> 'InstitutionConfig | None':
        """Get the associated institution config, if any."""
        return self._institution_config

    def to_dict(self) -> dict:
        """Convert manager state to dictionary for debugging/logging."""
        return {
            'instruction_set_id': self._instruction_set.id,
            'instruction_set_name': self._instruction_set.name,
            'instruction_set_version': self._instruction_set.version,
            'cpg_id': getattr(self._cpg, 'identifier', None) if self._cpg else None,
            'institution_id': (
                getattr(self._institution_config, 'institution_id', None)
                if self._institution_config else None
            ),
            'available_contexts': [c.value for c in self._instruction_set.context_instructions.keys()],
            'global_constraints_count': len(self._instruction_set.global_constraints),
        }
