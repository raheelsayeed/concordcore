#!/usr/bin/env python3
"""Session state management for Concord MCP server.

This module provides state management for MCP tool calls, including
session isolation, CPG caching, and evaluation result storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cpg import CPG
from core.concord import Concord
from core.concord_user import ConcordUser
from core.healthcontext import HealthContext
from primitives.types import Persona

log = logging.getLogger(__name__)


@dataclass
class EvaluationSession:
    """Encapsulates all state for a single evaluation session.

    Each session represents one patient evaluation workflow, containing
    health context, CPG evaluations, and cached results.

    Attributes:
        session_id: Unique identifier for this session
        created_at: When the session was created
        guidelines_acknowledged: Whether LLM has read mandatory guidelines
        guidelines_acknowledged_at: When guidelines were acknowledged
        health_context: Patient health data
        cpg_evaluations: Map of CPG ID to Concord instances
        attestations: Map of variable ID to attested values (deprecated, use user)
        user: ConcordUser session for PGHD data management
        fhir_resources: Original FHIR resources if provided
        confidence_scores: Cached confidence scores by CPG ID
        prioritized_recommendations: Cached prioritized recommendations
    """
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)

    # Guidelines acknowledgment - MUST be done before using data tools
    guidelines_acknowledged: bool = False
    guidelines_acknowledged_at: datetime | None = None

    # Core state
    health_context: HealthContext | None = None
    cpg_evaluations: dict[str, Concord] = field(default_factory=dict)
    attestations: dict[str, Any] = field(default_factory=dict)  # Deprecated: use user

    # ConcordUser for PGHD management
    user: ConcordUser | None = None

    # FHIR data (if provided)
    fhir_resources: list[dict] = field(default_factory=list)

    # Cached results
    confidence_scores: dict[str, Any] = field(default_factory=dict)
    prioritized_recommendations: list = field(default_factory=list)

    def acknowledge_guidelines(self) -> None:
        """Mark that LLM has read and acknowledged the guidelines."""
        self.guidelines_acknowledged = True
        self.guidelines_acknowledged_at = datetime.now()
        log.info(f"Session {self.session_id}: Guidelines acknowledged")

    def get_or_create_user(self, persona: Persona = Persona.patient) -> ConcordUser:
        """Get or create the ConcordUser for this session.

        Args:
            persona: Persona for the user (used only on creation)

        Returns:
            The session's ConcordUser instance
        """
        if self.user is None:
            self.user = ConcordUser(
                user_id=self.session_id,
                persona=persona,
            )
            log.info(f"Session {self.session_id}: Created ConcordUser")
        return self.user

    @property
    def active_concord(self) -> Concord | None:
        """Get most recently used Concord instance."""
        if self.cpg_evaluations:
            return list(self.cpg_evaluations.values())[-1]
        return None

    @property
    def has_health_context(self) -> bool:
        """Check if session has health context."""
        return self.health_context is not None

    def get_evaluation(self, cpg_id: str) -> Concord | None:
        """Get Concord instance for a specific CPG."""
        return self.cpg_evaluations.get(cpg_id)

    def store_evaluation(self, cpg_id: str, concord: Concord) -> None:
        """Store Concord instance for a CPG."""
        self.cpg_evaluations[cpg_id] = concord


class ConcordState:
    """Manages state across MCP tool calls with session isolation.

    This class maintains:
    - Loaded CPG definitions (cached)
    - Active evaluation sessions
    - Session cleanup for stale sessions

    Thread safety: This class is NOT thread-safe. Each MCP server
    instance should have its own ConcordState.

    Attributes:
        cpgs_dir: Directory containing CPG YAML files
        loaded_cpgs: Cache of loaded CPG objects
        sessions: Active evaluation sessions
    """

    def __init__(self, cpgs_dir: Path | str = None):
        """Initialize state manager.

        Args:
            cpgs_dir: Directory containing CPG YAML files.
                     Defaults to ../cpgs relative to this module.
        """
        if cpgs_dir is None:
            self.cpgs_dir = Path(__file__).parent.parent / "cpgs"
        else:
            self.cpgs_dir = Path(cpgs_dir)

        self.loaded_cpgs: dict[str, CPG] = {}
        self.sessions: dict[str, EvaluationSession] = {}

    def get_session(self, session_id: str, create: bool = True) -> EvaluationSession | None:
        """Get or create an evaluation session.

        Args:
            session_id: Unique session identifier
            create: If True, create session if it doesn't exist

        Returns:
            EvaluationSession or None if not found and create=False
        """
        if session_id not in self.sessions:
            if create:
                self.sessions[session_id] = EvaluationSession(session_id=session_id)
                log.info(f"Created new session: {session_id}")
            else:
                return None
        return self.sessions[session_id]

    def delete_session(self, session_id: str) -> bool:
        """Delete an evaluation session.

        Args:
            session_id: Session to delete

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            log.info(f"Deleted session: {session_id}")
            return True
        return False

    def get_available_cpgs(self) -> list[dict]:
        """List all available CPG YAML files.

        Returns:
            List of dicts with 'filename', 'path', and 'identifier' keys
        """
        cpgs = []
        if self.cpgs_dir.exists():
            for f in sorted(self.cpgs_dir.glob("*.yaml")):
                cpgs.append({
                    "filename": f.name,
                    "path": str(f),
                    "identifier": f.stem
                })
        return cpgs

    def load_cpg(self, identifier: str) -> CPG:
        """Load a CPG by identifier with caching.

        Args:
            identifier: CPG identifier (filename without .yaml extension)

        Returns:
            Loaded CPG object

        Raises:
            FileNotFoundError: If CPG file doesn't exist
        """
        if identifier in self.loaded_cpgs:
            return self.loaded_cpgs[identifier]

        cpg_path = self.cpgs_dir / f"{identifier}.yaml"
        if not cpg_path.exists():
            raise FileNotFoundError(f"CPG not found: {identifier}")

        cpg = CPG.from_document_path(str(cpg_path))
        self.loaded_cpgs[identifier] = cpg
        log.info(f"Loaded CPG: {identifier} ({cpg.title})")
        return cpg

    def reload_cpg(self, identifier: str) -> CPG:
        """Force reload a CPG from disk.

        Args:
            identifier: CPG identifier

        Returns:
            Reloaded CPG object
        """
        if identifier in self.loaded_cpgs:
            del self.loaded_cpgs[identifier]
        return self.load_cpg(identifier)

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum session age in hours

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        stale = [
            sid for sid, session in self.sessions.items()
            if (now - session.created_at).total_seconds() > max_age_hours * 3600
        ]
        for sid in stale:
            del self.sessions[sid]

        if stale:
            log.info(f"Cleaned up {len(stale)} stale sessions")
        return len(stale)

    def session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.sessions)

    def cpg_count(self) -> int:
        """Get number of loaded CPGs."""
        return len(self.loaded_cpgs)
