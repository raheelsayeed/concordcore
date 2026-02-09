"""Tests for ConcordUser session class."""

import pytest
from datetime import datetime

from concordcore.core.concord_user import ConcordUser
from concordcore.core.healthcontext import HealthContext
from concordcore.pghd.input_source import InputSource
from concordcore.pghd.validator import PGHDValidationError
from concordcore.primitives.types import Persona, ValueType
from concordcore.variables.var import Var
from concordcore.variables.value import Value
from concordcore.variables.record import Record


class TestConcordUserCreation:
    def test_create_with_defaults(self):
        user = ConcordUser(user_id='p1')
        assert user.user_id == 'p1'
        assert user.persona == Persona.patient
        assert isinstance(user.created_at, datetime)
        assert user.records == []
        assert user.attestation_log == []

    def test_create_with_provider_persona(self):
        user = ConcordUser(user_id='dr1', persona=Persona.provider)
        assert user.persona == Persona.provider


class TestConcordUserInput:
    @pytest.fixture
    def user(self):
        return ConcordUser(user_id='test-user')

    def test_add_input_simple(self, user):
        record = user.add_input('DM', True)
        assert record.has_value
        assert record.value.value is True
        assert user.has_data_for('DM')

    def test_add_input_with_var(self, user):
        var = Var(id='Age', title='Patient Age', type=ValueType.integer)
        record = user.add_input('Age', '55', var=var)
        assert record.value.value == 55

    def test_add_input_with_source(self, user):
        record = user.add_input('DM', True, source=InputSource.mcp_conversation)
        assert record.value.source == ['mcp-conversation']

    def test_add_inputs_bulk(self, user):
        data = {'DM': True, 'Smoker': False}
        records = user.add_inputs(data)
        assert len(records) == 2
        assert user.has_data_for('DM')
        assert user.has_data_for('Smoker')

    def test_add_inputs_with_var_lookup(self, user):
        var_lookup = {
            'Age': Var(id='Age', title='Age', type=ValueType.integer),
            'DM': Var(id='DM', title='Diabetes', type=ValueType.boolean),
        }
        records = user.add_inputs({'Age': '55', 'DM': 'yes'}, var_lookup=var_lookup)
        assert len(records) == 2
        age = user.get_record('Age')
        assert age.value.value == 55

    def test_add_input_overwrites_previous(self, user):
        user.add_input('DM', True)
        user.add_input('DM', False)
        assert user.get_record('DM').value.value is False

    def test_attestation_log_tracks_inputs(self, user):
        user.add_input('DM', True)
        user.add_input('Smoker', False)
        assert len(user.attestation_log) == 2
        assert user.attestation_log[0]['var_id'] == 'DM'
        assert user.attestation_log[1]['var_id'] == 'Smoker'


class TestConcordUserAttestation:
    @pytest.fixture
    def user(self):
        return ConcordUser(user_id='test-user')

    def test_attest_creates_record(self, user):
        user.attest('DM', True)
        assert user.has_data_for('DM')

    def test_attest_existing_record(self, user):
        var = Var(id='DM', title='Diabetes', type=ValueType.boolean, user_attestable=True)
        user.add_input('DM', True, var=var)
        # Attest with a different value
        user.attest('DM', False, var=var)
        # The attested value should override
        assert user.get_record('DM').value.value is False

    def test_attest_log_marked(self, user):
        user.attest('DM', True)
        log_entries = [e for e in user.attestation_log if e.get('is_attestation')]
        assert len(log_entries) == 1


class TestConcordUserQuery:
    @pytest.fixture
    def user(self):
        u = ConcordUser(user_id='test-user')
        u.add_input('DM', True)
        u.add_input('Age', 55)
        return u

    def test_records_property(self, user):
        assert len(user.records) == 2

    def test_get_record(self, user):
        rec = user.get_record('DM')
        assert rec is not None
        assert rec.value.value is True

    def test_get_record_nonexistent(self, user):
        assert user.get_record('NonExistent') is None

    def test_has_data_for(self, user):
        assert user.has_data_for('DM') is True
        assert user.has_data_for('NonExistent') is False


class TestConcordUserBuildHealthContext:
    @pytest.fixture
    def user(self):
        u = ConcordUser(user_id='test-user')
        u.add_input('DM', True)
        u.add_input('Smoker', False)
        return u

    def test_build_health_context(self, user):
        ctx = user.build_health_context()
        assert isinstance(ctx, HealthContext)
        assert len(ctx.records) == 2
        assert ctx.persona == Persona.patient

    def test_build_with_ehr_records(self, user):
        ehr_var = Var(id='LDL', title='LDL')
        ehr_record = Record(var=ehr_var, initial_values=[Value(150)])

        ctx = user.build_health_context(ehr_records=[ehr_record])
        assert len(ctx.records) == 3  # DM, Smoker, LDL
        ids = {r.id for r in ctx.records}
        assert 'LDL' in ids
        assert 'DM' in ids

    def test_ehr_overrides_pghd(self, user):
        """EHR records should take priority over PGHD records."""
        ehr_var = Var(id='DM', title='Diabetes')
        ehr_record = Record(var=ehr_var, initial_values=[Value(False)])

        ctx = user.build_health_context(ehr_records=[ehr_record])
        # DM should be from EHR (False), not PGHD (True)
        dm = next(r for r in ctx.records if r.id == 'DM')
        assert dm.value.value is False

    def test_update_health_context(self, user):
        # Create an existing context with LDL
        ehr_var = Var(id='LDL', title='LDL')
        ehr_record = Record(var=ehr_var, initial_values=[Value(150)])
        existing_ctx = HealthContext(records=[ehr_record], persona=Persona.patient)

        updated = user.update_health_context(existing_ctx)
        assert len(updated.records) == 3  # LDL (existing) + DM + Smoker
        ids = {r.id for r in updated.records}
        assert 'LDL' in ids
        assert 'DM' in ids
        assert 'Smoker' in ids

    def test_update_does_not_override_existing(self, user):
        """update_health_context should not replace existing records."""
        # Existing context already has DM=False
        ehr_var = Var(id='DM', title='Diabetes')
        ehr_record = Record(var=ehr_var, initial_values=[Value(False)])
        existing_ctx = HealthContext(records=[ehr_record], persona=Persona.patient)

        updated = user.update_health_context(existing_ctx)
        dm = next(r for r in updated.records if r.id == 'DM')
        assert dm.value.value is False  # From existing, not PGHD


class TestConcordUserSerialization:
    def test_to_dict(self):
        user = ConcordUser(user_id='p1', persona=Persona.patient)
        user.add_input('DM', True)
        d = user.to_dict()
        assert d['user_id'] == 'p1'
        assert d['persona'] == 'patient'
        assert 'DM' in d['records']
        assert d['records']['DM']['value'] is True

    def test_from_dict_roundtrip(self):
        user = ConcordUser(user_id='p1')
        user.add_input('DM', True)
        user.add_input('Age', 55)

        d = user.to_dict()
        restored = ConcordUser.from_dict(d)

        assert restored.user_id == 'p1'
        assert restored.persona == Persona.patient
        assert restored.has_data_for('DM')
        assert restored.has_data_for('Age')

    def test_clear(self):
        user = ConcordUser(user_id='p1')
        user.add_input('DM', True)
        assert len(user.records) == 1

        user.clear()
        assert len(user.records) == 0
        assert len(user.attestation_log) == 0


class TestConcordUserFullFlow:
    """Integration-style tests for the full ConcordUser → HealthContext → Concord flow."""

    def test_full_flow_with_cpg(self, minimal_cpg, sample_healthcontext):
        """Test: ConcordUser builds a HealthContext that Concord can evaluate."""
        from concordcore.core.concord import Concord

        user = ConcordUser(user_id='flow-test')
        # Add the same data that sample_healthcontext has
        for record in sample_healthcontext.records:
            if record.value:
                user.add_input(record.id, record.value.value)

        ctx = user.build_health_context()
        concord = Concord(cpg=minimal_cpg, healthcontext=ctx)
        result = concord.evaluate(ignore_attestations=True)
        assert result is not None
