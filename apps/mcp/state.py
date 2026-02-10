"""Session state management for Concord MCP server v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import logging

from concordcore.core.cpg import CPG
from concordcore.core.cpg_registry import get_registry
from concordcore.core.concord import Concord
from concordcore.core.concord_user import ConcordUser
from concordcore.core.healthcontext import HealthContext
from concordcore.primitives.types import Persona

log = logging.getLogger(__name__)


@dataclass
class EvaluationSession:
    """All state for a single patient evaluation workflow."""

    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    guidelines_acknowledged: bool = False
    guidelines_acknowledged_at: datetime | None = None
    health_context: HealthContext | None = None
    cpg_evaluations: dict[str, Concord] = field(default_factory=dict)
    attestations: dict[str, Any] = field(default_factory=dict)
    user: ConcordUser | None = None
    fhir_resources: list[dict] = field(default_factory=list)
    confidence_scores: dict[str, Any] = field(default_factory=dict)
    prioritized_recommendations: list = field(default_factory=list)
    verification_records: dict[str, dict] = field(default_factory=dict)

    def acknowledge_guidelines(self) -> None:
        self.guidelines_acknowledged = True
        self.guidelines_acknowledged_at = datetime.now()

    def get_or_create_user(self, persona: Persona = Persona.patient) -> ConcordUser:
        if self.user is None:
            self.user = ConcordUser(user_id=self.session_id, persona=persona)
        return self.user

    @property
    def active_concord(self) -> Concord | None:
        if self.cpg_evaluations:
            return list(self.cpg_evaluations.values())[-1]
        return None

    def get_evaluation(self, cpg_id: str) -> Concord | None:
        return self.cpg_evaluations.get(cpg_id)

    def store_evaluation(self, cpg_id: str, concord: Concord) -> None:
        self.cpg_evaluations[cpg_id] = concord


class ConcordState:
    """Manages sessions and CPG loading across MCP tool calls."""

    def __init__(self, cpgs_dir: Path | str = None):
        self._registry = get_registry(Path(cpgs_dir)) if cpgs_dir else get_registry()
        self.cpgs_dir = self._registry.cpgs_dir
        self.sessions: dict[str, EvaluationSession] = {}

    def get_session(self, session_id: str, create: bool = True) -> EvaluationSession | None:
        if session_id not in self.sessions:
            if not create:
                return None
            self.sessions[session_id] = EvaluationSession(session_id=session_id)
        return self.sessions[session_id]

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_available_cpgs(self) -> list[dict]:
        return [
            {"filename": e.path.name, "path": str(e.path), "identifier": e.identifier}
            for e in self._registry.list()
        ]

    def load_cpg(self, identifier: str) -> CPG:
        return self._registry.get(identifier)

    def reload_cpg(self, identifier: str) -> CPG:
        return self._registry.reload(identifier)

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        now = datetime.now()
        stale = [
            sid for sid, s in self.sessions.items()
            if (now - s.created_at).total_seconds() > max_age_hours * 3600
        ]
        for sid in stale:
            del self.sessions[sid]
        return len(stale)

    def session_count(self) -> int:
        return len(self.sessions)

    def cpg_count(self) -> int:
        return len(self._registry.identifiers())
