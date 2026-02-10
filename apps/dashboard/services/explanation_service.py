#!/usr/bin/env python3
"""Explanation service for generating patient-friendly content."""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .evaluator import EvaluationSummary, CPGEvaluationResult
from .priority_ranker import RankedRecommendation, PriorityLevel


@dataclass
class PatientExplanation:
    """Patient-friendly explanation of a recommendation."""

    title: str
    summary: str
    why_this_matters: str
    what_you_can_do: list[str]
    questions_for_doctor: list[str]
    learn_more: list[str]  # Educational resources
    urgency: str  # "Soon", "When convenient", "Discuss at next visit"


@dataclass
class HealthSummary:
    """Patient-friendly health summary."""

    overall_status: str
    key_findings: list[str]
    areas_doing_well: list[str]
    areas_needing_attention: list[str]
    recommended_actions: list[str]
    next_steps: list[str]


class ExplanationService:
    """Service for generating patient-friendly explanations."""

    # Map priority to urgency text
    URGENCY_MAP = {
        PriorityLevel.CRITICAL: "Discuss with your doctor as soon as possible",
        PriorityLevel.HIGH: "Discuss with your doctor soon",
        PriorityLevel.MODERATE: "Discuss at your next appointment",
        PriorityLevel.LOW: "Consider discussing when convenient",
        PriorityLevel.INFORMATIONAL: "For your awareness",
    }

    # Common questions templates by category
    QUESTION_TEMPLATES = {
        "Cardiovascular": [
            "What is my current risk for heart disease?",
            "Would medication help reduce my risk?",
            "What lifestyle changes would be most beneficial?",
            "How often should I have my cholesterol checked?",
        ],
        "Cancer Screening": [
            "What screening test do you recommend for me?",
            "How often should I be screened?",
            "What are the benefits and risks of this screening?",
            "What happens if the screening finds something?",
        ],
        "Metabolic": [
            "Am I at risk for diabetes?",
            "What changes can I make to reduce my risk?",
            "Should I monitor my blood sugar at home?",
            "What are the early signs I should watch for?",
        ],
        "Infectious Disease": [
            "Should I be tested for this condition?",
            "How is this test performed?",
            "What do the results mean?",
            "Is treatment available if I test positive?",
        ],
        "Mental Health": [
            "What are the signs of depression I should watch for?",
            "What treatment options are available?",
            "How can I support my mental health?",
            "Should I see a specialist?",
        ],
    }

    # Action suggestions by category
    ACTION_TEMPLATES = {
        "Cardiovascular": [
            "Follow a heart-healthy diet (limit saturated fats, increase fiber)",
            "Exercise regularly (aim for 150 minutes of moderate activity per week)",
            "If you smoke, consider quitting",
            "Manage stress through relaxation techniques",
            "Take medications as prescribed",
        ],
        "Cancer Screening": [
            "Schedule recommended screening tests",
            "Keep track of your screening history",
            "Report any unusual symptoms to your doctor",
            "Maintain a healthy lifestyle to reduce cancer risk",
        ],
        "Metabolic": [
            "Monitor your weight and work toward a healthy BMI",
            "Choose whole grains over refined carbohydrates",
            "Increase physical activity",
            "Limit sugary drinks and processed foods",
        ],
        "Infectious Disease": [
            "Get tested as recommended",
            "Practice safe behaviors to prevent infection",
            "Complete any prescribed treatments fully",
            "Discuss vaccination options with your doctor",
        ],
        "Mental Health": [
            "Maintain regular sleep patterns",
            "Stay connected with friends and family",
            "Engage in activities you enjoy",
            "Practice stress management techniques",
            "Seek help if symptoms persist",
        ],
    }

    def explain_recommendation(
        self,
        ranked_rec: RankedRecommendation
    ) -> PatientExplanation:
        """Generate a patient-friendly explanation for a recommendation.

        Args:
            ranked_rec: The ranked recommendation to explain

        Returns:
            PatientExplanation with accessible content
        """
        rec = ranked_rec.recommendation
        rec_var = rec.recommendation

        # Get the narrative (patient-facing text)
        narrative = getattr(rec, 'narrative', '') or ''
        if not narrative and hasattr(rec_var, 'narr'):
            # Try to get from the variable definition
            narr = rec_var.narr
            if hasattr(narr, 'patient') and narr.patient:
                narrative = str(narr.patient.get('HasValue', '')) or str(narr.patient.get('True', ''))

        # Generate title
        title = getattr(rec_var, 'title', '') or rec_var.id.replace('_', ' ').title()

        # Generate summary
        summary = narrative if narrative else f"Based on your health information, this guideline has a recommendation for you about {ranked_rec.category.lower()}."

        # Generate "why this matters"
        why_matters = self._generate_why_matters(ranked_rec)

        # Get actions and questions based on category
        actions = self._get_actions(ranked_rec)
        questions = self._get_questions(ranked_rec)

        # Get urgency
        urgency = self.URGENCY_MAP.get(
            ranked_rec.priority,
            "Discuss with your doctor"
        )

        # Educational resources
        learn_more = self._get_educational_links(ranked_rec)

        return PatientExplanation(
            title=title,
            summary=summary,
            why_this_matters=why_matters,
            what_you_can_do=actions,
            questions_for_doctor=questions,
            learn_more=learn_more,
            urgency=urgency,
        )

    def generate_health_summary(
        self,
        eval_summary: EvaluationSummary,
        ranked_recs: list[RankedRecommendation]
    ) -> HealthSummary:
        """Generate an overall health summary for the patient.

        Args:
            eval_summary: The multi-CPG evaluation summary
            ranked_recs: Priority-ranked recommendations

        Returns:
            HealthSummary with accessible overview
        """
        # Determine overall status
        critical_count = sum(1 for r in ranked_recs if r.priority == PriorityLevel.CRITICAL)
        high_count = sum(1 for r in ranked_recs if r.priority == PriorityLevel.HIGH)

        if critical_count > 0:
            overall_status = "There are some important health matters that need your attention soon."
        elif high_count > 0:
            overall_status = "There are some health recommendations you should discuss with your doctor."
        elif len(ranked_recs) > 0:
            overall_status = "You have some routine health recommendations to consider."
        else:
            overall_status = "No specific health recommendations at this time. Keep up the good work!"

        # Key findings
        key_findings = []
        for rec in ranked_recs[:5]:  # Top 5 recommendations
            rec_var = rec.recommendation.recommendation
            title = getattr(rec_var, 'title', '') or rec_var.id.replace('_', ' ').title()
            key_findings.append(f"{rec.category}: {title}")

        # Areas doing well (CPGs where patient is not eligible or has no recommendations)
        areas_doing_well = []
        for cpg_id, eval_result in eval_summary.evaluations.items():
            if not eval_result.applied_recommendations:
                if eval_result.is_eligible == False:
                    areas_doing_well.append(
                        f"{eval_result.cpg_title}: You don't meet the criteria for this guideline (which is good!)"
                    )
                elif eval_result.is_eligible and not eval_result.applied_recommendations:
                    areas_doing_well.append(
                        f"{eval_result.cpg_title}: No recommendations needed"
                    )

        # Areas needing attention
        areas_needing_attention = []
        by_category: dict[str, int] = {}
        for rec in ranked_recs:
            if rec.priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
                by_category[rec.category] = by_category.get(rec.category, 0) + 1

        for category, count in by_category.items():
            areas_needing_attention.append(
                f"{category}: {count} recommendation{'s' if count > 1 else ''}"
            )

        # Recommended actions (top 3 from highest priority)
        recommended_actions = []
        for rec in ranked_recs[:3]:
            explanation = self.explain_recommendation(rec)
            if explanation.what_you_can_do:
                recommended_actions.append(explanation.what_you_can_do[0])

        # Next steps
        next_steps = [
            "Review this summary with your healthcare provider",
            "Ask questions about any recommendations you don't understand",
            "Work with your doctor to create a plan that fits your lifestyle",
        ]

        if critical_count > 0:
            next_steps.insert(0, "Schedule an appointment with your doctor soon")

        return HealthSummary(
            overall_status=overall_status,
            key_findings=key_findings,
            areas_doing_well=areas_doing_well[:3],  # Limit to 3
            areas_needing_attention=areas_needing_attention,
            recommended_actions=recommended_actions,
            next_steps=next_steps,
        )

    def _generate_why_matters(self, ranked_rec: RankedRecommendation) -> str:
        """Generate 'why this matters' text."""
        category = ranked_rec.category
        priority = ranked_rec.priority

        base_text = {
            "Cardiovascular": "Heart disease is a leading cause of health problems, but many risk factors can be managed with lifestyle changes and treatment.",
            "Cancer Screening": "Finding cancer early, when it's most treatable, can save lives. Screening tests help detect problems before symptoms appear.",
            "Metabolic": "Conditions like diabetes can develop gradually. Early detection and management can prevent serious complications.",
            "Infectious Disease": "Some infections have no symptoms at first but can be treated effectively if found early.",
            "Mental Health": "Mental health is just as important as physical health. Many conditions respond well to treatment.",
        }.get(category, "Following evidence-based health guidelines can help you stay healthier longer.")

        if priority == PriorityLevel.CRITICAL:
            return f"This is particularly important for you. {base_text}"
        elif priority == PriorityLevel.HIGH:
            return f"This is relevant to your health profile. {base_text}"
        else:
            return base_text

    def _get_actions(self, ranked_rec: RankedRecommendation) -> list[str]:
        """Get action suggestions for a recommendation."""
        category = ranked_rec.category
        actions = self.ACTION_TEMPLATES.get(category, [
            "Discuss this recommendation with your healthcare provider",
            "Ask about any lifestyle changes that could help",
        ])

        # Customize based on action type
        action_type = ranked_rec.action_type.upper()
        if action_type == "MEDICATION":
            actions = [
                "Talk to your doctor about whether medication is right for you",
                "Ask about potential side effects and how to manage them",
            ] + actions[:2]
        elif action_type == "EVALUATION":
            actions = [
                "Schedule the recommended test or evaluation",
                "Prepare any questions you have about the test",
            ] + actions[:2]

        return actions[:4]  # Limit to 4 actions

    def _get_questions(self, ranked_rec: RankedRecommendation) -> list[str]:
        """Get questions for the doctor."""
        category = ranked_rec.category
        questions = self.QUESTION_TEMPLATES.get(category, [
            "What does this recommendation mean for me?",
            "What are my options?",
            "How urgent is this?",
        ])

        # Add evidence-based question
        if ranked_rec.evidence_grade:
            questions = questions + [
                f"Can you explain why this is rated as {ranked_rec.evidence_grade}?"
            ]

        return questions[:4]  # Limit to 4 questions

    def _get_educational_links(self, ranked_rec: RankedRecommendation) -> list[str]:
        """Get educational resource suggestions."""
        category = ranked_rec.category

        resources = {
            "Cardiovascular": [
                "American Heart Association (heart.org)",
                "CDC Heart Disease Prevention",
            ],
            "Cancer Screening": [
                "American Cancer Society (cancer.org)",
                "CDC Cancer Prevention",
            ],
            "Metabolic": [
                "American Diabetes Association (diabetes.org)",
                "CDC Diabetes Prevention",
            ],
            "Infectious Disease": [
                "CDC Prevention Information",
                "NIH Health Information",
            ],
            "Mental Health": [
                "National Institute of Mental Health (nimh.nih.gov)",
                "Mental Health America (mhanational.org)",
            ],
        }

        return resources.get(category, ["Ask your doctor for recommended resources"])
