#!/usr/bin/env python3
"""Health Copilot - LLM-grounded clinical decision support.

This module provides a bridge between Concord's evidence-based evaluation
and LLM-powered conversational interfaces. The LLM acts as an explainer
of computed recommendations, not a generator of medical advice.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

from concordcore.core.cpg import CPG
from concordcore.core.concord import Concord, PipelineResult
from concordcore.core.errors import NeedAttestationError
from concordcore.core.healthcontext import HealthContext
from concordcore.primitives.types import Persona
from .llm_provider import ConversationProvider

if TYPE_CHECKING:
    from ai.instructions import InstructionManager, LLMProviderType


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class CopilotContext:
    """Structured context from Concord evaluation for LLM grounding.

    This dataclass contains all the information an LLM needs to have
    an informed, evidence-based conversation about health recommendations.
    """

    # Evaluation results
    is_eligible: bool | None = None
    is_executable: bool | None = None

    # Recommendations that apply
    recommendations: list[dict] = field(default_factory=list)

    # Assessment results with narratives
    assessments: list[dict] = field(default_factory=list)

    # Variables that need patient input
    missing_data: list[dict] = field(default_factory=list)

    # Patient's health data values
    health_data: list[dict] = field(default_factory=list)

    # Evidence and citations
    citations: list[str] = field(default_factory=list)

    # CPG metadata
    cpg_title: str = None
    cpg_publisher: str = None

    # Raw evaluation errors
    errors: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Format context for LLM prompt injection."""
        sections = []

        if self.cpg_title:
            sections.append(f"## Clinical Guideline: {self.cpg_title}")
            if self.cpg_publisher:
                sections.append(f"Publisher: {self.cpg_publisher}")

        if self.is_eligible is False:
            sections.append("\n## Eligibility: NOT ELIGIBLE")
            sections.append("This guideline does not apply to this patient.")
            return "\n".join(sections)

        if self.health_data:
            sections.append("\n## Patient Health Data")
            for hd in self.health_data:
                sections.append(f"- **{hd.get('title', hd.get('id'))}**: {hd.get('value', 'N/A')}")

        if self.assessments:
            sections.append("\n## Health Assessments")
            for a in self.assessments:
                result = "Yes" if a.get('result') else "No" if a.get('result') is False else "Unknown"
                sections.append(f"- **{a.get('title', a.get('id'))}**: {result}")
                if a.get('narrative'):
                    sections.append(f"  {a['narrative']}")

        if self.recommendations:
            sections.append("\n## Recommendations")
            for r in self.recommendations:
                sections.append(f"- **{r.get('title', r.get('id'))}**")
                if r.get('narrative'):
                    sections.append(f"  {r['narrative']}")
                if r.get('class_of_recommendation'):
                    sections.append(f"  (Class: {r['class_of_recommendation']})")

        if self.missing_data:
            sections.append("\n## Missing Information Needed")
            for m in self.missing_data:
                sections.append(f"- {m.get('title', m.get('id'))}")

        if self.citations:
            sections.append("\n## Evidence Sources")
            for c in self.citations[:5]:  # Limit citations
                sections.append(f"- {c}")

        if self.errors:
            sections.append("\n## Evaluation Notes")
            for e in self.errors:
                sections.append(f"- {e}")

        return "\n".join(sections)

    def as_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'is_eligible': self.is_eligible,
            'is_executable': self.is_executable,
            'health_data': self.health_data,
            'recommendations': self.recommendations,
            'assessments': self.assessments,
            'missing_data': self.missing_data,
            'citations': self.citations,
            'cpg_title': self.cpg_title,
            'cpg_publisher': self.cpg_publisher,
            'errors': self.errors,
        }


class HealthCopilot:
    """LLM-grounded health assistant powered by Concord.

    The HealthCopilot evaluates patient data against clinical practice
    guidelines and provides structured context for LLM conversations.
    The LLM explains computed recommendations rather than generating
    medical advice, ensuring responses are evidence-based.

    Example:
        ```python
        from ai import HealthCopilot
        from concordcore.core.cpg_registry import get_registry
        from concordcore.core.healthcontext import HealthContext

        # Initialize
        cpg = get_registry().get('2019AccPrimaryPreventionASCVD')
        copilot = HealthCopilot(cpg)

        # Evaluate patient
        context = copilot.evaluate(patient_health_context)

        # Get LLM-ready prompt
        prompt = copilot.build_prompt(
            user_question="Why do I need a statin?",
            context=context
        )

        # Send to your LLM provider
        response = your_llm.generate(prompt)
        ```
    """

    def __init__(
        self,
        cpg: CPG,
        persona: Persona = Persona.patient,
        strict_validation: bool = False,
        llm_provider: 'LLMProviderType | None' = None,
        instruction_manager: 'InstructionManager | None' = None,
    ):
        """Initialize the Health Copilot.

        Args:
            cpg: The clinical practice guideline to evaluate against.
            persona: The target audience (patient or provider).
            strict_validation: If True, enforce strict data validation.
            llm_provider: Optional LLM provider type for instruction-based prompts.
                If provided, uses provider-specific formatting.
            instruction_manager: Optional InstructionManager. If not provided but
                llm_provider is set, creates one from the CPG.
        """
        self.cpg = cpg
        self.persona = persona
        self.strict_validation = strict_validation
        self.llm_provider = llm_provider
        self.conversation_history: list[ConversationTurn] = []
        self._last_context: CopilotContext | None = None
        self._last_result: PipelineResult | None = None

        # Set up instruction manager
        if instruction_manager:
            self._instruction_manager = instruction_manager
        elif llm_provider:
            from ai.instructions import InstructionManager
            self._instruction_manager = InstructionManager.for_cpg(cpg)
        else:
            self._instruction_manager = None

    def evaluate(
        self,
        health_context: HealthContext,
        skip_eligibility: bool = False
    ) -> CopilotContext:
        """Evaluate patient data and build LLM context.

        Args:
            health_context: Patient health data.
            skip_eligibility: If True, skip eligibility check.

        Returns:
            CopilotContext with structured evaluation results.
        """
        concord = Concord(
            cpg=self.cpg,
            healthcontext=health_context,
            strict_validation=self.strict_validation,
            ignore_eligibility=skip_eligibility
        )

        context = CopilotContext(
            cpg_title=self.cpg.title,
            cpg_publisher=self.cpg.publisher
        )

        try:
            result = concord.evaluate(
                skip_eligibility=skip_eligibility,
                ignore_attestations=True  # We'll handle missing data separately
            )
            self._last_result = result

            # Extract eligibility
            if result.eligibility:
                context.is_eligible = result.eligibility.is_eligible

            # Extract sufficiency and health data
            if result.sufficiency:
                context.is_executable = result.sufficiency.is_executable

                # Get missing attestable variables
                if result.sufficiency.attestation_variables:
                    for ev in result.sufficiency.attestation_variables:
                        var_type = ev.record.var.type
                        title = ev.record.var.title or ev.record.id
                        context.missing_data.append({
                            'id': ev.record.id,
                            'title': title,
                            'type': str(var_type.value) if var_type else None
                        })

                # Extract patient's health data values
                for ev in result.sufficiency.context.evaluation_list:
                    if ev.record.has_value:
                        values = ev.record.values
                        value_repr = values.representation if hasattr(values, 'representation') else str(values)
                        title = ev.record.var.title or ev.record.id
                        context.health_data.append({
                            'id': ev.record.id,
                            'title': title,
                            'value': value_repr,
                            'narrative': ev.record.narrative if hasattr(ev.record, 'narrative') else None
                        })

            # Extract assessments with narratives
            if result.assessment:
                for assessed in result.assessment.assessments:
                    title = assessed.id
                    if assessed.var.title:
                        title = assessed.var.title
                    assessment_dict = {
                        'id': assessed.id,
                        'title': title,
                        'result': assessed.value.value if assessed.value else None,
                        'narrative': assessed.narrative
                    }
                    context.assessments.append(assessment_dict)

            # Extract recommendations
            if result.recommendations:
                for rec in result.recommendations.applied or []:
                    rec_dict = {
                        'id': rec.recommendation.id,
                        'title': rec.recommendation.title,
                        'type': str(rec.recommendation.type) if rec.recommendation.type else None,
                        'narrative': rec.narrative,
                        'class_of_recommendation': str(rec.recommendation.class_of_recommendation) if rec.recommendation.class_of_recommendation else None,
                        'applies': rec.applies
                    }
                    context.recommendations.append(rec_dict)

            # Extract citations
            citations = self.cpg.recommendation_context()
            if citations:
                context.citations = [str(c) for c in citations]

            # Capture errors
            context.errors = [str(e) for e in result.errors]

        except NeedAttestationError as e:
            # Patient needs to provide more data
            for ev in e.records:
                var_type = ev.record.var.type
                title = ev.record.var.title or ev.record.id
                context.missing_data.append({
                    'id': ev.record.id,
                    'title': title,
                    'type': str(var_type.value) if var_type else None
                })
            context.errors.append("Additional patient information needed to complete evaluation.")

        except Exception as e:
            context.errors.append(str(e))

        self._last_context = context
        return context

    def build_prompt(
        self,
        user_question: str,
        context: CopilotContext = None,
        include_history: bool = True
    ) -> dict[str, str]:
        """Build a grounded prompt for the LLM.

        Args:
            user_question: The patient/user's question.
            context: Evaluation context (uses last if not provided).
            include_history: Include conversation history.

        Returns:
            Dict with 'system' and 'user' prompt components.
        """
        context = context or self._last_context

        # Use instruction manager if available
        if self._instruction_manager and self.llm_provider:
            from ai.instructions import InstructionContext
            prompt = self._build_instruction_based_prompt(
                user_question, context, include_history
            )
        else:
            prompt = {
                'system': self._build_system_prompt(context),
                'user': self._build_user_prompt(user_question, context, include_history)
            }

        # Track conversation
        self.conversation_history.append(ConversationTurn(
            role='user',
            content=user_question
        ))

        return prompt

    def _build_instruction_based_prompt(
        self,
        user_question: str,
        context: CopilotContext,
        include_history: bool
    ) -> dict[str, str]:
        """Build prompt using instruction manager for provider-specific formatting."""
        from ai.instructions import InstructionContext

        # Build user content with question and history
        user_content = self._build_user_prompt(user_question, context, include_history)

        # Get clinical context for additional context
        clinical_context = context.to_prompt_context() if context else "No evaluation data available."

        # Add persona information
        persona_desc = "patient" if self.persona == Persona.patient else "healthcare provider"
        additional = f"Target audience: {persona_desc}\n\n{clinical_context}"

        # Build using instruction manager
        return self._instruction_manager.build_prompt(
            context=InstructionContext.CONVERSATION,
            provider=self.llm_provider,
            user_content=user_content,
            include_examples=False,  # Don't include examples in conversation
            additional_context=additional,
        )

    def _build_system_prompt(self, context: CopilotContext) -> str:
        """Build the system prompt with grounding instructions."""
        persona_desc = "patient" if self.persona == Persona.patient else "healthcare provider"

        return f"""You are a health assistant helping a {persona_desc} understand their health evaluation results.

CRITICAL INSTRUCTIONS:
1. ONLY discuss information provided in the Clinical Context below
2. NEVER invent, guess, or hallucinate medical information
3. If asked about something not in the context, say "I don't have that information in your evaluation"
4. Always encourage consulting with healthcare providers for medical decisions
5. Be empathetic but factual
6. Use simple language appropriate for a {persona_desc}

CLINICAL CONTEXT (Evidence-Based):
{context.to_prompt_context() if context else "No evaluation data available."}

Remember: You are explaining computed, evidence-based recommendations. You are NOT providing medical advice."""

    def _build_user_prompt(
        self,
        question: str,
        context: CopilotContext,
        include_history: bool
    ) -> str:
        """Build the user prompt with question and optional history."""
        parts = []

        if include_history and len(self.conversation_history) > 1:
            parts.append("Previous conversation:")
            for turn in self.conversation_history[-6:]:  # Last 3 exchanges
                parts.append(f"{turn.role.upper()}: {turn.content}")
            parts.append("")

        parts.append(f"Current question: {question}")

        # Add helpful hints based on context
        if context and context.missing_data:
            missing_names = [m.get('title', m.get('id')) for m in context.missing_data]
            parts.append(f"\n(Note: The following information is still needed: {', '.join(missing_names)})")

        return "\n".join(parts)

    def record_response(self, response: str) -> None:
        """Record an LLM response in conversation history.

        Args:
            response: The LLM's response text.
        """
        self.conversation_history.append(ConversationTurn(
            role='assistant',
            content=response
        ))

    def get_attestation_questions(self) -> list[dict]:
        """Get questions to ask the patient for missing data.

        Returns:
            List of question dictionaries with id, title, and suggested prompt.
        """
        if not self._last_context:
            return []

        questions = []
        for missing in self._last_context.missing_data:
            var_id = missing.get('id')
            title = missing.get('title', var_id)
            var_type = missing.get('type')

            # Generate appropriate question based on type
            if var_type == 'boolean':
                prompt = f"Do you have {title.lower()}? (yes/no)"
            elif var_type == 'integer':
                prompt = f"What is your {title.lower()} value?"
            elif var_type in ('decimal', 'float'):
                prompt = f"What is your {title.lower()} measurement?"
            else:
                prompt = f"Please provide your {title.lower()}."

            questions.append({
                'id': var_id,
                'title': title,
                'prompt': prompt,
                'type': var_type
            })

        return questions

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []

    @property
    def has_recommendations(self) -> bool:
        """Check if evaluation produced recommendations."""
        return bool(self._last_context and self._last_context.recommendations)

    @property
    def needs_more_data(self) -> bool:
        """Check if more patient data is needed."""
        return bool(self._last_context and self._last_context.missing_data)
