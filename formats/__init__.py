"""Data format adapters for ConcordCore.

This module provides a protocol-based approach to parsing different health data
formats into ConcordCore Values and Records.

Supported formats:
- FHIR R4 (via FHIRAdapter)

To add a new format:
1. Implement DataFormatProtocol
2. Register with DataFormatRegistry
"""

from .protocol import DataFormatProtocol, DataFormatRegistry
from .fhir_adapter import FHIRAdapter

__all__ = ['DataFormatProtocol', 'DataFormatRegistry', 'FHIRAdapter']

# Default registry instance
registry = DataFormatRegistry()
registry.register(FHIRAdapter())
