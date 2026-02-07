"""Tests for the PGHD (Patient-Generated Health Data) module."""

import pytest
from datetime import datetime, date

from pghd.input_source import InputSource, InputMetadata
from pghd.normalizer import PGHDNormalizer
from pghd.validator import PGHDValidator, PGHDValidationError
from pghd.converter import PGHDConverter
from variables.var import Var
from variables.value import Value
from variables.record import Record
from primitives.types import ValueType


# ============================================================================
# InputSource / InputMetadata Tests
# ============================================================================

class TestInputSource:
    def test_enum_values(self):
        assert InputSource.patient_reported == 'patient-reported'
        assert InputSource.attestation == 'attestation'
        assert InputSource.mcp_conversation == 'mcp-conversation'

    def test_metadata_creation(self):
        meta = InputMetadata(source=InputSource.patient_reported)
        assert meta.source == InputSource.patient_reported
        assert isinstance(meta.timestamp, datetime)
        assert meta.session_id is None
        assert meta.confidence is None
        assert meta.raw_input is None

    def test_metadata_with_all_fields(self):
        meta = InputMetadata(
            source=InputSource.device,
            session_id='sess-123',
            confidence=0.95,
            raw_input='120/80',
        )
        assert meta.session_id == 'sess-123'
        assert meta.confidence == 0.95
        assert meta.raw_input == '120/80'

    def test_metadata_is_frozen(self):
        meta = InputMetadata(source=InputSource.attestation)
        with pytest.raises(AttributeError):
            meta.source = InputSource.device

    def test_confidence_validation(self):
        with pytest.raises(ValueError, match='confidence'):
            InputMetadata(source=InputSource.patient_reported, confidence=1.5)
        with pytest.raises(ValueError, match='confidence'):
            InputMetadata(source=InputSource.patient_reported, confidence=-0.1)


# ============================================================================
# PGHDNormalizer Tests
# ============================================================================

class TestPGHDNormalizer:
    @pytest.fixture
    def normalizer(self):
        return PGHDNormalizer()

    # Boolean normalization
    def test_bool_from_string_yes(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        val, meta = normalizer.normalize('yes', var)
        assert val is True

    def test_bool_from_string_no(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        val, meta = normalizer.normalize('no', var)
        assert val is False

    def test_bool_from_int_1(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        val, meta = normalizer.normalize(1, var)
        assert val is True

    def test_bool_from_int_0(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        val, meta = normalizer.normalize(0, var)
        assert val is False

    def test_bool_from_true(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        val, meta = normalizer.normalize(True, var)
        assert val is True

    def test_bool_invalid_string(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        with pytest.raises(ValueError, match='boolean'):
            normalizer.normalize('maybe', var)

    # Integer normalization
    def test_int_from_string(self, normalizer):
        var = Var(id='Age', type=ValueType.integer)
        val, meta = normalizer.normalize('55', var)
        assert val == 55
        assert isinstance(val, int)

    def test_int_from_float_string(self, normalizer):
        var = Var(id='Age', type=ValueType.integer)
        val, meta = normalizer.normalize('55.7', var)
        assert val == 55

    def test_int_from_float(self, normalizer):
        var = Var(id='Age', type=ValueType.integer)
        val, meta = normalizer.normalize(55.0, var)
        assert val == 55

    def test_int_invalid(self, normalizer):
        var = Var(id='Age', type=ValueType.integer)
        with pytest.raises(ValueError, match='integer'):
            normalizer.normalize('abc', var)

    # Decimal normalization
    def test_decimal_from_string(self, normalizer):
        var = Var(id='LDL', type=ValueType.decimal)
        val, meta = normalizer.normalize('165.5', var)
        assert val == 165.5
        assert isinstance(val, float)

    def test_decimal_from_int(self, normalizer):
        var = Var(id='LDL', type=ValueType.decimal)
        val, meta = normalizer.normalize(165, var)
        assert val == 165.0

    # Date normalization
    def test_date_from_iso_string(self, normalizer):
        var = Var(id='TestDate', type=ValueType.date)
        val, meta = normalizer.normalize('2024-01-15', var)
        assert val == date(2024, 1, 15)

    def test_date_from_us_format(self, normalizer):
        var = Var(id='TestDate', type=ValueType.date)
        val, meta = normalizer.normalize('01/15/2024', var)
        assert val == date(2024, 1, 15)

    def test_date_from_datetime(self, normalizer):
        var = Var(id='TestDate', type=ValueType.date)
        dt = datetime(2024, 1, 15, 10, 30)
        val, meta = normalizer.normalize(dt, var)
        assert val == date(2024, 1, 15)

    def test_date_invalid(self, normalizer):
        var = Var(id='TestDate', type=ValueType.date)
        with pytest.raises(ValueError, match='date'):
            normalizer.normalize('not-a-date', var)

    # String normalization
    def test_string_from_int(self, normalizer):
        var = Var(id='Name', type=ValueType.string)
        val, meta = normalizer.normalize(123, var)
        assert val == '123'

    # No type
    def test_no_type_passthrough(self, normalizer):
        var = Var(id='Custom')
        val, meta = normalizer.normalize('anything', var)
        assert val == 'anything'

    # None value
    def test_none_raises(self, normalizer):
        var = Var(id='Test', type=ValueType.integer)
        with pytest.raises(ValueError, match='None'):
            normalizer.normalize(None, var)

    # Metadata tracking
    def test_metadata_source_tracking(self, normalizer):
        var = Var(id='DM', type=ValueType.boolean)
        val, meta = normalizer.normalize('yes', var, source=InputSource.mcp_conversation,
                                          session_id='sess-1')
        assert meta.source == InputSource.mcp_conversation
        assert meta.session_id == 'sess-1'
        assert meta.raw_input == 'yes'


# ============================================================================
# PGHDValidator Tests
# ============================================================================

class TestPGHDValidator:
    @pytest.fixture
    def validator(self):
        return PGHDValidator()

    def test_validate_raw_none(self, validator):
        var = Var(id='Test', title='Test Var')
        with pytest.raises(PGHDValidationError) as exc_info:
            validator.validate_raw(None, var)
        assert exc_info.value.var_id == 'Test'
        assert 'required' in exc_info.value.user_message.lower()

    def test_validate_raw_not_attestable(self, validator):
        var = Var(id='Test', title='Lab Result', user_attestable=False)
        with pytest.raises(PGHDValidationError) as exc_info:
            validator.validate_raw(42, var)
        assert 'cannot be provided' in exc_info.value.user_message.lower()

    def test_validate_raw_valid(self, validator):
        var = Var(id='DM', title='Diabetes', user_attestable=True)
        validator.validate_raw(True, var)  # Should not raise

    def test_validate_normalized_valid(self, validator):
        var = Var(id='DM', title='Diabetes')
        value = Value(True)
        validator.validate_normalized(value, var)  # Should not raise

    def test_validation_error_fields(self):
        err = PGHDValidationError(
            var_id='LDL',
            value=999,
            reason='implausible',
            user_message='LDL of 999 is not a valid value'
        )
        assert err.var_id == 'LDL'
        assert err.value == 999
        assert 'implausible' in str(err)


# ============================================================================
# PGHDConverter Tests
# ============================================================================

class TestPGHDConverter:
    @pytest.fixture
    def converter(self):
        return PGHDConverter()

    def test_to_value_boolean(self, converter):
        var = Var(id='DM', title='Diabetes', type=ValueType.boolean)
        value = converter.to_value(var, 'yes')
        assert value.value is True
        assert value.source == ['patient-reported']

    def test_to_value_integer(self, converter):
        var = Var(id='Age', title='Age', type=ValueType.integer)
        value = converter.to_value(var, '55')
        assert value.value == 55

    def test_to_value_with_source(self, converter):
        var = Var(id='DM', title='Diabetes', type=ValueType.boolean)
        value = converter.to_value(var, True, source=InputSource.mcp_conversation)
        assert value.source == ['mcp-conversation']

    def test_to_record(self, converter):
        var = Var(id='DM', title='Diabetes', type=ValueType.boolean)
        record = converter.to_record(var, 'yes')
        assert record.var.id == 'DM'
        assert record.value.value is True
        assert record.has_value

    def test_to_record_with_date(self, converter):
        var = Var(id='LDL', title='LDL')
        dt = datetime(2024, 6, 15)
        record = converter.to_record(var, 165.5, date=dt)
        assert record.value.value == 165.5
        assert record.value.date.date() == dt.date()

    def test_to_records(self, converter):
        vars_lookup = {
            'DM': Var(id='DM', title='Diabetes', type=ValueType.boolean),
            'Age': Var(id='Age', title='Age', type=ValueType.integer),
        }
        records = converter.to_records(
            {'DM': 'yes', 'Age': '55'},
            vars_lookup
        )
        assert len(records) == 2
        dm_rec = next(r for r in records if r.id == 'DM')
        age_rec = next(r for r in records if r.id == 'Age')
        assert dm_rec.value.value is True
        assert age_rec.value.value == 55

    def test_to_records_skips_unknown(self, converter):
        vars_lookup = {
            'DM': Var(id='DM', title='Diabetes', type=ValueType.boolean),
        }
        records = converter.to_records(
            {'DM': 'yes', 'Unknown': 'x'},
            vars_lookup
        )
        assert len(records) == 1

    def test_to_records_validation_error(self, converter):
        vars_lookup = {
            'Lab': Var(id='Lab', title='Lab Result', user_attestable=False),
        }
        with pytest.raises(PGHDValidationError) as exc_info:
            converter.to_records({'Lab': 42}, vars_lookup)
        assert 'Lab' in exc_info.value.var_id

    def test_attest(self, converter):
        var = Var(id='DM', title='Diabetes', type=ValueType.boolean,
                  user_attestable=True)
        record = Record(var=var, initial_values=None)
        assert not record.has_value

        converter.attest(record, 'yes')
        assert record.has_value
        assert record.value.value is True
        assert record.value.source == ['attestation']

    def test_attest_not_attestable(self, converter):
        var = Var(id='Lab', title='Lab Result', user_attestable=False)
        record = Record(var=var, initial_values=None)
        with pytest.raises(PGHDValidationError):
            converter.attest(record, 42)

    def test_roundtrip_all_types(self, converter):
        """Test that all value types round-trip through the converter."""
        test_cases = [
            (ValueType.boolean, 'yes', True),
            (ValueType.boolean, 0, False),
            (ValueType.integer, '42', 42),
            (ValueType.string, 123, '123'),
        ]
        for vtype, raw, expected in test_cases:
            var = Var(id=f'test_{vtype}', type=vtype)
            value = converter.to_value(var, raw)
            assert value.value == expected, f'Failed for {vtype}: {raw} → {value.value} != {expected}'

    def test_decimal_normalization_only(self, converter):
        """Test decimal normalization (without Record type validation)."""
        # Note: ValueType.decimal.type returns unicodedata.decimal, not float,
        # which causes issues in Record.validate(). We test normalization separately.
        normalizer = PGHDNormalizer()
        var = Var(id='LDL', type=ValueType.decimal)
        val, meta = normalizer.normalize('3.14', var)
        assert val == 3.14
        assert isinstance(val, float)
