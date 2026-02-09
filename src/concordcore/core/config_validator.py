#!/usr/bin/env python3
"""Institutional configuration validation tool.

This module provides comprehensive validation for institutional configuration
files, including:
- Schema validation for YAML structure
- Override conflict detection
- Inheritance chain visualization
- Impact analysis for changes
- Expression validation
- Safe range checks

Example usage:
    ```python
    from concordcore.core.config_validator import ConfigValidator, validate_config_file

    # Quick validation
    result = validate_config_file("configs/hospital_abc.yaml")
    if not result.is_valid:
        print(result.errors)

    # Detailed validation with CPG context
    validator = ConfigValidator()
    result = validator.validate(config, cpg=my_cpg)
    print(result.summary())
    ```
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
import logging
import re
import yaml

from .institution_config import (
    InstitutionConfig,
    ThresholdOverride,
    ExpressionOverride,
    RecommendationFilter,
    LocalRule,
    load_institution_config,
)

log = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"          # Must be fixed, config invalid
    WARNING = "warning"      # Should be reviewed, may cause issues
    INFO = "info"           # Informational, no action required


@dataclass(slots=True)
class ValidationIssue:
    """A single validation issue found in the configuration.

    Attributes:
        severity: ERROR, WARNING, or INFO
        code: Machine-readable error code (e.g., "MISSING_FIELD")
        message: Human-readable description
        path: Path to the problematic field (e.g., "threshold_overrides[0].target_id")
        suggestion: Optional suggestion for fixing the issue
    """
    severity: ValidationSeverity
    code: str
    message: str
    path: str = None
    suggestion: str = None

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        location = f" at {self.path}" if self.path else ""
        result = f"{prefix} {self.code}: {self.message}{location}"
        if self.suggestion:
            result += f"\n  Suggestion: {self.suggestion}"
        return result


@dataclass(slots=True)
class InheritanceNode:
    """A node in the configuration inheritance chain."""
    config_id: str
    config_name: str
    level: int  # 0 = root, increases with depth
    overrides_count: int
    local_rules_count: int


@dataclass(slots=True)
class ImpactAnalysis:
    """Analysis of how a configuration change affects CPG evaluation.

    Attributes:
        affected_assessments: List of assessment IDs that may be affected
        affected_recommendations: List of recommendation IDs that may be affected
        threshold_changes: List of threshold changes with old/new values
        excluded_recommendations: List of recommendations that will be excluded
        added_rules: List of local rules that will be added
    """
    affected_assessments: list[str] = field(default_factory=list)
    affected_recommendations: list[str] = field(default_factory=list)
    threshold_changes: list[dict] = field(default_factory=list)
    excluded_recommendations: list[str] = field(default_factory=list)
    added_rules: list[dict] = field(default_factory=list)

    def has_impact(self) -> bool:
        """Check if the configuration has any impact."""
        return bool(
            self.affected_assessments or
            self.affected_recommendations or
            self.threshold_changes or
            self.excluded_recommendations or
            self.added_rules
        )


@dataclass(slots=True)
class ValidationResult:
    """Result of configuration validation.

    Attributes:
        is_valid: True if no errors found (warnings are OK)
        issues: List of all validation issues found
        inheritance_chain: Visualization of config inheritance
        impact_analysis: Analysis of configuration impact
        config_summary: Summary of the configuration
    """
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    inheritance_chain: list[InheritanceNode] = field(default_factory=list)
    impact_analysis: ImpactAnalysis = None
    config_summary: dict = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def infos(self) -> list[ValidationIssue]:
        """Get only info-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    def summary(self) -> str:
        """Generate a human-readable summary of the validation result."""
        lines = []
        lines.append("=" * 60)
        lines.append("INSTITUTIONAL CONFIGURATION VALIDATION REPORT")
        lines.append("=" * 60)

        # Config summary
        if self.config_summary:
            lines.append(f"\nConfiguration: {self.config_summary.get('institution_name', 'Unknown')}")
            lines.append(f"ID: {self.config_summary.get('institution_id', 'Unknown')}")

        # Validation status
        status = "VALID" if self.is_valid else "INVALID"
        lines.append(f"\nStatus: {status}")
        lines.append(f"  Errors: {len(self.errors)}")
        lines.append(f"  Warnings: {len(self.warnings)}")
        lines.append(f"  Info: {len(self.infos)}")

        # Inheritance chain
        if self.inheritance_chain:
            lines.append("\nInheritance Chain:")
            for node in self.inheritance_chain:
                indent = "  " * node.level
                lines.append(f"  {indent}{'└─' if node.level > 0 else ''}{node.config_name}")
                lines.append(f"  {indent}  (ID: {node.config_id}, "
                           f"{node.overrides_count} overrides, "
                           f"{node.local_rules_count} local rules)")

        # Impact analysis
        if self.impact_analysis and self.impact_analysis.has_impact():
            lines.append("\nImpact Analysis:")
            if self.impact_analysis.threshold_changes:
                lines.append("  Threshold Changes:")
                for change in self.impact_analysis.threshold_changes:
                    lines.append(f"    - {change['target_id']}.{change['parameter']}: "
                               f"{change['original']} → {change['override']}")

            if self.impact_analysis.excluded_recommendations:
                lines.append("  Excluded Recommendations:")
                for rec_id in self.impact_analysis.excluded_recommendations:
                    lines.append(f"    - {rec_id}")

            if self.impact_analysis.added_rules:
                lines.append("  Added Local Rules:")
                for rule in self.impact_analysis.added_rules:
                    lines.append(f"    - {rule['id']}: {rule['title']}")

        # Issues
        if self.issues:
            lines.append("\nIssues:")
            for issue in self.issues:
                lines.append(f"  {issue}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "issues": [
                {
                    "severity": i.severity.value,
                    "code": i.code,
                    "message": i.message,
                    "path": i.path,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "inheritance_chain": [
                {
                    "config_id": n.config_id,
                    "config_name": n.config_name,
                    "level": n.level,
                    "overrides_count": n.overrides_count,
                    "local_rules_count": n.local_rules_count,
                }
                for n in self.inheritance_chain
            ],
            "impact_analysis": {
                "affected_assessments": self.impact_analysis.affected_assessments,
                "affected_recommendations": self.impact_analysis.affected_recommendations,
                "threshold_changes": self.impact_analysis.threshold_changes,
                "excluded_recommendations": self.impact_analysis.excluded_recommendations,
                "added_rules": self.impact_analysis.added_rules,
            } if self.impact_analysis else None,
            "config_summary": self.config_summary,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


# Known safe ranges for common clinical parameters
SAFE_RANGES = {
    "risk_threshold": {"min": 0, "max": 100, "unit": "%"},
    "ldl_threshold": {"min": 30, "max": 300, "unit": "mg/dL"},
    "hdl_threshold": {"min": 10, "max": 150, "unit": "mg/dL"},
    "bp_systolic_threshold": {"min": 70, "max": 250, "unit": "mmHg"},
    "bp_diastolic_threshold": {"min": 40, "max": 150, "unit": "mmHg"},
    "age_threshold": {"min": 0, "max": 150, "unit": "years"},
    "a1c_threshold": {"min": 3, "max": 20, "unit": "%"},
    "bmi_threshold": {"min": 10, "max": 100, "unit": "kg/m²"},
}


class ConfigValidator:
    """Comprehensive validator for institutional configurations.

    This validator performs multiple checks:
    1. Schema validation - Required fields, correct types
    2. Override conflict detection - Duplicate targets, circular inheritance
    3. Expression validation - Syntax and variable references
    4. Safe range checks - Values within reasonable clinical bounds
    5. CPG compatibility - Targets exist in the referenced CPG
    """

    def __init__(self):
        """Initialize the validator."""
        self._expression_cache: dict[str, bool] = {}

    def validate(
        self,
        config: InstitutionConfig,
        cpg=None,
        check_safe_ranges: bool = True,
        strict_mode: bool = False,
    ) -> ValidationResult:
        """Validate an institutional configuration.

        Args:
            config: The InstitutionConfig to validate
            cpg: Optional CPG to validate against (for target existence checks)
            check_safe_ranges: Check if override values are within safe clinical ranges
            strict_mode: Treat warnings as errors

        Returns:
            ValidationResult with all issues found
        """
        issues: list[ValidationIssue] = []

        # 1. Schema validation
        issues.extend(self._validate_schema(config))

        # 2. Override conflict detection
        issues.extend(self._detect_override_conflicts(config))

        # 3. Expression validation
        issues.extend(self._validate_expressions(config, cpg))

        # 4. Safe range checks
        if check_safe_ranges:
            issues.extend(self._check_safe_ranges(config))

        # 5. CPG compatibility
        if cpg:
            issues.extend(self._validate_cpg_compatibility(config, cpg))

        # 6. Build inheritance chain
        inheritance_chain = self._build_inheritance_chain(config)

        # 7. Generate impact analysis
        impact_analysis = self._analyze_impact(config, cpg)

        # Determine validity
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        if strict_mode:
            has_warnings = any(i.severity == ValidationSeverity.WARNING for i in issues)
            is_valid = not has_errors and not has_warnings
        else:
            is_valid = not has_errors

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            inheritance_chain=inheritance_chain,
            impact_analysis=impact_analysis,
            config_summary={
                "institution_id": config.institution_id,
                "institution_name": config.institution_name,
                "threshold_overrides_count": len(config.threshold_overrides),
                "expression_overrides_count": len(config.expression_overrides),
                "recommendation_filters_count": len(config.recommendation_filters),
                "local_rules_count": len(config.local_rules),
                "has_parent": config.parent_config is not None,
            },
        )

    def _validate_schema(self, config: InstitutionConfig) -> list[ValidationIssue]:
        """Validate the configuration schema (required fields, types)."""
        issues = []

        # Required fields
        if not config.institution_id:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_INSTITUTION_ID",
                message="institution_id is required",
                path="institution_id",
                suggestion="Add a unique identifier for this institution",
            ))

        if not config.institution_name:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="MISSING_INSTITUTION_NAME",
                message="institution_name is not set",
                path="institution_name",
                suggestion="Add a human-readable name for this institution",
            ))

        # Validate threshold overrides
        for i, override in enumerate(config.threshold_overrides):
            path = f"threshold_overrides[{i}]"
            if not override.target_id:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_TARGET_ID",
                    message="target_id is required for threshold override",
                    path=f"{path}.target_id",
                ))
            if not override.parameter:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_PARAMETER",
                    message="parameter is required for threshold override",
                    path=f"{path}.parameter",
                ))
            if override.override_value is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_OVERRIDE_VALUE",
                    message="override_value is required",
                    path=f"{path}.override_value",
                ))
            if not override.reason:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_REASON",
                    message="No reason provided for threshold override",
                    path=f"{path}.reason",
                    suggestion="Add a reason explaining why this override is needed (for audit trail)",
                ))

        # Validate expression overrides
        for i, override in enumerate(config.expression_overrides):
            path = f"expression_overrides[{i}]"
            if not override.target_id:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_TARGET_ID",
                    message="target_id is required for expression override",
                    path=f"{path}.target_id",
                ))
            if not override.override_expression:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_OVERRIDE_EXPRESSION",
                    message="override_expression is required",
                    path=f"{path}.override_expression",
                ))
            if not override.reason:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_REASON",
                    message="No reason provided for expression override",
                    path=f"{path}.reason",
                    suggestion="Document why this expression is being changed",
                ))

        # Validate recommendation filters
        for i, filt in enumerate(config.recommendation_filters):
            path = f"recommendation_filters[{i}]"
            if not filt.recommendation_id:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_RECOMMENDATION_ID",
                    message="recommendation_id is required for filter",
                    path=f"{path}.recommendation_id",
                ))
            if filt.action not in ("include", "exclude"):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_FILTER_ACTION",
                    message=f"Invalid action '{filt.action}'. Must be 'include' or 'exclude'",
                    path=f"{path}.action",
                ))

        # Validate local rules
        for i, rule in enumerate(config.local_rules):
            path = f"local_rules[{i}]"
            if not rule.id:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_RULE_ID",
                    message="id is required for local rule",
                    path=f"{path}.id",
                ))
            if not rule.expression:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_RULE_EXPRESSION",
                    message="expression is required for local rule",
                    path=f"{path}.expression",
                ))
            if rule.type not in ("assessment", "recommendation"):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_RULE_TYPE",
                    message=f"Invalid type '{rule.type}'. Must be 'assessment' or 'recommendation'",
                    path=f"{path}.type",
                ))

        return issues

    def _detect_override_conflicts(self, config: InstitutionConfig) -> list[ValidationIssue]:
        """Detect conflicts between overrides."""
        issues = []

        # Check for duplicate threshold overrides
        threshold_keys = set()
        for i, override in enumerate(config.threshold_overrides):
            key = (override.target_id, override.parameter)
            if key in threshold_keys:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DUPLICATE_THRESHOLD_OVERRIDE",
                    message=f"Duplicate threshold override for {override.target_id}.{override.parameter}",
                    path=f"threshold_overrides[{i}]",
                    suggestion="Remove one of the duplicate overrides",
                ))
            threshold_keys.add(key)

        # Check for duplicate expression overrides
        expression_targets = set()
        for i, override in enumerate(config.expression_overrides):
            if override.target_id in expression_targets:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DUPLICATE_EXPRESSION_OVERRIDE",
                    message=f"Duplicate expression override for {override.target_id}",
                    path=f"expression_overrides[{i}]",
                    suggestion="Remove one of the duplicate overrides",
                ))
            expression_targets.add(override.target_id)

        # Check for conflicting recommendation filters
        filter_actions = {}
        for i, filt in enumerate(config.recommendation_filters):
            if filt.recommendation_id in filter_actions:
                if filter_actions[filt.recommendation_id] != filt.action:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CONFLICTING_FILTERS",
                        message=f"Conflicting filters for {filt.recommendation_id}: "
                               f"both 'include' and 'exclude' specified",
                        path=f"recommendation_filters[{i}]",
                        suggestion="Use only one filter action per recommendation",
                    ))
            filter_actions[filt.recommendation_id] = filt.action

        # Check for duplicate local rule IDs
        rule_ids = set()
        for i, rule in enumerate(config.local_rules):
            if rule.id in rule_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DUPLICATE_RULE_ID",
                    message=f"Duplicate local rule ID: {rule.id}",
                    path=f"local_rules[{i}]",
                    suggestion="Use unique IDs for local rules",
                ))
            rule_ids.add(rule.id)

        # Check for circular inheritance
        if config.parent_config:
            visited = {config.institution_id}
            current = config.parent_config
            while current:
                if current.institution_id in visited:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CIRCULAR_INHERITANCE",
                        message=f"Circular inheritance detected: {current.institution_id} already in chain",
                        suggestion="Fix the parent_config_path to remove the cycle",
                    ))
                    break
                visited.add(current.institution_id)
                current = current.parent_config

        return issues

    def _validate_expressions(self, config: InstitutionConfig, cpg=None) -> list[ValidationIssue]:
        """Validate expression syntax and variable references."""
        issues = []

        # Get all valid variable IDs if CPG provided
        valid_var_ids = set()
        if cpg:
            for v in (cpg.variables or []):
                valid_var_ids.add(v.id)
            for v in (cpg.eligibility_variables or []):
                valid_var_ids.add(v.id)
            for v in (cpg.assessment_variables or []):
                valid_var_ids.add(v.id)
            for v in (cpg.recommendation_variables or []):
                valid_var_ids.add(v.id)

        # Also add local rule IDs as valid references
        for rule in config.local_rules:
            valid_var_ids.add(rule.id)

        # Validate expression overrides
        for i, override in enumerate(config.expression_overrides):
            path = f"expression_overrides[{i}]"
            if override.override_expression:
                syntax_issues = self._check_expression_syntax(
                    override.override_expression, path, valid_var_ids
                )
                issues.extend(syntax_issues)

        # Validate local rule expressions
        for i, rule in enumerate(config.local_rules):
            path = f"local_rules[{i}]"
            if rule.expression:
                syntax_issues = self._check_expression_syntax(
                    rule.expression, path, valid_var_ids
                )
                issues.extend(syntax_issues)

        # Validate filter conditions
        for i, filt in enumerate(config.recommendation_filters):
            path = f"recommendation_filters[{i}]"
            if filt.condition:
                syntax_issues = self._check_expression_syntax(
                    filt.condition, path, valid_var_ids
                )
                issues.extend(syntax_issues)

        return issues

    def _check_expression_syntax(
        self,
        expression: str,
        path: str,
        valid_var_ids: set[str] = None,
    ) -> list[ValidationIssue]:
        """Check expression syntax and variable references."""
        issues = []

        # Try to parse the expression
        try:
            from .expression import Expression
            expr = Expression(expression)

            # Check variable references
            var_pattern = re.compile(r'\$([a-zA-Z_][a-zA-Z0-9_]*)')
            var_refs = var_pattern.findall(expression)

            if valid_var_ids:
                for var_ref in var_refs:
                    if var_ref not in valid_var_ids:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="UNDEFINED_VARIABLE_REF",
                            message=f"Expression references undefined variable: ${var_ref}",
                            path=path,
                            suggestion=f"Ensure ${var_ref} is defined in the CPG or as a local rule",
                        ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_EXPRESSION_SYNTAX",
                message=f"Invalid expression syntax: {e}",
                path=path,
                suggestion="Check the expression syntax and fix any errors",
            ))

        return issues

    def _check_safe_ranges(self, config: InstitutionConfig) -> list[ValidationIssue]:
        """Check if override values are within safe clinical ranges."""
        issues = []

        for i, override in enumerate(config.threshold_overrides):
            path = f"threshold_overrides[{i}]"

            # Check if we have a known safe range for this parameter
            if override.parameter in SAFE_RANGES:
                safe_range = SAFE_RANGES[override.parameter]
                value = override.override_value

                if isinstance(value, (int, float)):
                    if value < safe_range["min"]:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="VALUE_BELOW_SAFE_RANGE",
                            message=f"Override value {value} is below typical safe minimum "
                                   f"({safe_range['min']} {safe_range.get('unit', '')})",
                            path=f"{path}.override_value",
                            suggestion="Verify this value is intentional and clinically appropriate",
                        ))
                    elif value > safe_range["max"]:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="VALUE_ABOVE_SAFE_RANGE",
                            message=f"Override value {value} is above typical safe maximum "
                                   f"({safe_range['max']} {safe_range.get('unit', '')})",
                            path=f"{path}.override_value",
                            suggestion="Verify this value is intentional and clinically appropriate",
                        ))

            # Check for negative values where they don't make sense
            if override.override_value is not None:
                if isinstance(override.override_value, (int, float)):
                    if override.override_value < 0 and "threshold" in override.parameter.lower():
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="NEGATIVE_THRESHOLD",
                            message=f"Negative threshold value ({override.override_value}) is unusual",
                            path=f"{path}.override_value",
                            suggestion="Verify this value is intentional",
                        ))

        return issues

    def _validate_cpg_compatibility(self, config: InstitutionConfig, cpg) -> list[ValidationIssue]:
        """Validate that override targets exist in the CPG."""
        issues = []

        # Collect all variable IDs from CPG
        all_var_ids = set()
        for v in (cpg.variables or []):
            all_var_ids.add(v.id)
        for v in (cpg.eligibility_variables or []):
            all_var_ids.add(v.id)
        for v in (cpg.assessment_variables or []):
            all_var_ids.add(v.id)
        for v in (cpg.recommendation_variables or []):
            all_var_ids.add(v.id)

        rec_ids = {v.id for v in (cpg.recommendation_variables or [])}
        assessment_ids = {v.id for v in (cpg.assessment_variables or [])}

        # Check threshold override targets
        for i, override in enumerate(config.threshold_overrides):
            path = f"threshold_overrides[{i}]"
            if override.target_id not in all_var_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="TARGET_NOT_IN_CPG",
                    message=f"Threshold override target '{override.target_id}' not found in CPG",
                    path=f"{path}.target_id",
                    suggestion=f"Check the target_id matches an assessment or recommendation in the CPG. "
                              f"Available targets: {sorted(all_var_ids)[:10]}...",
                ))

        # Check expression override targets
        for i, override in enumerate(config.expression_overrides):
            path = f"expression_overrides[{i}]"
            if override.target_id not in all_var_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="TARGET_NOT_IN_CPG",
                    message=f"Expression override target '{override.target_id}' not found in CPG",
                    path=f"{path}.target_id",
                    suggestion=f"Check the target_id matches an assessment or recommendation in the CPG",
                ))

        # Check recommendation filter targets
        for i, filt in enumerate(config.recommendation_filters):
            path = f"recommendation_filters[{i}]"
            if filt.recommendation_id not in rec_ids:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="RECOMMENDATION_NOT_IN_CPG",
                    message=f"Recommendation filter target '{filt.recommendation_id}' not found in CPG",
                    path=f"{path}.recommendation_id",
                    suggestion=f"Available recommendations: {sorted(rec_ids)}",
                ))

        # Check local rule CPG references
        for i, rule in enumerate(config.local_rules):
            path = f"local_rules[{i}]"
            if rule.applies_to_cpg:
                if cpg.identifier not in rule.applies_to_cpg:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="RULE_NOT_FOR_THIS_CPG",
                        message=f"Local rule '{rule.id}' does not apply to CPG '{cpg.identifier}'",
                        path=f"{path}.applies_to_cpg",
                        suggestion="This rule will be skipped for this CPG",
                    ))

        return issues

    def _build_inheritance_chain(self, config: InstitutionConfig) -> list[InheritanceNode]:
        """Build the inheritance chain visualization."""
        chain = []
        current = config
        level = 0
        visited = set()  # Cycle detection

        while current:
            # Detect cycles
            if current.institution_id in visited:
                break
            visited.add(current.institution_id)

            overrides_count = (
                len(current.threshold_overrides) +
                len(current.expression_overrides) +
                len(current.recommendation_filters)
            )
            chain.append(InheritanceNode(
                config_id=current.institution_id,
                config_name=current.institution_name,
                level=level,
                overrides_count=overrides_count,
                local_rules_count=len(current.local_rules),
            ))
            current = current.parent_config
            level += 1

        return chain

    def _analyze_impact(self, config: InstitutionConfig, cpg=None, _visited: set = None) -> ImpactAnalysis:
        """Analyze the impact of the configuration on CPG evaluation."""
        # Cycle detection
        if _visited is None:
            _visited = set()
        if config.institution_id in _visited:
            return ImpactAnalysis()  # Stop recursion on cycle
        _visited = _visited | {config.institution_id}

        impact = ImpactAnalysis()

        # Collect all threshold changes
        for override in config.threshold_overrides:
            impact.threshold_changes.append({
                "target_id": override.target_id,
                "parameter": override.parameter,
                "original": override.original_value,
                "override": override.override_value,
                "reason": override.reason,
            })
            impact.affected_assessments.append(override.target_id)

        # Collect expression override impacts
        for override in config.expression_overrides:
            if override.target_id not in impact.affected_assessments:
                impact.affected_assessments.append(override.target_id)

        # Collect excluded recommendations
        for filt in config.recommendation_filters:
            if filt.action == "exclude":
                impact.excluded_recommendations.append(filt.recommendation_id)
            impact.affected_recommendations.append(filt.recommendation_id)

        # Collect added rules
        for rule in config.local_rules:
            impact.added_rules.append({
                "id": rule.id,
                "title": rule.title,
                "type": rule.type,
                "applies_to_cpg": rule.applies_to_cpg,
            })
            if rule.type == "assessment":
                impact.affected_assessments.append(rule.id)
            else:
                impact.affected_recommendations.append(rule.id)

        # Include parent config impacts
        if config.parent_config:
            parent_impact = self._analyze_impact(config.parent_config, cpg, _visited)
            # Merge parent impacts (child overrides parent)
            for change in parent_impact.threshold_changes:
                if not any(c["target_id"] == change["target_id"] and
                          c["parameter"] == change["parameter"]
                          for c in impact.threshold_changes):
                    impact.threshold_changes.append(change)

            for assessment_id in parent_impact.affected_assessments:
                if assessment_id not in impact.affected_assessments:
                    impact.affected_assessments.append(assessment_id)

            for rec_id in parent_impact.excluded_recommendations:
                if rec_id not in impact.excluded_recommendations:
                    impact.excluded_recommendations.append(rec_id)

        return impact


def validate_config_file(
    config_path: str,
    cpg=None,
    check_safe_ranges: bool = True,
    strict_mode: bool = False,
) -> ValidationResult:
    """Validate an institutional configuration file.

    This is a convenience function that loads and validates a config in one step.

    Args:
        config_path: Path to the YAML configuration file
        cpg: Optional CPG to validate against
        check_safe_ranges: Check if values are within safe clinical ranges
        strict_mode: Treat warnings as errors

    Returns:
        ValidationResult with all issues found
    """
    validator = ConfigValidator()
    issues = []

    # Try to load the config
    try:
        config = load_institution_config(config_path)
    except FileNotFoundError:
        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="FILE_NOT_FOUND",
                message=f"Configuration file not found: {config_path}",
            )],
        )
    except yaml.YAMLError as e:
        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_YAML",
                message=f"Invalid YAML syntax: {e}",
            )],
        )
    except ValueError as e:
        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="VALIDATION_ERROR",
                message=str(e),
            )],
        )
    except KeyError as e:
        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_REQUIRED_FIELD",
                message=f"Missing required field in configuration: {e}",
                suggestion="Check that all required fields are present (target_id, recommendation_id, etc.)",
            )],
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="LOAD_ERROR",
                message=f"Failed to load configuration: {e}",
            )],
        )

    # Validate the loaded config
    return validator.validate(config, cpg=cpg, check_safe_ranges=check_safe_ranges, strict_mode=strict_mode)


def visualize_inheritance_chain(config: InstitutionConfig) -> str:
    """Generate an ASCII visualization of the configuration inheritance chain.

    Args:
        config: The InstitutionConfig to visualize

    Returns:
        ASCII art string showing the inheritance chain
    """
    lines = []
    lines.append("Configuration Inheritance Chain")
    lines.append("=" * 40)

    current = config
    level = 0

    while current:
        prefix = "  " * level
        if level == 0:
            lines.append(f"{prefix}┌─ {current.institution_name}")
        else:
            lines.append(f"{prefix}└─ {current.institution_name}")

        lines.append(f"{prefix}   ID: {current.institution_id}")
        lines.append(f"{prefix}   Threshold overrides: {len(current.threshold_overrides)}")
        lines.append(f"{prefix}   Expression overrides: {len(current.expression_overrides)}")
        lines.append(f"{prefix}   Recommendation filters: {len(current.recommendation_filters)}")
        lines.append(f"{prefix}   Local rules: {len(current.local_rules)}")

        if current.parent_config:
            lines.append(f"{prefix}   │")
            lines.append(f"{prefix}   ▼ inherits from")

        current = current.parent_config
        level += 1

    return "\n".join(lines)
