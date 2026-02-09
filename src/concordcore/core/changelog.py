#!/usr/bin/env python3
"""CPG Changelog generation and diff analysis.

This module provides tools for:
- Automatic changelog generation from CPG changes
- Expression diff viewer with semantic analysis
- Breaking change detection
- Version bump recommendations

Example usage:
    ```python
    from concordcore.core.changelog import CPGDiffer, ChangelogGenerator

    # Compare two versions
    differ = CPGDiffer()
    diff = differ.diff_cpg_files("cpgs/v1/cholesterol.yaml", "cpgs/v2/cholesterol.yaml")
    print(diff.summary())

    # Generate changelog
    generator = ChangelogGenerator()
    changelog = generator.generate_changelog(diff)
    print(changelog)
    ```
"""

import re
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import logging

log = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of change in a CPG."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ChangeSeverity(Enum):
    """Severity/impact of a change."""
    BREAKING = "breaking"      # May affect existing evaluations
    SIGNIFICANT = "significant"  # Important but not breaking
    MINOR = "minor"            # Documentation, formatting
    NONE = "none"


class VersionBump(Enum):
    """Recommended version bump type."""
    MAJOR = "major"  # Breaking changes
    MINOR = "minor"  # New features, significant changes
    PATCH = "patch"  # Bug fixes, minor changes
    NONE = "none"    # No changes


@dataclass(slots=True)
class FieldChange:
    """A change to a specific field."""
    path: str  # e.g., "assessment[0].expression"
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None
    severity: ChangeSeverity = ChangeSeverity.MINOR

    def __str__(self) -> str:
        if self.change_type == ChangeType.ADDED:
            return f"+ {self.path}: {self.new_value}"
        elif self.change_type == ChangeType.REMOVED:
            return f"- {self.path}: {self.old_value}"
        elif self.change_type == ChangeType.MODIFIED:
            return f"~ {self.path}: {self.old_value} → {self.new_value}"
        return f"  {self.path}: unchanged"


@dataclass(slots=True)
class VariableChange:
    """Change to a variable definition."""
    variable_id: str
    variable_type: str  # "variable", "eligibility", "assessment", "recommendation"
    change_type: ChangeType
    field_changes: list[FieldChange] = field(default_factory=list)
    severity: ChangeSeverity = ChangeSeverity.MINOR

    @property
    def is_expression_change(self) -> bool:
        """Check if this includes expression changes."""
        return any("expression" in c.path for c in self.field_changes)

    @property
    def is_threshold_change(self) -> bool:
        """Check if this includes threshold-related changes."""
        threshold_keywords = ["threshold", "limit", "cutoff", "range", "min", "max"]
        for change in self.field_changes:
            path_lower = change.path.lower()
            if any(kw in path_lower for kw in threshold_keywords):
                return True
            # Check if value looks like a threshold change
            if change.old_value is not None and change.new_value is not None:
                if isinstance(change.old_value, (int, float)) and isinstance(change.new_value, (int, float)):
                    return True
        return False


@dataclass(slots=True)
class CPGDiff:
    """Diff between two CPG versions."""
    old_identifier: str
    new_identifier: str
    old_version: str = None
    new_version: str = None
    old_path: str = None
    new_path: str = None
    metadata_changes: list[FieldChange] = field(default_factory=list)
    variable_changes: list[VariableChange] = field(default_factory=list)
    has_breaking_changes: bool = False
    recommended_bump: VersionBump = VersionBump.NONE

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return len(self.metadata_changes) + len(self.variable_changes)

    @property
    def added_variables(self) -> list[VariableChange]:
        """Variables that were added."""
        return [v for v in self.variable_changes if v.change_type == ChangeType.ADDED]

    @property
    def removed_variables(self) -> list[VariableChange]:
        """Variables that were removed."""
        return [v for v in self.variable_changes if v.change_type == ChangeType.REMOVED]

    @property
    def modified_variables(self) -> list[VariableChange]:
        """Variables that were modified."""
        return [v for v in self.variable_changes if v.change_type == ChangeType.MODIFIED]

    @property
    def expression_changes(self) -> list[VariableChange]:
        """Variables with expression changes."""
        return [v for v in self.variable_changes if v.is_expression_change]

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append("CPG DIFF SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Old: {self.old_identifier} (v{self.old_version or 'unknown'})")
        lines.append(f"New: {self.new_identifier} (v{self.new_version or 'unknown'})")
        lines.append(f"Recommended version bump: {self.recommended_bump.value.upper()}")
        if self.has_breaking_changes:
            lines.append("⚠️  BREAKING CHANGES DETECTED")
        lines.append("")

        # Summary counts
        lines.append(f"Variables added: {len(self.added_variables)}")
        lines.append(f"Variables removed: {len(self.removed_variables)}")
        lines.append(f"Variables modified: {len(self.modified_variables)}")
        lines.append(f"Expression changes: {len(self.expression_changes)}")
        lines.append("")

        # Metadata changes
        if self.metadata_changes:
            lines.append("-" * 60)
            lines.append("METADATA CHANGES")
            lines.append("-" * 60)
            for change in self.metadata_changes:
                lines.append(str(change))
            lines.append("")

        # Variable changes
        if self.variable_changes:
            lines.append("-" * 60)
            lines.append("VARIABLE CHANGES")
            lines.append("-" * 60)

            # Group by type
            for var_type in ["eligibility", "assessment", "recommendation", "variable"]:
                type_changes = [v for v in self.variable_changes if v.variable_type == var_type]
                if type_changes:
                    lines.append(f"\n{var_type.upper()}:")
                    for vc in type_changes:
                        severity_marker = "⚠️ " if vc.severity in [ChangeSeverity.BREAKING, ChangeSeverity.SIGNIFICANT] else ""
                        lines.append(f"  {severity_marker}{vc.change_type.value}: {vc.variable_id}")
                        for fc in vc.field_changes:
                            lines.append(f"    {fc}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "old_identifier": self.old_identifier,
            "new_identifier": self.new_identifier,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "has_breaking_changes": self.has_breaking_changes,
            "recommended_bump": self.recommended_bump.value,
            "summary": {
                "total_changes": self.total_changes,
                "added_variables": len(self.added_variables),
                "removed_variables": len(self.removed_variables),
                "modified_variables": len(self.modified_variables),
                "expression_changes": len(self.expression_changes),
            },
            "metadata_changes": [
                {
                    "path": c.path,
                    "type": c.change_type.value,
                    "old": c.old_value,
                    "new": c.new_value,
                }
                for c in self.metadata_changes
            ],
            "variable_changes": [
                {
                    "id": vc.variable_id,
                    "type": vc.variable_type,
                    "change_type": vc.change_type.value,
                    "severity": vc.severity.value,
                    "is_expression_change": vc.is_expression_change,
                    "field_changes": [
                        {
                            "path": fc.path,
                            "type": fc.change_type.value,
                            "old": fc.old_value,
                            "new": fc.new_value,
                        }
                        for fc in vc.field_changes
                    ],
                }
                for vc in self.variable_changes
            ],
        }


class CPGDiffer:
    """Compares two CPG versions and generates diffs."""

    # Fields that indicate breaking changes when modified
    BREAKING_FIELDS = {"expression", "code", "required", "type"}

    # Fields that indicate significant changes
    SIGNIFICANT_FIELDS = {"title", "narrative", "evidence_class", "evidence_level"}

    def diff_cpg_files(self, old_path: str, new_path: str) -> CPGDiff:
        """Diff two CPG YAML files.

        Args:
            old_path: Path to old CPG YAML file
            new_path: Path to new CPG YAML file

        Returns:
            CPGDiff with all changes
        """
        with open(old_path) as f:
            old_data = yaml.safe_load(f)
        with open(new_path) as f:
            new_data = yaml.safe_load(f)

        old_cpg = old_data.get("CPG", old_data)
        new_cpg = new_data.get("CPG", new_data)

        return self.diff_cpg_dicts(old_cpg, new_cpg, old_path, new_path)

    def diff_cpg_dicts(
        self,
        old_cpg: dict,
        new_cpg: dict,
        old_path: str = None,
        new_path: str = None,
    ) -> CPGDiff:
        """Diff two CPG dictionaries.

        Args:
            old_cpg: Old CPG data
            new_cpg: New CPG data
            old_path: Optional path for reference
            new_path: Optional path for reference

        Returns:
            CPGDiff with all changes
        """
        diff = CPGDiff(
            old_identifier=old_cpg.get("identifier", "unknown"),
            new_identifier=new_cpg.get("identifier", "unknown"),
            old_version=old_cpg.get("version"),
            new_version=new_cpg.get("version"),
            old_path=old_path,
            new_path=new_path,
        )

        # Diff metadata fields
        metadata_fields = ["title", "doi", "publisher", "version", "last_updated", "source_url"]
        for field_name in metadata_fields:
            old_val = old_cpg.get(field_name)
            new_val = new_cpg.get(field_name)
            if old_val != new_val:
                change_type = ChangeType.ADDED if old_val is None else (
                    ChangeType.REMOVED if new_val is None else ChangeType.MODIFIED
                )
                diff.metadata_changes.append(FieldChange(
                    path=field_name,
                    change_type=change_type,
                    old_value=old_val,
                    new_value=new_val,
                    severity=ChangeSeverity.MINOR,
                ))

        # Diff variable sections
        variable_sections = [
            ("variables", "variable"),
            ("eligibility", "eligibility"),
            ("assessment", "assessment"),
            ("recommendations", "recommendation"),
        ]

        for section_name, var_type in variable_sections:
            old_vars = {v["id"]: v for v in (old_cpg.get(section_name) or []) if isinstance(v, dict) and "id" in v}
            new_vars = {v["id"]: v for v in (new_cpg.get(section_name) or []) if isinstance(v, dict) and "id" in v}

            all_ids = set(old_vars.keys()) | set(new_vars.keys())

            for var_id in all_ids:
                old_var = old_vars.get(var_id)
                new_var = new_vars.get(var_id)

                if old_var is None:
                    # Added
                    diff.variable_changes.append(VariableChange(
                        variable_id=var_id,
                        variable_type=var_type,
                        change_type=ChangeType.ADDED,
                        severity=ChangeSeverity.SIGNIFICANT,
                    ))
                elif new_var is None:
                    # Removed - this is breaking!
                    diff.variable_changes.append(VariableChange(
                        variable_id=var_id,
                        variable_type=var_type,
                        change_type=ChangeType.REMOVED,
                        severity=ChangeSeverity.BREAKING,
                    ))
                    diff.has_breaking_changes = True
                else:
                    # Check for modifications
                    field_changes = self._diff_variable(old_var, new_var, var_id)
                    if field_changes:
                        # Determine severity
                        severity = ChangeSeverity.MINOR
                        for fc in field_changes:
                            if fc.severity == ChangeSeverity.BREAKING:
                                severity = ChangeSeverity.BREAKING
                                diff.has_breaking_changes = True
                            elif fc.severity == ChangeSeverity.SIGNIFICANT and severity != ChangeSeverity.BREAKING:
                                severity = ChangeSeverity.SIGNIFICANT

                        diff.variable_changes.append(VariableChange(
                            variable_id=var_id,
                            variable_type=var_type,
                            change_type=ChangeType.MODIFIED,
                            field_changes=field_changes,
                            severity=severity,
                        ))

        # Determine recommended version bump
        diff.recommended_bump = self._recommend_version_bump(diff)

        return diff

    def _diff_variable(self, old_var: dict, new_var: dict, var_id: str) -> list[FieldChange]:
        """Diff two variable dictionaries."""
        changes = []
        all_keys = set(old_var.keys()) | set(new_var.keys())

        for key in all_keys:
            if key == "id":
                continue  # Skip ID field

            old_val = old_var.get(key)
            new_val = new_var.get(key)

            if old_val != new_val:
                change_type = ChangeType.ADDED if old_val is None else (
                    ChangeType.REMOVED if new_val is None else ChangeType.MODIFIED
                )

                # Determine severity
                if key in self.BREAKING_FIELDS:
                    severity = ChangeSeverity.BREAKING
                elif key in self.SIGNIFICANT_FIELDS:
                    severity = ChangeSeverity.SIGNIFICANT
                else:
                    severity = ChangeSeverity.MINOR

                changes.append(FieldChange(
                    path=f"{var_id}.{key}",
                    change_type=change_type,
                    old_value=old_val,
                    new_value=new_val,
                    severity=severity,
                ))

        return changes

    def _recommend_version_bump(self, diff: CPGDiff) -> VersionBump:
        """Recommend a version bump based on changes."""
        if diff.has_breaking_changes:
            return VersionBump.MAJOR

        # Check for significant changes
        has_significant = any(
            vc.severity == ChangeSeverity.SIGNIFICANT
            for vc in diff.variable_changes
        )
        if has_significant or diff.added_variables or diff.removed_variables:
            return VersionBump.MINOR

        # Any changes at all?
        if diff.total_changes > 0:
            return VersionBump.PATCH

        return VersionBump.NONE


class ChangelogGenerator:
    """Generates changelog entries from CPG diffs."""

    def generate_changelog(
        self,
        diff: CPGDiff,
        format: str = "markdown",
        include_details: bool = True,
    ) -> str:
        """Generate a changelog from a diff.

        Args:
            diff: CPGDiff to generate changelog from
            format: Output format ("markdown", "text", "json")
            include_details: Include detailed field changes

        Returns:
            Changelog string
        """
        if format == "markdown":
            return self._generate_markdown(diff, include_details)
        elif format == "json":
            import json
            return json.dumps(diff.to_dict(), indent=2)
        else:
            return self._generate_text(diff, include_details)

    def _generate_markdown(self, diff: CPGDiff, include_details: bool) -> str:
        """Generate markdown changelog."""
        lines = []

        # Header
        version = diff.new_version or "unreleased"
        date = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"## [{version}] - {date}")
        lines.append("")

        if diff.has_breaking_changes:
            lines.append("### ⚠️ Breaking Changes")
            lines.append("")
            for vc in diff.variable_changes:
                if vc.severity == ChangeSeverity.BREAKING:
                    lines.append(f"- **{vc.variable_id}** ({vc.variable_type}): {vc.change_type.value}")
                    if include_details:
                        for fc in vc.field_changes:
                            if fc.severity == ChangeSeverity.BREAKING:
                                lines.append(f"  - {fc.path}: `{fc.old_value}` → `{fc.new_value}`")
            lines.append("")

        # Added
        if diff.added_variables:
            lines.append("### Added")
            lines.append("")
            for vc in diff.added_variables:
                lines.append(f"- **{vc.variable_id}** ({vc.variable_type})")
            lines.append("")

        # Changed
        non_breaking_changes = [
            vc for vc in diff.modified_variables
            if vc.severity != ChangeSeverity.BREAKING
        ]
        if non_breaking_changes:
            lines.append("### Changed")
            lines.append("")
            for vc in non_breaking_changes:
                lines.append(f"- **{vc.variable_id}** ({vc.variable_type})")
                if include_details:
                    for fc in vc.field_changes:
                        lines.append(f"  - {fc.path}: `{fc.old_value}` → `{fc.new_value}`")
            lines.append("")

        # Removed
        if diff.removed_variables:
            lines.append("### Removed")
            lines.append("")
            for vc in diff.removed_variables:
                lines.append(f"- **{vc.variable_id}** ({vc.variable_type})")
            lines.append("")

        # Metadata changes
        if diff.metadata_changes:
            lines.append("### Metadata")
            lines.append("")
            for mc in diff.metadata_changes:
                if mc.change_type == ChangeType.MODIFIED:
                    lines.append(f"- {mc.path}: `{mc.old_value}` → `{mc.new_value}`")
                elif mc.change_type == ChangeType.ADDED:
                    lines.append(f"- {mc.path}: added `{mc.new_value}`")
            lines.append("")

        return "\n".join(lines)

    def _generate_text(self, diff: CPGDiff, include_details: bool) -> str:
        """Generate plain text changelog."""
        return diff.summary()


class ExpressionDiffer:
    """Detailed differ for CPG expressions."""

    def diff_expressions(self, old_expr: str, new_expr: str) -> dict:
        """Diff two expressions and explain the change.

        Args:
            old_expr: Old expression string
            new_expr: New expression string

        Returns:
            Dict with diff analysis
        """
        if old_expr == new_expr:
            return {"changed": False}

        # Extract variables
        var_pattern = re.compile(r'\$([a-zA-Z_][a-zA-Z0-9_]*)')
        old_vars = set(var_pattern.findall(old_expr or ""))
        new_vars = set(var_pattern.findall(new_expr or ""))

        added_vars = new_vars - old_vars
        removed_vars = old_vars - new_vars

        # Extract numeric values
        num_pattern = re.compile(r'\b(\d+\.?\d*)\b')
        old_nums = set(num_pattern.findall(old_expr or ""))
        new_nums = set(num_pattern.findall(new_expr or ""))

        # Analyze operators
        ops = ["==", "!=", ">=", "<=", ">", "<", "and", "or", "not"]
        old_ops = {op for op in ops if op in (old_expr or "")}
        new_ops = {op for op in ops if op in (new_expr or "")}

        return {
            "changed": True,
            "old_expression": old_expr,
            "new_expression": new_expr,
            "variables": {
                "added": list(added_vars),
                "removed": list(removed_vars),
                "unchanged": list(old_vars & new_vars),
            },
            "thresholds": {
                "old_values": list(old_nums),
                "new_values": list(new_nums),
            },
            "operators": {
                "added": list(new_ops - old_ops),
                "removed": list(old_ops - new_ops),
            },
            "potential_impact": self._assess_impact(old_expr, new_expr, added_vars, removed_vars),
        }

    def _assess_impact(
        self,
        old_expr: str,
        new_expr: str,
        added_vars: set,
        removed_vars: set,
    ) -> str:
        """Assess the potential impact of an expression change."""
        impacts = []

        if removed_vars:
            impacts.append(f"Variables removed ({', '.join(removed_vars)}) - may affect evaluation")

        if added_vars:
            impacts.append(f"New variables required ({', '.join(added_vars)})")

        # Check for threshold changes
        old_nums = re.findall(r'\b(\d+\.?\d*)\b', old_expr or "")
        new_nums = re.findall(r'\b(\d+\.?\d*)\b', new_expr or "")
        if old_nums != new_nums:
            impacts.append("Numeric thresholds changed - may affect who qualifies")

        # Check for logic changes
        if ("and" in (old_expr or "").lower() and "or" in (new_expr or "").lower()) or \
           ("or" in (old_expr or "").lower() and "and" in (new_expr or "").lower()):
            impacts.append("Logic operator change (AND/OR) - significant impact on evaluation")

        if not impacts:
            return "Minor change - cosmetic or formatting only"

        return "; ".join(impacts)


def diff_cpg_cli():
    """CLI for CPG diff."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Diff two CPG YAML files")
    parser.add_argument("old_file", help="Old CPG YAML file")
    parser.add_argument("new_file", help="New CPG YAML file")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    parser.add_argument("--changelog", action="store_true", help="Generate changelog format")

    args = parser.parse_args()

    differ = CPGDiffer()
    diff = differ.diff_cpg_files(args.old_file, args.new_file)

    if args.changelog:
        generator = ChangelogGenerator()
        print(generator.generate_changelog(diff, format=args.format))
    else:
        if args.format == "json":
            import json
            print(json.dumps(diff.to_dict(), indent=2))
        else:
            print(diff.summary())


if __name__ == "__main__":
    diff_cpg_cli()
