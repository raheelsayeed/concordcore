#!/usr/bin/env python3
"""Reproducibility verification for CPG evaluations.

This module provides cryptographic verification that CPG evaluations are
deterministic and reproducible. Same input + same CPG version = identical output.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import logging
from typing import Any

from .concord import Concord, PipelineResult, EvaluationMetadata
from .cpg import CPG
from .healthcontext import HealthContext

log = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of reproducibility verification."""
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    CPG_VERSION_CHANGED = "cpg_version_changed"
    INPUT_HASH_MISMATCH = "input_hash_mismatch"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Result of a reproducibility verification.

    Attributes:
        status: Verification status
        original_input_hash: Hash from original evaluation
        recomputed_input_hash: Hash from re-evaluation
        original_output_hash: Hash from original evaluation output
        recomputed_output_hash: Hash from re-evaluation output
        cpg_version_original: CPG version from original evaluation
        cpg_version_current: Current CPG version
        verification_timestamp: When verification was performed
        details: Additional details or error message
    """
    status: VerificationStatus
    original_input_hash: str
    recomputed_input_hash: str
    original_output_hash: str | None
    recomputed_output_hash: str | None
    cpg_version_original: str
    cpg_version_current: str
    verification_timestamp: str
    details: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "verified": self.status == VerificationStatus.VERIFIED,
            "original_input_hash": self.original_input_hash,
            "recomputed_input_hash": self.recomputed_input_hash,
            "input_hashes_match": self.original_input_hash == self.recomputed_input_hash,
            "original_output_hash": self.original_output_hash,
            "recomputed_output_hash": self.recomputed_output_hash,
            "output_hashes_match": self.original_output_hash == self.recomputed_output_hash,
            "cpg_version_original": self.cpg_version_original,
            "cpg_version_current": self.cpg_version_current,
            "cpg_versions_match": self.cpg_version_original == self.cpg_version_current,
            "verification_timestamp": self.verification_timestamp,
            "details": self.details,
        }


def compute_output_hash(result: PipelineResult) -> str:
    """Compute SHA-256 hash of evaluation output.

    Args:
        result: PipelineResult from evaluation

    Returns:
        Hex string of the hash
    """
    output_data = {
        "is_complete": result.is_complete,
        "is_eligible": result.is_eligible,
        "is_executable": result.is_executable,
    }

    # Add assessment results
    if result.assessment:
        assessment_data = []
        for assessed in result.assessment.assessments:
            assessment_data.append({
                "id": assessed.id,
                "evaluation_result": assessed.evaluation_result.name if assessed.evaluation_result else None,
            })
        assessment_data.sort(key=lambda x: x["id"])
        output_data["assessments"] = assessment_data

    # Add recommendation results
    if result.recommendations:
        rec_data = []
        for rec in result.recommendations.recommendations:
            rec_data.append({
                "id": rec.recommendation.id if rec.recommendation else None,
                "applies": rec.applies,
            })
        rec_data.sort(key=lambda x: x["id"] or "")
        output_data["recommendations"] = rec_data

    json_str = json.dumps(output_data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


class ReproducibilityVerifier:
    """Verifies that CPG evaluations are reproducible.

    This class provides cryptographic verification that the same input data
    with the same CPG version produces identical output.

    Example:
        ```python
        # Original evaluation
        concord = Concord(cpg=cpg, healthcontext=context)
        result = concord.evaluate()

        # Store the verification data
        verification_data = verifier.create_verification_record(result, context)

        # Later, verify reproducibility
        verifier = ReproducibilityVerifier(cpg)
        verification = verifier.verify(verification_data, context)

        if verification.status == VerificationStatus.VERIFIED:
            print("Evaluation is reproducible!")
        ```
    """

    def __init__(self, cpg: CPG):
        """Initialize verifier with a CPG.

        Args:
            cpg: The CPG to use for verification
        """
        self.cpg = cpg

    def create_verification_record(
        self,
        result: PipelineResult,
        healthcontext: HealthContext
    ) -> dict:
        """Create a verification record from an evaluation result.

        This record can be stored and later used to verify reproducibility.

        Args:
            result: PipelineResult from evaluation
            healthcontext: HealthContext used in evaluation

        Returns:
            Dictionary containing verification data
        """
        output_hash = compute_output_hash(result)

        return {
            "cpg_id": self.cpg.identifier,
            "cpg_version": self.cpg.version or "1.0.0",
            "input_hash": result.metadata.input_data_hash if result.metadata else None,
            "output_hash": output_hash,
            "evaluation_timestamp": result.metadata.evaluation_timestamp if result.metadata else None,
            "is_complete": result.is_complete,
        }

    def verify(
        self,
        original_record: dict,
        healthcontext: HealthContext,
        skip_eligibility: bool = False,
        ignore_attestations: bool = True
    ) -> VerificationResult:
        """Verify that an evaluation is reproducible.

        Re-runs the evaluation with the provided health context and compares
        the results to the original record.

        Args:
            original_record: Verification record from create_verification_record
            healthcontext: HealthContext to re-evaluate
            skip_eligibility: Whether to skip eligibility check
            ignore_attestations: Whether to ignore attestation requirements

        Returns:
            VerificationResult with verification status
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        original_input_hash = original_record.get("input_hash", "")
        original_output_hash = original_record.get("output_hash")
        original_cpg_version = original_record.get("cpg_version", "1.0.0")
        current_cpg_version = self.cpg.version or "1.0.0"

        try:
            # Re-run the evaluation
            concord = Concord(cpg=self.cpg, healthcontext=healthcontext)
            result = concord.evaluate(
                skip_eligibility=skip_eligibility,
                ignore_attestations=ignore_attestations
            )

            recomputed_input_hash = result.metadata.input_data_hash if result.metadata else ""
            recomputed_output_hash = compute_output_hash(result)

            # Check CPG version
            if original_cpg_version != current_cpg_version:
                return VerificationResult(
                    status=VerificationStatus.CPG_VERSION_CHANGED,
                    original_input_hash=original_input_hash,
                    recomputed_input_hash=recomputed_input_hash,
                    original_output_hash=original_output_hash,
                    recomputed_output_hash=recomputed_output_hash,
                    cpg_version_original=original_cpg_version,
                    cpg_version_current=current_cpg_version,
                    verification_timestamp=timestamp,
                    details=f"CPG version changed from {original_cpg_version} to {current_cpg_version}"
                )

            # Check input hash
            if original_input_hash != recomputed_input_hash:
                return VerificationResult(
                    status=VerificationStatus.INPUT_HASH_MISMATCH,
                    original_input_hash=original_input_hash,
                    recomputed_input_hash=recomputed_input_hash,
                    original_output_hash=original_output_hash,
                    recomputed_output_hash=recomputed_output_hash,
                    cpg_version_original=original_cpg_version,
                    cpg_version_current=current_cpg_version,
                    verification_timestamp=timestamp,
                    details="Input data has changed since original evaluation"
                )

            # Check output hash
            if original_output_hash != recomputed_output_hash:
                return VerificationResult(
                    status=VerificationStatus.MISMATCH,
                    original_input_hash=original_input_hash,
                    recomputed_input_hash=recomputed_input_hash,
                    original_output_hash=original_output_hash,
                    recomputed_output_hash=recomputed_output_hash,
                    cpg_version_original=original_cpg_version,
                    cpg_version_current=current_cpg_version,
                    verification_timestamp=timestamp,
                    details="Output mismatch - evaluation is not reproducible"
                )

            # All checks passed
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                original_input_hash=original_input_hash,
                recomputed_input_hash=recomputed_input_hash,
                original_output_hash=original_output_hash,
                recomputed_output_hash=recomputed_output_hash,
                cpg_version_original=original_cpg_version,
                cpg_version_current=current_cpg_version,
                verification_timestamp=timestamp,
                details="Evaluation is reproducible - all hashes match"
            )

        except Exception as e:
            log.error(f"Verification failed with error: {e}")
            return VerificationResult(
                status=VerificationStatus.ERROR,
                original_input_hash=original_input_hash,
                recomputed_input_hash="",
                original_output_hash=original_output_hash,
                recomputed_output_hash=None,
                cpg_version_original=original_cpg_version,
                cpg_version_current=current_cpg_version,
                verification_timestamp=timestamp,
                details=f"Verification error: {str(e)}"
            )


def verify_evaluation(
    cpg: CPG,
    healthcontext: HealthContext,
    original_record: dict
) -> VerificationResult:
    """Convenience function to verify an evaluation.

    Args:
        cpg: CPG to use for verification
        healthcontext: HealthContext to re-evaluate
        original_record: Verification record from previous evaluation

    Returns:
        VerificationResult with verification status
    """
    verifier = ReproducibilityVerifier(cpg)
    return verifier.verify(original_record, healthcontext)
