#!/usr/bin/env python3
"""Deep explanation generator for recommendations.

This module generates comprehensive explanations for clinical recommendations,
including:
- Assessment chain showing the logic that led to the recommendation
- Source data used in evaluation
- Evidence citations and grades
- Patient-friendly and provider-focused summaries

Example usage:
    from mcp_server.explanation import ExplanationGenerator

    generator = ExplanationGenerator()
    explanation = generator.explain(concord, "rec_high_ldl")
    print(explanation.patient_summary)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.concord import Concord
from core.recommendation import EvaluatedRecommendation
from core.evaluation import EvaluatedRecord
from primitives.types import Persona

log = logging.getLogger(__name__)


@dataclass
class RecommendationExplanation:
    """Comprehensive explanation of a recommendation.

    Attributes:
        recommendation_id: The recommendation identifier
        title: Recommendation title
        applies: Whether the recommendation applies
        assessment_chain: Ordered list of assessments leading to this
        citations: List of evidence citations
        class_of_recommendation: COR grade if available
        level_of_evidence: LOE grade if available
        uspstf_grade: USPSTF grade if available
        patient_summary: Patient-friendly explanation
        provider_summary: Clinical summary for providers
        source_data: Data values used in the recommendation
    """
    recommendation_id: str
    title: str
    applies: bool

    # Assessment chain
    assessment_chain: list[dict]

    # Evidence
    citations: list[str]
    class_of_recommendation: str | None
    level_of_evidence: str | None
    uspstf_grade: str | None

    # Summaries
    patient_summary: str
    provider_summary: str

    # Source data
    source_data: list[dict]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "applies": self.applies,
            "assessment_chain": self.assessment_chain,
            "evidence": {
                "citations": self.citations,
                "class_of_recommendation": self.class_of_recommendation,
                "level_of_evidence": self.level_of_evidence,
                "uspstf_grade": self.uspstf_grade,
                "citations_count": len(self.citations)
            },
            "summaries": {
                "patient": self.patient_summary,
                "provider": self.provider_summary
            },
            "source_data": self.source_data
        }


class ExplanationGenerator:
    """Generate deep explanations for recommendations.

    Creates comprehensive explanations that trace the logic from
    source data through assessments to the final recommendation,
    with evidence citations and persona-appropriate summaries.
    """

    def explain(
        self,
        concord: Concord,
        recommendation_id: str,
        persona: Persona = Persona.patient
    ) -> RecommendationExplanation:
        """Generate comprehensive explanation for a recommendation.

        Args:
            concord: Concord instance with completed evaluation
            recommendation_id: ID of recommendation to explain
            persona: Persona for summary generation

        Returns:
            RecommendationExplanation with full explanation

        Raises:
            ValueError: If recommendation not found
        """
        # Find the recommendation
        eval_rec = concord.evaluated_recommendation(recommendation_id)
        if not eval_rec:
            raise ValueError(f"Recommendation not found: {recommendation_id}")

        rec_var = eval_rec.recommendation

        # Build assessment chain
        assessment_chain = self._build_assessment_chain(eval_rec, concord)

        # Extract source data
        source_data = self._extract_source_data(eval_rec, concord)

        # Generate summaries
        patient_summary = self._generate_patient_summary(
            eval_rec, assessment_chain, source_data
        )
        provider_summary = self._generate_provider_summary(
            eval_rec, assessment_chain, source_data
        )

        return RecommendationExplanation(
            recommendation_id=recommendation_id,
            title=rec_var.title,
            applies=eval_rec.applies,
            assessment_chain=assessment_chain,
            citations=rec_var.citations or [],
            class_of_recommendation=str(rec_var.class_of_recommendation)
                if rec_var.class_of_recommendation else None,
            level_of_evidence=str(rec_var.level_of_evidence)
                if rec_var.level_of_evidence else None,
            uspstf_grade=rec_var.uspstf_grade.value
                if rec_var.uspstf_grade else None,
            patient_summary=patient_summary,
            provider_summary=provider_summary,
            source_data=source_data
        )

    def _build_assessment_chain(
        self,
        eval_rec: EvaluatedRecommendation,
        concord: Concord
    ) -> list[dict]:
        """Build the chain of assessments that led to this recommendation.

        Args:
            eval_rec: The evaluated recommendation
            concord: Concord instance

        Returns:
            List of assessment chain items
        """
        chain = []

        # Get based_on records from recommendation
        based_on = eval_rec.based_on or []

        for record in based_on:
            # Handle both EvaluatedRecord and Record types
            rec = record.record if hasattr(record, 'record') else record

            chain_item = {
                "id": rec.id if hasattr(rec, 'id') else str(rec),
                "title": self._get_title(rec),
                "value": self._extract_value(rec),
                "narrative": getattr(rec, 'narrative', None),
                "expression": self._get_expression(rec),
                "role": "assessment"
            }

            # Get source records (the variables this assessment depends on)
            source_records = self._get_source_records(rec)
            if source_records:
                chain_item["depends_on"] = source_records

            chain.append(chain_item)

        return chain

    def _get_title(self, rec) -> str:
        """Extract title from record."""
        if hasattr(rec, 'var') and rec.var:
            return rec.var.title or rec.id
        if hasattr(rec, 'id'):
            return rec.id
        return str(rec)

    def _extract_value(self, rec) -> Any:
        """Extract value from record."""
        if hasattr(rec, 'value') and rec.value:
            return rec.value.value if hasattr(rec.value, 'value') else rec.value
        if hasattr(rec, 'assessment_value'):
            return rec.assessment_value
        return None

    def _get_expression(self, rec) -> str | None:
        """Get expression from record's variable."""
        if hasattr(rec, 'var') and hasattr(rec.var, 'expression'):
            return rec.var.expression
        return None

    def _get_source_records(self, rec) -> list[dict]:
        """Get source records that this record depends on."""
        sources = []

        if hasattr(rec, 'value') and rec.value:
            value = rec.value
            if hasattr(value, 'source') and value.source:
                for source in value.source:
                    if hasattr(source, 'id'):
                        sources.append({
                            "id": source.id,
                            "title": self._get_title(source),
                            "value": self._extract_value(source)
                        })
        return sources

    def _extract_source_data(
        self,
        eval_rec: EvaluatedRecommendation,
        concord: Concord
    ) -> list[dict]:
        """Extract original patient data used in this recommendation.

        Args:
            eval_rec: The evaluated recommendation
            concord: Concord instance

        Returns:
            List of source data items
        """
        source_data = []
        seen_ids = set()

        # Collect from based_on records
        try:
            based_on_records = eval_rec.based_on_records or []
        except Exception:
            based_on_records = eval_rec.based_on or []

        for record in based_on_records:
            rec = record.record if hasattr(record, 'record') else record

            rec_id = rec.id if hasattr(rec, 'id') else str(rec)
            if rec_id in seen_ids:
                continue
            seen_ids.add(rec_id)

            data_item = {
                "variable_id": rec_id,
                "title": self._get_title(rec),
                "value": self._extract_value(rec),
                "date": self._extract_date(rec),
                "category": self._get_category(rec)
            }
            source_data.append(data_item)

        return source_data

    def _extract_date(self, rec) -> str | None:
        """Extract date from record."""
        if hasattr(rec, 'value') and rec.value:
            date = getattr(rec.value, 'date', None)
            if date:
                return str(date)
        return None

    def _get_category(self, rec) -> str | None:
        """Get variable category from record."""
        if hasattr(rec, 'var') and rec.var:
            cat = getattr(rec.var, 'category', None)
            if cat:
                return str(cat.value) if hasattr(cat, 'value') else str(cat)
        return None

    def _generate_patient_summary(
        self,
        eval_rec: EvaluatedRecommendation,
        assessment_chain: list[dict],
        source_data: list[dict]
    ) -> str:
        """Generate patient-friendly explanation.

        Args:
            eval_rec: Evaluated recommendation
            assessment_chain: Assessment chain
            source_data: Source data items

        Returns:
            Patient-friendly summary string
        """
        rec = eval_rec.recommendation
        parts = []

        # Opening statement
        if not eval_rec.applies:
            parts.append(
                f"This recommendation ({rec.title}) does not apply to you "
                "based on your health data."
            )
            return " ".join(parts)

        parts.append(f"Based on your health information, {rec.title.lower()}.")

        # Key findings
        key_findings = [
            a for a in assessment_chain
            if a.get('value') is True or isinstance(a.get('value'), (int, float))
        ]
        if key_findings:
            parts.append("\n\nKey findings that led to this recommendation:")
            for finding in key_findings[:3]:  # Limit to top 3
                title = finding.get('title', finding['id'])
                value = finding.get('value')
                if isinstance(value, bool):
                    parts.append(f"- {title}: Yes")
                elif isinstance(value, (int, float)):
                    parts.append(f"- {title}: {value}")
                else:
                    parts.append(f"- {title}")

        # Add narrative if available
        if eval_rec.narrative:
            parts.append(f"\n\n{eval_rec.narrative}")

        # Evidence grade in simple terms
        cor = rec.class_of_recommendation
        if cor:
            cor_str = str(cor)
            if cor_str == 'I':
                parts.append(
                    "\n\nThis is a strong recommendation based on solid "
                    "medical evidence."
                )
            elif 'II' in cor_str:
                parts.append(
                    "\n\nThis recommendation is supported by medical evidence "
                    "and may benefit you."
                )

        # Citations hint
        if rec.citations and len(rec.citations) > 0:
            parts.append(
                f"\n\nThis recommendation is based on {len(rec.citations)} "
                "medical research citation(s)."
            )

        return " ".join(parts)

    def _generate_provider_summary(
        self,
        eval_rec: EvaluatedRecommendation,
        assessment_chain: list[dict],
        source_data: list[dict]
    ) -> str:
        """Generate provider-focused summary.

        Args:
            eval_rec: Evaluated recommendation
            assessment_chain: Assessment chain
            source_data: Source data items

        Returns:
            Provider summary string
        """
        rec = eval_rec.recommendation
        parts = []

        # Header
        parts.append(f"RECOMMENDATION: {rec.title}")
        parts.append(f"Applies: {eval_rec.applies}")

        # Evidence grades
        if rec.class_of_recommendation:
            parts.append(f"COR: {rec.class_of_recommendation}")
        if rec.level_of_evidence:
            parts.append(f"LOE: {rec.level_of_evidence}")
        if rec.uspstf_grade:
            parts.append(f"USPSTF: {rec.uspstf_grade.value}")

        # Assessment logic
        parts.append("\nASSESSMENT LOGIC:")
        for a in assessment_chain:
            expression = a.get('expression', '')
            value = a.get('value')
            parts.append(f"  - {a['id']}: {value}")
            if expression:
                parts.append(f"    Expression: {expression}")

        # Source data
        if source_data:
            parts.append("\nSOURCE DATA:")
            for d in source_data[:5]:  # Limit
                parts.append(
                    f"  - {d['variable_id']}: {d['value']} "
                    f"({d.get('date', 'date unknown')})"
                )

        # Citations
        if rec.citations:
            parts.append("\nCITATIONS:")
            for c in rec.citations[:3]:
                # Truncate long citations
                citation_text = c[:200] + "..." if len(c) > 200 else c
                parts.append(f"  - {citation_text}")

        return "\n".join(parts)

    def explain_multiple(
        self,
        concord: Concord,
        recommendation_ids: list[str] | None = None
    ) -> list[RecommendationExplanation]:
        """Generate explanations for multiple recommendations.

        Args:
            concord: Concord instance
            recommendation_ids: IDs to explain, or None for all applicable

        Returns:
            List of explanations
        """
        explanations = []

        if recommendation_ids is None:
            # Get all applicable recommendations
            if concord.recommendation_result:
                recommendation_ids = [
                    r.recommendation.id
                    for r in concord.recommendation_result.applied or []
                ]
            else:
                return []

        for rec_id in recommendation_ids:
            try:
                explanation = self.explain(concord, rec_id)
                explanations.append(explanation)
            except ValueError as e:
                log.warning(f"Could not explain {rec_id}: {e}")

        return explanations
