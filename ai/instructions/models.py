#!/usr/bin/env python3
"""Data models for LLM instruction scaffolding.

This module defines the core types for provider-specific LLM instructions:
- Enums for providers, contexts, and formatting styles
- Frozen dataclasses for instructions at various levels
- Merge operations for hierarchical instruction combination
"""

from dataclasses import dataclass, field
from typing import Any

from concordcore.primitives.types import YMLStrEnum


class LLMProviderType(YMLStrEnum):
    """LLM provider identifiers.

    Used to select provider-specific instructions optimized for each LLM's
    preferred formatting and capabilities.
    """
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEFAULT = "default"


class InstructionContext(YMLStrEnum):
    """Context types for instruction selection.

    Different contexts have different instruction needs:
    - EXTRACTION: Precise data extraction from clinical notes
    - CONVERSATION: Patient/provider dialogue
    - EXPLANATION: Explaining clinical recommendations
    - SUMMARY: Summarizing evaluation results
    """
    EXTRACTION = "extraction"
    CONVERSATION = "conversation"
    EXPLANATION = "explanation"
    SUMMARY = "summary"


class FormattingStyle(YMLStrEnum):
    """Formatting preferences for different LLM providers.

    - XML_TAGS: Claude's preferred structured format
    - MARKDOWN: GPT's preferred format with headers/sections
    - JSON: Structured JSON responses
    - PLAIN: Plain text without special formatting
    """
    XML_TAGS = "xml_tags"
    MARKDOWN = "markdown"
    JSON = "json"
    PLAIN = "plain"


@dataclass(frozen=True)
class FewShotExample:
    """A single few-shot example for in-context learning.

    Attributes:
        input: The example input/query
        output: The expected output/response
        explanation: Optional explanation of why this output is correct
    """
    input: str
    output: str
    explanation: str | None = None

    def format(self, style: FormattingStyle) -> str:
        """Format example for a specific provider style."""
        if style == FormattingStyle.XML_TAGS:
            result = f"<example>\n<input>{self.input}</input>\n<output>{self.output}</output>"
            if self.explanation:
                result += f"\n<explanation>{self.explanation}</explanation>"
            result += "\n</example>"
            return result
        elif style == FormattingStyle.MARKDOWN:
            result = f"**Input:** {self.input}\n\n**Output:** {self.output}"
            if self.explanation:
                result += f"\n\n*Explanation:* {self.explanation}"
            return result
        elif style == FormattingStyle.JSON:
            import json
            data = {"input": self.input, "output": self.output}
            if self.explanation:
                data["explanation"] = self.explanation
            return json.dumps(data, indent=2)
        else:
            result = f"Input: {self.input}\nOutput: {self.output}"
            if self.explanation:
                result += f"\nExplanation: {self.explanation}"
            return result


@dataclass(frozen=True)
class ProviderInstructions:
    """Instructions optimized for a specific LLM provider.

    Contains all the tuning parameters for a provider in a specific context.

    Attributes:
        provider: The LLM provider these instructions are for
        system_prompt: The system prompt text
        formatting_style: Preferred formatting style
        temperature_hint: Suggested temperature for this context
        few_shot_examples: Example input/output pairs for in-context learning
        custom_tags: XML tag names for structured output (Claude)
        constraints: List of constraint rules
        response_format: Optional structured response format spec
        metadata: Additional provider-specific metadata
    """
    provider: LLMProviderType
    system_prompt: str | None = None
    formatting_style: FormattingStyle = FormattingStyle.PLAIN
    temperature_hint: float | None = None
    few_shot_examples: tuple[FewShotExample, ...] = field(default_factory=tuple)
    custom_tags: dict[str, str] = field(default_factory=dict)
    constraints: tuple[str, ...] = field(default_factory=tuple)
    response_format: dict | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def merge(self, other: 'ProviderInstructions') -> 'ProviderInstructions':
        """Merge with another ProviderInstructions, other takes precedence.

        Used for layered instruction configuration where CPG-level
        instructions override system defaults.
        """
        return ProviderInstructions(
            provider=other.provider if other.provider != LLMProviderType.DEFAULT else self.provider,
            system_prompt=other.system_prompt if other.system_prompt else self.system_prompt,
            formatting_style=other.formatting_style if other.formatting_style != FormattingStyle.PLAIN else self.formatting_style,
            temperature_hint=other.temperature_hint if other.temperature_hint is not None else self.temperature_hint,
            few_shot_examples=self.few_shot_examples + other.few_shot_examples,
            custom_tags={**self.custom_tags, **other.custom_tags},
            constraints=self.constraints + other.constraints,
            response_format=other.response_format if other.response_format else self.response_format,
            metadata={**self.metadata, **other.metadata},
        )

    def format_examples(self) -> str:
        """Format all few-shot examples according to the formatting style."""
        if not self.few_shot_examples:
            return ""

        examples = [ex.format(self.formatting_style) for ex in self.few_shot_examples]

        if self.formatting_style == FormattingStyle.XML_TAGS:
            return "<examples>\n" + "\n".join(examples) + "\n</examples>"
        elif self.formatting_style == FormattingStyle.MARKDOWN:
            return "## Examples\n\n" + "\n\n---\n\n".join(examples)
        else:
            return "Examples:\n\n" + "\n\n".join(examples)

    def format_constraints(self) -> str:
        """Format constraints according to the formatting style."""
        if not self.constraints:
            return ""

        if self.formatting_style == FormattingStyle.XML_TAGS:
            constraints_str = "\n".join(f"<constraint>{c}</constraint>" for c in self.constraints)
            return f"<constraints>\n{constraints_str}\n</constraints>"
        elif self.formatting_style == FormattingStyle.MARKDOWN:
            constraints_str = "\n".join(f"- {c}" for c in self.constraints)
            return f"## Constraints\n\n{constraints_str}"
        else:
            return "Constraints:\n" + "\n".join(f"- {c}" for c in self.constraints)

    def build_full_prompt(self, user_content: str, include_examples: bool = True) -> dict[str, str]:
        """Build a complete prompt with system and user components.

        Args:
            user_content: The user's message/query content
            include_examples: Whether to include few-shot examples

        Returns:
            Dict with 'system' and 'user' prompt strings
        """
        system_parts = []

        if self.system_prompt:
            system_parts.append(self.system_prompt)

        if self.constraints:
            system_parts.append(self.format_constraints())

        if include_examples and self.few_shot_examples:
            system_parts.append(self.format_examples())

        user_prompt = user_content
        if self.formatting_style == FormattingStyle.XML_TAGS and self.custom_tags:
            # Wrap user content in custom tags if specified
            content_tag = self.custom_tags.get('content', 'content')
            user_prompt = f"<{content_tag}>\n{user_content}\n</{content_tag}>"

        return {
            'system': '\n\n'.join(system_parts),
            'user': user_prompt
        }


@dataclass(frozen=True)
class ContextInstructions:
    """Instructions for a specific context (extraction, conversation, etc.).

    Contains provider-specific instructions for each LLM provider,
    plus default instructions as fallback.

    Attributes:
        context: The context these instructions are for
        provider_instructions: Map of provider to their specific instructions
        default_instructions: Fallback instructions if no provider match
    """
    context: InstructionContext
    provider_instructions: dict[LLMProviderType, ProviderInstructions] = field(default_factory=dict)
    default_instructions: ProviderInstructions | None = None

    def get_for_provider(self, provider: LLMProviderType) -> ProviderInstructions:
        """Get instructions for a specific provider.

        Falls back to default if provider-specific not found.
        """
        if provider in self.provider_instructions:
            if self.default_instructions:
                # Merge with defaults
                return self.default_instructions.merge(self.provider_instructions[provider])
            return self.provider_instructions[provider]

        if self.default_instructions:
            return self.default_instructions

        # Return empty instructions if nothing found
        return ProviderInstructions(provider=provider)

    def merge(self, other: 'ContextInstructions') -> 'ContextInstructions':
        """Merge with another ContextInstructions, other takes precedence."""
        merged_providers = dict(self.provider_instructions)

        for provider, instructions in other.provider_instructions.items():
            if provider in merged_providers:
                merged_providers[provider] = merged_providers[provider].merge(instructions)
            else:
                merged_providers[provider] = instructions

        merged_default = None
        if self.default_instructions and other.default_instructions:
            merged_default = self.default_instructions.merge(other.default_instructions)
        elif other.default_instructions:
            merged_default = other.default_instructions
        elif self.default_instructions:
            merged_default = self.default_instructions

        return ContextInstructions(
            context=other.context,
            provider_instructions=merged_providers,
            default_instructions=merged_default
        )


@dataclass(frozen=True)
class LLMInstructionSet:
    """Complete set of LLM instructions.

    Contains instructions for all contexts and all providers.
    Represents one level in the instruction hierarchy
    (system, CPG, or institution level).

    Attributes:
        id: Unique identifier for this instruction set
        name: Human-readable name
        version: Version string for tracking changes
        context_instructions: Map of context to context-specific instructions
        global_constraints: Constraints that apply to all contexts
    """
    id: str
    name: str
    version: str
    context_instructions: dict[InstructionContext, ContextInstructions] = field(default_factory=dict)
    global_constraints: tuple[str, ...] = field(default_factory=tuple)

    def get_for_context(self, context: InstructionContext) -> ContextInstructions | None:
        """Get instructions for a specific context."""
        return self.context_instructions.get(context)

    def get_instructions(
        self,
        context: InstructionContext,
        provider: LLMProviderType
    ) -> ProviderInstructions:
        """Get provider-specific instructions for a context.

        Includes global constraints merged into the result.
        """
        context_inst = self.get_for_context(context)
        if context_inst:
            provider_inst = context_inst.get_for_provider(provider)
        else:
            provider_inst = ProviderInstructions(provider=provider)

        # Add global constraints
        if self.global_constraints:
            return ProviderInstructions(
                provider=provider_inst.provider,
                system_prompt=provider_inst.system_prompt,
                formatting_style=provider_inst.formatting_style,
                temperature_hint=provider_inst.temperature_hint,
                few_shot_examples=provider_inst.few_shot_examples,
                custom_tags=provider_inst.custom_tags,
                constraints=self.global_constraints + provider_inst.constraints,
                response_format=provider_inst.response_format,
                metadata=provider_inst.metadata,
            )

        return provider_inst

    def merge(self, other: 'LLMInstructionSet') -> 'LLMInstructionSet':
        """Merge with another LLMInstructionSet, other takes precedence.

        Used to layer system → CPG → institution instructions.
        """
        merged_contexts = dict(self.context_instructions)

        for context, instructions in other.context_instructions.items():
            if context in merged_contexts:
                merged_contexts[context] = merged_contexts[context].merge(instructions)
            else:
                merged_contexts[context] = instructions

        return LLMInstructionSet(
            id=other.id,
            name=other.name,
            version=other.version,
            context_instructions=merged_contexts,
            global_constraints=self.global_constraints + other.global_constraints,
        )
