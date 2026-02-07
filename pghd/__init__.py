"""Patient-Generated Health Data (PGHD) module for ConcordCore.

Provides normalization, validation, and conversion of raw patient input
into Concord Records and Values with source tracking.
"""

from .input_source import InputSource, InputMetadata
from .normalizer import PGHDNormalizer
from .validator import PGHDValidator, PGHDValidationError
from .converter import PGHDConverter

__all__ = [
    'InputSource',
    'InputMetadata',
    'PGHDNormalizer',
    'PGHDValidator',
    'PGHDValidationError',
    'PGHDConverter',
]
