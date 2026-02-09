#!/usr/bin/env python3
"""Clinical notes extraction pipeline.

This module provides the ClinicalNotesExtractor class for extracting
variable values from clinical notes using LLM adapters.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ai.llm_provider import ExtractionResult, LLMProvider
from ai.clinical_note import ClinicalNote
from ai.adapters import get_adapter, is_registered
from variables.var import Var
from variables.value import Value
from variables.record import Record

if TYPE_CHECKING:
    from core.cpg import CPG

log = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for clinical notes extraction.

    Attributes:
        provider: Name of the LLM provider to use ('anthropic', 'openai')
        model: Optional model override for the provider
        api_key: Optional API key (falls back to environment variable)
        batch_size: Number of variables to extract per batch
        min_confidence: Minimum confidence threshold to accept a value
        include_low_confidence: Include low-confidence values as attestable
    """

    provider: str = "anthropic"
    model: str = None
    api_key: str = None
    batch_size: int = 10
    min_confidence: float = 0.7
    include_low_confidence: bool = False


@dataclass
class ExtractionSummary:
    """Summary of a clinical notes extraction operation.

    Attributes:
        total_variables: Total number of variables with llm_prompt
        extracted: Number of successfully extracted values
        not_found: Number of variables not found in notes
        low_confidence: Number of low-confidence extractions
        errors: Number of extraction errors
        results: List of all ExtractionResult objects
    """

    total_variables: int = 0
    extracted: int = 0
    not_found: int = 0
    low_confidence: int = 0
    errors: int = 0
    results: list[ExtractionResult] = field(default_factory=list)


class ClinicalNotesExtractor:
    """Extract variable values from clinical notes using LLM.

    This class provides methods for extracting CPG variable values from
    unstructured clinical notes text using configured LLM adapters.

    Example:
        from ai.notes_extractor import ClinicalNotesExtractor, ExtractionConfig
        from core.cpg_registry import get_registry

        cpg = get_registry().get('uspstf_colorectal_cancer_screening')
        config = ExtractionConfig(provider='anthropic')
        extractor = ClinicalNotesExtractor(config)

        notes = "Patient is 55 yo male. Mother had colon cancer at age 62."
        records = extractor.extract_variables(notes, cpg.variables)
        print(records)  # [Record<family_history_crc; values=True>]
    """

    def __init__(self, config: ExtractionConfig = None):
        """Initialize the clinical notes extractor.

        Args:
            config: Extraction configuration. Uses defaults if not provided.

        Raises:
            ValueError: If the specified provider is not registered.
        """
        self.config = config or ExtractionConfig()
        self._adapter: LLMProvider = None

    @property
    def adapter(self) -> LLMProvider:
        """Get the LLM adapter, initializing on first access.

        Returns:
            The configured LLM adapter instance.

        Raises:
            ValueError: If the provider is not registered.
        """
        if self._adapter is None:
            kwargs = {}
            if self.config.model:
                kwargs['model'] = self.config.model
            if self.config.api_key:
                kwargs['api_key'] = self.config.api_key

            self._adapter = get_adapter(self.config.provider, **kwargs)

        return self._adapter

    def extract_variables(
        self,
        clinical_notes: str,
        variables: list[Var]
    ) -> list[Record]:
        """Extract variable values from clinical notes.

        Processes all variables that have an llm_prompt defined and
        returns Records for successfully extracted values.

        Args:
            clinical_notes: The clinical notes text to extract from.
            variables: List of Var objects to extract.

        Returns:
            List of Record objects with extracted values.
        """
        records = []
        summary = self._extract_with_summary(clinical_notes, variables)
        notes_hash = self._compute_notes_hash(clinical_notes)

        for result in summary.results:
            if not result.found:
                continue

            if result.confidence < self.config.min_confidence:
                if not self.config.include_low_confidence:
                    continue

            # Find the matching variable
            var = next((v for v in variables if v.id == result.variable_id), None)
            if var is None:
                continue

            # Create ClinicalNote source with snippet and metadata
            clinical_note_source = ClinicalNote(
                snippet=result.source_text or "",
                variable_id=result.variable_id,
                confidence=result.confidence,
                provider=self.config.provider,
                model=self.config.model,
                extraction_timestamp=datetime.now(),
                full_notes_hash=notes_hash,
            )

            # Create Value with ClinicalNote as source
            value = Value(
                result.parsed_value,
                source=[clinical_note_source]
            )
            records.append(Record(var, [value]))

        return records

    def _compute_notes_hash(self, clinical_notes: str) -> str:
        """Compute a hash of the clinical notes for reference tracking."""
        return hashlib.sha256(clinical_notes.encode('utf-8')).hexdigest()[:16]

    def extract_with_summary(
        self,
        clinical_notes: str,
        variables: list[Var]
    ) -> tuple[list[Record], ExtractionSummary]:
        """Extract variables and return both records and summary.

        Args:
            clinical_notes: The clinical notes text to extract from.
            variables: List of Var objects to extract.

        Returns:
            Tuple of (records, summary) where records is the list of
            extracted Record objects and summary contains statistics.
        """
        records = []
        summary = self._extract_with_summary(clinical_notes, variables)
        notes_hash = self._compute_notes_hash(clinical_notes)

        for result in summary.results:
            if not result.found:
                continue

            if result.confidence < self.config.min_confidence:
                if not self.config.include_low_confidence:
                    continue

            var = next((v for v in variables if v.id == result.variable_id), None)
            if var is None:
                continue

            # Create ClinicalNote source with snippet and metadata
            clinical_note_source = ClinicalNote(
                snippet=result.source_text or "",
                variable_id=result.variable_id,
                confidence=result.confidence,
                provider=self.config.provider,
                model=self.config.model,
                extraction_timestamp=datetime.now(),
                full_notes_hash=notes_hash,
            )

            value = Value(
                result.parsed_value,
                source=[clinical_note_source]
            )
            records.append(Record(var, [value]))

        return records, summary

    def _extract_with_summary(
        self,
        clinical_notes: str,
        variables: list[Var]
    ) -> ExtractionSummary:
        """Internal method to extract variables and build summary.

        Args:
            clinical_notes: The clinical notes text.
            variables: List of variables to extract.

        Returns:
            ExtractionSummary with statistics and results.
        """
        # Filter to variables with llm_prompt
        extractable = [v for v in variables if getattr(v, 'llm_prompt', None)]

        summary = ExtractionSummary(total_variables=len(extractable))

        for var in extractable:
            expected_type = var.type.value if var.type else 'string'

            try:
                result = self.adapter.extract_value(
                    prompt=var.llm_prompt,
                    clinical_notes=clinical_notes,
                    expected_type=expected_type,
                    variable_id=var.id
                )
                summary.results.append(result)

                if result.error:
                    summary.errors += 1
                elif not result.found:
                    summary.not_found += 1
                elif result.confidence < self.config.min_confidence:
                    summary.low_confidence += 1
                else:
                    summary.extracted += 1

            except Exception as e:
                log.error(f"Error extracting {var.id}: {e}")
                summary.errors += 1
                summary.results.append(ExtractionResult(
                    variable_id=var.id,
                    found=False,
                    error=str(e)
                ))

        return summary

    def extract_from_cpg(
        self,
        clinical_notes: str,
        cpg: 'CPG'
    ) -> list[Record]:
        """Extract all extractable variables from a CPG.

        Extracts from variables, eligibility criteria, and assessments
        that have llm_prompt defined.

        Args:
            clinical_notes: The clinical notes text.
            cpg: The CPG to extract variables from.

        Returns:
            List of Record objects with extracted values.
        """
        all_vars = []

        # Collect variables from CPG
        if cpg.variables:
            all_vars.extend(cpg.variables)

        # Collect eligibility criteria
        if cpg.eligibility:
            all_vars.extend(list(cpg.eligibility))

        # Collect assessments
        if cpg.assessments:
            all_vars.extend(list(cpg.assessments))

        return self.extract_variables(clinical_notes, all_vars)
