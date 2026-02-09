"""Tests for Code hierarchy (parent_code and is_descendant_of)."""

import pytest
from concordcore.primitives.code import Code


class TestCodeHierarchy:
    """Tests for Code.parent_code and Code.is_descendant_of()."""

    def test_code_without_parent(self):
        """Code without parent_code defaults to None."""
        code = Code.loinc('13457-7', 'LDL')
        assert code.parent_code is None

    def test_code_with_parent(self):
        """Code can have a parent_code."""
        parent = Code.snomed('73211009', 'Diabetes mellitus')
        child = Code.snomed('44054006', 'Type 2 diabetes', parent_code=parent)
        assert child.parent_code == parent

    def test_is_descendant_of_direct_parent(self):
        """is_descendant_of returns True for direct parent."""
        parent = Code.snomed('73211009', 'Diabetes mellitus')
        child = Code.snomed('44054006', 'Type 2 diabetes', parent_code=parent)
        assert child.is_descendant_of(parent) is True

    def test_is_descendant_of_grandparent(self):
        """is_descendant_of returns True for grandparent."""
        grandparent = Code.snomed('64572001', 'Disease')
        parent = Code.snomed('73211009', 'Diabetes mellitus', parent_code=grandparent)
        child = Code.snomed('44054006', 'Type 2 diabetes', parent_code=parent)
        assert child.is_descendant_of(grandparent) is True

    def test_is_descendant_of_unrelated(self):
        """is_descendant_of returns False for unrelated code."""
        unrelated = Code.snomed('38341003', 'Hypertension')
        parent = Code.snomed('73211009', 'Diabetes mellitus')
        child = Code.snomed('44054006', 'Type 2 diabetes', parent_code=parent)
        assert child.is_descendant_of(unrelated) is False

    def test_is_descendant_of_self(self):
        """is_descendant_of returns False for self (not a descendant of itself)."""
        code = Code.snomed('44054006', 'Type 2 diabetes')
        assert code.is_descendant_of(code) is False

    def test_is_descendant_of_no_parent(self):
        """is_descendant_of returns False when code has no parent."""
        ancestor = Code.snomed('73211009', 'Diabetes mellitus')
        code = Code.snomed('44054006', 'Type 2 diabetes')
        assert code.is_descendant_of(ancestor) is False

    def test_backward_compatible_creation(self):
        """Existing code without parent_code still works."""
        code = Code('13457-7', 'http://loinc.org', 'LDL')
        assert code.code == '13457-7'
        assert code.system == 'http://loinc.org'
        assert code.display == 'LDL'
        assert code.parent_code is None

    def test_equality_ignores_parent(self):
        """Two codes are equal if system|code match, regardless of parent."""
        parent = Code.snomed('73211009')
        code1 = Code.snomed('44054006', parent_code=parent)
        code2 = Code.snomed('44054006')
        assert code1 == code2

    def test_frozen_with_parent(self):
        """Code with parent_code is still frozen."""
        parent = Code.snomed('73211009')
        child = Code.snomed('44054006', parent_code=parent)
        with pytest.raises(AttributeError):
            child.parent_code = None
