#!/usr/bin/env python3
"""Assessment evaluation for ConcordCore.

This module provides AssessmentVar and AssessmentRecord classes for
evaluating CPG assessment criteria against patient data.
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Protocol

from .expression import Expression
from .evaluation import EvaluatedRecord, EvaluationResultStatus
from .errors import CPGDefinitionError
from primitives.errors import VariableEvaluationError
from primitives.types import Persona, ValueType
from primitives.vlist import vlist
from variables import record, var, value

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluableVar(var.Var):
    """Base class for variables that can be evaluated via expression or function.

    This provides the common foundation for both AssessmentVar and EligibilityVar,
    which both need expression/function evaluation capabilities.

    Attributes:
        type: The expected value type (default: boolean)
        expression: Expression string to evaluate (e.g., '$LDL > 130')
        function: Name of custom function to call for evaluation
    """

    type: ValueType = ValueType.boolean
    expression: str | None = None
    function: str | None = None

    def __post_init__(self):
        if not self.expression and not self.function:
            raise CPGDefinitionError(f'{self.__class__.__name__}<{self.id}> must have either an expression or a function')

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def instantiate_from_yaml(cls, yml):
        return super(EvaluableVar, cls).instantiate_from_yaml(yml)


@dataclass(frozen=True)
class AssessmentVar(EvaluableVar):
    """Assessment variable for evaluating patient health status.

    Extends EvaluableVar with assessment-specific fields for display control,
    dating, and references.

    Attributes:
        show_if_negative: Whether to display when result is False
        dated: Optional date associated with the assessment
        reference: Optional reference information
        user_attestable: Whether user can attest to this value
        llm_prompt: Prompt text for extracting this variable from clinical notes
    """

    show_if_negative: bool = False
    dated: datetime | None = None
    reference: Any | None = None
    user_attestable: bool = False
    llm_prompt: str | None = None

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def instantiate_from_yaml(cls, yml):
        return super(AssessmentVar, cls).instantiate_from_yaml(yml)

@dataclass
class AssessmentRecord(record.Record):

    var: AssessmentVar
    __expression: Expression = field(init=False)
    __assessed_value: value.Value | None = None

    def __post_init__(self, initial_values=None):
        super().__post_init__(initial_values)

        self.__expression = Expression(self.var.expression) if self.var.expression else None
        self.__assessed_value = None 

    @property 
    def expression(self):
        return self.__expression if self.__expression else None

    def evaluate(self, records, persona: Persona = Persona.patient, functions_module=None,
                 record_index=None, record_dict=None):
        """Evaluate the assessment expression or function.

        Args:
            records: List of records to evaluate against
            persona: Persona for narrative generation
            functions_module: Module containing custom evaluation functions
            record_index: Optional pre-built RecordIndex for O(1) lookups
            record_dict: Optional pre-built dict mapping id to value (avoids rebuilding)
        """
        # Use pre-built dict if provided, otherwise build it (for backward compatibility)
        if record_dict is None:
            record_dict = {r.id: r.value if r.value else None for r in records}

        try:
            if self.var.function:
                func = getattr(functions_module, self.var.function)
                result = func(record_dict)
                if result is None:
                    raise ValueError(f'EvaluationFunction failed for AssessmentVar:{self.var.id}')
                self.__assessed_value = value.Value(result)

            elif self.__expression:
                result = self.__expression.evaluate(records, record_index=record_index)
                if result:
                    # already result is a value.Value type
                    self.__assessed_value = self.__expression.result

        except Exception as e:
            raise VariableEvaluationError([e], self.id)

        finally:
            # assign narrative
            var_dict = None
            if self.var.narr and self.var.narr.variables:
                # Use record_index for O(1) lookup if available
                narr_var_ids = set(self.var.narr.variables)
                if record_index:
                    records_for_narr = [record_index.get(vid) for vid in narr_var_ids]
                    records_for_narr = [r for r in records_for_narr if r is not None]
                else:
                    records_for_narr = [r for r in records if r.id in narr_var_ids]
                var_dict = {r.id: r.as_dict() for r in records_for_narr}

            self.set_narrative(persona=persona, variable_data_dict=var_dict)
            log.debug(f'AssessmentEval={self.id} expression={self.var.expression} function={self.var.function} result={self.value} narrative={self.narrative}')
        return self.__assessed_value


    @property
    def value(self):
        return self.__assessed_value

    @property
    def values(self):
        return vlist([self.__assessed_value]) if self.__assessed_value else None



@dataclass(slots=True)
class AssessedRecord:
    """Result of evaluating one assessment variable."""
    record: AssessmentRecord
    evaluation_result: EvaluationResultStatus
    error: Exception | None = None

    @property
    def id(self) -> str:
        return self.record.id

    @property
    def var(self) -> AssessmentVar:
        return self.record.var

    @property
    def value(self) -> value.Value | None:
        return self.record.value

    @property
    def expression(self) -> Expression | None:
        return self.record.expression

    @property
    def narrative(self) -> str | None:
        return self.record.narrative

    @property
    def show_if_negative(self) -> bool:
        return self.record.var.show_if_negative


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    assessments: list[AssessedRecord]

    @property
    def success(self) -> bool:
        return all(a.evaluation_result == EvaluationResultStatus.Successful
                   for a in self.assessments if a.var.required)

    @property
    def errors(self) -> list[Exception]:
        return [a.error for a in self.assessments if a.error]
    

class AssessmentEvaluatorProtocol(Protocol):

    def assess(self,
                assessment_variables: list[AssessmentVar],
                evaluated_records: list[EvaluatedRecord],
                persona: Persona = Persona.patient,
                functions_module=None) -> AssessmentResult:

        ...

class AssessmentEvaluator(AssessmentEvaluatorProtocol):
    """Evaluates assessment variables against patient records."""

    def assess(self,
               assessment_variables: list[AssessmentVar],
               evaluated_records: list[EvaluatedRecord],
               persona: Persona = Persona.patient,
               functions_module=None) -> AssessmentResult:
        """Evaluate all assessment variables.

        Args:
            assessment_variables: List of AssessmentVar definitions
            evaluated_records: List of EvaluatedRecord from sufficiency phase
            persona: Persona for narrative generation
            functions_module: Module containing custom evaluation functions

        Returns:
            AssessmentResult: Result containing evaluated assessments
        """
        from .record_index import RecordIndex

        assessed_records: list[AssessedRecord] = []

        # Extract records from evaluated records
        records = [e.record for e in evaluated_records]

        # Create single list to accumulate records (avoid O(n²) list concat)
        all_records = list(records)  # Copy once

        # Build index once - will be updated as assessments are added
        record_index = RecordIndex(all_records)

        # Pre-build record dict for function evaluations
        record_dict = {r.id: r.value if r.value else None for r in all_records}

        # Evaluate each assessment variable
        for var in assessment_variables:
            assessment_record = AssessmentRecord(var=var)
            try:
                # Pass pre-built index and dict
                assessment_record.evaluate(
                    all_records,
                    persona=persona,
                    functions_module=functions_module,
                    record_index=record_index,
                    record_dict=record_dict
                )
                # Add to list and update index/dict
                all_records.append(assessment_record)
                record_index.add(assessment_record)
                record_dict[assessment_record.id] = assessment_record.value
                assessed_records.append(AssessedRecord(
                    record=assessment_record,
                    evaluation_result=EvaluationResultStatus.Successful
                ))
            except VariableEvaluationError as e:
                all_records.append(assessment_record)
                record_index.add(assessment_record)
                record_dict[assessment_record.id] = assessment_record.value
                assessed_records.append(AssessedRecord(
                    record=assessment_record,
                    evaluation_result=EvaluationResultStatus.Failed,
                    error=e
                ))
            except Exception:
                raise

        return AssessmentResult(assessments=assessed_records)

