#!/usr/bin/env python3
"""Data format protocol and registry for ConcordCore.

This module defines the protocol for data format adapters and provides
a registry for managing multiple adapters.

Example usage:
    from concordcore.formats import registry

    # Parse a resource using auto-detection
    value = registry.parse(fhir_observation)

    # Parse with explicit format
    value = registry.parse(fhir_observation, format='fhir')

    # Register a custom adapter
    registry.register(MyCustomAdapter())
"""

import logging
from typing import Any, Protocol, runtime_checkable

from concordcore.variables.value import Value
from concordcore.variables.var import Var
from concordcore.variables.record import Record
from concordcore.primitives.code import Code

log = logging.getLogger(__name__)


@runtime_checkable
class DataFormatProtocol(Protocol):
    """Protocol for data format adapters.

    Implement this protocol to add support for new health data formats.
    Each adapter handles parsing of resources from a specific format
    (e.g., FHIR R4, HL7v2, CDA) into ConcordCore Values and Records.

    Attributes:
        format_name: Unique identifier for this format (e.g., 'fhir', 'hl7v2')
        supported_resource_types: List of resource types this adapter can parse

    Example implementation:
        class HL7v2Adapter(DataFormatProtocol):
            format_name = 'hl7v2'
            supported_resource_types = ['ORU', 'ADT', 'ORM']

            def parse_resource(self, resource: str) -> Value | list[Value]:
                # Parse HL7v2 message
                ...

            def can_parse(self, resource: Any) -> bool:
                return isinstance(resource, str) and resource.startswith('MSH|')
    """

    format_name: str
    """Unique name identifying this data format."""

    supported_resource_types: list[str]
    """List of resource types this adapter can handle."""

    def parse_resource(self, resource: Any) -> Value | list[Value] | None:
        """Parse a resource into one or more Values.

        Args:
            resource: The resource to parse (format-specific structure)

        Returns:
            A single Value, list of Values, or None if parsing fails.

        Raises:
            ValueError: If the resource cannot be parsed.
        """
        ...

    def parse_to_record(self, resource: Any, var: Var) -> Record | None:
        """Parse a resource into a Record for a specific variable.

        This method matches the resource to a variable definition and
        creates a Record if they are compatible (e.g., matching codes).

        Args:
            resource: The resource to parse
            var: The variable definition to match against

        Returns:
            A Record if the resource matches the variable, None otherwise.
        """
        ...

    def extract_codes(self, resource: Any) -> list[Code]:
        """Extract medical codes from a resource.

        Args:
            resource: The resource to extract codes from

        Returns:
            List of Code objects found in the resource.
        """
        ...

    def can_parse(self, resource: Any) -> bool:
        """Check if this adapter can parse the given resource.

        Args:
            resource: The resource to check

        Returns:
            True if this adapter can handle the resource, False otherwise.
        """
        ...


class DataFormatRegistry:
    """Registry for data format adapters.

    The registry manages multiple data format adapters and provides
    unified methods for parsing resources with automatic format detection.

    Example:
        registry = DataFormatRegistry()
        registry.register(FHIRAdapter())
        registry.register(HL7v2Adapter())

        # Auto-detect format and parse
        value = registry.parse(resource)

        # Explicitly specify format
        value = registry.parse(resource, format='fhir')
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._adapters: dict[str, DataFormatProtocol] = {}

    def register(self, adapter: DataFormatProtocol) -> None:
        """Register a data format adapter.

        Args:
            adapter: The adapter to register

        Raises:
            ValueError: If an adapter with the same format_name is already registered.
        """
        if adapter.format_name in self._adapters:
            log.warning(f"Overwriting existing adapter for format: {adapter.format_name}")

        self._adapters[adapter.format_name] = adapter
        log.debug(f"Registered adapter: {adapter.format_name}")

    def unregister(self, format_name: str) -> None:
        """Unregister a data format adapter.

        Args:
            format_name: The format name to unregister
        """
        if format_name in self._adapters:
            del self._adapters[format_name]
            log.debug(f"Unregistered adapter: {format_name}")

    def get_adapter(self, format_name: str) -> DataFormatProtocol | None:
        """Get an adapter by format name.

        Args:
            format_name: The format name to look up

        Returns:
            The adapter if found, None otherwise.
        """
        return self._adapters.get(format_name)

    def list_formats(self) -> list[str]:
        """List all registered format names.

        Returns:
            List of registered format names.
        """
        return list(self._adapters.keys())

    def detect_format(self, resource: Any) -> str | None:
        """Detect the format of a resource.

        Iterates through registered adapters to find one that can parse
        the given resource.

        Args:
            resource: The resource to detect format for

        Returns:
            The format name if detected, None otherwise.
        """
        for format_name, adapter in self._adapters.items():
            if adapter.can_parse(resource):
                return format_name
        return None

    def parse(
        self,
        resource: Any,
        format: str | None = None
    ) -> Value | list[Value] | None:
        """Parse a resource into Value(s).

        If format is not specified, attempts to auto-detect the format
        by querying registered adapters.

        Args:
            resource: The resource to parse
            format: Optional format name to use for parsing

        Returns:
            Parsed Value(s) or None if parsing fails.

        Raises:
            ValueError: If format is specified but not registered.
            ValueError: If format cannot be detected and not specified.
        """
        if format is not None:
            adapter = self.get_adapter(format)
            if adapter is None:
                raise ValueError(f"Unknown format: {format}")
            return adapter.parse_resource(resource)

        # Auto-detect format
        detected_format = self.detect_format(resource)
        if detected_format is None:
            raise ValueError("Could not detect resource format")

        adapter = self._adapters[detected_format]
        return adapter.parse_resource(resource)

    def parse_to_record(
        self,
        resource: Any,
        var: Var,
        format: str | None = None
    ) -> Record | None:
        """Parse a resource into a Record for a specific variable.

        Args:
            resource: The resource to parse
            var: The variable definition to match against
            format: Optional format name

        Returns:
            A Record if successful, None otherwise.
        """
        if format is not None:
            adapter = self.get_adapter(format)
            if adapter is None:
                raise ValueError(f"Unknown format: {format}")
            return adapter.parse_to_record(resource, var)

        # Auto-detect format
        detected_format = self.detect_format(resource)
        if detected_format is None:
            return None

        adapter = self._adapters[detected_format]
        return adapter.parse_to_record(resource, var)

    def extract_codes(
        self,
        resource: Any,
        format: str | None = None
    ) -> list[Code]:
        """Extract medical codes from a resource.

        Args:
            resource: The resource to extract codes from
            format: Optional format name

        Returns:
            List of extracted Code objects.
        """
        if format is not None:
            adapter = self.get_adapter(format)
            if adapter is None:
                raise ValueError(f"Unknown format: {format}")
            return adapter.extract_codes(resource)

        # Auto-detect format
        detected_format = self.detect_format(resource)
        if detected_format is None:
            return []

        adapter = self._adapters[detected_format]
        return adapter.extract_codes(resource)
