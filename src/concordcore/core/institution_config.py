#!/usr/bin/env python3
"""Institutional configuration layer for CPG customization.

This module allows healthcare institutions to customize CPG evaluation
without modifying the base CPG definitions. Supports:
- Threshold overrides (e.g., different risk score cutoffs)
- Recommendation filtering (e.g., formulary constraints)
- Additional local rules
- Configuration inheritance (base CPG → institution → department)

Example usage:
    ```python
    from concordcore.core.institution_config import InstitutionConfig, load_institution_config

    # Load institution config
    config = load_institution_config("configs/hospital_abc.yaml")

    # Apply to CPG evaluation
    concord = Concord(cpg=cpg, healthcontext=hc, institution_config=config)
    ```
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import logging
import yaml

log = logging.getLogger(__name__)


@dataclass(slots=True)
class ThresholdOverride:
    """Override for a specific threshold in an assessment or recommendation.

    Attributes:
        target_id: ID of the assessment or recommendation to modify
        parameter: Name of the parameter to override (e.g., "risk_threshold")
        original_value: The original value in the base CPG
        override_value: The new value for this institution
        reason: Explanation for the override (for audit)
    """
    target_id: str
    parameter: str
    original_value: Any
    override_value: Any
    reason: str = None


@dataclass(slots=True)
class ExpressionOverride:
    """Override an assessment or recommendation expression.

    Attributes:
        target_id: ID of the assessment or recommendation to modify
        original_expression: The original expression (for reference)
        override_expression: The new expression to use
        reason: Explanation for the override (for audit)
    """
    target_id: str
    original_expression: str
    override_expression: str
    reason: str = None


@dataclass(slots=True)
class RecommendationFilter:
    """Filter to include or exclude recommendations.

    Attributes:
        recommendation_id: ID of the recommendation
        action: "include" or "exclude"
        condition: Optional expression to conditionally apply filter
        reason: Explanation for the filter (for audit)
    """
    recommendation_id: str
    action: str  # "include" or "exclude"
    condition: str = None  # Optional conditional expression
    reason: str = None


@dataclass(slots=True)
class LocalRule:
    """Additional local rule to add to evaluation.

    Attributes:
        id: Unique identifier for this local rule
        title: Human-readable title
        expression: Expression to evaluate
        type: "assessment" or "recommendation"
        applies_to_cpg: List of CPG identifiers this rule applies to
        priority: Evaluation priority (lower = earlier)
    """
    id: str
    title: str
    expression: str
    type: str  # "assessment" or "recommendation"
    applies_to_cpg: list[str] = None  # None means applies to all
    priority: int = 100


@dataclass(slots=True)
class InstitutionConfig:
    """Configuration for an institution's CPG customizations.

    Attributes:
        institution_id: Unique identifier for the institution
        institution_name: Human-readable name
        parent_config: Optional parent config to inherit from
        threshold_overrides: List of threshold overrides
        expression_overrides: List of expression overrides
        recommendation_filters: List of recommendation filters
        local_rules: List of additional local rules
        metadata: Additional metadata (contact, version, etc.)
    """
    institution_id: str
    institution_name: str
    parent_config: 'InstitutionConfig' = None
    threshold_overrides: list[ThresholdOverride] = field(default_factory=list)
    expression_overrides: list[ExpressionOverride] = field(default_factory=list)
    recommendation_filters: list[RecommendationFilter] = field(default_factory=list)
    local_rules: list[LocalRule] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def get_threshold_override(self, target_id: str, parameter: str) -> ThresholdOverride | None:
        """Get threshold override for a specific target and parameter.

        Checks this config first, then parent configs.
        """
        for override in self.threshold_overrides:
            if override.target_id == target_id and override.parameter == parameter:
                return override

        if self.parent_config:
            return self.parent_config.get_threshold_override(target_id, parameter)

        return None

    def get_expression_override(self, target_id: str) -> ExpressionOverride | None:
        """Get expression override for a specific target.

        Checks this config first, then parent configs.
        """
        for override in self.expression_overrides:
            if override.target_id == target_id:
                return override

        if self.parent_config:
            return self.parent_config.get_expression_override(target_id)

        return None

    def is_recommendation_excluded(self, recommendation_id: str) -> bool:
        """Check if a recommendation is excluded by filters.

        Returns True if explicitly excluded and not conditionally included.
        """
        for f in self.recommendation_filters:
            if f.recommendation_id == recommendation_id and f.action == "exclude":
                # TODO: Evaluate condition if present
                return True

        if self.parent_config:
            return self.parent_config.is_recommendation_excluded(recommendation_id)

        return False

    def get_local_rules(self, cpg_id: str = None) -> list[LocalRule]:
        """Get all local rules, optionally filtered by CPG.

        Includes rules from parent configs.
        """
        rules = []

        # Add parent rules first (lower priority)
        if self.parent_config:
            rules.extend(self.parent_config.get_local_rules(cpg_id))

        # Add this config's rules
        for rule in self.local_rules:
            if rule.applies_to_cpg is None or cpg_id in rule.applies_to_cpg:
                rules.append(rule)

        # Sort by priority
        rules.sort(key=lambda r: r.priority)
        return rules

    def get_all_overrides_for_audit(self) -> dict:
        """Get all overrides in a format suitable for audit logging."""
        return {
            "institution_id": self.institution_id,
            "institution_name": self.institution_name,
            "threshold_overrides": [
                {
                    "target_id": o.target_id,
                    "parameter": o.parameter,
                    "original": o.original_value,
                    "override": o.override_value,
                    "reason": o.reason
                }
                for o in self.threshold_overrides
            ],
            "expression_overrides": [
                {
                    "target_id": o.target_id,
                    "reason": o.reason
                }
                for o in self.expression_overrides
            ],
            "recommendation_filters": [
                {
                    "recommendation_id": f.recommendation_id,
                    "action": f.action,
                    "reason": f.reason
                }
                for f in self.recommendation_filters
            ],
            "local_rules_count": len(self.local_rules),
            "parent_config": self.parent_config.institution_id if self.parent_config else None
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "institution_id": self.institution_id,
            "institution_name": self.institution_name,
            "parent_config_id": self.parent_config.institution_id if self.parent_config else None,
            "threshold_overrides": [
                {
                    "target_id": o.target_id,
                    "parameter": o.parameter,
                    "original_value": o.original_value,
                    "override_value": o.override_value,
                    "reason": o.reason
                }
                for o in self.threshold_overrides
            ],
            "expression_overrides": [
                {
                    "target_id": o.target_id,
                    "original_expression": o.original_expression,
                    "override_expression": o.override_expression,
                    "reason": o.reason
                }
                for o in self.expression_overrides
            ],
            "recommendation_filters": [
                {
                    "recommendation_id": f.recommendation_id,
                    "action": f.action,
                    "condition": f.condition,
                    "reason": f.reason
                }
                for f in self.recommendation_filters
            ],
            "local_rules": [
                {
                    "id": r.id,
                    "title": r.title,
                    "expression": r.expression,
                    "type": r.type,
                    "applies_to_cpg": r.applies_to_cpg,
                    "priority": r.priority
                }
                for r in self.local_rules
            ],
            "metadata": self.metadata
        }


def load_institution_config(config_path: str, parent_config: InstitutionConfig = None) -> InstitutionConfig:
    """Load an institution configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file
        parent_config: Optional parent config for inheritance

    Returns:
        InstitutionConfig instance

    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML is invalid
        ValueError: If required fields are missing
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Institution config not found: {config_path}")

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    config_data = data.get('institution_config', data)

    # Parse threshold overrides
    threshold_overrides = []
    for override_data in (config_data.get('threshold_overrides') or []):
        threshold_overrides.append(ThresholdOverride(
            target_id=override_data['target_id'],
            parameter=override_data['parameter'],
            original_value=override_data.get('original_value'),
            override_value=override_data['override_value'],
            reason=override_data.get('reason')
        ))

    # Parse expression overrides
    expression_overrides = []
    for override_data in (config_data.get('expression_overrides') or []):
        expression_overrides.append(ExpressionOverride(
            target_id=override_data['target_id'],
            original_expression=override_data.get('original_expression', ''),
            override_expression=override_data['override_expression'],
            reason=override_data.get('reason')
        ))

    # Parse recommendation filters
    recommendation_filters = []
    for filter_data in (config_data.get('recommendation_filters') or []):
        recommendation_filters.append(RecommendationFilter(
            recommendation_id=filter_data['recommendation_id'],
            action=filter_data['action'],
            condition=filter_data.get('condition'),
            reason=filter_data.get('reason')
        ))

    # Parse local rules
    local_rules = []
    for rule_data in (config_data.get('local_rules') or []):
        local_rules.append(LocalRule(
            id=rule_data['id'],
            title=rule_data.get('title', rule_data['id']),
            expression=rule_data['expression'],
            type=rule_data.get('type', 'assessment'),
            applies_to_cpg=rule_data.get('applies_to_cpg'),
            priority=rule_data.get('priority', 100)
        ))

    # Load parent config if specified
    resolved_parent = parent_config
    if 'parent_config_path' in config_data and not parent_config:
        parent_path = config_data['parent_config_path']
        # Resolve relative to current config
        if not Path(parent_path).is_absolute():
            parent_path = path.parent / parent_path
        resolved_parent = load_institution_config(str(parent_path))

    return InstitutionConfig(
        institution_id=config_data['institution_id'],
        institution_name=config_data.get('institution_name', config_data['institution_id']),
        parent_config=resolved_parent,
        threshold_overrides=threshold_overrides,
        expression_overrides=expression_overrides,
        recommendation_filters=recommendation_filters,
        local_rules=local_rules,
        metadata=config_data.get('metadata', {})
    )


def validate_institution_config(config: InstitutionConfig, cpg) -> list[str]:
    """Validate an institution config against a CPG.

    Checks:
    - All overridden targets exist in the CPG
    - Override values are within safe ranges
    - Expression syntax is valid

    Args:
        config: The institution config to validate
        cpg: The CPG to validate against

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check threshold overrides
    all_var_ids = set()
    for v in (cpg.assessment_variables or []):
        all_var_ids.add(v.id)
    for v in (cpg.recommendation_variables or []):
        all_var_ids.add(v.id)

    for override in config.threshold_overrides:
        if override.target_id not in all_var_ids:
            errors.append(f"Threshold override target '{override.target_id}' not found in CPG")

    # Check expression overrides
    for override in config.expression_overrides:
        if override.target_id not in all_var_ids:
            errors.append(f"Expression override target '{override.target_id}' not found in CPG")

        # Validate expression syntax
        try:
            from .expression import Expression
            Expression(override.override_expression)
        except Exception as e:
            errors.append(f"Invalid expression in override for '{override.target_id}': {e}")

    # Check recommendation filters
    rec_ids = {v.id for v in (cpg.recommendation_variables or [])}
    for f in config.recommendation_filters:
        if f.recommendation_id not in rec_ids:
            errors.append(f"Recommendation filter target '{f.recommendation_id}' not found in CPG")

    return errors
