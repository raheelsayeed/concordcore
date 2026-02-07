#!/usr/bin/env python3
"""FHIR R4 data format adapter for ConcordCore.

This module implements the DataFormatProtocol for FHIR R4 resources,
providing parsing capabilities for:
- Observation (lab results, vitals)
- Condition (diagnoses)
- MedicationRequest (prescriptions)
- Procedure (procedures)

Example usage:
    from formats.fhir_adapter import FHIRAdapter

    adapter = FHIRAdapter()

    # Check if resource can be parsed
    if adapter.can_parse(fhir_json):
        value = adapter.parse_resource(fhir_json)

    # Extract codes
    codes = adapter.extract_codes(fhir_json)

    # Parse to record for specific variable
    record = adapter.parse_to_record(fhir_json, ldl_var)
"""

import logging
from typing import Any

from variables.value import Value
from variables.var import Var
from variables.record import Record
from primitives.code import Code
from primitives.unit import Unit

log = logging.getLogger(__name__)


class FHIRAdapter:
    """FHIR R4 data format adapter.

    Implements DataFormatProtocol for parsing FHIR R4 resources into
    ConcordCore Values and Records.

    Attributes:
        format_name: 'fhir'
        supported_resource_types: ['Observation', 'Condition', 'MedicationRequest', 'Procedure']
    """

    format_name: str = 'fhir'
    supported_resource_types: list[str] = [
        'Observation',
        'Condition',
        'MedicationRequest',
        'Procedure'
    ]

    def can_parse(self, resource: Any) -> bool:
        """Check if this adapter can parse the given resource.

        Args:
            resource: The resource to check (should be a dict with 'resourceType')

        Returns:
            True if this is a supported FHIR resource, False otherwise.
        """
        if not isinstance(resource, dict):
            return False

        resource_type = resource.get('resourceType')
        return resource_type in self.supported_resource_types

    def parse_resource(self, resource: Any) -> Value | list[Value] | None:
        """Parse a FHIR resource into one or more Values.

        Args:
            resource: FHIR resource as dict (JSON-parsed)

        Returns:
            A Value object, or None if parsing fails.

        Raises:
            ValueError: If the resource type is not supported.
        """
        if not isinstance(resource, dict):
            raise ValueError("Resource must be a dictionary")

        resource_type = resource.get('resourceType')

        if resource_type == 'Observation':
            return self._parse_observation(resource)
        elif resource_type == 'Condition':
            return self._parse_condition(resource)
        elif resource_type == 'MedicationRequest':
            return self._parse_medication_request(resource)
        elif resource_type == 'Procedure':
            return self._parse_procedure(resource)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")

    def parse_to_record(self, resource: Any, var: Var) -> Record | None:
        """Parse a FHIR resource into a Record for a specific variable.

        Matches the resource to the variable by comparing codes.

        Args:
            resource: FHIR resource as dict
            var: The variable definition to match against

        Returns:
            A Record if codes match, None otherwise.
        """
        if not self.can_parse(resource):
            return None

        # Extract codes from resource
        resource_codes = self.extract_codes(resource)
        if not resource_codes:
            return None

        # Check if any resource code matches variable codes
        if not var.code:
            return None

        var_code_strings = {c.as_string for c in var.code}
        resource_code_strings = {c.as_string for c in resource_codes}

        if not var_code_strings & resource_code_strings:
            return None  # No matching codes

        # Parse the value
        try:
            value = self.parse_resource(resource)
            if value is None:
                return None

            values = [value] if isinstance(value, Value) else value
            return Record(var=var, _Record__values=values)

        except Exception as e:
            log.warning(f"Failed to parse resource to record: {e}")
            return None

    def extract_codes(self, resource: Any) -> list[Code]:
        """Extract medical codes from a FHIR resource.

        Args:
            resource: FHIR resource as dict

        Returns:
            List of Code objects found in the resource.
        """
        codes = []

        if not isinstance(resource, dict):
            return codes

        # Extract from 'code' field (Observation, Condition, Procedure)
        code_field = resource.get('code', {})
        codes.extend(self._extract_codes_from_codeable_concept(code_field))

        # Extract from 'medicationCodeableConcept' (MedicationRequest)
        med_code = resource.get('medicationCodeableConcept', {})
        codes.extend(self._extract_codes_from_codeable_concept(med_code))

        return codes

    def _extract_codes_from_codeable_concept(
        self,
        codeable_concept: dict
    ) -> list[Code]:
        """Extract codes from a FHIR CodeableConcept."""
        codes = []
        coding_list = codeable_concept.get('coding', [])

        for coding in coding_list:
            code_value = coding.get('code')
            system = coding.get('system', '')
            display = coding.get('display')

            if code_value:
                # Determine system type
                system_type = self._normalize_system(system)
                codes.append(Code(code_value, system_type, display))

        return codes

    def _normalize_system(self, system: str) -> str:
        """Normalize FHIR system URI to ConcordCore system URI.

        Maps FHIR system URIs to the canonical URIs used by ConcordCore's
        Code factory methods (e.g., CodeSystemType.loinc.value).
        """
        from ontology.definitions import CodeSystemType

        system_lower = system.lower()

        if 'loinc' in system_lower:
            return CodeSystemType.loinc.value
        elif 'snomed' in system_lower:
            return CodeSystemType.snomed.value
        elif 'rxnorm' in system_lower:
            return CodeSystemType.rxnorm.value
        elif 'cpt' in system_lower:
            return CodeSystemType.cpt.value
        elif 'icd' in system_lower:
            return system  # Keep ICD system URI as-is
        else:
            return system

    def _parse_observation(self, obs: dict) -> Value | None:
        """Parse a FHIR Observation resource."""
        # Extract date
        date = self._extract_date(obs, [
            'effectiveDateTime',
            'issued',
            ('meta', 'lastUpdated')
        ])

        # Extract codes
        codes = self._extract_codes_from_codeable_concept(obs.get('code', {}))

        # Extract value and unit
        value = None
        unit = None

        # Quantity value (numeric)
        if 'valueQuantity' in obs:
            vq = obs['valueQuantity']
            value = vq.get('value')
            if 'unit' in vq or 'code' in vq:
                unit = Unit(
                    vq.get('code', ''),
                    vq.get('system', ''),
                    vq.get('unit', '')
                )

        # Boolean value
        elif 'valueBoolean' in obs:
            value = obs['valueBoolean']

        # String value
        elif 'valueString' in obs:
            value = obs['valueString']

        # Integer value
        elif 'valueInteger' in obs:
            value = obs['valueInteger']

        # CodeableConcept value
        elif 'valueCodeableConcept' in obs:
            value_codes = self._extract_codes_from_codeable_concept(
                obs['valueCodeableConcept']
            )
            if value_codes:
                value = value_codes[0]  # Return first code

        # Component values (e.g., Blood Pressure)
        elif 'component' in obs:
            value = self._parse_observation_components(obs)

        else:
            log.warning(f"Unknown Observation value type in {obs.get('id', 'unknown')}")
            return None

        result = Value(value=value, unit=unit, date=date, source=[obs])
        result.code = codes[0] if codes else None
        return result

    def _parse_observation_components(self, obs: dict) -> Any:
        """Parse Observation components (e.g., Blood Pressure)."""
        components = obs.get('component', [])

        # Check for Blood Pressure
        obs_codes = self._extract_codes_from_codeable_concept(obs.get('code', {}))
        bp_codes = {'55284-4', '85354-9'}  # LOINC codes for BP

        is_bp = any(c.code in bp_codes for c in obs_codes)

        if is_bp:
            sbp = None
            dbp = None

            for comp in components:
                comp_codes = self._extract_codes_from_codeable_concept(
                    comp.get('code', {})
                )
                comp_code = comp_codes[0].code if comp_codes else None

                if comp_code == '8480-6':  # Systolic
                    sbp = comp.get('valueQuantity', {}).get('value')
                elif comp_code == '8462-4':  # Diastolic
                    dbp = comp.get('valueQuantity', {}).get('value')

            if sbp is not None and dbp is not None:
                return (sbp, dbp)

        # Generic component handling
        return {
            comp.get('code', {}).get('text', f'comp_{i}'):
            comp.get('valueQuantity', {}).get('value')
            for i, comp in enumerate(components)
        }

    def _parse_condition(self, cond: dict) -> Value | None:
        """Parse a FHIR Condition resource."""
        date = self._extract_date(cond, ['recordedDate', 'onsetDateTime'])
        codes = self._extract_codes_from_codeable_concept(cond.get('code', {}))

        # Conditions are represented as boolean True (condition exists)
        # Clinical status can modify this
        clinical_status = cond.get('clinicalStatus', {})
        status_coding = clinical_status.get('coding', [{}])[0]
        status_code = status_coding.get('code', 'active')

        # Active conditions = True, resolved = False
        value = status_code in ['active', 'recurrence', 'relapse']

        result = Value(value=value, date=date, source=[cond])
        result.code = codes[0] if codes else None
        return result

    def _parse_medication_request(self, med_req: dict) -> Value | None:
        """Parse a FHIR MedicationRequest resource."""
        date = self._extract_date(med_req, ['authoredOn'])
        codes = self._extract_codes_from_codeable_concept(
            med_req.get('medicationCodeableConcept', {})
        )

        # Check status
        status = med_req.get('status', 'active')
        value = status in ['active', 'completed']

        result = Value(value=codes if codes else value, date=date, source=[med_req])
        result.code = codes[0] if codes else None
        return result

    def _parse_procedure(self, proc: dict) -> Value | None:
        """Parse a FHIR Procedure resource."""
        date = self._extract_date(proc, [
            'performedDateTime',
            ('performedPeriod', 'start')
        ])
        codes = self._extract_codes_from_codeable_concept(proc.get('code', {}))

        # Procedures are represented as True (procedure performed)
        status = proc.get('status', 'completed')
        value = status == 'completed'

        result = Value(value=value, date=date, source=[proc])
        result.code = codes[0] if codes else None
        return result

    def parse_bundle_to_records(self, bundle: dict,
                               variables: list[Var]) -> list[Record]:
        """Parse a FHIR Bundle into Records matched against CPG variables.

        Iterates through bundle entries, extracts values, and matches them
        to CPG variables by comparing codes. Returns one Record per matched
        variable.

        Args:
            bundle: FHIR Bundle dict with 'entry' array
            variables: List of CPG variable definitions to match against

        Returns:
            List of Records with values from the FHIR Bundle
        """
        # Build a code→Var index for O(1) matching
        code_to_var: dict[str, Var] = {}
        for var in variables:
            if var.code:
                for c in var.code:
                    code_to_var[c.as_string] = var

        # Collect values per var_id
        var_values: dict[str, list[Value]] = {}

        entries = bundle.get('entry', [])
        for entry in entries:
            resource = entry.get('resource', {})
            if not resource or not self.can_parse(resource):
                continue

            resource_codes = self.extract_codes(resource)
            if not resource_codes:
                continue

            # Match resource codes to CPG variables
            matched_var = None
            for rc in resource_codes:
                matched_var = code_to_var.get(rc.as_string)
                if matched_var:
                    break

            if not matched_var:
                continue

            try:
                value = self.parse_resource(resource)
                if value is None:
                    continue

                values = [value] if isinstance(value, Value) else value
                var_values.setdefault(matched_var.id, []).extend(values)
            except Exception as e:
                log.warning(f"Failed to parse FHIR resource for {matched_var.id}: {e}")

        # Build Records
        records = []
        for var in variables:
            vals = var_values.get(var.id)
            if vals:
                records.append(Record(var=var, initial_values=vals))

        return records

    def _extract_date(self, resource: dict, fields: list) -> Any:
        """Extract date from resource using multiple possible field paths."""
        from datetime import datetime

        for field in fields:
            if isinstance(field, tuple):
                # Nested path
                value = resource
                for key in field:
                    value = value.get(key, {}) if isinstance(value, dict) else None
                    if value is None:
                        break
            else:
                value = resource.get(field)

            if value:
                try:
                    # Handle FHIR dateTime format
                    if isinstance(value, str):
                        # Remove timezone info for simple parsing
                        value = value.replace('Z', '+00:00')
                        if '+' in value:
                            value = value.split('+')[0]
                        if 'T' in value:
                            return datetime.fromisoformat(value)
                        else:
                            return datetime.strptime(value, '%Y-%m-%d')
                    return value
                except (ValueError, TypeError):
                    continue

        return datetime.now()  # Default to now if no date found
