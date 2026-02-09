#!/usr/bin/env python3
"""Unit tests for the CPG module."""

import pytest
from concordcore.core.cpg import CPG
from concordcore.core.security import SecurityError


class TestCPGCreation:
    """Tests for CPG instantiation."""

    def test_create_cpg_from_document(self, minimal_cpg_dict):
        """Test creating a CPG from a document dictionary."""
        cpg = CPG.from_document(minimal_cpg_dict)
        assert cpg.identifier == 'test_cpg'
        assert cpg.title == 'Test CPG'

    def test_cpg_has_variables(self, minimal_cpg):
        """Test that CPG has variables."""
        assert minimal_cpg.variables is not None
        assert len(minimal_cpg.variables) > 0

    def test_cpg_has_eligibility_variables(self, minimal_cpg):
        """Test that CPG has eligibility variables."""
        assert minimal_cpg.eligibility_variables is not None
        assert len(minimal_cpg.eligibility_variables) > 0

    def test_cpg_has_assessment_variables(self, minimal_cpg):
        """Test that CPG has assessment variables."""
        assert minimal_cpg.assessment_variables is not None
        assert len(minimal_cpg.assessment_variables) > 0

    def test_cpg_has_recommendation_variables(self, minimal_cpg):
        """Test that CPG has recommendation variables."""
        assert minimal_cpg.recommendation_variables is not None
        assert len(minimal_cpg.recommendation_variables) > 0


class TestCPGFromFilePath:
    """Tests for CPG loading from file path."""

    def test_load_cpg_from_valid_path(self, cholesterol_cpg):
        """Test loading a CPG from a valid YAML file."""
        assert cholesterol_cpg is not None
        assert cholesterol_cpg.identifier is not None

    def test_load_cpg_invalid_path_raises_error(self):
        """Test that loading from invalid path raises error."""
        with pytest.raises((FileNotFoundError, SecurityError)):
            CPG.from_document_path('/nonexistent/path/cpg.yaml')


class TestCPGSecurity:
    """Tests for CPG security features."""

    def test_path_traversal_rejected(self, tmp_path):
        """Test that path traversal attempts are rejected."""
        # Create a temp file to try to access via traversal
        malicious_path = str(tmp_path / '..' / '..' / 'etc' / 'passwd.yaml')
        with pytest.raises(SecurityError):
            CPG.from_document_path(malicious_path)

    def test_non_yaml_file_rejected(self, tmp_path):
        """Test that non-YAML files are rejected."""
        # Create a .py file
        py_file = tmp_path / 'malicious.py'
        py_file.write_text('print("malicious")')

        with pytest.raises(SecurityError):
            CPG.from_document_path(str(py_file))


class TestCPGVariableMethods:
    """Tests for CPG variable accessor properties."""

    def test_non_optional_variables(self, minimal_cpg):
        """Test getting non-optional (required) variables."""
        result = minimal_cpg.non_optional_variables  # cached_property, not method
        # Result should be list or None
        assert result is None or isinstance(result, list)

    def test_optional_variables(self, minimal_cpg):
        """Test getting optional variables."""
        result = minimal_cpg.optional_variables  # cached_property, not method
        # Result should be list or None
        assert result is None or isinstance(result, list)

    def test_attestable_variables(self, minimal_cpg):
        """Test getting attestable variables."""
        result = minimal_cpg.attestable_variables  # cached_property, not method
        # Result should be list or None
        assert result is None or isinstance(result, list)


class TestCPGGetVar:
    """Tests for CPG.get_var static method."""

    def test_get_var_finds_existing(self, minimal_cpg):
        """Test getting an existing variable."""
        var = CPG.get_var('Age', minimal_cpg.variables)
        assert var is not None
        assert var.id == 'Age'

    def test_get_var_returns_none_for_missing(self, minimal_cpg):
        """Test getting a non-existent variable returns None."""
        var = CPG.get_var('NonExistent', minimal_cpg.variables)
        assert var is None


class TestCPGValidation:
    """Tests for CPG validation."""

    def test_valid_cpg_passes_validation(self, minimal_cpg):
        """Test that a valid CPG passes validation."""
        result = minimal_cpg.validate()
        assert result is True

    def test_cpg_without_assessments_fails_validation(self, minimal_cpg_dict):
        """Test that CPG without assessments fails validation."""
        minimal_cpg_dict['assessments'] = []
        cpg = CPG.from_document(minimal_cpg_dict)
        with pytest.raises(ExceptionGroup):
            cpg.validate()

    def test_cpg_without_recommendations_fails_validation(self, minimal_cpg_dict):
        """Test that CPG without recommendations fails validation."""
        minimal_cpg_dict['recommendations'] = []
        cpg = CPG.from_document(minimal_cpg_dict)
        with pytest.raises(ExceptionGroup):
            cpg.validate()


class TestCPGContext:
    """Tests for CPG context methods."""

    def test_assessment_context(self, minimal_cpg):
        """Test getting assessment context."""
        context = minimal_cpg.assessment_context()
        # Should return list or None
        assert context is None or isinstance(context, list)

    def test_recommendation_context(self, minimal_cpg):
        """Test getting recommendation context."""
        context = minimal_cpg.recommendation_context()
        # Should return list or None
        assert context is None or isinstance(context, list)

    def test_eligibility_context(self, minimal_cpg):
        """Test getting eligibility context."""
        context = minimal_cpg.eligibility_context()
        # Should return list or None
        assert context is None or isinstance(context, list)


class TestCPGCodeHelpers:
    """Tests for CPG code helper methods."""

    def test_lab_test_codes(self, cholesterol_cpg):
        """Test getting LOINC codes for lab tests."""
        if cholesterol_cpg is None:
            pytest.skip("Cholesterol CPG not available")
        codes = cholesterol_cpg.lab_test_codes()
        assert codes is not None
        # Should contain LOINC codes
        for code in codes:
            assert 'loinc' in code.lower()

    def test_conditions_codes(self, cholesterol_cpg):
        """Test getting SNOMED codes for conditions."""
        if cholesterol_cpg is None:
            pytest.skip("Cholesterol CPG not available")
        codes = cholesterol_cpg.conditions_codes()
        # May be empty or contain SNOMED codes
        if codes:
            for code in codes:
                assert 'snomed' in code.lower()

    def test_medication_codes(self, cholesterol_cpg):
        """Test getting RxNorm codes for medications."""
        if cholesterol_cpg is None:
            pytest.skip("Cholesterol CPG not available")
        codes = cholesterol_cpg.medication_codes()
        # May be empty or contain RxNorm codes
        if codes:
            for code in codes:
                assert 'rxnorm' in code.lower()


class TestCPGAsDict:
    """Tests for CPG.as_dict method."""

    def test_as_dict_contains_title(self, minimal_cpg):
        """Test that as_dict contains CPG title."""
        d = minimal_cpg.as_dict()
        assert 'cpg_title' in d
        assert d['cpg_title'] == minimal_cpg.title

    def test_as_dict_contains_publisher(self, minimal_cpg):
        """Test that as_dict contains publisher."""
        d = minimal_cpg.as_dict()
        assert 'cpg_publisher' in d
