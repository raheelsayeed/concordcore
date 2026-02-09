#!/usr/bin/env python3
"""Main orchestrator for CPG evaluation pipeline.

This module provides the Concord class which manages the complete
CPG evaluation workflow: eligibility -> sufficiency -> assessment -> recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from functools import cached_property
import hashlib
import json
import logging
from typing import NamedTuple

from .cpg import CPG
from .eligibility import EligibilityResult, EligibilityEvaluator, EligibilityEvaluatorProtocol
from .assessment import AssessmentEvaluatorProtocol, AssessmentResult, AssessmentEvaluator
from .recommendation import EvaluatedRecommendation, RecommendationResult
from .sufficiency import SufficiencyResult, SufficiencyEvaluator, SufficiencyEvaluatorProtocol
from .evaluation import EvaluatedRecord, EvaluationContext
from .record_index import RecordIndex
from .errors import NeedAttestationError, CPGDefinitionError, PipelineError
from concordcore.variables.value import Value
from .healthcontext import HealthContext

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EvaluationMetadata:
    """Metadata for tracking evaluation provenance and reproducibility.

    Attributes:
        cpg_id: CPG identifier
        cpg_version: Version of the CPG used
        cpg_last_updated: Last update date of the CPG
        evaluation_timestamp: When the evaluation was performed
        input_data_hash: SHA-256 hash of input health data for reproducibility
    """
    cpg_id: str
    cpg_version: str
    cpg_last_updated: str | None
    evaluation_timestamp: str
    input_data_hash: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "cpg_id": self.cpg_id,
            "cpg_version": self.cpg_version,
            "cpg_last_updated": self.cpg_last_updated,
            "evaluation_timestamp": self.evaluation_timestamp,
            "input_data_hash": self.input_data_hash,
        }


class PipelineResult(NamedTuple):
    """Unified result from complete CPG evaluation pipeline.

    Contains results from all evaluation phases for easy access.

    Attributes:
        eligibility: Result from eligibility check (or None if skipped)
        sufficiency: Result from sufficiency check
        assessment: Result from assessment phase
        recommendations: Result from recommendations phase
        is_complete: True if all phases completed successfully
        errors: List of any errors encountered
        metadata: Evaluation metadata for reproducibility and auditing
    """
    eligibility: EligibilityResult | None
    sufficiency: SufficiencyResult | None
    assessment: AssessmentResult | None
    recommendations: RecommendationResult | None
    is_complete: bool
    errors: list[Exception]
    metadata: EvaluationMetadata | None = None

    @property
    def is_eligible(self) -> bool | None:
        """Whether patient is eligible for this CPG."""
        return self.eligibility.is_eligible if self.eligibility else None

    @property
    def is_executable(self) -> bool | None:
        """Whether data is sufficient to execute CPG."""
        return self.sufficiency.is_executable if self.sufficiency else None

    @property
    def applied_recommendations(self) -> list | None:
        """List of recommendations that apply to this patient."""
        return self.recommendations.applied if self.recommendations else None

@dataclass
class Concord:
    """Main orchestrator for Clinical Practice Guideline (CPG) evaluation.

    The Concord class manages the complete CPG evaluation pipeline, processing
    patient health data through four sequential phases:

    1. **Eligibility**: Determines if the CPG applies to the patient
    2. **Sufficiency**: Checks if health data is sufficient to execute the CPG
    3. **Assessment**: Evaluates health status based on CPG-defined criteria
    4. **Recommendations**: Generates personalized recommendations

    Each phase must complete successfully before the next can proceed. The class
    maintains state between phases and provides access to intermediate results.

    Example:
        ```python
        from concordcore.core.cpg_registry import get_registry
        from concordcore.core.concord import Concord

        cpg = get_registry().get('2019AccPrimaryPreventionASCVD')
        concord = Concord(cpg=cpg, healthcontext=patient_data)

        # Run evaluation pipeline
        eligibility = concord.eligibility()
        if eligibility.is_eligible:
            sufficiency = concord.sufficiency()
            if sufficiency.is_executable:
                assessment = concord.assess()
                recommendations = concord.recommendations()
        ```

    Attributes:
        cpg: The Clinical Practice Guideline definition to evaluate.
        healthcontext: Patient health data including records and persona.
        strict_validation: If True, enforces panel and plausible validators.
        ignore_eligibility: If True, skips eligibility check for assessment.
        until_year: Optional year to filter health data (for historical analysis).
    """

    cpg: CPG
    """The CPG definition to evaluate against patient data."""

    healthcontext: HealthContext
    """Patient health data including records, values, and persona."""

    strict_validation: bool = False
    """If True, validates panel relationships and plausible value ranges."""

    ignore_eligibility: bool = False
    """If True, allows assessment even if eligibility was not checked."""

    until_year: int | None = None
    """Optional: Only consider health data up to this year."""

    __eligibility_result: EligibilityResult | None = field(default=None)
    __assessment_result: AssessmentResult | None = field(default=None)
    __recommendation_result: RecommendationResult | None = field(default=None)
    __sufficiency_result: SufficiencyResult | None = field(default=None, init=False)

    @cached_property
    def until_date(self) -> date|None:
        return datetime(self.until_year, 12, 31).date() if self.until_year else None
    
    @property
    def records(self):
        """Patient data, from HealthContext"""
        return self.healthcontext.records

    @property
    def eligibility_result(self) -> EligibilityResult | None:
        """Result from eligibility evaluation."""
        return self.__eligibility_result

    @property
    def assessment_result(self) -> AssessmentResult | None:
        """Result from assessment evaluation."""
        return self.__assessment_result

    @property
    def recommendation_result(self) -> RecommendationResult | None:
        """Result from recommendation evaluation."""
        return self.__recommendation_result

    @property
    def sufficiency_evaluated_records(self):
        """Sufficiency evaluated records"""
        return self.sufficiency_result.context.evaluation_list

    @property
    def sufficiency_result(self):
        return self.__sufficiency_result

    def _compute_input_hash(self) -> str:
        """Compute SHA-256 hash of input health data for reproducibility.

        Returns:
            Hex string of the hash
        """
        data_repr = []
        for record in self.healthcontext.records:
            record_data = {
                "id": record.id,
                "values": [
                    {"value": str(v.value), "date": str(v.date) if v.date else None}
                    for v in (record.values or [])
                ]
            }
            data_repr.append(record_data)

        # Sort by record id for consistent hashing
        data_repr.sort(key=lambda x: x["id"])
        json_str = json.dumps(data_repr, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _create_metadata(self, input_data_hash: str = None) -> EvaluationMetadata:
        """Create evaluation metadata for tracking and reproducibility."""
        return EvaluationMetadata(
            cpg_id=self.cpg.identifier,
            cpg_version=self.cpg.version or "1.0.0",
            cpg_last_updated=self.cpg.last_updated,
            evaluation_timestamp=datetime.utcnow().isoformat() + "Z",
            input_data_hash=input_data_hash or self._compute_input_hash(),
        )

    def eligibility(self,
                    evaluator: EligibilityEvaluatorProtocol = None,
                    context: EvaluationContext = None) -> EligibilityResult:
        """Evaluate patient eligibility for the CPG.

        Checks if the patient meets all inclusion criteria and does not meet
        any exclusion criteria defined in the CPG. This is typically the first
        step in the evaluation pipeline.

        Args:
            evaluator: Optional custom eligibility evaluator. If not provided,
                uses the default EligibilityEvaluator.
            context: Optional evaluation context for tracking results.

        Returns:
            EligibilityResult containing eligibility status and evaluated criteria.

        Raises:
            Exception: If the CPG has no eligibility criteria defined.
        """
        if not self.cpg.eligibility_variables:
            raise CPGDefinitionError('No eligibility criteria defined for this CPG')
        
        eligibility_eval = evaluator or EligibilityEvaluator(self.cpg.eligibility_variables)
        # evalute eligibility
        self.__eligibility_result = eligibility_eval.evaluate(self.healthcontext, context=context)

        return self.__eligibility_result


    def sufficiency(self,
                    sufficiency_evaluator: SufficiencyEvaluatorProtocol = None,
                    context: EvaluationContext = None) -> SufficiencyResult:
        """Evaluate data sufficiency for CPG execution.

        Checks if the patient's health data contains all required variables
        for executing the CPG. Variables are classified as:
        - Sufficient: Required variable with value present
        - Insufficient: Required variable without value (blocks execution)
        - SufficientWithUserAttestation: Missing but user can provide
        - Optional: Not required for CPG execution

        Args:
            sufficiency_evaluator: Optional custom sufficiency evaluator.
            context: Optional evaluation context for tracking results.

        Returns:
            SufficiencyResult containing sufficiency status and variable classifications.

        Raises:
            Exception: If the CPG has no variables defined.
        """
        if not self.cpg.variables:
            raise CPGDefinitionError('No variables defined for this CPG')
    
        # initialize an evaluator 
        sufficiency_eval = sufficiency_evaluator or SufficiencyEvaluator('se', cpg_variables=self.cpg.variables)
        # evaluate sufficiency
        self.__sufficiency_result = sufficiency_eval.evaluate(
                    self.healthcontext, 
                    context, 
                    strict=self.strict_validation
                )
        
        log.debug(f"Evaluation done with strict={self.strict_validation} policy")
        log.info(f'Validation policy={self.strict_validation}')

        return self.__sufficiency_result

    def assess(self,
                assessment_evaluator: AssessmentEvaluatorProtocol = None,
                ignore_sufficiency: bool = False,
                ignore_required_variable_attestations: bool = False) -> AssessmentResult:
        """Evaluate patient health status using CPG-defined assessments.

        Evaluates all assessment variables defined in the CPG using the
        patient's health data. Assessments can use expressions (e.g., '$LDL > 130')
        or custom functions for complex calculations (e.g., ASCVD risk score).

        Prerequisites:
        - Eligibility must be checked (unless ignore_eligibility=True)
        - Sufficiency must be checked
        - Required attestations must be collected (unless ignored)

        Args:
            assessment_evaluator: Optional custom assessment evaluator.
            ignore_sufficiency: If True, proceeds even with insufficient data.
            ignore_required_variable_attestations: If True, proceeds without
                collecting user attestations for missing required variables.

        Returns:
            AssessmentResult containing evaluated assessment records.

        Raises:
            Exception: If eligibility or sufficiency checks not completed.
            NeedAttestationError: If user attestation is required.
            ExceptionGroup: If data is insufficient for CPG execution.
        """
        errs = []

        if not self.ignore_eligibility:
            if self.__eligibility_result is None:
                errs.append(PipelineError('Eligibility evaluation must be completed before risk assessment'))

            if self.__eligibility_result.is_eligible is False:
                errs.append(PipelineError('Eligibility criteria not met, cannot execute CPG'))

        if self.__sufficiency_result.result is None:
            errs.append(PipelineError(f'Sufficiency not evaluated for CPG={self.cpg.identifier}'))

        if self.__sufficiency_result.is_executable is False:
            suff_errors = [ev.error for ev in self.__sufficiency_result.insufficient_variables]
            errs.append(ExceptionGroup(f'Userdata is insufficient to execute CPG={self.cpg.identifier}', suff_errors))

        log.debug(f'Sufficiency check complete; IS_Executable={self.__sufficiency_result.is_executable}')
        if errs:
            self.__assessment_result = None
            exe = ExceptionGroup('Cannot Execute CPG', errs)
            if not ignore_sufficiency:
                raise exe
            else:
                log.error(exe)


        # --> check if they need Input
        need_attestation = self.__sufficiency_result.attestation_variables
        log.info(f'Attestation needed for {len(need_attestation)} variables')
        if need_attestation:
            for n in need_attestation:
                log.error(f'Need Input for record={n.record.id}')
            e = NeedAttestationError(need_attestation)
            if ignore_required_variable_attestations:
                log.warning(e) 
            else:
                raise e
        else:
            log.debug('UserAttestation/PGHD Not Needed, proceeding..to evaluation')

        

        evaluator = assessment_evaluator or AssessmentEvaluator()

        self.__assessment_result = evaluator.assess(
            assessment_variables= self.cpg.assessment_variables,
            evaluated_records= self.sufficiency_evaluated_records,
            persona= self.healthcontext.persona,
            functions_module= self.cpg.functions_module,
        )



        return self.__assessment_result


    def recommendations(self, context: EvaluationContext = None) -> RecommendationResult:
        """Generate personalized recommendations based on assessments.

        Evaluates each recommendation variable defined in the CPG. Recommendations
        are based on assessment results and can be:
        - Display-type: Always shown (informational content)
        - Expression-based: Shown when expression evaluates to True

        Recommendations include evidence-based classifications:
        - Class of Recommendation (I, IIa, IIb, III)
        - Level of Evidence (A, B-R, B-NR, C-LD, C-EO)
        - USPSTF Grade (A, B, C, D, I)

        Args:
            context: Optional evaluation context for tracking results.

        Returns:
            RecommendationResult with evaluated recommendations sorted by applicability.

        Raises:
            Exception: If assessment has not been completed.
        """
        context = context or EvaluationContext()
        evaluated_recommendations = []
        if self.assessment_result is None:
            raise PipelineError('Assessment must be completed before calling recommendations()')

        # Build indexes once for O(1) lookup during all recommendation evaluations
        assessment_list = self.assessment_result.assessments
        sufficiency_list = self.sufficiency_evaluated_records

        assessment_index = {ea.id: ea for ea in assessment_list}
        record_index = {er.id: er for er in sufficiency_list}

        for recommendation in self.cpg.recommendation_variables:
            eval_rec = EvaluatedRecommendation(recommendation=recommendation)
            try:
                eval_rec.evaluate(
                    assessment_list,
                    evaluated_records=sufficiency_list,
                    persona=self.healthcontext.persona,
                    assessment_index=assessment_index,
                    record_index=record_index
                )
            except Exception as e:
                eval_rec.error = e
                log.error(e)
            finally:
                log.debug(eval_rec)
                evaluated_recommendations.append(eval_rec)

        self.__recommendation_result = RecommendationResult(
            context=context,
            recommendations=sorted(evaluated_recommendations, key=lambda er: er.applies if er.applies else False, reverse=True)
        )
        return self.__recommendation_result

    
    @property
    def applied_recommendations(self) -> list | None:
        """Recommendations that apply to this patient."""
        if not self.__recommendation_result:
            return None
        return self.recommendation_result.applied

    def evaluate(self,
                 skip_eligibility: bool = False,
                 ignore_attestations: bool = False,
                 record_index: RecordIndex = None,
                 code_index: dict = None,
                 _input_data_hash: str = None) -> PipelineResult:
        """Run complete CPG evaluation pipeline.

        Convenience method that executes all phases in sequence and returns
        a unified result. Handles errors gracefully and continues where possible.

        This is the recommended entry point for most use cases.

        Args:
            skip_eligibility: If True, skips eligibility check
            ignore_attestations: If True, proceeds without user attestations
            record_index: Optional pre-built RecordIndex for shared index reuse
            code_index: Optional pre-built code index dict for shared index reuse
            _input_data_hash: Optional pre-computed input hash (avoids recomputation)

        Returns:
            PipelineResult with results from all phases

        Example:
            ```python
            result = concord.evaluate()
            if result.is_complete:
                for rec in result.applied_recommendations:
                    print(rec.title)
            ```
        """
        errors = []
        eligibility_result = None
        sufficiency_result = None
        assessment_result = None
        recommendations_result = None

        # Create metadata for tracking
        metadata = self._create_metadata(input_data_hash=_input_data_hash)

        # Phase 1: Eligibility
        if not skip_eligibility and self.cpg.eligibility_variables:
            try:
                elig_evaluator = EligibilityEvaluator(self.cpg.eligibility_variables)
                eligibility_result = elig_evaluator.evaluate(
                    self.healthcontext, record_index=record_index
                )
                self.__eligibility_result = eligibility_result
                if not eligibility_result.is_eligible:
                    return PipelineResult(
                        eligibility=eligibility_result,
                        sufficiency=None,
                        assessment=None,
                        recommendations=None,
                        is_complete=False,
                        errors=[Exception("Patient not eligible for this CPG")],
                        metadata=metadata
                    )
            except Exception as e:
                errors.append(e)
                log.error(f"Eligibility check failed: {e}")

        # Phase 2: Sufficiency
        if self.cpg.variables:
            try:
                suff_evaluator = SufficiencyEvaluator('se', cpg_variables=self.cpg.variables)
                sufficiency_result = suff_evaluator.evaluate(
                    self.healthcontext,
                    strict=self.strict_validation,
                    record_index=record_index,
                    code_index=code_index
                )
                self.__sufficiency_result = sufficiency_result
            except Exception as e:
                errors.append(e)
                log.error(f"Sufficiency check failed: {e}")
                return PipelineResult(
                    eligibility=eligibility_result,
                    sufficiency=None,
                    assessment=None,
                    recommendations=None,
                    is_complete=False,
                    errors=errors,
                    metadata=metadata
                )

        # Phase 3: Assessment
        if sufficiency_result:
            try:
                assessment_result = self.assess(
                    ignore_required_variable_attestations=ignore_attestations
                )
            except NeedAttestationError as e:
                errors.append(e)
                log.warning(f"Assessment needs attestation: {e}")
                return PipelineResult(
                    eligibility=eligibility_result,
                    sufficiency=sufficiency_result,
                    assessment=None,
                    recommendations=None,
                    is_complete=False,
                    errors=errors,
                    metadata=metadata
                )
            except Exception as e:
                errors.append(e)
                log.error(f"Assessment failed: {e}")

        # Phase 4: Recommendations
        if assessment_result:
            try:
                recommendations_result = self.recommendations()
            except Exception as e:
                errors.append(e)
                log.error(f"Recommendations failed: {e}")

        is_complete = (
            recommendations_result is not None and
            (eligibility_result is None or eligibility_result.is_eligible) and
            (sufficiency_result is None or sufficiency_result.is_executable)
        )

        return PipelineResult(
            eligibility=eligibility_result,
            sufficiency=sufficiency_result,
            assessment=assessment_result,
            recommendations=recommendations_result,
            is_complete=is_complete,
            errors=errors,
            metadata=metadata
        )

    @staticmethod
    def evaluated_record(identifier: str, records: list[EvaluatedRecord]) -> EvaluatedRecord | None:
        """Find an evaluated record by identifier.

        Args:
            identifier: The record ID to find
            records: List of EvaluatedRecord to search

        Returns:
            The matching EvaluatedRecord or None
        """
        # Use index for O(1) lookup
        index = RecordIndex(records)
        return index.get_by_id(identifier)

    def evaluated_recommendation(self, identifier: str) -> EvaluatedRecommendation | None:
        """Find an evaluated recommendation by identifier.

        Args:
            identifier: The recommendation ID to find

        Returns:
            The matching EvaluatedRecommendation or None
        """
        if not self.recommendation_result:
            return None
        return self.evaluated_record(identifier=identifier, records=self.recommendation_result.recommendations)

