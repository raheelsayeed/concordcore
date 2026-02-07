#!/usr/bin/env python3
"""Tests for institutional configuration validation."""

import pytest
from pathlib import Path

from core.config_validator import (
    ConfigValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationIssue,
    validate_config_file,
    visualize_inheritance_chain,
    SAFE_RANGES,
)
from core.institution_config import (
    InstitutionConfig,
    ThresholdOverride,
    ExpressionOverride,
    RecommendationFilter,
    LocalRule,
    load_institution_config,
)


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_validator_initialization(self):
        """Test validator can be initialized."""
        validator = ConfigValidator()
        assert validator is not None

    def test_valid_config(self):
        """Test validation of a valid configuration."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="MED_B",
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=7.5,
                    reason="More aggressive prevention",
                )
            ],
            local_rules=[
                LocalRule(
                    id="local_rule_1",
                    title="Test Rule",
                    expression="$Age > 65",
                    type="assessment",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_institution_id(self):
        """Test that missing institution_id is an error."""
        config = InstitutionConfig(
            institution_id="",  # Empty string
            institution_name="Test Hospital",
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "MISSING_INSTITUTION_ID" for i in result.errors)

    def test_missing_institution_name_warning(self):
        """Test that missing institution_name is a warning."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="",  # Empty string
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        # Should be valid (warnings don't invalidate)
        assert result.is_valid
        assert any(i.code == "MISSING_INSTITUTION_NAME" for i in result.warnings)

    def test_strict_mode_treats_warnings_as_errors(self):
        """Test that strict mode treats warnings as errors."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="",  # Missing name is a warning
        )

        validator = ConfigValidator()
        result = validator.validate(config, strict_mode=True)

        assert not result.is_valid  # Warning treated as error in strict mode


class TestSchemaValidation:
    """Tests for schema validation."""

    def test_threshold_override_missing_target_id(self):
        """Test threshold override with missing target_id."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="",  # Missing
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=7.5,
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "MISSING_TARGET_ID" for i in result.errors)

    def test_threshold_override_missing_reason_warning(self):
        """Test that missing reason on threshold override is a warning."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="MED_B",
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=7.5,
                    reason=None,  # Missing reason
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.is_valid  # Still valid, just a warning
        assert any(i.code == "MISSING_REASON" for i in result.warnings)

    def test_local_rule_invalid_type(self):
        """Test local rule with invalid type."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            local_rules=[
                LocalRule(
                    id="rule_1",
                    title="Test Rule",
                    expression="$Age > 65",
                    type="invalid_type",  # Should be assessment or recommendation
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "INVALID_RULE_TYPE" for i in result.errors)

    def test_recommendation_filter_invalid_action(self):
        """Test recommendation filter with invalid action."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            recommendation_filters=[
                RecommendationFilter(
                    recommendation_id="MED_A",
                    action="maybe",  # Should be include or exclude
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "INVALID_FILTER_ACTION" for i in result.errors)


class TestConflictDetection:
    """Tests for override conflict detection."""

    def test_duplicate_threshold_override(self):
        """Test detection of duplicate threshold overrides."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="MED_B",
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=7.5,
                    reason="First override",
                ),
                ThresholdOverride(
                    target_id="MED_B",
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=8.0,
                    reason="Duplicate override",
                ),
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "DUPLICATE_THRESHOLD_OVERRIDE" for i in result.errors)

    def test_duplicate_expression_override(self):
        """Test detection of duplicate expression overrides."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            expression_overrides=[
                ExpressionOverride(
                    target_id="risk_factors",
                    original_expression="$a == True",
                    override_expression="$b == True",
                    reason="First",
                ),
                ExpressionOverride(
                    target_id="risk_factors",
                    original_expression="$a == True",
                    override_expression="$c == True",
                    reason="Duplicate",
                ),
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "DUPLICATE_EXPRESSION_OVERRIDE" for i in result.errors)

    def test_conflicting_recommendation_filters(self):
        """Test detection of conflicting recommendation filters."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            recommendation_filters=[
                RecommendationFilter(
                    recommendation_id="MED_A",
                    action="include",
                    reason="Include it",
                ),
                RecommendationFilter(
                    recommendation_id="MED_A",
                    action="exclude",
                    reason="Also exclude it",
                ),
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "CONFLICTING_FILTERS" for i in result.errors)

    def test_duplicate_local_rule_ids(self):
        """Test detection of duplicate local rule IDs."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            local_rules=[
                LocalRule(
                    id="rule_1",
                    title="First Rule",
                    expression="$Age > 65",
                    type="assessment",
                ),
                LocalRule(
                    id="rule_1",
                    title="Duplicate Rule",
                    expression="$Age > 70",
                    type="assessment",
                ),
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid
        assert any(i.code == "DUPLICATE_RULE_ID" for i in result.errors)

    def test_circular_inheritance_detection(self):
        """Test detection of circular inheritance."""
        # Create a chain that loops back
        parent_config = InstitutionConfig(
            institution_id="parent",
            institution_name="Parent Hospital",
        )
        child_config = InstitutionConfig(
            institution_id="child",
            institution_name="Child Hospital",
            parent_config=parent_config,
        )
        # Create circular reference
        parent_config.parent_config = child_config

        validator = ConfigValidator()
        result = validator.validate(child_config)

        assert not result.is_valid
        assert any(i.code == "CIRCULAR_INHERITANCE" for i in result.errors)


class TestSafeRangeChecks:
    """Tests for safe range validation."""

    def test_value_above_safe_range(self):
        """Test detection of values above safe range."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="highLDL",
                    parameter="ldl_threshold",
                    original_value=140,
                    override_value=500,  # Way above 300 max
                    reason="Testing",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config, check_safe_ranges=True)

        assert result.is_valid  # Warnings don't invalidate
        assert any(i.code == "VALUE_ABOVE_SAFE_RANGE" for i in result.warnings)

    def test_value_below_safe_range(self):
        """Test detection of values below safe range."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="highLDL",
                    parameter="ldl_threshold",
                    original_value=140,
                    override_value=10,  # Below 30 min
                    reason="Testing",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config, check_safe_ranges=True)

        assert result.is_valid  # Warnings don't invalidate
        assert any(i.code == "VALUE_BELOW_SAFE_RANGE" for i in result.warnings)

    def test_negative_threshold_warning(self):
        """Test warning for negative threshold values."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="some_assessment",
                    parameter="some_threshold",
                    original_value=10,
                    override_value=-5,  # Negative
                    reason="Testing",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config, check_safe_ranges=True)

        assert any(i.code == "NEGATIVE_THRESHOLD" for i in result.warnings)

    def test_safe_ranges_can_be_disabled(self):
        """Test that safe range checking can be disabled."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="highLDL",
                    parameter="ldl_threshold",
                    original_value=140,
                    override_value=500,  # Would trigger warning
                    reason="Testing",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config, check_safe_ranges=False)

        assert not any(i.code == "VALUE_ABOVE_SAFE_RANGE" for i in result.warnings)


class TestExpressionValidation:
    """Tests for expression syntax validation."""

    def test_undefined_variable_reference_with_context(self):
        """Test detection of undefined variable references when context is available."""
        # When local rules provide context, undefined variables are detected
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            expression_overrides=[
                ExpressionOverride(
                    target_id="risk_factors",
                    original_expression="$a == True",
                    override_expression="$undefined_variable == True",  # Not defined anywhere
                    reason="Testing",
                )
            ],
            local_rules=[
                LocalRule(
                    id="known_rule",
                    title="Known Rule",
                    expression="$Age > 65",  # $Age is undefined
                    type="assessment",
                )
            ],
        )

        validator = ConfigValidator()
        # With local rules providing some context, undefined variables should produce warnings
        result = validator.validate(config)

        assert result.is_valid  # Warnings don't invalidate
        # The expression_override references $undefined_variable which is not a local_rule id
        assert any(i.code == "UNDEFINED_VARIABLE_REF" for i in result.warnings)

    def test_valid_expression_syntax(self):
        """Test that valid expressions pass."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            expression_overrides=[
                ExpressionOverride(
                    target_id="risk_factors",
                    original_expression="$a == True",
                    override_expression="$has_diabetes == True and $htn == True",
                    reason="Testing",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not any(i.code == "INVALID_EXPRESSION_SYNTAX" for i in result.issues)


class TestInheritanceChain:
    """Tests for inheritance chain building."""

    def test_single_config_chain(self):
        """Test inheritance chain with single config."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert len(result.inheritance_chain) == 1
        assert result.inheritance_chain[0].config_id == "test_hospital"
        assert result.inheritance_chain[0].level == 0

    def test_parent_child_chain(self):
        """Test inheritance chain with parent and child."""
        parent_config = InstitutionConfig(
            institution_id="parent",
            institution_name="Parent Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="MED_A",
                    parameter="threshold",
                    original_value=10,
                    override_value=8,
                    reason="Parent override",
                )
            ],
        )
        child_config = InstitutionConfig(
            institution_id="child",
            institution_name="Child Hospital",
            parent_config=parent_config,
        )

        validator = ConfigValidator()
        result = validator.validate(child_config)

        assert len(result.inheritance_chain) == 2
        assert result.inheritance_chain[0].config_id == "child"
        assert result.inheritance_chain[0].level == 0
        assert result.inheritance_chain[1].config_id == "parent"
        assert result.inheritance_chain[1].level == 1


class TestImpactAnalysis:
    """Tests for impact analysis."""

    def test_impact_analysis_threshold_changes(self):
        """Test impact analysis captures threshold changes."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="MED_B",
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=7.5,
                    reason="More aggressive",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.impact_analysis is not None
        assert result.impact_analysis.has_impact()
        assert len(result.impact_analysis.threshold_changes) == 1
        assert result.impact_analysis.threshold_changes[0]["target_id"] == "MED_B"
        assert result.impact_analysis.threshold_changes[0]["original"] == 10.0
        assert result.impact_analysis.threshold_changes[0]["override"] == 7.5

    def test_impact_analysis_excluded_recommendations(self):
        """Test impact analysis captures excluded recommendations."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            recommendation_filters=[
                RecommendationFilter(
                    recommendation_id="MED_A",
                    action="exclude",
                    reason="Not on formulary",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.impact_analysis is not None
        assert "MED_A" in result.impact_analysis.excluded_recommendations

    def test_impact_analysis_added_rules(self):
        """Test impact analysis captures added local rules."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            local_rules=[
                LocalRule(
                    id="local_rule_1",
                    title="Custom Assessment",
                    expression="$Age > 65",
                    type="assessment",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.impact_analysis is not None
        assert len(result.impact_analysis.added_rules) == 1
        assert result.impact_analysis.added_rules[0]["id"] == "local_rule_1"


class TestValidateConfigFile:
    """Tests for validate_config_file convenience function."""

    def test_validate_existing_file(self):
        """Test validation of existing config file."""
        result = validate_config_file("configs/example_hospital.yaml")
        assert result is not None
        assert isinstance(result, ValidationResult)

    def test_validate_nonexistent_file(self):
        """Test validation of nonexistent file."""
        result = validate_config_file("configs/nonexistent.yaml")
        assert not result.is_valid
        assert any(i.code == "FILE_NOT_FOUND" for i in result.errors)

    def test_validate_invalid_yaml(self, tmp_path):
        """Test validation of file with invalid YAML."""
        # Create a file with invalid YAML
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("invalid: yaml: content: [}")

        result = validate_config_file(str(bad_yaml))
        assert not result.is_valid
        assert any(i.code == "INVALID_YAML" for i in result.errors)


class TestVisualizeInheritanceChain:
    """Tests for inheritance chain visualization."""

    def test_visualize_single_config(self):
        """Test visualization of single config."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
        )

        output = visualize_inheritance_chain(config)

        assert "Test Hospital" in output
        assert "test_hospital" in output
        assert "Configuration Inheritance Chain" in output

    def test_visualize_parent_child(self):
        """Test visualization of parent-child config."""
        parent = InstitutionConfig(
            institution_id="parent",
            institution_name="Parent Hospital",
        )
        child = InstitutionConfig(
            institution_id="child",
            institution_name="Child Hospital",
            parent_config=parent,
        )

        output = visualize_inheritance_chain(child)

        assert "Child Hospital" in output
        assert "Parent Hospital" in output
        assert "inherits from" in output


class TestValidationResultSerialization:
    """Tests for ValidationResult serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
            threshold_overrides=[
                ThresholdOverride(
                    target_id="MED_B",
                    parameter="risk_threshold",
                    original_value=10.0,
                    override_value=7.5,
                    reason="Testing",
                )
            ],
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "is_valid" in result_dict
        assert "issues" in result_dict
        assert "inheritance_chain" in result_dict
        assert "impact_analysis" in result_dict
        assert "config_summary" in result_dict

    def test_summary_generation(self):
        """Test summary text generation."""
        config = InstitutionConfig(
            institution_id="test_hospital",
            institution_name="Test Hospital",
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        summary = result.summary()

        assert "INSTITUTIONAL CONFIGURATION VALIDATION REPORT" in summary
        assert "Test Hospital" in summary
        assert "Status:" in summary
