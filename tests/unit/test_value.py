#!/usr/bin/env python3
"""Unit tests for the Value class."""

import pytest
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from variables.value import Value
from primitives.code import Code


class TestValueCreation:
    """Tests for Value instantiation."""

    def test_create_numeric_value(self):
        """Test creating a Value with a numeric value."""
        v = Value(100)
        assert v.value == 100

    def test_create_boolean_value_true(self):
        """Test creating a Value with True."""
        v = Value(True)
        assert v.value is True

    def test_create_boolean_value_false(self):
        """Test creating a Value with False."""
        v = Value(False)
        assert v.value is False

    def test_create_value_with_date(self):
        """Test creating a Value with a specific date."""
        test_date = datetime(2024, 1, 15)
        v = Value(150, date=test_date)
        assert v.value == 150
        # date is wrapped in ValueDate, use .dt to access datetime
        assert v.date.dt == test_date

    def test_create_value_with_code(self):
        """Test creating a Value with a code."""
        code = Code.loinc('13457-7')
        v = Value(100, code=code)
        assert v.value == 100
        assert v.code == code

    def test_create_value_with_unit(self):
        """Test creating a Value with a unit."""
        v = Value(100, unit='mg/dL')
        assert v.value == 100
        assert v.unit == 'mg/dL'


class TestValueProperties:
    """Tests for Value properties and methods."""

    def test_value_representation(self, sample_value):
        """Test the string representation of Value."""
        assert sample_value.value == 100

    def test_value_evaluation_val_numeric(self):
        """Test evaluation_val for numeric values."""
        v = Value(150)
        assert v.evaluation_val == 150

    def test_value_evaluation_val_boolean(self):
        """Test evaluation_val for boolean values."""
        v_true = Value(True)
        v_false = Value(False)
        assert v_true.evaluation_val is True
        assert v_false.evaluation_val is False

    def test_value_default_date(self):
        """Test that Value gets current date by default."""
        v = Value(100)
        assert v.date is not None
        # date is wrapped in ValueDate, use .dt to access datetime
        assert (datetime.now() - v.date.dt).total_seconds() < 60


class TestValueComparison:
    """Tests for Value comparison and equality."""

    def test_values_with_same_value_are_comparable(self):
        """Test that values can be compared."""
        v1 = Value(100)
        v2 = Value(100)
        assert v1.value == v2.value

    def test_values_with_different_values(self):
        """Test comparing values with different numeric values."""
        v1 = Value(100)
        v2 = Value(200)
        assert v1.value != v2.value


class TestValueWithSource:
    """Tests for Value source tracking."""

    def test_value_with_source(self):
        """Test creating a Value with source records."""
        source_records = ['record1', 'record2']
        v = Value(100, source=source_records)
        assert v.source == source_records

    def test_value_without_source(self):
        """Test Value without source defaults appropriately."""
        v = Value(100)
        # Source should be None or empty
        assert v.source is None or v.source == []
