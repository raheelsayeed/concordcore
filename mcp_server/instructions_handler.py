#!/usr/bin/env python3
"""MCP tool handlers for LLM instruction scaffolding.

Provides MCP tools for:
- Getting provider-specific LLM instructions
- Building optimized prompts for different providers
"""

import json
import logging
from typing import Any

from mcp.types import Tool, TextContent

from ai.instructions import (
    InstructionManager,
    LLMProviderType,
    InstructionContext,
    FormattingStyle,
)

log = logging.getLogger(__name__)


def get_instruction_tools() -> list[Tool]:
    """Return the instruction-related MCP tools."""
    return [
        Tool(
            name="get_llm_instructions",
            description="""Get provider-specific LLM instructions for a context.

Returns instructions optimized for your LLM provider (Claude, OpenAI, Gemini)
for a specific usage context (extraction, conversation, explanation, summary).

Use this to understand how to format prompts and structure interactions
for optimal results with your LLM provider.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["claude", "openai", "gemini", "default"],
                        "description": "The LLM provider to get instructions for"
                    },
                    "context": {
                        "type": "string",
                        "enum": ["extraction", "conversation", "explanation", "summary"],
                        "description": "The usage context for the instructions"
                    },
                    "cpg_id": {
                        "type": "string",
                        "description": "Optional CPG ID to include CPG-specific instructions"
                    }
                },
                "required": ["provider", "context"]
            }
        ),
        Tool(
            name="build_optimized_prompt",
            description="""Build a prompt optimized for your LLM provider.

Takes your content and wraps it with provider-specific system prompts,
formatting, and optional few-shot examples. Returns ready-to-use
system and user prompts.

Use this when you need to make an LLM call for extraction, conversation,
explanation, or summary tasks.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["claude", "openai", "gemini"],
                        "description": "The target LLM provider"
                    },
                    "context": {
                        "type": "string",
                        "enum": ["extraction", "conversation", "explanation", "summary"],
                        "description": "The usage context"
                    },
                    "user_content": {
                        "type": "string",
                        "description": "The user message/content to include"
                    },
                    "cpg_id": {
                        "type": "string",
                        "description": "Optional CPG ID for CPG-specific context"
                    },
                    "include_examples": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to include few-shot examples"
                    },
                    "additional_context": {
                        "type": "string",
                        "description": "Optional additional context to include"
                    }
                },
                "required": ["provider", "context", "user_content"]
            }
        ),
    ]


async def handle_get_llm_instructions(
    args: dict,
    state: Any = None
) -> list[TextContent]:
    """Handle get_llm_instructions tool call."""
    provider_str = args.get("provider", "default")
    context_str = args.get("context", "conversation")
    cpg_id = args.get("cpg_id")

    # Parse provider
    try:
        provider = LLMProviderType.YAML(provider_str)
    except (ValueError, Exception):
        provider = LLMProviderType.DEFAULT

    # Parse context
    try:
        context = InstructionContext.YAML(context_str)
        if context is None:
            raise ValueError(f"Invalid context: {context_str}")
    except (ValueError, Exception):
        return [TextContent(type="text", text=json.dumps({
            "error": f"Unknown context: {context_str}",
            "valid_contexts": ["extraction", "conversation", "explanation", "summary"]
        }))]

    # Get instruction manager
    if cpg_id and state:
        try:
            cpg = state.load_cpg(cpg_id)
            manager = InstructionManager.for_cpg(cpg)
        except Exception as e:
            log.warning(f"Could not load CPG {cpg_id}: {e}, using system instructions")
            manager = InstructionManager.system_only()
    else:
        manager = InstructionManager.system_only()

    # Get instructions
    instructions = manager.get_instructions(context, provider)

    # Build response
    result = {
        "provider": provider.value,
        "context": context.value,
        "cpg_id": cpg_id,
        "instructions": {
            "formatting_style": instructions.formatting_style.value,
            "temperature_hint": instructions.temperature_hint,
            "constraints": list(instructions.constraints),
            "custom_tags": instructions.custom_tags,
            "has_system_prompt": bool(instructions.system_prompt),
            "few_shot_example_count": len(instructions.few_shot_examples),
            "response_format": instructions.response_format,
        },
        "system_prompt_preview": (
            instructions.system_prompt[:500] + "..."
            if instructions.system_prompt and len(instructions.system_prompt) > 500
            else instructions.system_prompt
        ),
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_build_optimized_prompt(
    args: dict,
    state: Any = None
) -> list[TextContent]:
    """Handle build_optimized_prompt tool call."""
    provider_str = args.get("provider", "default")
    context_str = args.get("context", "conversation")
    user_content = args.get("user_content", "")
    cpg_id = args.get("cpg_id")
    include_examples = args.get("include_examples", True)
    additional_context = args.get("additional_context")

    if not user_content:
        return [TextContent(type="text", text=json.dumps({
            "error": "user_content is required"
        }))]

    # Parse provider
    try:
        provider = LLMProviderType.YAML(provider_str)
    except (ValueError, Exception):
        provider = LLMProviderType.DEFAULT

    # Parse context
    try:
        context = InstructionContext.YAML(context_str)
        if context is None:
            raise ValueError(f"Invalid context: {context_str}")
    except (ValueError, Exception):
        return [TextContent(type="text", text=json.dumps({
            "error": f"Unknown context: {context_str}",
            "valid_contexts": ["extraction", "conversation", "explanation", "summary"]
        }))]

    # Get instruction manager
    if cpg_id and state:
        try:
            cpg = state.load_cpg(cpg_id)
            manager = InstructionManager.for_cpg(cpg)
        except Exception as e:
            log.warning(f"Could not load CPG {cpg_id}: {e}, using system instructions")
            manager = InstructionManager.system_only()
    else:
        manager = InstructionManager.system_only()

    # Build prompt
    prompt = manager.build_prompt(
        context=context,
        provider=provider,
        user_content=user_content,
        include_examples=include_examples,
        additional_context=additional_context,
    )

    # Get metadata
    instructions = manager.get_instructions(context, provider)

    result = {
        "provider": provider.value,
        "context": context.value,
        "cpg_id": cpg_id,
        "prompt": {
            "system": prompt["system"],
            "user": prompt["user"],
        },
        "metadata": {
            "formatting_style": instructions.formatting_style.value,
            "temperature_hint": instructions.temperature_hint,
            "included_examples": include_examples and len(instructions.few_shot_examples) > 0,
            "example_count": len(instructions.few_shot_examples) if include_examples else 0,
        },
        "_usage_note": (
            "Use 'system' as your system prompt and 'user' as the user message. "
            f"Suggested temperature: {instructions.temperature_hint or 'not specified'}"
        )
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
