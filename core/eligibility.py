#!/usr/bin/env python3

from dataclasses import dataclass
from enum import Enum, auto
from functools import cached_property
from typing import Any, Protocol
from .assessment import EvaluableVar, AssessmentRecord
from .healthcontext import HealthContext
from .evaluation import EvaluationResult, EvaluationContext
from .record_index import RecordIndex
from primitives.types import YMLStrEnum, ValueType


class EligbilityValueAbstract(Protocol):
    ...

@dataclass(frozen=True)
class EligibilityResult(EvaluationResult):

    def __repr__(self) -> str:
        return f"""
        IS_Eligibile: {self.is_eligible}
        {super().__repr__()}
        """

    @cached_property
    def is_eligible(self) -> bool:
        # Use any() instead of creating a list - short-circuits on first False
        return not any(ev.record.is_eligible is False for ev in self.context.evaluation_list)
            

class EligbilityCriteriaType(YMLStrEnum):
    inclusion = 'inclusion'
    exclusion = 'exclusion'



@dataclass(frozen=True)
class EligibilityVar(EvaluableVar):
    """Eligibility variable for determining if a CPG applies to a patient.

    Extends EvaluableVar with eligibility-specific criteria type for
    distinguishing between inclusion and exclusion criteria.

    Attributes:
        criteria_type: Whether this is an inclusion or exclusion criterion
        llm_prompt: Prompt text for extracting this variable from clinical notes
    """

    criteria_type: EligbilityCriteriaType = None
    llm_prompt: str = None

    @classmethod
    def instantiate_from_yaml(cls, yml):
        if 'criteria_type' in yml:
            yml['criteria_type'] = EligbilityCriteriaType(yml['criteria_type'])
        return super(EligibilityVar, cls).instantiate_from_yaml(yml)


@dataclass
class EligibilityRecord(AssessmentRecord):
    var: EligibilityVar

    @property
    def is_eligible(self):
        res = not self.value.value if self.var.criteria_type == EligbilityCriteriaType.exclusion else self.value.value
        return res


    
    
class EligibilityEvaluatorProtocol(Protocol):


    def __init__(self, criterias: list[EligibilityVar]):
        ...

    def evaluate(self, 
                healthcontext: HealthContext, 
                context: EvaluationContext = None) -> EligibilityResult:
        ...


class EligibilityEvaluator(EligibilityEvaluatorProtocol):

    def __init__(self, criterias: list[EligibilityVar]):
        self.criterias = criterias

    def evaluate(self,
                healthcontext: HealthContext,
                context: EvaluationContext = None) -> EligibilityResult:

        if not self.criterias:
            raise ValueError('No criterias to evaluate')

        eval_ctx = context or EvaluationContext()

        # Build record index once for O(1) lookups during expression evaluation
        record_index = RecordIndex(healthcontext.records)

        # Pre-build record dict for function evaluations (built once, reused)
        record_dict = {r.id: r.value if r.value else None for r in healthcontext.records}

        for criteria in self.criterias:
            try:
                criteria_record = EligibilityRecord(criteria)
                criteria_record.evaluate(
                    records=healthcontext.records,
                    persona=healthcontext.persona,
                    record_index=record_index,
                    record_dict=record_dict
                )
                eval_ctx.successful_evaluation(criteria_record)
            except Exception as e:
                eval_ctx.failed_evaluation(criteria_record, e)

        # Raise eligibility errors immediately
        if eval_ctx.errors:
            raise ExceptionGroup('EligibilityEvaluationError', eval_ctx.errors)

        return EligibilityResult(eval_ctx)




        





