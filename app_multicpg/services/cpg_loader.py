#!/usr/bin/env python3
"""CPG loading service for the Multi-CPG app.

Thin wrapper around :class:`core.cpg_registry.CPGRegistry`.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from concordcore.core.cpg import CPG
from concordcore.core.cpg_registry import get_registry


class CPGLoaderService:
    """Service for loading and caching CPG definitions."""

    def __init__(self, cpgs_dir: Path | None = None):
        self._registry = get_registry(cpgs_dir)

    def load_cpg(self, cpg_id: str) -> CPG | None:
        """Load a CPG by its identifier.

        Args:
            cpg_id: The CPG identifier (as defined in the YAML)

        Returns:
            CPG instance or None if not found
        """
        try:
            return self._registry.get(cpg_id)
        except KeyError:
            return None

    def load_cpgs(self, cpg_ids: list[str]) -> list[CPG]:
        """Load multiple CPGs by their identifiers."""
        cpgs = []
        for cpg_id in cpg_ids:
            cpg = self.load_cpg(cpg_id)
            if cpg:
                cpgs.append(cpg)
        return cpgs

    def get_available_cpgs(self) -> list[dict]:
        """Get list of available CPGs with metadata.

        Adds ``id``, ``name``, and a scalar ``category`` alias so that UI
        code can use the short keys (``cpg["id"]``, ``cpg["name"]``) while
        the registry uses ``identifier`` / ``title``.
        """
        result = []
        for entry in self._registry.list():
            d = entry.as_dict()
            d["id"] = d["identifier"]
            d["name"] = d["title"]
            d["category"] = d["category"][0] if d["category"] else "Other"
            result.append(d)
        return result

    def get_cpgs_by_category(self) -> dict[str, list[dict]]:
        """Get available CPGs organized by category."""
        result = {}
        for cat, entries in self._registry.list_by_category().items():
            items = []
            for e in entries:
                d = e.as_dict()
                d["id"] = d["identifier"]
                d["name"] = d["title"]
                d["category"] = cat
                items.append(d)
            result[cat] = items
        return result

    def clear_cache(self):
        """Clear the CPG cache by rescanning."""
        self._registry.rescan()


# Global loader instance
_loader: CPGLoaderService | None = None


def get_cpg_loader() -> CPGLoaderService:
    """Get the global CPG loader instance."""
    global _loader
    if _loader is None:
        _loader = CPGLoaderService()
    return _loader
