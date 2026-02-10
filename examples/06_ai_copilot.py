#!/usr/bin/env python3
"""Example: AI Health Copilot with LLM Integration

This example demonstrates how to use Concord with an LLM to create
a grounded, evidence-based health assistant.

The copilot evaluates patient data against clinical guidelines and
provides structured context for LLM conversations. The LLM explains
computed recommendations rather than generating medical advice.

Usage:
    # With Anthropic Claude
    export ANTHROPIC_API_KEY=your_key
    python examples/06_ai_copilot.py --provider anthropic

    # With OpenAI
    export OPENAI_API_KEY=your_key
    python examples/06_ai_copilot.py --provider openai

    # Dry run (prints prompts without calling LLM)
    python examples/06_ai_copilot.py --dry-run
"""

import argparse
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concordcore.core.cpg import CPG
from concordcore.core.healthcontext import HealthContext
from concordcore.primitives.types import Persona
from concordcore.ai import HealthCopilot, PromptBuilder
from concordcore.ai.prompts import PromptStyle, format_template
import misc


def create_llm_client(provider: str):
    """Create an LLM client based on provider."""
    if provider == 'anthropic':
        try:
            import anthropic
            return anthropic.Anthropic()
        except ImportError:
            print("Install anthropic: pip install anthropic")
            sys.exit(1)

    elif provider == 'openai':
        try:
            import openai
            return openai.OpenAI()
        except ImportError:
            print("Install openai: pip install openai")
            sys.exit(1)

    return None


def call_llm(client, provider: str, system: str, user: str) -> str:
    """Call the LLM with the given prompts."""
    if provider == 'anthropic':
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return response.content[0].text

    elif provider == 'openai':
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return response.choices[0].message.content

    return ""


def main():
    parser = argparse.ArgumentParser(description="AI Health Copilot Demo")
    parser.add_argument('--provider', choices=['anthropic', 'openai', 'none'],
                        default='none', help='LLM provider')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print prompts without calling LLM')
    parser.add_argument('--cpg', default='cpgs/cholesterol/cholesterol.yaml',
                        help='Path to CPG file')
    parser.add_argument('--persona', choices=['patient', 'provider'],
                        default='patient', help='Target persona')
    args = parser.parse_args()

    print("=" * 60)
    print("CONCORD AI HEALTH COPILOT DEMO")
    print("=" * 60)

    # --- 1. Load CPG and Patient Data ---
    print("\n[1] Loading CPG and patient data...")

    cpg = CPG.from_document_path(args.cpg)
    print(f"    CPG: {cpg.title}")

    persona = Persona.patient if args.persona == 'patient' else Persona.provider
    health_context = misc.sample_healthcontext(args.persona)
    print(f"    Persona: {persona.value}")
    print(f"    Records: {len(health_context.records)}")

    # --- 2. Initialize Copilot and Evaluate ---
    print("\n[2] Initializing Health Copilot...")

    copilot = HealthCopilot(cpg=cpg, persona=persona)
    context = copilot.evaluate(health_context)

    print(f"    Eligible: {context.is_eligible}")
    print(f"    Executable: {context.is_executable}")
    print(f"    Recommendations: {len(context.recommendations)}")
    print(f"    Missing Data: {len(context.missing_data)}")

    # --- 3. Show the Grounded Context ---
    print("\n[3] Clinical Context (for LLM grounding):")
    print("-" * 40)
    print(context.to_prompt_context())
    print("-" * 40)

    # --- 4. Example Q&A Interactions ---
    sample_questions = [
        "What does my cholesterol evaluation show?",
        "Why might I need a statin medication?",
        "What is my ASCVD risk score?",
    ]

    print("\n[4] Sample Q&A Interactions")
    print("-" * 40)

    client = None
    if not args.dry_run and args.provider != 'none':
        client = create_llm_client(args.provider)

    for question in sample_questions:
        print(f"\nQ: {question}")

        prompt = copilot.build_prompt(question)

        if args.dry_run or not client:
            print("\n[DRY RUN - System Prompt Preview]")
            print(prompt['system'][:500] + "..." if len(prompt['system']) > 500 else prompt['system'])
            print("\n[User Prompt]")
            print(prompt['user'])
        else:
            print("\nA: ", end="")
            response = call_llm(client, args.provider, prompt['system'], prompt['user'])
            print(response)
            copilot.record_response(response)

        print()

    # --- 5. Show Different Prompt Styles ---
    print("\n[5] Alternative Prompt Styles")
    print("-" * 40)

    # Clinical style for providers
    clinical_builder = PromptBuilder(style=PromptStyle.CLINICAL)
    clinical_prompt = clinical_builder.build_summary_prompt(context)
    print("\n[Clinical Summary Prompt]")
    print(clinical_prompt['user'][:300] + "...")

    # Educational style
    edu_builder = PromptBuilder(style=PromptStyle.EDUCATIONAL)
    edu_prompt = edu_builder.build_explanation_prompt(context, "LDL cholesterol")
    print("\n[Educational Prompt for 'LDL cholesterol']")
    print(edu_prompt['system'][:300] + "...")

    # --- 6. Missing Data Collection ---
    if copilot.needs_more_data:
        print("\n[6] Missing Data Collection")
        print("-" * 40)
        questions = copilot.get_attestation_questions()
        for q in questions:
            print(f"  - {q['prompt']}")

    # --- 7. Export Context as JSON ---
    print("\n[7] Context as JSON (for API integration)")
    print("-" * 40)
    print(json.dumps(context.as_dict(), indent=2, default=str)[:500] + "...")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
