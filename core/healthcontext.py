#!/usr/bin/env python3
"""Health context for patient data in ConcordCore.

This module provides the HealthContext class which holds patient health
records and persona information for CPG evaluation.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, TYPE_CHECKING

from primitives.types import Persona
from variables import var, value, record

if TYPE_CHECKING:
    from core.cpg import CPG
    from core.concord_user import ConcordUser
    from ai.notes_extractor import ExtractionConfig


@dataclass(frozen=True)
class HealthContext:
    """Container for patient health data used in CPG evaluation.

    Attributes:
        records: List of Record objects containing patient data
        persona: The persona (patient/provider) for narrative generation
    """

    records: list[record.Record]
    persona: Persona

    @classmethod
    def from_dict(cls,
                  data: dict[str, Any],
                  persona: Persona = Persona.patient) -> 'HealthContext':
        """Create HealthContext from a simple dictionary.

        Convenience method for creating a HealthContext without manually
        constructing Var and Record objects.

        Args:
            data: Dictionary mapping variable IDs to values.
                  Values can be:
                  - Single value (int, float, str, bool)
                  - List of values (for historical data)
                  - Tuple for compound values like blood pressure
            persona: Persona for narrative generation

        Returns:
            HealthContext with records built from the dictionary

        Example:
            ```python
            ctx = HealthContext.from_dict({
                'Age': 55,
                'LDL': [165, 158, 170],  # Historical values
                'HDL': 45,
                'BP': (130, 85),  # Systolic, Diastolic
                'DM': True,
            })
            ```
        """
        records = []

        for var_id, val in data.items():
            # Create a simple Var for this data
            v = var.Var(id=var_id, title=var_id)

            # Handle different value types
            if val is None:
                values = None
            elif isinstance(val, list):
                # List of values (historical)
                values = [value.Value(v) for v in val]
            elif isinstance(val, tuple):
                # Tuple value (e.g., blood pressure)
                values = [value.Value(val)]
            else:
                # Single value
                values = [value.Value(val)]

            rec = record.Record(var=v, initial_values=values)
            records.append(rec)

        return cls(records=records, persona=persona)

    @classmethod
    def from_values(cls, values: list[value.Value], for_variables: list[var.Var], age: record.Record, gender: record.Record, race: record.Record, persona: Persona, until_date: date = None):
        
        var_values = [[var.Var('-',code=v.code), v] for v in values]
        till_date = until_date or date.today().replace(month=12, day=31)
        # FOR EACH VAR, BUILD A RECORD WITH VALUES
        records = [] 

        if age:
            records.append(age)
        if gender:
            records.append(gender)
        if race:
            records.append(race)
            
        for variable in for_variables:
            
            filtered_values = list(filter(lambda value: value[0] == variable, var_values))
            vals = [t[1] for t in filtered_values] if filtered_values else None
            if vals:
                vals = list(filter(lambda v: v.date.date() <= till_date, vals))

            rec = record.Record(var=variable, initial_values=vals if vals else None)
            records.append(rec)
       


        return HealthContext(records=records, persona=persona)


    def describe(self, missing_notation:str='N/A'):
        texts = [f"{r.title or r.id}: {r.value.representation if r.value else missing_notation}" for r in self.records]
        texts = '\n'.join(texts)
        return texts

    @classmethod
    def from_clinical_notes(
        cls,
        clinical_notes: str,
        cpg: 'CPG',
        persona: Persona = None,
        extraction_config: 'ExtractionConfig' = None
    ) -> 'HealthContext':
        """Create HealthContext by extracting variables from clinical notes.

        Uses an LLM to extract variable values from unstructured clinical
        notes text based on the llm_prompt defined in each variable.

        Args:
            clinical_notes: The clinical notes text to extract from.
            cpg: The CPG containing variable definitions with llm_prompts.
            persona: Persona for narrative generation. Defaults to patient.
            extraction_config: Optional ExtractionConfig for LLM settings.

        Returns:
            HealthContext with records extracted from the notes.

        Example:
            ```python
            cpg = CPG.load('cpgs/cholesterol.yaml')
            notes = "55 yo male, LDL 165 mg/dL, HDL 42 mg/dL, no diabetes."
            ctx = HealthContext.from_clinical_notes(notes, cpg)
            ```
        """
        from ai.notes_extractor import ClinicalNotesExtractor

        extractor = ClinicalNotesExtractor(extraction_config)
        records = extractor.extract_from_cpg(clinical_notes, cpg)

        return cls(records, persona or Persona.patient)

    @classmethod
    def from_mixed_sources(
        cls,
        cpg: 'CPG',
        fhir_bundle: dict = None,
        clinical_notes: str = None,
        attestations: dict = None,
        concord_user: 'ConcordUser | None' = None,
        persona: Persona = None,
        extraction_config: 'ExtractionConfig' = None
    ) -> 'HealthContext':
        """Create HealthContext from multiple data sources with priority.

        Combines data from FHIR resources, clinical notes (via LLM extraction),
        and user attestations or ConcordUser session data. Data sources are prioritized:
        1. FHIR data (highest priority - structured EHR data)
        2. Clinical notes (LLM-extracted, only for missing variables)
        3. ConcordUser PGHD data OR attestations (user-provided, only for missing variables)

        Args:
            cpg: The CPG containing variable definitions.
            fhir_bundle: Optional FHIR Bundle with patient resources.
            clinical_notes: Optional clinical notes text for LLM extraction.
            attestations: Optional dict mapping variable IDs to values.
            concord_user: Optional ConcordUser with accumulated PGHD data.
                          When provided, takes precedence over attestations dict.
            persona: Persona for narrative generation. Defaults to patient.
            extraction_config: Optional ExtractionConfig for LLM settings.

        Returns:
            HealthContext with records from all sources, prioritized.

        Example:
            ```python
            cpg = CPG.load('cpgs/cholesterol.yaml')
            ctx = HealthContext.from_mixed_sources(
                cpg=cpg,
                fhir_bundle=fhir_data,
                clinical_notes="Additional notes...",
                attestations={'Smoker': True}
            )
            ```
        """
        records = []
        existing_ids = set()

        # Priority 1: FHIR data
        if fhir_bundle:
            fhir_records = cls._parse_fhir_bundle(fhir_bundle, cpg)
            for rec in fhir_records:
                records.append(rec)
                existing_ids.add(rec.id)

        # Priority 2: Clinical notes (LLM extraction)
        if clinical_notes and cpg:
            from ai.notes_extractor import ClinicalNotesExtractor

            extractor = ClinicalNotesExtractor(extraction_config)

            # Collect all variables from CPG
            all_vars = []
            if cpg.variables:
                all_vars.extend(cpg.variables)
            if cpg.eligibility_variables:
                all_vars.extend(list(cpg.eligibility_variables))
            if cpg.assessment_variables:
                all_vars.extend(list(cpg.assessment_variables))

            # Only extract for variables not already in FHIR
            missing_vars = [v for v in all_vars
                           if v.id not in existing_ids
                           and getattr(v, 'llm_prompt', None)]

            if missing_vars:
                notes_records = extractor.extract_variables(clinical_notes, missing_vars)
                for rec in notes_records:
                    records.append(rec)
                    existing_ids.add(rec.id)

        # Priority 3: ConcordUser PGHD data (preferred over raw attestations)
        if concord_user is not None:
            for pghd_record in concord_user.records:
                if pghd_record.id not in existing_ids and pghd_record.has_value:
                    records.append(pghd_record)
                    existing_ids.add(pghd_record.id)
        elif attestations:
            attestation_records = cls._attestations_to_records(attestations, cpg, existing_ids)
            records.extend(attestation_records)

        return cls(records, persona or Persona.patient)

    @staticmethod
    def _parse_fhir_bundle(fhir_bundle: dict, cpg: 'CPG') -> list[record.Record]:
        """Parse a FHIR Bundle into Records matched against CPG variables.

        Uses FHIRAdapter.parse_bundle_to_records() for code-based matching
        between FHIR resources and CPG variable definitions.

        Args:
            fhir_bundle: FHIR Bundle dict with patient resources.
            cpg: The CPG for variable matching.

        Returns:
            List of Record objects parsed from FHIR resources.
        """
        try:
            from formats.fhir_adapter import FHIRAdapter

            adapter = FHIRAdapter()

            # Collect all variables from CPG for matching
            all_vars = []
            if cpg.variables:
                all_vars.extend(cpg.variables)
            if cpg.eligibility_variables:
                all_vars.extend(list(cpg.eligibility_variables))

            if not all_vars:
                return []

            return adapter.parse_bundle_to_records(fhir_bundle, all_vars)

        except ImportError:
            return []
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"FHIR bundle parsing failed: {e}")
            return []

    @staticmethod
    def _attestations_to_records(
        attestations: dict,
        cpg: 'CPG',
        existing_ids: set = None
    ) -> list[record.Record]:
        """Convert attestation dict to Records.

        Args:
            attestations: Dict mapping variable IDs to values.
            cpg: The CPG for variable lookup.
            existing_ids: Set of variable IDs to skip (already have data).

        Returns:
            List of Record objects from attestations.
        """
        records = []
        existing_ids = existing_ids or set()

        # Build variable lookup from CPG
        var_lookup = {}
        if cpg.variables:
            for v in cpg.variables:
                var_lookup[v.id] = v
        if cpg.eligibility_variables:
            for v in cpg.eligibility_variables:
                var_lookup[v.id] = v
        if cpg.assessment_variables:
            for v in cpg.assessment_variables:
                var_lookup[v.id] = v

        for var_id, val in attestations.items():
            if var_id in existing_ids:
                continue

            v = var_lookup.get(var_id)
            if v is None:
                # Create a simple Var if not in CPG
                v = var.Var(id=var_id, title=var_id)

            if val is not None:
                rec = record.Record(
                    var=v,
                    initial_values=[value.Value(val, source=['attestation'])]
                )
                records.append(rec)

        return records
