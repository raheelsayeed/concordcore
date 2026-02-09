#!/usr/bin/env python3
from __future__ import annotations

"""Centralized CPG auto-discovery registry.

Provides a single registry that discovers CPG YAML files from the filesystem,
exposes lightweight metadata (CPGEntry) without full parsing, and lazy-loads
full CPG objects on demand with caching.

Example usage:
    ```python
    from concordcore.core.cpg_registry import get_registry

    registry = get_registry()

    # List all discovered CPGs (metadata only, no full parse)
    for entry in registry.list():
        print(f"{entry.identifier}: {entry.title}")

    # Load a full CPG by identifier
    cpg = registry.get("2019AccPrimaryPreventionASCVD")

    # Group by category
    by_cat = registry.list_by_category()

    # Find CPGs that use a specific variable (e.g., a lab test)
    hits = registry.find_by_variable("LDL")
    for hit in hits:
        print(f"{hit.cpg_title}: used in {hit.phases}")
    ```
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CPGEntry:
    """Lightweight CPG metadata extracted from YAML without full variable parsing."""

    identifier: str
    title: str
    description: str
    category: list[str]
    publisher: str | None
    version: str
    path: Path

    def as_dict(self) -> dict:
        """Convert to a plain dictionary for serialization."""
        return {
            "identifier": self.identifier,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "publisher": self.publisher,
            "version": self.version,
            "path": str(self.path),
        }


@dataclass(frozen=True, slots=True)
class VariableUsage:
    """Describes how a variable is used within a specific CPG."""

    cpg_identifier: str
    cpg_title: str
    phases: tuple[str, ...]  # e.g. ("input", "assessment", "recommendation")
    details: tuple[str, ...]  # human-readable detail per usage

    def as_dict(self) -> dict:
        return {
            "cpg_identifier": self.cpg_identifier,
            "cpg_title": self.cpg_title,
            "phases": list(self.phases),
            "details": list(self.details),
        }


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    """Result of screening a patient against a single CPG."""

    cpg_identifier: str
    cpg_title: str
    is_eligible: bool
    description: str
    category: str
    publisher: str | None


@dataclass(frozen=True, slots=True)
class CPGVar:
    """A variable definition with cross-CPG provenance."""

    var: object  # Var — use object to avoid import at class level
    cpg_identifiers: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "variable_id": self.var.id,
            "title": self.var.title,
            "category": str(self.var.category) if self.var.category else None,
            "type": self.var.type.value if self.var.type else None,
            "required": self.var.required,
            "user_attestable": self.var.user_attestable,
            "cpg_identifiers": list(self.cpg_identifiers),
            "cpg_count": len(self.cpg_identifiers),
        }


class CPGRegistry:
    """Auto-discovers CPGs from a directory and provides lazy-loaded access.

    On construction the registry scans ``cpgs_dir`` for ``**/*.yaml`` files,
    reads only the ``CPG:`` metadata block from each, and builds an index of
    ``CPGEntry`` objects keyed by identifier.  Full ``CPG`` objects are loaded
    on demand via :meth:`get` and cached for subsequent calls.
    """

    def __init__(self, cpgs_dir: Path | None = None):
        if cpgs_dir is None:
            cpgs_dir = Path(__file__).parent.parent / "cpgs"
        self._cpgs_dir = cpgs_dir.resolve()
        self._entries: dict[str, CPGEntry] = {}
        self._cpg_cache: dict[str, object] = {}  # identifier -> CPG
        self._var_index: dict[str, list[VariableUsage]] | None = None  # lazy
        self._variables_index: dict[str, CPGVar] | None = None  # lazy
        self._scan()

    @property
    def cpgs_dir(self) -> Path:
        return self._cpgs_dir

    # ------------------------------------------------------------------
    # Scanning / discovery
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        """Glob ``cpgs_dir/**/*.yaml`` and extract metadata from each."""
        self._entries.clear()
        if not self._cpgs_dir.exists():
            log.warning("CPGs directory does not exist: %s", self._cpgs_dir)
            return

        for yaml_path in sorted(self._cpgs_dir.glob("**/*.yaml")):
            try:
                self._index_yaml(yaml_path)
            except Exception as exc:
                log.debug("Skipping %s: %s", yaml_path, exc)

    def _index_yaml(self, yaml_path: Path) -> None:
        """Read only the CPG metadata block from a YAML file."""
        with open(yaml_path, "r") as f:
            doc = yaml.safe_load(f)

        if not isinstance(doc, dict) or "CPG" not in doc:
            return

        cpg_block = doc["CPG"]
        identifier = cpg_block.get("identifier")
        if not identifier:
            return

        # Category: prefer 'type', fall back to 'tags'
        category = cpg_block.get("type") or cpg_block.get("tags") or []
        if isinstance(category, str):
            category = [category]

        entry = CPGEntry(
            identifier=identifier,
            title=cpg_block.get("title", identifier),
            description=cpg_block.get("description", "") or "",
            category=category,
            publisher=cpg_block.get("publisher"),
            version=cpg_block.get("version") or cpg_block.get("revision", "1.0.0"),
            path=yaml_path.resolve(),
        )

        if identifier in self._entries:
            log.debug(
                "Duplicate CPG identifier '%s': %s shadows %s",
                identifier,
                yaml_path,
                self._entries[identifier].path,
            )
        self._entries[identifier] = entry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, identifier: str):
        """Load and return a full CPG object by identifier (cached).

        Args:
            identifier: The CPG identifier as defined in the YAML.

        Returns:
            CPG instance.

        Raises:
            KeyError: If no CPG with that identifier was discovered.
        """
        if identifier not in self._entries:
            raise KeyError(
                f"Unknown CPG identifier: '{identifier}'. "
                f"Available: {self.identifiers()}"
            )

        if identifier not in self._cpg_cache:
            from concordcore.core.cpg import CPG

            entry = self._entries[identifier]
            cpg = CPG.from_document_path(str(entry.path))
            self._cpg_cache[identifier] = cpg

        return self._cpg_cache[identifier]

    def list(self) -> list[CPGEntry]:
        """Return all discovered CPG entries (metadata only)."""
        return list(self._entries.values())

    def list_by_category(self) -> dict[str, list[CPGEntry]]:
        """Return entries grouped by their first category tag."""
        by_cat: dict[str, list[CPGEntry]] = {}
        for entry in self._entries.values():
            cat = entry.category[0] if entry.category else "Other"
            by_cat.setdefault(cat, []).append(entry)
        return by_cat

    def identifiers(self) -> list[str]:
        """Return sorted list of all discovered CPG identifiers."""
        return sorted(self._entries.keys())

    def entry(self, identifier: str) -> CPGEntry:
        """Return the CPGEntry for a given identifier.

        Raises:
            KeyError: If not found.
        """
        return self._entries[identifier]

    def reload(self, identifier: str):
        """Evict cache and reload a CPG from disk.

        Raises:
            KeyError: If the identifier is unknown.
        """
        if identifier not in self._entries:
            raise KeyError(f"Unknown CPG identifier: '{identifier}'")
        self._cpg_cache.pop(identifier, None)
        return self.get(identifier)

    def find_by_variable(self, variable_id: str) -> list[VariableUsage]:
        """Find all CPGs that reference a given variable.

        Uses a lazily-built inverted index for O(1) lookups after first call.

        Args:
            variable_id: Variable name to search for (case-insensitive).

        Returns:
            List of VariableUsage describing each CPG's use of the variable.
        """
        if self._var_index is None:
            self._build_var_index()
        return self._var_index.get(variable_id.lower(), [])

    def _build_var_index(self) -> None:
        """Build inverted index: variable_id (lowercase) -> list[VariableUsage]."""
        index: dict[str, list[VariableUsage]] = {}

        for identifier in self.identifiers():
            try:
                cpg = self.get(identifier)
            except Exception:
                continue

            # Collect all (variable_id, phase, detail) tuples for this CPG
            var_hits: dict[str, list[tuple[str, str]]] = {}  # vid -> [(phase, detail)]

            for v in cpg.variables:
                vid = v.id.lower()
                title = getattr(v, "title", None) or v.id
                var_hits.setdefault(vid, []).append(
                    ("input", f"Defined as input variable: {title}")
                )

            for v in cpg.eligibility_variables:
                expr = getattr(v, "expression", "") or ""
                for ref in re.findall(r"\$(\w+)", expr):
                    var_hits.setdefault(ref.lower(), []).append(
                        ("eligibility", f"Referenced in eligibility '{v.id}': {expr[:80]}")
                    )

            for v in cpg.assessment_variables:
                expr = getattr(v, "expression", "") or ""
                for ref in re.findall(r"\$(\w+)", expr):
                    title = getattr(v, "title", None) or v.id
                    var_hits.setdefault(ref.lower(), []).append(
                        ("assessment", f"Referenced in assessment '{title}'")
                    )

            for v in cpg.recommendation_variables:
                expr = str(getattr(v, "expression", "") or "")
                compl = str(getattr(v, "compliance_expression", "") or "")
                for ref in re.findall(r"\$(\w+)", expr + " " + compl):
                    title = getattr(v, "title", None) or v.id
                    var_hits.setdefault(ref.lower(), []).append(
                        ("recommendation", f"Referenced in recommendation '{title}'")
                    )

            # Build VariableUsage per variable for this CPG
            for vid, hits in var_hits.items():
                phases = tuple(dict.fromkeys(p for p, _ in hits))
                details = tuple(d for _, d in hits)
                usage = VariableUsage(
                    cpg_identifier=identifier,
                    cpg_title=cpg.title,
                    phases=phases,
                    details=details,
                )
                index.setdefault(vid, []).append(usage)

        self._var_index = index

    def variables(self, cpgs: list[str] | None = None) -> list[CPGVar]:
        """Return all unique input variables across CPGs.

        Args:
            cpgs: Optional list of CPG identifiers to filter by.
                  If ``None``, returns variables from all CPGs.

        Returns:
            List of :class:`CPGVar` sorted by variable ID.

        Raises:
            KeyError: If any identifier in *cpgs* is unknown.
        """
        if cpgs is not None and len(cpgs) == 0:
            return []

        if self._variables_index is None:
            self._build_variables_index()

        if cpgs is None:
            return sorted(self._variables_index.values(), key=lambda cv: cv.var.id)

        # Validate all requested identifiers
        for ident in cpgs:
            if ident not in self._entries:
                raise KeyError(
                    f"Unknown CPG identifier: '{ident}'. "
                    f"Available: {self.identifiers()}"
                )

        cpg_set = set(cpgs)
        result: list[CPGVar] = []
        for cv in self._variables_index.values():
            overlap = tuple(i for i in cv.cpg_identifiers if i in cpg_set)
            if overlap:
                result.append(CPGVar(var=cv.var, cpg_identifiers=overlap))
        return sorted(result, key=lambda cv: cv.var.id)

    def _build_variables_index(self) -> None:
        """Build index: variable_id -> CPGVar with provenance."""
        index: dict[str, CPGVar] = {}

        for identifier in self.identifiers():
            try:
                cpg = self.get(identifier)
            except Exception:
                continue

            for v in cpg.variables:
                if v.id in index:
                    # Accumulate this CPG identifier
                    existing = index[v.id]
                    index[v.id] = CPGVar(
                        var=existing.var,
                        cpg_identifiers=existing.cpg_identifiers + (identifier,),
                    )
                else:
                    index[v.id] = CPGVar(var=v, cpg_identifiers=(identifier,))

        self._variables_index = index

    def screen(self, health_context) -> list[ScreeningResult]:
        """Screen a patient against all CPGs for eligibility.

        This is the single canonical implementation — app and MCP server
        should both delegate here instead of reimplementing the loop.

        Args:
            health_context: Patient HealthContext to check.

        Returns:
            List of ScreeningResult for every CPG (eligible and ineligible).
        """
        from concordcore.core.eligibility import EligibilityEvaluator

        results: list[ScreeningResult] = []

        for identifier in self.identifiers():
            try:
                cpg = self.get(identifier)
            except Exception:
                continue

            try:
                if cpg.eligibility_variables:
                    evaluator = EligibilityEvaluator(cpg.eligibility_variables)
                    result = evaluator.evaluate(health_context)
                    is_eligible = result.is_eligible
                else:
                    is_eligible = True
            except Exception:
                is_eligible = False

            results.append(ScreeningResult(
                cpg_identifier=identifier,
                cpg_title=cpg.title,
                is_eligible=is_eligible,
                description=getattr(cpg, "description", "") or "",
                category=getattr(cpg, "category", "") or "",
                publisher=cpg.publisher,
            ))

        return results

    def rescan(self) -> None:
        """Re-glob the directory and rebuild the entry index.

        Preserves the CPG cache for identifiers that still exist.
        """
        old_cache = self._cpg_cache.copy()
        self._cpg_cache.clear()
        self._var_index = None  # invalidate
        self._variables_index = None  # invalidate
        self._scan()
        # Restore cached CPGs that are still valid
        for ident in self._entries:
            if ident in old_cache:
                self._cpg_cache[ident] = old_cache[ident]


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_default: CPGRegistry | None = None


def get_registry(cpgs_dir: Path | None = None) -> CPGRegistry:
    """Get (or create) the module-level CPGRegistry singleton.

    Args:
        cpgs_dir: Override directory.  If provided, a new registry is created.
                  If ``None``, returns the existing singleton (creating it with
                  the default directory on first call).
    """
    global _default
    if _default is None or cpgs_dir is not None:
        _default = CPGRegistry(cpgs_dir)
    return _default
