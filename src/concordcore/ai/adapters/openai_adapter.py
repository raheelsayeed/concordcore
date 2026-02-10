#!/usr/bin/env python3
"""OpenAI GPT adapter for clinical notes extraction.

This module provides an LLM adapter for extracting variable values
from clinical notes using OpenAI's GPT models.
"""

import json
import logging
import os
from typing import Any

try:
    import openai
except ImportError:
    openai = None

from concordcore.ai.llm_provider import ExtractionResult, LLMProvider

log = logging.getLogger(__name__)

# System prompt for clinical notes extraction
EXTRACTION_SYSTEM_PROMPT = """You are a clinical data extraction assistant. Your task is to extract specific medical information from clinical notes.

CRITICAL INSTRUCTIONS:
1. Extract ONLY the information explicitly stated in the notes
2. NEVER infer, assume, or hallucinate information
3. If the information is not present or unclear, indicate "not_found"
4. Return your response in the exact JSON format requested
5. Include the relevant quote from the notes as source_text

Response format:
{
    "found": true/false,
    "value": <extracted value or null>,
    "confidence": <0.0-1.0>,
    "source_text": "<relevant excerpt from notes>"
}

For boolean values: return true, false, or null (if not found)
For numeric values: return the number or null (if not found)
For string values: return the string or null (if not found)
"""


class OpenAIAdapter:
    """OpenAI GPT adapter for clinical notes extraction.

    This adapter uses GPT models to extract variable values from clinical notes
    based on provided prompts.

    Example:
        adapter = OpenAIAdapter(api_key='...')
        result = adapter.extract_value(
            prompt="Does the patient have diabetes?",
            clinical_notes="Patient is a 55yo male with Type 2 DM...",
            expected_type="boolean",
            variable_id="has_diabetes"
        )
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4",
        max_tokens: int = 1024,
        temperature: float = 0.0
    ):
        """Initialize the OpenAI adapter.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: GPT model to use for extraction.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 for deterministic extraction).

        Raises:
            ImportError: If openai package is not installed.
            ValueError: If no API key is provided.
        """
        if openai is None:
            raise ImportError(
                "openai package is required for OpenAIAdapter. "
                "Install with: pip install openai"
            )

        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Provide api_key parameter or "
                "set OPENAI_API_KEY environment variable."
            )

        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def extract_value(
        self,
        prompt: str,
        clinical_notes: str,
        expected_type: str,
        variable_id: str
    ) -> ExtractionResult:
        """Extract a variable value from clinical notes.

        Args:
            prompt: The extraction prompt for this variable
            clinical_notes: The clinical notes text to extract from
            expected_type: Expected value type ('boolean', 'integer', 'decimal', 'string')
            variable_id: The ID of the variable being extracted

        Returns:
            ExtractionResult with the extracted value and metadata
        """
        user_prompt = self._build_user_prompt(prompt, clinical_notes, expected_type)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )

            return self._parse_response(response, variable_id, expected_type)

        except openai.APIError as e:
            log.error(f"OpenAI API error extracting {variable_id}: {e}")
            return ExtractionResult(
                variable_id=variable_id,
                found=False,
                error=f"API error: {str(e)}"
            )
        except Exception as e:
            log.error(f"Error extracting {variable_id}: {e}")
            return ExtractionResult(
                variable_id=variable_id,
                found=False,
                error=str(e)
            )

    def extract_batch(
        self,
        extractions: list[tuple[str, str, str]],
        clinical_notes: str
    ) -> list[ExtractionResult]:
        """Batch extraction for multiple variables.

        Currently implements sequential extraction. Could be optimized
        with a single multi-variable prompt in the future.

        Args:
            extractions: List of (prompt, expected_type, variable_id) tuples
            clinical_notes: The clinical notes text to extract from

        Returns:
            List of ExtractionResult objects
        """
        results = []
        for prompt, expected_type, variable_id in extractions:
            result = self.extract_value(prompt, clinical_notes, expected_type, variable_id)
            results.append(result)
        return results

    def _build_user_prompt(
        self,
        extraction_prompt: str,
        clinical_notes: str,
        expected_type: str
    ) -> str:
        """Build the user prompt for extraction.

        Args:
            extraction_prompt: The variable-specific extraction prompt
            clinical_notes: The clinical notes text
            expected_type: Expected value type

        Returns:
            Formatted user prompt string
        """
        type_instructions = {
            'boolean': 'Return true, false, or null (if not determinable).',
            'integer': 'Return an integer number or null (if not found).',
            'decimal': 'Return a decimal number or null (if not found).',
            'string': 'Return a string value or null (if not found).',
            'date': 'Return the date in YYYY-MM-DD format or null (if not found).',
        }

        type_hint = type_instructions.get(expected_type, type_instructions['string'])

        return f"""Extract the following information from the clinical notes:

{extraction_prompt}

Expected value type: {expected_type}
{type_hint}

Clinical Notes:
---
{clinical_notes}
---

Respond with a JSON object containing: found, value, confidence, source_text"""

    def _parse_response(
        self,
        response: Any,
        variable_id: str,
        expected_type: str
    ) -> ExtractionResult:
        """Parse the LLM response into an ExtractionResult.

        Args:
            response: The OpenAI API response
            variable_id: The ID of the variable
            expected_type: Expected value type

        Returns:
            ExtractionResult parsed from the response
        """
        try:
            # Extract text content from response
            content = response.choices[0].message.content

            # Parse JSON from response
            # Handle case where response might have markdown code blocks
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]

            data = json.loads(content.strip())

            found = data.get('found', False)
            raw_value = data.get('value')
            confidence = float(data.get('confidence', 0.0))
            source_text = data.get('source_text')

            # Parse value to expected type
            parsed_value = self._parse_value(raw_value, expected_type)

            return ExtractionResult(
                variable_id=variable_id,
                found=found and raw_value is not None,
                raw_value=raw_value,
                parsed_value=parsed_value,
                confidence=min(max(confidence, 0.0), 1.0),  # Clamp to [0, 1]
                source_text=source_text
            )

        except json.JSONDecodeError as e:
            log.warning(f"Failed to parse JSON response for {variable_id}: {e}")
            return ExtractionResult(
                variable_id=variable_id,
                found=False,
                error=f"JSON parse error: {str(e)}"
            )
        except Exception as e:
            log.warning(f"Failed to parse response for {variable_id}: {e}")
            return ExtractionResult(
                variable_id=variable_id,
                found=False,
                error=f"Parse error: {str(e)}"
            )

    def _parse_value(self, value: Any, expected_type: str) -> Any:
        """Parse a raw value to the expected type.

        Args:
            value: The raw value from the LLM
            expected_type: Expected value type

        Returns:
            The value converted to the expected type, or None if conversion fails
        """
        if value is None:
            return None

        try:
            if expected_type == 'boolean':
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1')
                return bool(value)

            elif expected_type == 'integer':
                if isinstance(value, int):
                    return value
                return int(float(value))

            elif expected_type == 'decimal':
                return float(value)

            elif expected_type == 'string':
                return str(value)

            elif expected_type == 'date':
                # Return as string in ISO format
                return str(value)

            else:
                return value

        except (ValueError, TypeError) as e:
            log.warning(f"Failed to convert value '{value}' to {expected_type}: {e}")
            return None
