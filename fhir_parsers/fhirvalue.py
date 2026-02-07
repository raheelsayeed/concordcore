#!/usr/bin/env python3
"""FHIR Resource to Value conversion.

This module provides FHIRValue class for converting FHIR R4 resources
into ConcordCore Value objects that can be used in CPG evaluation.

Uses fhir.resources package (Pydantic-based) for FHIR model validation.
"""

import logging

from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.procedure import Procedure
from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.questionnaireresponse import QuestionnaireResponse

from variables import value
from primitives.unit import Unit
from primitives.code import Code


log = logging.getLogger(__name__)


class FHIRValue(value.Value):
    """A Value derived from a FHIR resource.

    Extends Value with FHIR-specific parsing methods for converting
    FHIR R4 resources (Observation, Condition, etc.) into ConcordCore values.
    """

    @property
    def fhirtype(self):
        """Get the FHIR resource type from source."""
        if self.source and len(self.source) > 0:
            return self.source[0].resource_type
        return None

    @classmethod
    def from_medicationRequest(cls, mr: MedicationRequest):
        """Create FHIRValue from MedicationRequest resource."""
        date = mr.authoredOn if mr.authoredOn else None
        coding = mr.medicationCodeableConcept.coding if mr.medicationCodeableConcept else []
        codes = [Code(c.code, c.system, c.display) for c in coding]
        return cls(value=codes, date=date, source=[mr])

    @classmethod
    def from_procedure(cls, pr: Procedure):
        """Create FHIRValue from Procedure resource."""
        log.warning(f'Procedure parsing: {pr.id}')

        date = None
        if pr.performedDateTime:
            date = pr.performedDateTime
        elif pr.performedPeriod and pr.performedPeriod.start:
            date = pr.performedPeriod.start

        cd = None
        if pr.code and pr.code.coding:
            cd = [Code(cc.code, cc.system, cc.display) for cc in pr.code.coding]

        instance = cls(value=True, unit=None, date=date, source=[pr])
        instance.code = cd
        return instance

    @classmethod
    def from_observation(cls, ob: Observation):
        """Create FHIRValue from Observation resource.

        Handles various Observation value types:
        - valueQuantity (numeric with units)
        - valueBoolean (true/false)
        - valueCodeableConcept (coded values)
        - component (multi-part like blood pressure)
        """
        # Extract date - fhir.resources returns datetime directly
        date = None
        if ob.effectiveDateTime:
            date = ob.effectiveDateTime
        elif ob.issued:
            date = ob.issued
        elif ob.meta and ob.meta.lastUpdated:
            date = ob.meta.lastUpdated

        unit = None
        cd = None

        # Extract codes
        if ob.code and ob.code.coding:
            cd = [Code(cc.code, cc.system, cc.display) for cc in ob.code.coding]

        # Extract value based on type
        val = None

        # Quantity (decimal/numeric)
        if ob.valueQuantity:
            vq = ob.valueQuantity
            val = vq.value
            unit = Unit(vq.code, vq.system, vq.unit)

        # Boolean
        elif ob.valueBoolean is not None:
            val = ob.valueBoolean

        # Blood pressure (component observation)
        elif ob.component and ob.code and ob.code.coding:
            code_val = ob.code.coding[0].code
            if code_val in ('55284-4', '85354-9'):  # BP LOINC codes
                sbp_value = None
                dbp_value = None
                for c in ob.component:
                    if c.code and c.code.coding:
                        scode = c.code.coding[0].code
                        if scode == '8480-6' and c.valueQuantity:  # Systolic
                            sbp_value = c.valueQuantity.value
                        elif scode == '8462-4' and c.valueQuantity:  # Diastolic
                            dbp_value = c.valueQuantity.value

                if sbp_value is None or dbp_value is None:
                    raise ValueError('Blood pressure missing systolic or diastolic component')
                val = (sbp_value, dbp_value)
                unit = Unit('mm[Hg]', 'http://unitsofmeasure.org', 'mmHg')

        # CodeableConcept
        elif ob.valueCodeableConcept and ob.valueCodeableConcept.coding:
            coding = ob.valueCodeableConcept.coding[0]
            val = Code(coding.code, coding.system, coding.display)

        # String
        elif ob.valueString:
            val = ob.valueString

        # Integer
        elif ob.valueInteger is not None:
            val = ob.valueInteger

        else:
            raise ValueError(f'FHIRValue: Observation value not assigned for {ob.id}')

        instance = cls(value=val, unit=unit, date=date, source=[ob])
        instance.code = cd
        return instance

    @property
    def title(self):
        """Get display title from codes."""
        if self.code:
            return ", ".join([c.display or c.code for c in self.code])
        return None

    @classmethod
    def from_condition(cls, c: Condition):
        """Create FHIRValue from Condition resource.

        Conditions are represented as boolean True (presence of condition).
        """
        date = c.recordedDate if c.recordedDate else None

        cd = None
        if c.code and c.code.coding:
            cd = [Code(cc.code, cc.system, cc.display) for cc in c.code.coding]

        instance = cls(value=True, unit=None, date=date, source=[c])
        instance.code = cd
        return instance

    @classmethod
    def from_questionnaireResponse(cls, qr: QuestionnaireResponse):
        """Create FHIRValue from QuestionnaireResponse resource."""
        log.info('Processing QuestionnaireResponse')

        val = None
        if qr.item:
            if len(qr.item) == 1:
                first = qr.item[0]
                if first and first.answer:
                    ans = first.answer[0]
                    if ans.valueBoolean is not None:
                        val = ans.valueBoolean
                    elif ans.valueQuantity:
                        val = ans.valueQuantity.value
                    elif ans.valueCoding:
                        val = ans.valueCoding.code

        date = qr.authored if qr.authored else None

        if val is None:
            raise ValueError('Cannot extract value from QuestionnaireResponse')

        return cls(value=val, unit=None, date=date, source=[qr])

    @classmethod
    def from_fhir(cls, fhirjson: dict):
        """Create FHIRValue from a FHIR resource JSON dict.

        Automatically detects resource type and calls appropriate parser.

        Args:
            fhirjson: FHIR resource as dictionary

        Returns:
            FHIRValue instance

        Raises:
            ValueError: If resource type is unknown or missing
        """
        resource_type = fhirjson.get('resourceType')
        if not resource_type:
            raise ValueError(f'Unknown file, missing resourceType: {fhirjson}')

        # Observation
        if resource_type == 'Observation':
            try:
                ob = Observation.model_validate(fhirjson)
                return cls.from_observation(ob)
            except Exception as e:
                log.error(f"Error parsing Observation: {e}")
                raise

        # Condition
        elif resource_type == 'Condition':
            c = Condition.model_validate(fhirjson)
            return cls.from_condition(c)

        # QuestionnaireResponse
        elif resource_type == 'QuestionnaireResponse':
            qr = QuestionnaireResponse.model_validate(fhirjson)
            return cls.from_questionnaireResponse(qr)

        # MedicationRequest
        elif resource_type == 'MedicationRequest':
            mr = MedicationRequest.model_validate(fhirjson)
            return cls.from_medicationRequest(mr)

        # Procedure
        elif resource_type == 'Procedure':
            pr = Procedure.model_validate(fhirjson)
            return cls.from_procedure(pr)

        else:
            raise ValueError(f'Unknown FHIR resource type: {resource_type}')
