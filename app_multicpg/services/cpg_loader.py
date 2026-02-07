#!/usr/bin/env python3
"""CPG loading service for the Multi-CPG app."""

import sys
from pathlib import Path
from functools import lru_cache

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.cpg import CPG
from app_multicpg.config import CPGS_DIR, AVAILABLE_CPGS


class CPGLoaderService:
    """Service for loading and caching CPG definitions."""

    def __init__(self, cpgs_dir: Path | None = None):
        """Initialize the loader.

        Args:
            cpgs_dir: Directory containing CPG YAML files
        """
        self.cpgs_dir = cpgs_dir or CPGS_DIR
        self._cache: dict[str, CPG] = {}

    def load_cpg(self, cpg_id: str) -> CPG | None:
        """Load a CPG by its ID.

        Args:
            cpg_id: The CPG identifier

        Returns:
            CPG instance or None if not found
        """
        # Check cache first
        if cpg_id in self._cache:
            return self._cache[cpg_id]

        # Find the CPG config
        cpg_config = None
        for cfg in AVAILABLE_CPGS:
            if cfg["id"] == cpg_id:
                cpg_config = cfg
                break

        if not cpg_config:
            return None

        # Load the CPG
        cpg_path = self.cpgs_dir / cpg_config["file"]
        if not cpg_path.exists():
            return None

        try:
            cpg = CPG.from_document_path(str(cpg_path))
            self._cache[cpg_id] = cpg
            return cpg
        except Exception as e:
            print(f"Error loading CPG {cpg_id}: {e}")
            return None

    def load_cpgs(self, cpg_ids: list[str]) -> list[CPG]:
        """Load multiple CPGs by their IDs.

        Args:
            cpg_ids: List of CPG identifiers

        Returns:
            List of successfully loaded CPG instances
        """
        cpgs = []
        for cpg_id in cpg_ids:
            cpg = self.load_cpg(cpg_id)
            if cpg:
                cpgs.append(cpg)
        return cpgs

    def get_available_cpgs(self) -> list[dict]:
        """Get list of available CPGs with metadata.

        Returns:
            List of CPG metadata dictionaries
        """
        available = []
        for cfg in AVAILABLE_CPGS:
            cpg_path = self.cpgs_dir / cfg["file"]
            if cpg_path.exists():
                available.append(cfg)
        return available

    def get_cpgs_by_category(self) -> dict[str, list[dict]]:
        """Get available CPGs organized by category.

        Returns:
            Dictionary mapping category names to lists of CPG configs
        """
        by_category: dict[str, list[dict]] = {}
        for cfg in self.get_available_cpgs():
            category = cfg.get("category", "Other")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(cfg)
        return by_category

    def clear_cache(self):
        """Clear the CPG cache."""
        self._cache.clear()


# Global loader instance
_loader: CPGLoaderService | None = None


def get_cpg_loader() -> CPGLoaderService:
    """Get the global CPG loader instance."""
    global _loader
    if _loader is None:
        _loader = CPGLoaderService()
    return _loader
