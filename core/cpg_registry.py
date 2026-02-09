#!/usr/bin/env python3
from __future__ import annotations

"""Centralized CPG auto-discovery registry.

Provides a single registry that discovers CPG YAML files from the filesystem,
exposes lightweight metadata (CPGEntry) without full parsing, and lazy-loads
full CPG objects on demand with caching.

Example usage:
    ```python
    from core.cpg_registry import get_registry

    registry = get_registry()

    # List all discovered CPGs (metadata only, no full parse)
    for entry in registry.list():
        print(f"{entry.identifier}: {entry.title}")

    # Load a full CPG by identifier
    cpg = registry.get("2019AccPrimaryPreventionASCVD")

    # Group by category
    by_cat = registry.list_by_category()
    ```
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


@dataclass(frozen=True)
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
            from core.cpg import CPG

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

    def rescan(self) -> None:
        """Re-glob the directory and rebuild the entry index.

        Preserves the CPG cache for identifiers that still exist.
        """
        old_cache = self._cpg_cache.copy()
        self._cpg_cache.clear()
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
