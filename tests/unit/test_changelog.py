#!/usr/bin/env python3
"""Tests for CPG changelog generation."""

import pytest
import tempfile
import yaml
from pathlib import Path

from concordcore.core.changelog import (
    CPGDiffer,
    ChangelogGenerator,
    ExpressionDiffer,
    CPGDiff,
    FieldChange,
    VariableChange,
    ChangeType,
    ChangeSeverity,
    VersionBump,
)


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_change_types_exist(self):
        """Test that all change types exist."""
        assert ChangeType.ADDED
        assert ChangeType.REMOVED
        assert ChangeType.MODIFIED
        assert ChangeType.UNCHANGED


class TestChangeSeverity:
    """Tests for ChangeSeverity enum."""

    def test_severity_levels_exist(self):
        """Test that all severity levels exist."""
        assert ChangeSeverity.BREAKING
        assert ChangeSeverity.SIGNIFICANT
        assert ChangeSeverity.MINOR
        assert ChangeSeverity.NONE


class TestFieldChange:
    """Tests for FieldChange dataclass."""

    def test_str_added(self):
        """Test string representation for added field."""
        change = FieldChange(
            path="test.field",
            change_type=ChangeType.ADDED,
            new_value="new_value",
        )
        assert "+ test.field: new_value" in str(change)

    def test_str_removed(self):
        """Test string representation for removed field."""
        change = FieldChange(
            path="test.field",
            change_type=ChangeType.REMOVED,
            old_value="old_value",
        )
        assert "- test.field: old_value" in str(change)

    def test_str_modified(self):
        """Test string representation for modified field."""
        change = FieldChange(
            path="test.field",
            change_type=ChangeType.MODIFIED,
            old_value="old",
            new_value="new",
        )
        assert "~ test.field: old" in str(change)
        assert "→ new" in str(change)


class TestVariableChange:
    """Tests for VariableChange dataclass."""

    def test_is_expression_change(self):
        """Test expression change detection."""
        change = VariableChange(
            variable_id="test_var",
            variable_type="assessment",
            change_type=ChangeType.MODIFIED,
            field_changes=[
                FieldChange(
                    path="test_var.expression",
                    change_type=ChangeType.MODIFIED,
                    old_value="$a > 5",
                    new_value="$a > 10",
                )
            ],
        )
        assert change.is_expression_change

    def test_is_threshold_change(self):
        """Test threshold change detection."""
        change = VariableChange(
            variable_id="test_var",
            variable_type="assessment",
            change_type=ChangeType.MODIFIED,
            field_changes=[
                FieldChange(
                    path="test_var.risk_threshold",
                    change_type=ChangeType.MODIFIED,
                    old_value=10.0,
                    new_value=7.5,
                )
            ],
        )
        assert change.is_threshold_change


class TestCPGDiff:
    """Tests for CPGDiff dataclass."""

    def test_total_changes(self):
        """Test total changes calculation."""
        diff = CPGDiff(
            old_identifier="test_cpg",
            new_identifier="test_cpg",
            metadata_changes=[
                FieldChange(path="version", change_type=ChangeType.MODIFIED),
            ],
            variable_changes=[
                VariableChange(variable_id="var1", variable_type="variable", change_type=ChangeType.ADDED),
                VariableChange(variable_id="var2", variable_type="variable", change_type=ChangeType.REMOVED),
            ],
        )
        assert diff.total_changes == 3

    def test_added_variables(self):
        """Test added variables filter."""
        diff = CPGDiff(
            old_identifier="test_cpg",
            new_identifier="test_cpg",
            variable_changes=[
                VariableChange(variable_id="var1", variable_type="variable", change_type=ChangeType.ADDED),
                VariableChange(variable_id="var2", variable_type="variable", change_type=ChangeType.REMOVED),
            ],
        )
        assert len(diff.added_variables) == 1
        assert diff.added_variables[0].variable_id == "var1"

    def test_removed_variables(self):
        """Test removed variables filter."""
        diff = CPGDiff(
            old_identifier="test_cpg",
            new_identifier="test_cpg",
            variable_changes=[
                VariableChange(variable_id="var1", variable_type="variable", change_type=ChangeType.ADDED),
                VariableChange(variable_id="var2", variable_type="variable", change_type=ChangeType.REMOVED),
            ],
        )
        assert len(diff.removed_variables) == 1
        assert diff.removed_variables[0].variable_id == "var2"

    def test_summary_generation(self):
        """Test summary generation."""
        diff = CPGDiff(
            old_identifier="test_cpg",
            new_identifier="test_cpg",
            old_version="1.0.0",
            new_version="1.1.0",
        )
        summary = diff.summary()
        assert "CPG DIFF SUMMARY" in summary
        assert "test_cpg" in summary

    def test_to_dict(self):
        """Test conversion to dictionary."""
        diff = CPGDiff(
            old_identifier="test_cpg",
            new_identifier="test_cpg",
            old_version="1.0.0",
            new_version="1.1.0",
            recommended_bump=VersionBump.MINOR,
        )
        d = diff.to_dict()
        assert d["old_identifier"] == "test_cpg"
        assert d["recommended_bump"] == "minor"


class TestCPGDiffer:
    """Tests for CPGDiffer class."""

    @pytest.fixture
    def differ(self):
        """Create a differ instance."""
        return CPGDiffer()

    @pytest.fixture
    def old_cpg_dict(self):
        """Create sample old CPG dict."""
        return {
            "identifier": "test_cpg",
            "title": "Test CPG",
            "version": "1.0.0",
            "variables": [
                {"id": "var1", "title": "Variable 1"},
                {"id": "var2", "title": "Variable 2"},
            ],
            "assessment": [
                {"id": "assess1", "title": "Assessment 1", "expression": "$var1 > 10"},
            ],
            "recommendations": [
                {"id": "rec1", "title": "Recommendation 1", "expression": "$assess1 == True"},
            ],
        }

    @pytest.fixture
    def new_cpg_dict(self):
        """Create sample new CPG dict."""
        return {
            "identifier": "test_cpg",
            "title": "Test CPG Updated",
            "version": "1.1.0",
            "variables": [
                {"id": "var1", "title": "Variable 1"},
                {"id": "var3", "title": "Variable 3"},  # var2 removed, var3 added
            ],
            "assessment": [
                {"id": "assess1", "title": "Assessment 1", "expression": "$var1 > 20"},  # expression changed
            ],
            "recommendations": [
                {"id": "rec1", "title": "Recommendation 1", "expression": "$assess1 == True"},
            ],
        }

    def test_diff_detects_added_variable(self, differ, old_cpg_dict, new_cpg_dict):
        """Test detection of added variables."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, new_cpg_dict)

        added = [v for v in diff.variable_changes if v.change_type == ChangeType.ADDED]
        assert any(v.variable_id == "var3" for v in added)

    def test_diff_detects_removed_variable(self, differ, old_cpg_dict, new_cpg_dict):
        """Test detection of removed variables."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, new_cpg_dict)

        removed = [v for v in diff.variable_changes if v.change_type == ChangeType.REMOVED]
        assert any(v.variable_id == "var2" for v in removed)

    def test_diff_detects_expression_change(self, differ, old_cpg_dict, new_cpg_dict):
        """Test detection of expression changes."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, new_cpg_dict)

        modified = [v for v in diff.variable_changes if v.change_type == ChangeType.MODIFIED]
        assert any(v.variable_id == "assess1" and v.is_expression_change for v in modified)

    def test_diff_detects_metadata_change(self, differ, old_cpg_dict, new_cpg_dict):
        """Test detection of metadata changes."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, new_cpg_dict)

        assert any(c.path == "title" for c in diff.metadata_changes)
        assert any(c.path == "version" for c in diff.metadata_changes)

    def test_removed_variable_is_breaking(self, differ, old_cpg_dict, new_cpg_dict):
        """Test that removed variable is marked as breaking."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, new_cpg_dict)

        assert diff.has_breaking_changes
        removed = [v for v in diff.variable_changes if v.change_type == ChangeType.REMOVED]
        assert any(v.severity == ChangeSeverity.BREAKING for v in removed)

    def test_recommend_version_bump(self, differ, old_cpg_dict, new_cpg_dict):
        """Test version bump recommendation."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, new_cpg_dict)

        # Should recommend major due to removed variable
        assert diff.recommended_bump == VersionBump.MAJOR

    def test_no_changes_returns_empty_diff(self, differ, old_cpg_dict):
        """Test that identical CPGs return empty diff."""
        diff = differ.diff_cpg_dicts(old_cpg_dict, old_cpg_dict)

        assert diff.total_changes == 0
        assert diff.recommended_bump == VersionBump.NONE

    def test_diff_cpg_files(self, differ, old_cpg_dict, new_cpg_dict):
        """Test diffing from YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = Path(tmpdir) / "old.yaml"
            new_path = Path(tmpdir) / "new.yaml"

            with open(old_path, "w") as f:
                yaml.dump({"CPG": old_cpg_dict}, f)
            with open(new_path, "w") as f:
                yaml.dump({"CPG": new_cpg_dict}, f)

            diff = differ.diff_cpg_files(str(old_path), str(new_path))

            assert diff.old_identifier == "test_cpg"
            assert diff.total_changes > 0


class TestChangelogGenerator:
    """Tests for ChangelogGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return ChangelogGenerator()

    @pytest.fixture
    def sample_diff(self):
        """Create a sample diff."""
        return CPGDiff(
            old_identifier="test_cpg",
            new_identifier="test_cpg",
            old_version="1.0.0",
            new_version="1.1.0",
            has_breaking_changes=True,
            recommended_bump=VersionBump.MAJOR,
            variable_changes=[
                VariableChange(
                    variable_id="var1",
                    variable_type="variable",
                    change_type=ChangeType.ADDED,
                    severity=ChangeSeverity.SIGNIFICANT,
                ),
                VariableChange(
                    variable_id="var2",
                    variable_type="assessment",
                    change_type=ChangeType.REMOVED,
                    severity=ChangeSeverity.BREAKING,
                ),
            ],
        )

    def test_generate_markdown(self, generator, sample_diff):
        """Test markdown changelog generation."""
        changelog = generator.generate_changelog(sample_diff, format="markdown")

        assert "## [1.1.0]" in changelog
        assert "Breaking Changes" in changelog
        assert "var1" in changelog
        assert "var2" in changelog

    def test_generate_text(self, generator, sample_diff):
        """Test text changelog generation."""
        changelog = generator.generate_changelog(sample_diff, format="text")

        assert "CPG DIFF SUMMARY" in changelog

    def test_generate_json(self, generator, sample_diff):
        """Test JSON changelog generation."""
        import json

        changelog = generator.generate_changelog(sample_diff, format="json")
        data = json.loads(changelog)

        assert data["old_identifier"] == "test_cpg"
        assert data["has_breaking_changes"] is True


class TestExpressionDiffer:
    """Tests for ExpressionDiffer class."""

    @pytest.fixture
    def differ(self):
        """Create a differ instance."""
        return ExpressionDiffer()

    def test_no_change(self, differ):
        """Test when expressions are identical."""
        result = differ.diff_expressions("$a > 10", "$a > 10")
        assert result["changed"] is False

    def test_detects_change(self, differ):
        """Test change detection."""
        result = differ.diff_expressions("$a > 10", "$a > 20")
        assert result["changed"] is True

    def test_detects_added_variables(self, differ):
        """Test detection of added variables."""
        result = differ.diff_expressions("$a > 10", "$a > 10 and $b < 5")
        assert "b" in result["variables"]["added"]

    def test_detects_removed_variables(self, differ):
        """Test detection of removed variables."""
        result = differ.diff_expressions("$a > 10 and $b < 5", "$a > 10")
        assert "b" in result["variables"]["removed"]

    def test_detects_threshold_changes(self, differ):
        """Test detection of threshold changes."""
        result = differ.diff_expressions("$a > 10", "$a > 20")
        assert "10" in result["thresholds"]["old_values"]
        assert "20" in result["thresholds"]["new_values"]

    def test_assess_impact(self, differ):
        """Test impact assessment."""
        result = differ.diff_expressions("$a > 10", "$b > 10")
        assert "potential_impact" in result
        assert len(result["potential_impact"]) > 0
