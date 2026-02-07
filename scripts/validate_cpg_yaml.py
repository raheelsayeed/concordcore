#!/usr/bin/env python3
"""Validate CPG YAML files for pre-commit hook.

Checks:
- Valid YAML syntax
- Required CPG root key
- Required fields (identifier, title)
- Expression variable references
- Version field presence (warning only)
"""

import sys
import re
import yaml
from pathlib import Path

VAR_PATTERN = re.compile(r'\$([a-zA-Z_][a-zA-Z0-9_]*)')


def validate_cpg_file(filepath: str) -> tuple[list[str], list[str]]:
    """Validate a single CPG YAML file.

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"{filepath}: Invalid YAML - {e}")
        return errors, warnings
    except Exception as e:
        errors.append(f"{filepath}: {e}")
        return errors, warnings

    if not data:
        errors.append(f"{filepath}: Empty file")
        return errors, warnings

    if 'CPG' not in data:
        errors.append(f"{filepath}: Missing CPG root key")
        return errors, warnings

    cpg = data['CPG']

    # Check required fields
    required = ['identifier', 'title']
    for field in required:
        if field not in cpg:
            errors.append(f"{filepath}: Missing required field: {field}")

    # Check version field (warning only)
    if 'version' not in cpg:
        warnings.append(f"{filepath}: Missing version field (recommended for reproducibility)")

    # Collect all variable IDs
    var_ids = set()
    for section in ['variables', 'eligibility', 'assessment', 'recommendations']:
        for item in cpg.get(section, []) or []:
            if isinstance(item, dict) and 'id' in item:
                var_ids.add(item['id'])

    # Check expression variable references
    def check_expressions(items, section_name):
        for item in items or []:
            if not isinstance(item, dict):
                continue
            expr = item.get('expression', '')
            if expr:
                refs = VAR_PATTERN.findall(str(expr))
                for ref in refs:
                    if ref not in var_ids:
                        warnings.append(
                            f"{filepath} [{section_name}]: "
                            f"Expression may reference undefined variable: ${ref}"
                        )

    check_expressions(cpg.get('eligibility', []), 'eligibility')
    check_expressions(cpg.get('assessment', []), 'assessment')
    check_expressions(cpg.get('recommendations', []), 'recommendations')

    return errors, warnings


def main():
    """Main entry point for pre-commit hook."""
    all_errors = []
    all_warnings = []

    for arg in sys.argv[1:]:
        if not arg.endswith('.yaml'):
            continue
        if not arg.startswith('cpgs/') and 'cpgs/' not in arg:
            continue

        errors, warnings = validate_cpg_file(arg)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # Print warnings
    for warn in all_warnings:
        print(f"WARNING: {warn}", file=sys.stderr)

    # Print errors
    for err in all_errors:
        print(f"ERROR: {err}", file=sys.stderr)

    # Exit with error if any errors found
    if all_errors:
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
