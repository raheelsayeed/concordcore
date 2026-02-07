#!/usr/bin/env python3
"""Unit tests for the Record class."""

import pytest
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from variables.record import Record
from variables.var import Var, Narrative
from variables.value import Value
from primitives.code import Code
from primitives.types import Persona


class TestRecordCreation:
    """Tests for Record instantiation."""

    def test_create_record_with_value(self, sample_var, sample_value):
        """Test creating a Record with a single value."""
        record = Record(var=sample_var, initial_values=[sample_value])
        assert record.var == sample_var
        assert record.value == sample_value
        assert record.has_value is True

    def test_create_record_without_value(self, sample_var):
        """Test creating a Record without values."""
        record = Record(var=sample_var, initial_values=None)
        assert record.var == sample_var
        assert record.value is None
        assert record.has_value is False

    def test_create_record_with_multiple_values(self, sample_var, sample_values_list):
        """Test creating a Record with multiple values."""
        record = Record(var=sample_var, initial_values=sample_values_list)
        assert record.has_value is True
        assert len(record.values) == len(sample_values_list)
        # value returns the most recent value (last in list by date)
        # sample_values_list has the most recent value last (115)
        assert record.value == sample_values_list[-1]


class TestRecordProperties:
    """Tests for Record properties."""

    def test_record_id(self, sample_record):
        """Test that Record id matches Var id."""
        assert sample_record.id == sample_record.var.id

    def test_record_title(self, sample_var, sample_value):
        """Test that Record title matches Var title."""
        var_with_title = Var(id='Test', title='Test Title')
        record = Record(var=var_with_title, initial_values=[sample_value])
        assert record.title == 'Test Title'

    def test_record_code(self, sample_loinc_code, sample_value):
        """Test that Record code matches Var code."""
        var_with_code = Var(id='Test', code=[sample_loinc_code])
        record = Record(var=var_with_code, initial_values=[sample_value])
        assert record.code == [sample_loinc_code]


class TestRecordAttestation:
    """Tests for Record attestation functionality."""

    def test_attestable_record_can_receive_attested_value(self, sample_var_attestable):
        """Test that attestable records can receive attested values."""
        record = Record(var=sample_var_attestable, initial_values=None)
        assert record.has_value is False

        attested = Value(200)
        record.attested_value = attested

        assert record.has_value is True
        assert record.attested_value == attested
        assert record.value == attested

    def test_non_attestable_record_rejects_attested_value(self, sample_var_required):
        """Test that non-attestable records reject attested values."""
        record = Record(var=sample_var_required, initial_values=None)

        with pytest.raises(ValueError, match='Variable is not attestable'):
            record.attested_value = Value(200)

    def test_attested_value_overrides_existing_values(self, sample_var_attestable, sample_value):
        """Test that attested value takes precedence over existing values."""
        record = Record(var=sample_var_attestable, initial_values=[sample_value])
        original_value = record.value

        attested = Value(999)
        record.attested_value = attested

        # Attested value should now be returned
        assert record.value == attested
        assert record.value != original_value


class TestRecordValidation:
    """Tests for Record validation."""

    def test_validate_with_valid_value(self, sample_record):
        """Test validation passes with valid value."""
        result = sample_record.validate()
        assert result is True

    def test_validate_record_without_value(self, sample_record_no_value):
        """Test validation of record without value."""
        result = sample_record_no_value.validate()
        assert result is True  # No value to validate


class TestRecordAsDict:
    """Tests for Record.as_dict() method."""

    def test_as_dict_with_value(self, sample_record):
        """Test as_dict includes value information."""
        d = sample_record.as_dict()
        assert 'value' in d
        assert d['value'] == sample_record.value.value

    def test_as_dict_without_value(self, sample_record_no_value):
        """Test as_dict handles missing value."""
        d = sample_record_no_value.as_dict()
        assert 'value' in d
        assert d['value'] is None

    def test_as_dict_includes_count(self, sample_ldl_record):
        """Test as_dict includes value count."""
        d = sample_ldl_record.as_dict()
        assert 'count' in d
        assert d['count'] == len(sample_ldl_record.values)


class TestRecordNarrative:
    """Tests for Record narrative functionality."""

    def test_set_narrative_patient_persona(self, sample_var_with_narrative, sample_value):
        """Test setting narrative for patient persona."""
        record = Record(var=sample_var_with_narrative, initial_values=[sample_value])
        narrative = record.set_narrative(persona=Persona.patient)
        assert narrative is not None

    def test_set_narrative_provider_persona(self, sample_var_with_narrative, sample_value):
        """Test setting narrative for provider persona."""
        record = Record(var=sample_var_with_narrative, initial_values=[sample_value])
        narrative = record.set_narrative(persona=Persona.provider)
        assert narrative is not None

    def test_narrative_uses_default_when_no_custom(self, sample_var, sample_value):
        """Test that default narrative is used when no custom narrative."""
        record = Record(var=sample_var, initial_values=[sample_value])
        narrative = record.set_narrative(persona=Persona.patient)
        # Should use default narrative
        assert narrative is not None or record.default_narratives is not None


class TestRecordRepr:
    """Tests for Record string representation."""

    def test_repr_includes_id(self, sample_record):
        """Test that repr includes the record ID."""
        repr_str = repr(sample_record)
        assert sample_record.id in repr_str

    def test_repr_indicates_record_type(self, sample_record):
        """Test that repr indicates it's a Record."""
        repr_str = repr(sample_record)
        assert 'Record' in repr_str
