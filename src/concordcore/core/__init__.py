#!/usr/bin/env python3
"""Core module for ConcordCore CPG evaluation.

This module provides the main orchestration classes and evaluation pipeline
for Clinical Practice Guideline (CPG) evaluation.

Note: Imports are lazy to avoid circular import issues. Import specific
submodules directly:

    from concordcore.core.cpg import CPG
    from concordcore.core.concord import Concord
    from concordcore.core.errors import NeedAttestationError
"""

# Lazy imports using __getattr__ to avoid circular import issues
# Only errors is safe to import at module level since it has no dependencies
from .errors import (
    ConcordError,
    ExpressionError,
    ExpressionEvaluationError,
    ExpressionVariableNotFound,
    VarError,
    VariableEvaluationError,
    SecurityError,
    NeedAttestationError,
    FHIRParseError,
)

__all__ = [
    # Errors (available immediately)
    'ConcordError',
    'ExpressionError',
    'ExpressionEvaluationError',
    'ExpressionVariableNotFound',
    'VarError',
    'VariableEvaluationError',
    'SecurityError',
    'NeedAttestationError',
    'FHIRParseError',
    # Lazy-loaded
    'CPG',
    'Concord',
    'PipelineResult',
    'HealthContext',
    'EligibilityResult',
    'EligibilityEvaluator',
    'SufficiencyResult',
    'SufficiencyEvaluator',
    'AssessmentResult',
    'AssessedRecord',
    'AssessmentEvaluator',
    'RecommendationResult',
    'EvaluatedRecommendation',
    'EvaluatedRecord',
    'EvaluationContext',
    # Reproducibility
    'ReproducibilityVerifier',
    'VerificationStatus',
    'VerificationResult',
    'verify_evaluation',
    # Batch Processing
    'BatchProcessor',
    'BatchResult',
    'BatchProcessingReport',
    'MultiCPGEvaluator',
    'MultiCPGResult',
    'ProcessingMode',
    # Config Validation
    'ConfigValidator',
    'ValidationResult',
    'ValidationSeverity',
    'ValidationIssue',
    'validate_config_file',
    'visualize_inheritance_chain',
    # Institution Config
    'InstitutionConfig',
    'load_institution_config',
    # Benchmarks
    'BenchmarkRunner',
    'BenchmarkReport',
    'BenchmarkResult',
    # Changelog
    'CPGDiffer',
    'ChangelogGenerator',
    'CPGDiff',
    # CPG Registry
    'CPGRegistry',
    'CPGEntry',
    'CPGVar',
    'get_registry',
]


def __getattr__(name):
    """Lazy import of core classes to avoid circular imports."""
    if name == 'CPG':
        from .cpg import CPG
        return CPG
    elif name == 'Concord':
        from .concord import Concord
        return Concord
    elif name == 'PipelineResult':
        from .concord import PipelineResult
        return PipelineResult
    elif name == 'HealthContext':
        from .healthcontext import HealthContext
        return HealthContext
    elif name == 'EligibilityResult':
        from .eligibility import EligibilityResult
        return EligibilityResult
    elif name == 'EligibilityEvaluator':
        from .eligibility import EligibilityEvaluator
        return EligibilityEvaluator
    elif name == 'SufficiencyResult':
        from .sufficiency import SufficiencyResult
        return SufficiencyResult
    elif name == 'SufficiencyEvaluator':
        from .sufficiency import SufficiencyEvaluator
        return SufficiencyEvaluator
    elif name == 'AssessmentResult':
        from .assessment import AssessmentResult
        return AssessmentResult
    elif name == 'AssessedRecord':
        from .assessment import AssessedRecord
        return AssessedRecord
    elif name == 'AssessmentEvaluator':
        from .assessment import AssessmentEvaluator
        return AssessmentEvaluator
    elif name == 'RecommendationResult':
        from .recommendation import RecommendationResult
        return RecommendationResult
    elif name == 'EvaluatedRecommendation':
        from .recommendation import EvaluatedRecommendation
        return EvaluatedRecommendation
    elif name == 'EvaluatedRecord':
        from .evaluation import EvaluatedRecord
        return EvaluatedRecord
    elif name == 'EvaluationContext':
        from .evaluation import EvaluationContext
        return EvaluationContext
    # Reproducibility
    elif name == 'ReproducibilityVerifier':
        from .reproducibility import ReproducibilityVerifier
        return ReproducibilityVerifier
    elif name == 'VerificationStatus':
        from .reproducibility import VerificationStatus
        return VerificationStatus
    elif name == 'VerificationResult':
        from .reproducibility import VerificationResult
        return VerificationResult
    elif name == 'verify_evaluation':
        from .reproducibility import verify_evaluation
        return verify_evaluation
    # Batch Processing
    elif name == 'BatchProcessor':
        from .batch_processor import BatchProcessor
        return BatchProcessor
    elif name == 'BatchResult':
        from .batch_processor import BatchResult
        return BatchResult
    elif name == 'BatchProcessingReport':
        from .batch_processor import BatchProcessingReport
        return BatchProcessingReport
    elif name == 'MultiCPGEvaluator':
        from .batch_processor import MultiCPGEvaluator
        return MultiCPGEvaluator
    elif name == 'MultiCPGResult':
        from .batch_processor import MultiCPGResult
        return MultiCPGResult
    elif name == 'ProcessingMode':
        from .batch_processor import ProcessingMode
        return ProcessingMode
    # Config Validation
    elif name == 'ConfigValidator':
        from .config_validator import ConfigValidator
        return ConfigValidator
    elif name == 'ValidationResult':
        from .config_validator import ValidationResult
        return ValidationResult
    elif name == 'ValidationSeverity':
        from .config_validator import ValidationSeverity
        return ValidationSeverity
    elif name == 'ValidationIssue':
        from .config_validator import ValidationIssue
        return ValidationIssue
    elif name == 'validate_config_file':
        from .config_validator import validate_config_file
        return validate_config_file
    elif name == 'visualize_inheritance_chain':
        from .config_validator import visualize_inheritance_chain
        return visualize_inheritance_chain
    # Institution Config
    elif name == 'InstitutionConfig':
        from .institution_config import InstitutionConfig
        return InstitutionConfig
    elif name == 'load_institution_config':
        from .institution_config import load_institution_config
        return load_institution_config
    # Benchmarks
    elif name == 'BenchmarkRunner':
        from .benchmarks import BenchmarkRunner
        return BenchmarkRunner
    elif name == 'BenchmarkReport':
        from .benchmarks import BenchmarkReport
        return BenchmarkReport
    elif name == 'BenchmarkResult':
        from .benchmarks import BenchmarkResult
        return BenchmarkResult
    # Changelog
    elif name == 'CPGDiffer':
        from .changelog import CPGDiffer
        return CPGDiffer
    elif name == 'ChangelogGenerator':
        from .changelog import ChangelogGenerator
        return ChangelogGenerator
    elif name == 'CPGDiff':
        from .changelog import CPGDiff
        return CPGDiff
    # CPG Registry
    elif name == 'CPGRegistry':
        from .cpg_registry import CPGRegistry
        return CPGRegistry
    elif name == 'CPGEntry':
        from .cpg_registry import CPGEntry
        return CPGEntry
    elif name == 'CPGVar':
        from .cpg_registry import CPGVar
        return CPGVar
    elif name == 'get_registry':
        from .cpg_registry import get_registry
        return get_registry
    raise AttributeError(f"module 'concordcore.core' has no attribute '{name}'")
