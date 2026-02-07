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
from .evaluation import EvaluatedRecord, EvaluationContext, EvaluationResult, SufficiencyResultStatus
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
    expression: str = None
    function: str = None

    def __post_init__(self):
        if not self.expression and not self.function:
            raise Exception(f'{self.__class__.__name__}<{self.id}> must have either an expression or a function')

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
    dated: datetime = None
    reference: Any = None
    user_attestable: bool = False
    llm_prompt: str = None

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def instantiate_from_yaml(cls, yml):
        return super(AssessmentVar, cls).instantiate_from_yaml(yml)

@dataclass
class AssessmentRecord(record.Record):

    var: AssessmentVar
    __expression: Expression = field(init=False)
    __assessed_value: value.Value = None

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



@dataclass
class EvaluatedAssessmentRecord(EvaluatedRecord):
    pass



@dataclass(frozen=True)
class AssessmentResult(EvaluationResult):
    
    @property
    def success(self) -> bool:
        # successful only when no records have Insufficient status 
        log.info('AssessmentResult is successful only when no evaluated assessment records are designated=Insufficient')
        for eval_record in self.context.evaluation_list:
            is_success = (eval_record.sufficiency_status != SufficiencyResultStatus.Insufficient)
            if not is_success:
                return False

        return True
    

class AssessmentEvaluatorProtocol(Protocol):

    result: EvaluationResult = None

    def assess(self, 
                assessment_variables: list[AssessmentVar], 
                evaluated_records: list[EvaluatedRecord],
                persona: Persona = Persona.patient,
                functions_module=None,
                context: EvaluationContext = None) -> AssessmentResult:
        
        ...

class AssessmentEvaluator(AssessmentEvaluatorProtocol):
    """Evaluates assessment variables against patient records."""

    def assess(self,
               assessment_variables: list[AssessmentVar],
               evaluated_records: list[EvaluatedRecord],
               persona: Persona = Persona.patient,
               functions_module=None,
               context: EvaluationContext = None) -> AssessmentResult:
        """Evaluate all assessment variables.

        Args:
            assessment_variables: List of AssessmentVar definitions
            evaluated_records: List of EvaluatedRecord from sufficiency phase
            persona: Persona for narrative generation
            functions_module: Module containing custom evaluation functions
            context: Optional existing evaluation context

        Returns:
            AssessmentResult: Result containing evaluated assessments
        """
        from .record_index import RecordIndex

        eval_context = context or EvaluationContext()

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
                eval_context.successful_evaluation(assessment_record)
            except VariableEvaluationError as e:
                all_records.append(assessment_record)
                record_index.add(assessment_record)
                record_dict[assessment_record.id] = assessment_record.value
                eval_context.failed_evaluation(assessment_record, e)
            except Exception as e:
                raise e

        return AssessmentResult(context=eval_context)

