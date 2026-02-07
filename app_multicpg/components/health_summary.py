#!/usr/bin/env python3
"""Patient health summary component."""

import streamlit as st
from app_multicpg.services import (
    ExplanationService,
    EvaluationSummary,
    RankedRecommendation,
    PriorityLevel,
)


def render_health_summary(
    eval_summary: EvaluationSummary,
    ranked_recommendations: list[RankedRecommendation],
    explanation_service: ExplanationService
):
    """Render a patient-friendly health summary.

    Args:
        eval_summary: The evaluation summary
        ranked_recommendations: Priority-ranked recommendations
        explanation_service: Service for generating explanations
    """
    # Generate the health summary
    health_summary = explanation_service.generate_health_summary(
        eval_summary, ranked_recommendations
    )

    # Overall status
    st.subheader("Your Health Summary")

    # Status message with appropriate styling
    critical_count = sum(1 for r in ranked_recommendations if r.priority == PriorityLevel.CRITICAL)
    high_count = sum(1 for r in ranked_recommendations if r.priority == PriorityLevel.HIGH)

    if critical_count > 0:
        st.error(health_summary.overall_status)
    elif high_count > 0:
        st.warning(health_summary.overall_status)
    else:
        st.success(health_summary.overall_status)

    # Two-column layout for findings
    col1, col2 = st.columns(2)

    with col1:
        # Areas doing well
        st.markdown("### What's Going Well")
        if health_summary.areas_doing_well:
            for area in health_summary.areas_doing_well:
                st.markdown(f"✅ {area}")
        else:
            st.markdown("Your doctor can discuss your positive health factors with you.")

    with col2:
        # Areas needing attention
        st.markdown("### Areas to Focus On")
        if health_summary.areas_needing_attention:
            for area in health_summary.areas_needing_attention:
                st.markdown(f"⚠️ {area}")
        else:
            st.markdown("No specific areas of concern identified.")

    # Key findings
    if health_summary.key_findings:
        st.markdown("### Key Findings")
        for finding in health_summary.key_findings:
            st.markdown(f"- {finding}")

    # Recommended actions
    st.markdown("### What You Can Do")
    if health_summary.recommended_actions:
        for idx, action in enumerate(health_summary.recommended_actions, 1):
            st.markdown(f"**{idx}.** {action}")
    else:
        st.markdown("Continue your healthy habits and follow up with your doctor as scheduled.")

    # Next steps
    st.divider()
    st.markdown("### Next Steps")
    for step in health_summary.next_steps:
        st.markdown(f"➡️ {step}")


def render_action_items(
    ranked_recommendations: list[RankedRecommendation],
    explanation_service: ExplanationService
):
    """Render actionable items for the patient.

    Args:
        ranked_recommendations: Priority-ranked recommendations
        explanation_service: Service for generating explanations
    """
    st.subheader("What You Can Do")

    if not ranked_recommendations:
        st.success("No specific actions needed at this time. Keep up the good work!")
        return

    # Group by urgency
    urgent = [r for r in ranked_recommendations if r.priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]]
    routine = [r for r in ranked_recommendations if r.priority == PriorityLevel.MODERATE]
    consider = [r for r in ranked_recommendations if r.priority in [PriorityLevel.LOW, PriorityLevel.INFORMATIONAL]]

    if urgent:
        st.markdown("### Talk to Your Doctor Soon")
        for rec in urgent:
            explanation = explanation_service.explain_recommendation(rec)
            _render_action_card(explanation, urgent=True)

    if routine:
        st.markdown("### At Your Next Appointment")
        for rec in routine:
            explanation = explanation_service.explain_recommendation(rec)
            _render_action_card(explanation, urgent=False)

    if consider:
        with st.expander("Other Things to Consider"):
            for rec in consider:
                explanation = explanation_service.explain_recommendation(rec)
                _render_action_card(explanation, urgent=False)


def _render_action_card(explanation, urgent: bool = False):
    """Render an action item card."""
    with st.container(border=True):
        st.markdown(f"**{explanation.title}**")
        st.markdown(explanation.summary)

        if urgent:
            st.caption(f"⏰ {explanation.urgency}")

        # Actions
        if explanation.what_you_can_do:
            st.markdown("**What you can do:**")
            for action in explanation.what_you_can_do[:3]:
                st.markdown(f"- {action}")


def render_questions_for_doctor(
    ranked_recommendations: list[RankedRecommendation],
    explanation_service: ExplanationService
):
    """Render questions the patient can ask their doctor.

    Args:
        ranked_recommendations: Priority-ranked recommendations
        explanation_service: Service for generating explanations
    """
    st.subheader("Questions for Your Doctor")

    st.markdown(
        "Here are some questions you might want to ask based on your health recommendations. "
        "Feel free to print this page or take notes to bring to your appointment."
    )

    # Collect all questions
    all_questions = []
    seen = set()

    for rec in ranked_recommendations:
        explanation = explanation_service.explain_recommendation(rec)
        for question in explanation.questions_for_doctor:
            if question not in seen:
                all_questions.append({
                    "question": question,
                    "category": rec.category,
                    "recommendation": explanation.title
                })
                seen.add(question)

    # Group by category
    by_category = {}
    for item in all_questions:
        cat = item["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    # Display
    for category, items in by_category.items():
        st.markdown(f"### {category}")
        for item in items:
            st.checkbox(
                item["question"],
                key=f"q_{hash(item['question'])}",
                help=f"Related to: {item['recommendation']}"
            )

    # General questions
    st.markdown("### General Questions")
    general_questions = [
        "What are the most important things I should focus on for my health?",
        "Are there any lifestyle changes that could help me?",
        "How often should I follow up with you?",
        "Are there any warning signs I should watch for?",
    ]
    for q in general_questions:
        st.checkbox(q, key=f"gen_{hash(q)}")

    # Print button
    st.divider()
    st.markdown(
        "💡 **Tip:** Use your browser's print function (Ctrl+P or Cmd+P) "
        "to save or print this list."
    )


def render_educational_resources(
    ranked_recommendations: list[RankedRecommendation],
    explanation_service: ExplanationService
):
    """Render educational resources for the patient.

    Args:
        ranked_recommendations: Priority-ranked recommendations
        explanation_service: Service for generating explanations
    """
    st.subheader("Learn More")

    st.markdown(
        "Understanding your health is an important step. "
        "Here are some trusted resources to learn more about the topics relevant to you."
    )

    # Collect resources by category
    resources_by_category = {}

    for rec in ranked_recommendations:
        explanation = explanation_service.explain_recommendation(rec)
        cat = rec.category

        if cat not in resources_by_category:
            resources_by_category[cat] = {
                "why_it_matters": explanation.why_this_matters,
                "resources": []
            }

        for resource in explanation.learn_more:
            if resource not in resources_by_category[cat]["resources"]:
                resources_by_category[cat]["resources"].append(resource)

    # Display
    for category, info in resources_by_category.items():
        with st.expander(f"**{category}**", expanded=True):
            st.markdown(info["why_it_matters"])

            st.markdown("**Trusted Resources:**")
            for resource in info["resources"]:
                st.markdown(f"- {resource}")

    # General resources
    st.markdown("### General Health Resources")
    st.markdown(
        """
        - **MedlinePlus** (medlineplus.gov) - Easy-to-understand health information
        - **CDC** (cdc.gov) - Prevention and wellness information
        - **NIH** (nih.gov) - Research-based health information
        """
    )

    st.info(
        "**Remember:** These resources are for general information only. "
        "Always discuss your specific health questions with your healthcare provider."
    )
