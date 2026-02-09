"""ConcordUser session class for accumulating patient input across interactions.

Provides an optional session state that tracks user-provided data, attestations,
and builds HealthContext instances for CPG evaluation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from concordcore.pghd.converter import PGHDConverter
from concordcore.pghd.input_source import InputSource
from concordcore.primitives.types import Persona
from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.variables.record import Record

log = logging.getLogger(__name__)


@dataclass(slots=True)
class ConcordUser:
    """Session state that accumulates user inputs across multiple interactions.

    ConcordUser is optional — Concord works fine without it. It provides:
    - Input accumulation across multiple interactions
    - Source tracking via PGHD module
    - Attestation logging
    - HealthContext building (merging EHR + PGHD data)
    - Serialization for session persistence

    Example:
        user = ConcordUser(user_id='patient-1', persona=Persona.patient)
        user.add_input('DM', True, var=dm_var)
        user.add_input('Smoker', 'no', var=smoker_var)
        ctx = user.build_health_context()
    """

    user_id: str
    persona: Persona = Persona.patient
    created_at: datetime = field(default_factory=datetime.now)

    _records: dict[str, Record] = field(default_factory=dict, repr=False)
    _attestation_log: list[dict] = field(default_factory=list, repr=False)
    _recommendation_actions: list[dict] = field(default_factory=list, repr=False)
    _converter: PGHDConverter = field(default_factory=PGHDConverter, repr=False)

    # --- Input Methods ---

    def add_input(self, var_id: str, value: Any,
                  var: Var | None = None,
                  source: InputSource = InputSource.patient_reported) -> Record:
        """Add a single user input.

        Args:
            var_id: Variable identifier
            value: Raw value from the user
            var: Optional Var definition (creates a simple Var if not provided)
            source: Data source type

        Returns:
            The created Record

        Raises:
            PGHDValidationError: If the value fails validation
        """
        var = var or Var(id=var_id, title=var_id)
        record = self._converter.to_record(var, value, source=source)
        self._records[var_id] = record

        self._attestation_log.append({
            'var_id': var_id,
            'value': value,
            'source': source.value,
            'timestamp': datetime.now().isoformat(),
        })

        log.debug(f'ConcordUser({self.user_id}): added input {var_id}={value}')
        return record

    def add_inputs(self, data: dict[str, Any],
                   var_lookup: dict[str, Var] | None = None,
                   source: InputSource = InputSource.patient_reported) -> list[Record]:
        """Add multiple user inputs at once.

        Args:
            data: Dict mapping variable IDs to raw values
            var_lookup: Optional dict of Var definitions. If not provided,
                        simple Vars are created for each key.
            source: Data source type

        Returns:
            List of created Records

        Raises:
            PGHDValidationError: If any value fails validation
        """
        records = []
        for var_id, value in data.items():
            var = (var_lookup or {}).get(var_id)
            record = self.add_input(var_id, value, var=var, source=source)
            records.append(record)
        return records

    def attest(self, var_id: str, value: Any,
               var: Var | None = None) -> None:
        """Record an attestation for a variable.

        If a record already exists for var_id, applies the attestation
        to it. Otherwise, creates a new record.

        Args:
            var_id: Variable identifier
            value: Attested value
            var: Optional Var definition
        """
        existing = self._records.get(var_id)
        if existing and existing.var.user_attestable:
            self._converter.attest(existing, value)
        else:
            self.add_input(var_id, value, var=var, source=InputSource.attestation)

        self._attestation_log.append({
            'var_id': var_id,
            'value': value,
            'source': InputSource.attestation.value,
            'timestamp': datetime.now().isoformat(),
            'is_attestation': True,
        })

    # --- Query Methods ---

    @property
    def records(self) -> list[Record]:
        """All accumulated records."""
        return list(self._records.values())

    def get_record(self, var_id: str) -> Record | None:
        """Get a record by variable ID."""
        return self._records.get(var_id)

    def has_data_for(self, var_id: str) -> bool:
        """Check if we have data for a variable."""
        rec = self._records.get(var_id)
        return rec is not None and rec.has_value

    @property
    def attestation_log(self) -> list[dict]:
        """Log of all inputs and attestations."""
        return list(self._attestation_log)

    # --- Recommendation Action Tracking ---

    def record_recommendation_action(self, rec_id: str, action: str,
                                     reason: str | None = None) -> None:
        """Record a provider's response to a recommendation.

        Args:
            rec_id: The recommendation ID
            action: Action taken (accepted, rejected, deferred, not-applicable)
            reason: Optional reason for the action
        """
        from concordcore.core.recommendation import RecommendationAction
        # Validate action is a known value
        RecommendationAction(action)

        self._recommendation_actions.append({
            'recommendation_id': rec_id,
            'action': action,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
        })
        log.debug(f'ConcordUser({self.user_id}): recorded action {action} for rec {rec_id}')

    @property
    def recommendation_actions(self) -> list[dict]:
        """Log of recommendation actions."""
        return list(self._recommendation_actions)

    # --- Build Methods ---

    def build_health_context(self,
                             ehr_records: list[Record] | None = None
                             ) -> 'HealthContext':
        """Build a HealthContext from accumulated data.

        Merges EHR records with PGHD records. EHR records take priority —
        if a variable has both EHR and PGHD data, the EHR data is used.

        Args:
            ehr_records: Optional list of EHR-sourced Records (higher priority)

        Returns:
            A new frozen HealthContext instance
        """
        from concordcore.core.healthcontext import HealthContext

        merged: dict[str, Record] = {}

        # PGHD records first (lower priority)
        for var_id, record in self._records.items():
            merged[var_id] = record

        # EHR records override (higher priority)
        if ehr_records:
            for record in ehr_records:
                merged[record.id] = record

        return HealthContext(
            records=list(merged.values()),
            persona=self.persona,
        )

    def update_health_context(self, existing_ctx: 'HealthContext') -> 'HealthContext':
        """Return a new HealthContext with PGHD data merged in.

        The existing context's records take priority. PGHD records are
        added only for variables not already present.

        Args:
            existing_ctx: The existing HealthContext to extend

        Returns:
            A new frozen HealthContext with PGHD data merged in
        """
        from concordcore.core.healthcontext import HealthContext

        existing_ids = {r.id for r in existing_ctx.records}
        new_records = list(existing_ctx.records)

        for var_id, record in self._records.items():
            if var_id not in existing_ids:
                new_records.append(record)

        return HealthContext(
            records=new_records,
            persona=existing_ctx.persona,
        )

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize to a dictionary for persistence."""
        return {
            'user_id': self.user_id,
            'persona': self.persona.value,
            'created_at': self.created_at.isoformat(),
            'records': {
                var_id: {
                    'var_id': var_id,
                    'value': rec.value.value if rec.value else None,
                    'has_value': rec.has_value,
                }
                for var_id, rec in self._records.items()
            },
            'attestation_log': self._attestation_log,
            'recommendation_actions': self._recommendation_actions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ConcordUser':
        """Deserialize from a dictionary.

        Note: This creates a new ConcordUser with simple Vars.
        Full Var definitions must be re-applied via add_input with
        proper Var objects.
        """
        user = cls(
            user_id=data['user_id'],
            persona=Persona(data.get('persona', 'patient')),
            created_at=datetime.fromisoformat(data['created_at']),
        )

        for var_id, rec_data in data.get('records', {}).items():
            raw_value = rec_data.get('value')
            if raw_value is not None:
                user.add_input(var_id, raw_value)

        user._attestation_log = data.get('attestation_log', [])
        user._recommendation_actions = data.get('recommendation_actions', [])
        return user

    def clear(self) -> None:
        """Reset all accumulated state."""
        self._records.clear()
        self._attestation_log.clear()
        self._recommendation_actions.clear()
