#!/usr/bin/env python3
"""FHIR R4 resource handling for MCP server.

This module provides FHIR Bundle and resource parsing capabilities,
converting FHIR R4 resources into ConcordCore HealthContext objects.

Supported resource types:
- Observation (lab results, vitals, measurements)
- Condition (diagnoses, problems)
- MedicationRequest (prescriptions)
- Procedure (procedures performed)

Example usage:
    from mcp_server.fhir_handler import FHIRHandler

    handler = FHIRHandler()

    # Parse FHIR Bundle
    health_context = handler.create_health_context(
        fhir_data=bundle_json,
        cpg_variables=cpg.variables,
        persona=Persona.patient
    )
"""

import logging
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from formats.fhir_adapter import FHIRAdapter
from variables.var import Var
from variables.value import Value
from variables.record import Record
from core.healthcontext import HealthContext
from core.errors import FHIRParseError
from primitives.types import Persona

log = logging.getLogger(__name__)


class FHIRHandler:
    """Handles FHIR R4 Bundle and resource parsing.

    Wraps the FHIRAdapter to provide Bundle-level parsing and
    HealthContext creation from FHIR data.

    Attributes:
        adapter: The underlying FHIRAdapter for resource parsing
    """

    def __init__(self):
        """Initialize FHIR handler with adapter."""
        self.adapter = FHIRAdapter()

    def can_parse_resource(self, resource: Any) -> bool:
        """Check if a resource can be parsed.

        Args:
            resource: FHIR resource as dict

        Returns:
            True if resource type is supported
        """
        return self.adapter.can_parse(resource)

    def parse_bundle(self, bundle: dict) -> list[dict]:
        """Extract parseable resources from FHIR Bundle.

        Args:
            bundle: FHIR Bundle as dict

        Returns:
            List of parseable FHIR resources

        Raises:
            FHIRParseError: If input is not a valid Bundle
        """
        if not isinstance(bundle, dict):
            raise FHIRParseError("Bundle must be a dictionary")

        if bundle.get('resourceType') != 'Bundle':
            raise FHIRParseError(
                f"Expected Bundle, got {bundle.get('resourceType', 'unknown')}"
            )

        resources = []
        entries = bundle.get('entry', [])

        for i, entry in enumerate(entries):
            resource = entry.get('resource')
            if resource and self.adapter.can_parse(resource):
                resources.append(resource)
                log.debug(
                    f"Extracted {resource.get('resourceType')} "
                    f"from entry {i}"
                )

        log.info(f"Extracted {len(resources)} parseable resources from Bundle")
        return resources

    def parse_resources(self, fhir_data: dict | list) -> list[dict]:
        """Parse FHIR data (Bundle or resource list) into resources.

        Args:
            fhir_data: FHIR Bundle dict, single resource, or list of resources

        Returns:
            List of parseable FHIR resources
        """
        # Handle Bundle
        if isinstance(fhir_data, dict) and fhir_data.get('resourceType') == 'Bundle':
            return self.parse_bundle(fhir_data)

        # Handle list of resources
        if isinstance(fhir_data, list):
            return [r for r in fhir_data if self.adapter.can_parse(r)]

        # Handle single resource
        if isinstance(fhir_data, dict) and self.adapter.can_parse(fhir_data):
            return [fhir_data]

        return []

    def create_health_context(
        self,
        fhir_data: dict | list,
        cpg_variables: list[Var] | None = None,
        persona: Persona = Persona.patient
    ) -> HealthContext:
        """Create HealthContext from FHIR data.

        Two modes of operation:
        1. With CPG variables: Matches FHIR resource codes to CPG variable codes
        2. Without CPG variables: Creates variables from FHIR codes

        Args:
            fhir_data: FHIR Bundle or list of resources
            cpg_variables: Optional CPG variables for code matching
            persona: Persona for narrative generation

        Returns:
            HealthContext with parsed records

        Raises:
            FHIRParseError: If no parseable resources found
        """
        resources = self.parse_resources(fhir_data)

        if not resources:
            raise FHIRParseError("No parseable FHIR resources found")

        records = []

        if cpg_variables:
            # Match resources to CPG variables by code
            records = self._match_resources_to_variables(resources, cpg_variables)
        else:
            # Create records from resource codes
            records = self._create_records_from_resources(resources)

        log.info(f"Created HealthContext with {len(records)} records")
        return HealthContext(records=records, persona=persona)

    def _match_resources_to_variables(
        self,
        resources: list[dict],
        cpg_variables: list[Var]
    ) -> list[Record]:
        """Match FHIR resources to CPG variables by code.

        For each CPG variable, finds FHIR resources with matching codes
        and creates Records.

        Args:
            resources: List of FHIR resources
            cpg_variables: CPG variable definitions

        Returns:
            List of Records with matched values
        """
        records = []
        matched_resources = set()

        for var in cpg_variables:
            if not var.code:
                continue

            var_code_strings = {c.as_string for c in var.code}
            var_values = []

            for i, resource in enumerate(resources):
                if i in matched_resources:
                    continue

                resource_codes = self.adapter.extract_codes(resource)
                resource_code_strings = {c.as_string for c in resource_codes}

                if var_code_strings & resource_code_strings:
                    # Found a match
                    try:
                        value = self.adapter.parse_resource(resource)
                        if value is not None:
                            if isinstance(value, list):
                                var_values.extend(value)
                            else:
                                var_values.append(value)
                            matched_resources.add(i)
                            log.debug(f"Matched {resource.get('resourceType')} to {var.id}")
                    except Exception as e:
                        log.warning(f"Failed to parse resource for {var.id}: {e}")

            if var_values:
                record = Record(var=var, initial_values=var_values)
                records.append(record)

        return records

    def _create_records_from_resources(
        self,
        resources: list[dict]
    ) -> list[Record]:
        """Create Records from FHIR resources without CPG matching.

        Uses FHIR codes as variable IDs.

        Args:
            resources: List of FHIR resources

        Returns:
            List of Records
        """
        records = []
        code_to_values: dict[str, tuple[Var, list[Value]]] = {}

        for resource in resources:
            try:
                value = self.adapter.parse_resource(resource)
                codes = self.adapter.extract_codes(resource)

                if value is None or not codes:
                    continue

                # Use first code as variable ID
                primary_code = codes[0]
                code_key = primary_code.as_string

                if code_key not in code_to_values:
                    # Create new variable
                    var = Var(
                        id=primary_code.code,
                        title=primary_code.display or primary_code.code,
                        code=codes
                    )
                    code_to_values[code_key] = (var, [])

                # Add value
                values_list = code_to_values[code_key][1]
                if isinstance(value, list):
                    values_list.extend(value)
                else:
                    values_list.append(value)

            except Exception as e:
                log.warning(f"Failed to parse resource: {e}")

        # Create records from aggregated values
        for var, values in code_to_values.values():
            if values:
                record = Record(var=var, initial_values=values)
                records.append(record)

        return records

    def get_resource_summary(self, resources: list[dict]) -> dict:
        """Get summary of FHIR resources.

        Args:
            resources: List of FHIR resources

        Returns:
            Summary dict with counts by resource type
        """
        summary = {
            'total': len(resources),
            'by_type': {}
        }

        for resource in resources:
            rtype = resource.get('resourceType', 'Unknown')
            summary['by_type'][rtype] = summary['by_type'].get(rtype, 0) + 1

        return summary
