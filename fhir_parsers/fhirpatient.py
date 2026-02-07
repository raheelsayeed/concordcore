#!/usr/bin/env python3
"""FHIR Patient resource parsing.

This module provides FHIRPatient class for extracting demographic
information from FHIR Patient resources into ConcordCore Records.

Uses fhir.resources package (Pydantic-based) for FHIR model validation.
"""

from functools import cached_property
from datetime import date

from fhir.resources.R4B.patient import Patient

from primitives.code import Code, CodeSystemType
from variables import record, value, var, age


class FHIRPatient:
    """Extract ConcordCore Records from a FHIR Patient resource.

    Creates Records for:
    - Age (calculated from birthDate)
    - Gender
    - Race (from US Core extension)
    - Ethnicity (from US Core extension)
    """

    def __init__(self, pt: Patient) -> None:
        """Creates Record(s) from FHIR Patient resource.

        Args:
            pt: FHIR Patient resource (fhir.resources model)
        """
        self.pt = pt
        (_race, _eth) = self.race_ethnicity()
        self.race = _race
        self.ethnicity = _eth

    @cached_property
    def name(self):
        """Get patient name (placeholder)."""
        return "Name"

    @cached_property
    def gender(self):
        """Create Gender Record from Patient.gender."""
        if self.pt.gender:
            v = var.Var.Gender()
            val_code = Code(self.pt.gender, CodeSystemType.concord.value, self.pt.gender)
            val = value.Value(val_code, source=[self.pt])
            rec = record.Record(v, [val])
            return rec
        return None

    @cached_property
    def age(self):
        """Calculate Age Record from Patient.birthDate."""
        if self.pt.birthDate:
            # fhir.resources returns date directly
            bd = self.pt.birthDate
            if hasattr(bd, 'date'):
                bd = bd.date()
            today = date.today()
            _age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
            return age.Age(_age)
        return None

    def race_ethnicity(self):
        """Extract race and ethnicity from US Core extensions.

        Returns:
            Tuple of (race_record, ethnicity_record), either may be None
        """
        exts = self.pt.extension
        if not exts:
            return (None, None)

        from ontology.codes import Code
        from ontology.definitions import CodeSystemType
        from ontology.codes import CodeGender, CodeRaceEthnicity

        _race = None
        _eth = None

        for ex in exts:
            # US Core Race Extension
            if ex.url == CodeSystemType.USCore_Race.value:
                if ex.extension:
                    race_code = ex.extension[0].valueCoding
                    if race_code and race_code.system == CodeSystemType.CDC_RaceEthnicity.value:
                        raceCode = Code(race_code.code, CodeSystemType.CDC_RaceEthnicity.value, race_code.display)
                        v = var.Var.RaceEthnicity()
                        val = value.Value(raceCode, source=[self.pt])
                        _race = record.Record(v, [val])

            # US Core Ethnicity Extension
            if ex.url == CodeSystemType.USCore_Ethnicity.value:
                if ex.extension:
                    eth_code = ex.extension[0].valueCoding
                    if eth_code and eth_code.system == CodeSystemType.CDC_RaceEthnicity.value:
                        ethCode = Code(eth_code.code, CodeSystemType.CDC_RaceEthnicity.value, eth_code.display)
                        v = var.Var.RaceEthnicity()
                        val = value.Value(ethCode, source=[self.pt])
                        _eth = record.Record(v, [val])

        return (_race, _eth)

    def records(self):
        """Get all available demographic Records.

        Returns:
            List of Records (age, gender, race, ethnicity)
        """
        return [
            self.age,
            self.gender,
            self.race,
            self.ethnicity
        ]
