#!/usr/bin/env python3
"""Example: Interactive Chat with Health Copilot

A simple interactive chat loop demonstrating the Health Copilot.
Run with an LLM provider for full functionality, or dry-run to see prompts.

Usage:
    # Interactive mode with Claude
    export ANTHROPIC_API_KEY=your_key
    python examples/07_copilot_chat.py

    # Dry run (shows what would be sent to LLM)
    python examples/07_copilot_chat.py --dry-run
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cpg import CPG
from primitives.types import Persona
from ai import HealthCopilot
from ai.prompts import format_template
import misc


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--cpg', default='cpgs/cholesterol/cholesterol.yaml')
    args = parser.parse_args()

    # Setup
    cpg = CPG.from_document_path(args.cpg)
    health_context = misc.sample_healthcontext('patient')
    copilot = HealthCopilot(cpg=cpg, persona=Persona.patient)

    # Evaluate
    print("Evaluating health data...")
    context = copilot.evaluate(health_context)

    # Greeting
    greeting = format_template('patient_greeting', cpg_title=cpg.title)
    print(f"\nAssistant: {greeting}\n")

    # Check if we need more data
    if copilot.needs_more_data:
        print("(Note: Some health information is missing. Type 'missing' to see what's needed)\n")

    # LLM client setup
    client = None
    if not args.dry_run:
        try:
            import anthropic
            client = anthropic.Anthropic()
        except (ImportError, Exception) as e:
            print(f"(Running in dry-run mode: {e})\n")

    # Chat loop
    print("Type 'quit' to exit, 'context' to see evaluation, 'missing' for needed data\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() == 'quit':
            print("Goodbye!")
            break

        if user_input.lower() == 'context':
            print("\n" + context.to_prompt_context() + "\n")
            continue

        if user_input.lower() == 'missing':
            questions = copilot.get_attestation_questions()
            if questions:
                print("\nMissing information needed:")
                for q in questions:
                    print(f"  - {q['title']}: {q['prompt']}")
                print()
            else:
                print("\nNo missing information needed.\n")
            continue

        # Build prompt
        prompt = copilot.build_prompt(user_input)

        if client:
            # Call LLM
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=prompt['system'],
                messages=[{"role": "user", "content": prompt['user']}]
            )
            answer = response.content[0].text
            print(f"\nAssistant: {answer}\n")
            copilot.record_response(answer)
        else:
            # Dry run
            print("\n[DRY RUN - Would send to LLM:]")
            print(f"System: {prompt['system'][:200]}...")
            print(f"User: {prompt['user']}")
            print()


if __name__ == '__main__':
    main()
