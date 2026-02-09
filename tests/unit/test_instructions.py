#!/usr/bin/env python3
"""Unit tests for the LLM instruction scaffolding system."""

import pytest

from ai.instructions import (
    LLMProviderType,
    InstructionContext,
    FormattingStyle,
    FewShotExample,
    ProviderInstructions,
    ContextInstructions,
    LLMInstructionSet,
    InstructionLoader,
    InstructionManager,
    get_system_instructions,
)


class TestEnums:
    """Tests for instruction enum types."""

    def test_llm_provider_type_values(self):
        """Test LLMProviderType enum values."""
        assert LLMProviderType.CLAUDE.value == "claude"
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.GEMINI.value == "gemini"
        assert LLMProviderType.DEFAULT.value == "default"

    def test_instruction_context_values(self):
        """Test InstructionContext enum values."""
        assert InstructionContext.EXTRACTION.value == "extraction"
        assert InstructionContext.CONVERSATION.value == "conversation"
        assert InstructionContext.EXPLANATION.value == "explanation"
        assert InstructionContext.SUMMARY.value == "summary"

    def test_formatting_style_values(self):
        """Test FormattingStyle enum values."""
        assert FormattingStyle.XML_TAGS.value == "xml_tags"
        assert FormattingStyle.MARKDOWN.value == "markdown"
        assert FormattingStyle.JSON.value == "json"
        assert FormattingStyle.PLAIN.value == "plain"

    def test_llm_provider_yaml_parsing(self):
        """Test YAML parsing for LLMProviderType."""
        assert LLMProviderType.YAML("claude") == LLMProviderType.CLAUDE
        assert LLMProviderType.YAML("openai") == LLMProviderType.OPENAI

    def test_instruction_context_yaml_parsing(self):
        """Test YAML parsing for InstructionContext."""
        assert InstructionContext.YAML("extraction") == InstructionContext.EXTRACTION
        assert InstructionContext.YAML("conversation") == InstructionContext.CONVERSATION


class TestFewShotExample:
    """Tests for FewShotExample dataclass."""

    def test_create_example(self):
        """Test creating a FewShotExample."""
        example = FewShotExample(
            input="Test input",
            output="Test output",
            explanation="Test explanation"
        )
        assert example.input == "Test input"
        assert example.output == "Test output"
        assert example.explanation == "Test explanation"

    def test_example_without_explanation(self):
        """Test creating a FewShotExample without explanation."""
        example = FewShotExample(input="Input", output="Output")
        assert example.explanation is None

    def test_format_xml_tags(self):
        """Test formatting example with XML tags style."""
        example = FewShotExample(input="Input", output="Output")
        formatted = example.format(FormattingStyle.XML_TAGS)
        assert "<example>" in formatted
        assert "<input>Input</input>" in formatted
        assert "<output>Output</output>" in formatted

    def test_format_markdown(self):
        """Test formatting example with markdown style."""
        example = FewShotExample(input="Input", output="Output")
        formatted = example.format(FormattingStyle.MARKDOWN)
        assert "**Input:**" in formatted
        assert "**Output:**" in formatted

    def test_format_json(self):
        """Test formatting example with JSON style."""
        example = FewShotExample(input="Input", output="Output")
        formatted = example.format(FormattingStyle.JSON)
        assert '"input"' in formatted
        assert '"output"' in formatted


class TestProviderInstructions:
    """Tests for ProviderInstructions dataclass."""

    def test_create_instructions(self):
        """Test creating ProviderInstructions."""
        inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            system_prompt="Test prompt",
            formatting_style=FormattingStyle.XML_TAGS,
            temperature_hint=0.5,
        )
        assert inst.provider == LLMProviderType.CLAUDE
        assert inst.system_prompt == "Test prompt"
        assert inst.formatting_style == FormattingStyle.XML_TAGS
        assert inst.temperature_hint == 0.5

    def test_default_values(self):
        """Test default values for ProviderInstructions."""
        inst = ProviderInstructions(provider=LLMProviderType.DEFAULT)
        assert inst.system_prompt is None
        assert inst.formatting_style == FormattingStyle.PLAIN
        assert inst.temperature_hint is None
        assert inst.few_shot_examples == ()
        assert inst.constraints == ()

    def test_merge_instructions(self):
        """Test merging two ProviderInstructions."""
        base = ProviderInstructions(
            provider=LLMProviderType.DEFAULT,
            system_prompt="Base prompt",
            constraints=("Constraint 1",),
        )
        override = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            formatting_style=FormattingStyle.XML_TAGS,
            constraints=("Constraint 2",),
        )
        merged = base.merge(override)
        assert merged.provider == LLMProviderType.CLAUDE
        assert merged.system_prompt == "Base prompt"  # Base value preserved
        assert merged.formatting_style == FormattingStyle.XML_TAGS  # Override applied
        assert len(merged.constraints) == 2  # Constraints combined

    def test_build_full_prompt(self):
        """Test building a full prompt."""
        inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            system_prompt="System prompt",
            formatting_style=FormattingStyle.XML_TAGS,
            constraints=("Be precise",),
        )
        prompt = inst.build_full_prompt("User content")
        assert "System prompt" in prompt["system"]
        assert "User content" in prompt["user"]

    def test_format_examples(self):
        """Test formatting examples."""
        examples = (
            FewShotExample(input="In1", output="Out1"),
            FewShotExample(input="In2", output="Out2"),
        )
        inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            formatting_style=FormattingStyle.XML_TAGS,
            few_shot_examples=examples,
        )
        formatted = inst.format_examples()
        assert "<examples>" in formatted
        assert "In1" in formatted
        assert "Out1" in formatted

    def test_format_constraints(self):
        """Test formatting constraints."""
        inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            formatting_style=FormattingStyle.XML_TAGS,
            constraints=("Constraint A", "Constraint B"),
        )
        formatted = inst.format_constraints()
        assert "<constraints>" in formatted
        assert "Constraint A" in formatted


class TestContextInstructions:
    """Tests for ContextInstructions dataclass."""

    def test_create_context_instructions(self):
        """Test creating ContextInstructions."""
        claude_inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            system_prompt="Claude prompt",
        )
        ctx = ContextInstructions(
            context=InstructionContext.EXTRACTION,
            provider_instructions={LLMProviderType.CLAUDE: claude_inst},
        )
        assert ctx.context == InstructionContext.EXTRACTION
        assert LLMProviderType.CLAUDE in ctx.provider_instructions

    def test_get_for_provider(self):
        """Test getting instructions for a specific provider."""
        claude_inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            system_prompt="Claude prompt",
        )
        default_inst = ProviderInstructions(
            provider=LLMProviderType.DEFAULT,
            system_prompt="Default prompt",
        )
        ctx = ContextInstructions(
            context=InstructionContext.EXTRACTION,
            provider_instructions={LLMProviderType.CLAUDE: claude_inst},
            default_instructions=default_inst,
        )

        # Claude should get merged default + claude
        result = ctx.get_for_provider(LLMProviderType.CLAUDE)
        assert "Claude prompt" in result.system_prompt

        # OpenAI should fall back to default
        result = ctx.get_for_provider(LLMProviderType.OPENAI)
        assert result.system_prompt == "Default prompt"

    def test_merge_context_instructions(self):
        """Test merging ContextInstructions."""
        ctx1 = ContextInstructions(
            context=InstructionContext.EXTRACTION,
            provider_instructions={
                LLMProviderType.CLAUDE: ProviderInstructions(
                    provider=LLMProviderType.CLAUDE,
                    system_prompt="Base Claude",
                )
            },
        )
        ctx2 = ContextInstructions(
            context=InstructionContext.EXTRACTION,
            provider_instructions={
                LLMProviderType.CLAUDE: ProviderInstructions(
                    provider=LLMProviderType.CLAUDE,
                    constraints=("New constraint",),
                )
            },
        )
        merged = ctx1.merge(ctx2)
        claude_inst = merged.provider_instructions[LLMProviderType.CLAUDE]
        assert "Base Claude" in claude_inst.system_prompt
        assert "New constraint" in claude_inst.constraints


class TestLLMInstructionSet:
    """Tests for LLMInstructionSet dataclass."""

    def test_create_instruction_set(self):
        """Test creating an LLMInstructionSet."""
        inst_set = LLMInstructionSet(
            id="test_set",
            name="Test Instructions",
            version="1.0",
            global_constraints=("Never fabricate data",),
        )
        assert inst_set.id == "test_set"
        assert inst_set.version == "1.0"
        assert len(inst_set.global_constraints) == 1

    def test_get_instructions(self):
        """Test getting instructions from a set."""
        claude_inst = ProviderInstructions(
            provider=LLMProviderType.CLAUDE,
            system_prompt="Claude prompt",
        )
        ctx = ContextInstructions(
            context=InstructionContext.EXTRACTION,
            provider_instructions={LLMProviderType.CLAUDE: claude_inst},
        )
        inst_set = LLMInstructionSet(
            id="test",
            name="Test",
            version="1.0",
            context_instructions={InstructionContext.EXTRACTION: ctx},
            global_constraints=("Global constraint",),
        )

        result = inst_set.get_instructions(
            InstructionContext.EXTRACTION,
            LLMProviderType.CLAUDE
        )
        # Should include global constraint
        assert "Global constraint" in result.constraints

    def test_merge_instruction_sets(self):
        """Test merging two instruction sets."""
        set1 = LLMInstructionSet(
            id="base",
            name="Base",
            version="1.0",
            global_constraints=("Constraint 1",),
        )
        set2 = LLMInstructionSet(
            id="override",
            name="Override",
            version="2.0",
            global_constraints=("Constraint 2",),
        )
        merged = set1.merge(set2)
        assert merged.id == "override"
        assert merged.version == "2.0"
        assert len(merged.global_constraints) == 2


class TestInstructionLoader:
    """Tests for InstructionLoader."""

    def test_load_system_instructions(self):
        """Test loading system instructions."""
        loader = InstructionLoader()
        inst_set = loader.load_system_instructions()
        assert inst_set.id == "concord_system_default"
        assert inst_set.version == "1.0"
        assert len(inst_set.global_constraints) > 0

    def test_cache_works(self):
        """Test that caching works."""
        loader = InstructionLoader()
        inst1 = loader.load_system_instructions()
        inst2 = loader.load_system_instructions()
        assert inst1 is inst2  # Same object from cache

    def test_clear_cache(self):
        """Test clearing the cache."""
        loader = InstructionLoader()
        loader.load_system_instructions()
        assert len(loader._cache) > 0
        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_file_not_found(self):
        """Test handling of missing file."""
        loader = InstructionLoader()
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/path.yaml")


class TestGetSystemInstructions:
    """Tests for get_system_instructions function."""

    def test_get_system_instructions(self):
        """Test getting cached system instructions."""
        inst = get_system_instructions()
        assert inst.id == "concord_system_default"

    def test_extraction_context_exists(self):
        """Test that extraction context is defined."""
        inst = get_system_instructions()
        ctx = inst.get_for_context(InstructionContext.EXTRACTION)
        assert ctx is not None

    def test_conversation_context_exists(self):
        """Test that conversation context is defined."""
        inst = get_system_instructions()
        ctx = inst.get_for_context(InstructionContext.CONVERSATION)
        assert ctx is not None

    def test_claude_has_xml_style(self):
        """Test that Claude instructions use XML style."""
        inst = get_system_instructions()
        result = inst.get_instructions(
            InstructionContext.EXTRACTION,
            LLMProviderType.CLAUDE
        )
        assert result.formatting_style == FormattingStyle.XML_TAGS


class TestInstructionManager:
    """Tests for InstructionManager."""

    def test_system_only(self):
        """Test creating system-only manager."""
        manager = InstructionManager.system_only()
        assert manager.instruction_set.id == "concord_system_default"
        assert manager.cpg is None

    def test_get_instructions(self):
        """Test getting instructions from manager."""
        manager = InstructionManager.system_only()
        inst = manager.get_instructions(
            InstructionContext.EXTRACTION,
            LLMProviderType.CLAUDE
        )
        assert inst.provider == LLMProviderType.CLAUDE

    def test_build_prompt(self):
        """Test building a prompt."""
        manager = InstructionManager.system_only()
        prompt = manager.build_prompt(
            context=InstructionContext.EXTRACTION,
            provider=LLMProviderType.CLAUDE,
            user_content="Extract LDL from: LDL-C 145 mg/dL"
        )
        assert "system" in prompt
        assert "user" in prompt
        assert len(prompt["system"]) > 0
        assert "145" in prompt["user"]

    def test_build_prompt_with_additional_context(self):
        """Test building a prompt with additional context."""
        manager = InstructionManager.system_only()
        prompt = manager.build_prompt(
            context=InstructionContext.CONVERSATION,
            provider=LLMProviderType.CLAUDE,
            user_content="Why do I need a statin?",
            additional_context="Patient has LDL 180 mg/dL"
        )
        assert "LDL 180" in prompt["system"]

    def test_get_temperature(self):
        """Test getting temperature hint."""
        manager = InstructionManager.system_only()
        temp = manager.get_temperature(
            InstructionContext.EXTRACTION,
            LLMProviderType.CLAUDE
        )
        assert temp == 0.0  # Extraction should be deterministic

    def test_get_formatting_style(self):
        """Test getting formatting style."""
        manager = InstructionManager.system_only()
        style = manager.get_formatting_style(
            InstructionContext.EXTRACTION,
            LLMProviderType.CLAUDE
        )
        assert style == FormattingStyle.XML_TAGS

    def test_to_dict(self):
        """Test converting manager to dict."""
        manager = InstructionManager.system_only()
        data = manager.to_dict()
        assert "instruction_set_id" in data
        assert "available_contexts" in data


class TestInstructionIntegration:
    """Integration tests for the instruction system."""

    def test_extraction_prompt_for_claude(self):
        """Test that Claude extraction prompt has expected structure."""
        manager = InstructionManager.system_only()
        prompt = manager.build_prompt(
            context=InstructionContext.EXTRACTION,
            provider=LLMProviderType.CLAUDE,
            user_content="Extract diabetes status from: Type 2 DM"
        )
        # Should have XML-style formatting
        assert "<" in prompt["system"]
        # Should have clinical extraction context
        assert "extract" in prompt["system"].lower() or "clinical" in prompt["system"].lower()

    def test_conversation_prompt_for_openai(self):
        """Test that OpenAI conversation prompt has expected structure."""
        manager = InstructionManager.system_only()
        prompt = manager.build_prompt(
            context=InstructionContext.CONVERSATION,
            provider=LLMProviderType.OPENAI,
            user_content="Why do I need this medication?"
        )
        # Should have markdown-style formatting
        assert "#" in prompt["system"] or "**" in prompt["system"]

    def test_all_providers_have_extraction_instructions(self):
        """Test that all providers have extraction context instructions."""
        manager = InstructionManager.system_only()
        for provider in [LLMProviderType.CLAUDE, LLMProviderType.OPENAI, LLMProviderType.GEMINI]:
            inst = manager.get_instructions(InstructionContext.EXTRACTION, provider)
            assert inst.system_prompt is not None or inst.constraints

    def test_global_constraints_present(self):
        """Test that global safety constraints are included."""
        manager = InstructionManager.system_only()
        inst = manager.get_instructions(
            InstructionContext.EXTRACTION,
            LLMProviderType.CLAUDE
        )
        # Should have some constraints about not fabricating data
        constraint_text = " ".join(inst.constraints).lower()
        assert "never" in constraint_text or "fabricate" in constraint_text or "not" in constraint_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
