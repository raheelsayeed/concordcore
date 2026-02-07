#!/usr/bin/env python3
"""Tests for reproducibility verification."""

import pytest
from datetime import date

from core.reproducibility import (
    ReproducibilityVerifier,
    VerificationStatus,
    VerificationResult,
    compute_output_hash,
    verify_evaluation,
)
from core.cpg import CPG
from core.concord import Concord, PipelineResult
from core.healthcontext import HealthContext
from primitives.types import Persona
from variables.value import Value
from variables.record import Record
from variables.var import Var


class TestComputeOutputHash:
    """Tests for compute_output_hash function."""

    def test_same_result_same_hash(self, minimal_cpg, minimal_healthcontext):
        """Same PipelineResult should produce same hash."""
        concord = Concord(cpg=minimal_cpg, healthcontext=minimal_healthcontext, ignore_eligibility=True)
        result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        hash1 = compute_output_hash(result)
        hash2 = compute_output_hash(result)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_hash_is_valid_sha256(self, minimal_cpg, minimal_healthcontext):
        """Hash should be valid SHA-256 hex string."""
        concord = Concord(cpg=minimal_cpg, healthcontext=minimal_healthcontext, ignore_eligibility=True)
        result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        hash_value = compute_output_hash(result)

        # Should be 64 hex characters
        assert len(hash_value) == 64
        # Should only contain hex characters
        assert all(c in '0123456789abcdef' for c in hash_value)


class TestReproducibilityVerifier:
    """Tests for ReproducibilityVerifier class."""

    def test_create_verification_record(self, minimal_cpg, minimal_healthcontext):
        """Should create a valid verification record."""
        concord = Concord(cpg=minimal_cpg, healthcontext=minimal_healthcontext, ignore_eligibility=True)
        result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        verifier = ReproducibilityVerifier(minimal_cpg)
        record = verifier.create_verification_record(result, minimal_healthcontext)

        assert "cpg_id" in record
        assert "cpg_version" in record
        assert "input_hash" in record
        assert "output_hash" in record
        assert record["cpg_id"] == minimal_cpg.identifier

    def test_verify_detects_input_hash_mismatch(self, minimal_cpg, minimal_healthcontext):
        """Verification should fail for different input."""
        concord = Concord(cpg=minimal_cpg, healthcontext=minimal_healthcontext, ignore_eligibility=True)
        result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        verifier = ReproducibilityVerifier(minimal_cpg)
        record = verifier.create_verification_record(result, minimal_healthcontext)

        # Create different health context
        var = minimal_cpg.variables[0] if minimal_cpg.variables else Var(id="test", title="Test")
        different_context = HealthContext(
            records=[Record(var=var, initial_values=[Value(value=999)])],
            persona=Persona.patient
        )

        verification = verifier.verify(record, different_context, skip_eligibility=True)

        assert verification.status == VerificationStatus.INPUT_HASH_MISMATCH

    def test_verify_detects_cpg_version_change(self, minimal_cpg, minimal_healthcontext):
        """Verification should detect CPG version change."""
        concord = Concord(cpg=minimal_cpg, healthcontext=minimal_healthcontext, ignore_eligibility=True)
        result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        verifier = ReproducibilityVerifier(minimal_cpg)
        record = verifier.create_verification_record(result, minimal_healthcontext)

        # Modify the original record to have a different version
        record["cpg_version"] = "0.0.1"

        verification = verifier.verify(record, minimal_healthcontext, skip_eligibility=True)

        assert verification.status == VerificationStatus.CPG_VERSION_CHANGED

    def test_verification_result_to_dict(self, minimal_cpg, minimal_healthcontext):
        """VerificationResult should convert to dict correctly."""
        concord = Concord(cpg=minimal_cpg, healthcontext=minimal_healthcontext, ignore_eligibility=True)
        result = concord.evaluate(skip_eligibility=True, ignore_attestations=True)

        verifier = ReproducibilityVerifier(minimal_cpg)
        record = verifier.create_verification_record(result, minimal_healthcontext)

        # Test with version mismatch (guaranteed to trigger specific status)
        record["cpg_version"] = "0.0.1"
        verification = verifier.verify(record, minimal_healthcontext, skip_eligibility=True)

        result_dict = verification.to_dict()

        assert "status" in result_dict
        assert "verified" in result_dict
        assert "input_hashes_match" in result_dict
        assert "output_hashes_match" in result_dict
        assert result_dict["cpg_versions_match"] == False


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_status_values(self):
        """Verify all expected status values exist."""
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.MISMATCH.value == "mismatch"
        assert VerificationStatus.CPG_VERSION_CHANGED.value == "cpg_version_changed"
        assert VerificationStatus.INPUT_HASH_MISMATCH.value == "input_hash_mismatch"
        assert VerificationStatus.ERROR.value == "error"


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_to_dict(self):
        """VerificationResult should serialize correctly."""
        result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            original_input_hash="abc123",
            recomputed_input_hash="abc123",
            original_output_hash="def456",
            recomputed_output_hash="def456",
            cpg_version_original="1.0.0",
            cpg_version_current="1.0.0",
            verification_timestamp="2024-01-01T00:00:00Z",
            details="Test verification"
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "verified"
        assert result_dict["verified"] == True
        assert result_dict["input_hashes_match"] == True
        assert result_dict["output_hashes_match"] == True
        assert result_dict["cpg_versions_match"] == True

    def test_to_dict_with_mismatch(self):
        """VerificationResult should correctly show mismatches."""
        result = VerificationResult(
            status=VerificationStatus.MISMATCH,
            original_input_hash="abc123",
            recomputed_input_hash="abc123",
            original_output_hash="def456",
            recomputed_output_hash="ghi789",
            cpg_version_original="1.0.0",
            cpg_version_current="1.0.0",
            verification_timestamp="2024-01-01T00:00:00Z",
            details="Output mismatch"
        )

        result_dict = result.to_dict()

        assert result_dict["verified"] == False
        assert result_dict["input_hashes_match"] == True
        assert result_dict["output_hashes_match"] == False
