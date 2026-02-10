#!/usr/bin/env python3
"""Prompt templates for LLM integration.

Provides structured prompt builders for different use cases:
- Patient education and Q&A
- Provider clinical summaries
- Data collection conversations
- Report generation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .copilot import CopilotContext


class PromptStyle(Enum):
    """Style of prompt to generate."""
    CONVERSATIONAL = "conversational"  # For chat interfaces
    CLINICAL = "clinical"              # For provider summaries
    EDUCATIONAL = "educational"        # For patient education
    COLLECTION = "collection"          # For gathering missing data


@dataclass
class PromptBuilder:
    """Builder for generating prompts for different LLM use cases.

    Example:
        ```python
        builder = PromptBuilder(style=PromptStyle.CONVERSATIONAL)
        prompt = builder.build_qa_prompt(context, "What does my LDL mean?")
        ```
    """

    style: PromptStyle = PromptStyle.CONVERSATIONAL

    def build_qa_prompt(self, context: CopilotContext, question: str) -> dict[str, str]:
        """Build a Q&A prompt for patient questions.

        Args:
            context: The evaluation context.
            question: Patient's question.

        Returns:
            Dict with 'system' and 'user' prompts.
        """
        if self.style == PromptStyle.CLINICAL:
            return self._clinical_qa(context, question)
        elif self.style == PromptStyle.EDUCATIONAL:
            return self._educational_qa(context, question)
        else:
            return self._conversational_qa(context, question)

    def build_summary_prompt(self, context: CopilotContext) -> dict[str, str]:
        """Build a prompt for generating a summary.

        Args:
            context: The evaluation context.

        Returns:
            Dict with 'system' and 'user' prompts.
        """
        if self.style == PromptStyle.CLINICAL:
            return self._clinical_summary(context)
        else:
            return self._patient_summary(context)

    def build_collection_prompt(
        self,
        context: CopilotContext,
        missing_var: dict
    ) -> dict[str, str]:
        """Build a prompt for collecting missing patient data.

        Args:
            context: The evaluation context.
            missing_var: Dict with 'id', 'title', 'type' of missing variable.

        Returns:
            Dict with 'system' and 'user' prompts.
        """
        system = """You are a friendly health assistant helping collect health information.

INSTRUCTIONS:
1. Ask for ONE piece of information at a time
2. Be conversational and empathetic
3. Explain briefly why this information is helpful
4. Accept the patient's answer and confirm you understood
5. If the patient is unsure, offer to skip and continue

Do NOT provide medical advice. Only collect information."""

        var_title = missing_var.get('title', missing_var.get('id'))
        var_type = missing_var.get('type', 'text')

        user = f"""Please ask the patient for: {var_title}

Expected answer type: {var_type}

Generate a friendly, single question to collect this information."""

        return {'system': system, 'user': user}

    def build_explanation_prompt(
        self,
        context: CopilotContext,
        topic: str
    ) -> dict[str, str]:
        """Build a prompt to explain a specific topic from the evaluation.

        Args:
            context: The evaluation context.
            topic: The topic to explain (e.g., 'LDL', 'statin', 'ASCVD risk').

        Returns:
            Dict with 'system' and 'user' prompts.
        """
        system = f"""You are a health educator explaining medical concepts to patients.

CLINICAL CONTEXT:
{context.to_prompt_context()}

INSTRUCTIONS:
1. Explain the topic in simple, accessible language
2. Relate it to the patient's specific evaluation results when possible
3. Use analogies to make concepts clear
4. Keep explanations concise (2-3 paragraphs max)
5. Always note this is educational, not medical advice"""

        user = f"Please explain: {topic}"

        return {'system': system, 'user': user}

    def _conversational_qa(self, context: CopilotContext, question: str) -> dict[str, str]:
        """Conversational style Q&A prompt."""
        system = f"""You are a friendly health assistant helping someone understand their health evaluation.

CLINICAL CONTEXT:
{context.to_prompt_context()}

GUIDELINES:
- Be warm and empathetic
- Use simple language
- Only discuss what's in the context
- Encourage follow-up with healthcare providers
- Keep responses concise but complete"""

        return {'system': system, 'user': question}

    def _clinical_qa(self, context: CopilotContext, question: str) -> dict[str, str]:
        """Clinical style Q&A for providers."""
        system = f"""You are a clinical decision support assistant for healthcare providers.

EVALUATION SUMMARY:
{context.to_prompt_context()}

GUIDELINES:
- Use clinical terminology
- Be precise and evidence-based
- Reference the guideline sources when relevant
- Note any limitations in the evaluation"""

        return {'system': system, 'user': question}

    def _educational_qa(self, context: CopilotContext, question: str) -> dict[str, str]:
        """Educational style for patient learning."""
        system = f"""You are a health educator helping a patient learn about their health.

PATIENT'S EVALUATION:
{context.to_prompt_context()}

GUIDELINES:
- Prioritize education and understanding
- Use analogies and simple explanations
- Break down complex concepts
- Encourage questions
- Always distinguish education from medical advice"""

        return {'system': system, 'user': question}

    def _clinical_summary(self, context: CopilotContext) -> dict[str, str]:
        """Generate a clinical summary for providers."""
        system = """Generate a clinical summary suitable for a healthcare provider's review.

FORMAT:
- Chief findings (1-2 sentences)
- Relevant assessments (bullet points)
- Guideline-based recommendations (bullet points)
- Data gaps or limitations
- Suggested next steps"""

        user = f"""Generate a clinical summary from this evaluation:

{context.to_prompt_context()}"""

        return {'system': system, 'user': user}

    def _patient_summary(self, context: CopilotContext) -> dict[str, str]:
        """Generate a patient-friendly summary."""
        system = """Generate a patient-friendly summary of health evaluation results.

FORMAT:
- Opening: Brief, reassuring context
- Key findings: What the evaluation shows (simple language)
- Recommendations: What actions are suggested and why
- Next steps: What the patient should do
- Closing: Encouragement to discuss with their doctor

Keep it warm, clear, and under 200 words."""

        user = f"""Generate a patient-friendly summary from this evaluation:

{context.to_prompt_context()}"""

        return {'system': system, 'user': user}


# Pre-built prompt templates for common scenarios
TEMPLATES = {
    'patient_greeting': """Hello! I'm your health assistant. I've reviewed your health information
against the {cpg_title} guidelines. I can help you understand:

- Your assessment results
- Why certain recommendations apply to you
- What the medical terms mean

What would you like to know?""",

    'no_recommendations': """Based on your health data and the {cpg_title} guidelines,
there are no specific recommendations that apply to you at this time.

This is generally good news! It means your current health indicators don't trigger
any of the guideline criteria.

Is there anything you'd like me to explain about the evaluation?""",

    'missing_data_intro': """To give you a complete evaluation, I need a bit more information.
I'll ask you a few quick questions. If you're not sure about any answer, just let me know
and we can skip it.

Ready to get started?""",

    'evaluation_complete': """I've completed your health evaluation using the {cpg_title} guidelines.

Here's what I found:
{summary}

Would you like me to explain any of these findings in more detail?""",
}


def format_template(template_name: str, **kwargs) -> str:
    """Format a template with provided values.

    Args:
        template_name: Name of template from TEMPLATES dict.
        **kwargs: Values to substitute in template.

    Returns:
        Formatted template string.
    """
    template = TEMPLATES.get(template_name, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
