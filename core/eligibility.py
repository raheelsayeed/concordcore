#!/usr/bin/env python3

from dataclasses import dataclass
from enum import Enum, auto
from functools import cached_property
from typing import Any, Protocol
from .assessment import AssessmentVar, AssessmentRecord
from .healthcontext import HealthContext
from .evaluation import EvaluationResult, EvaluationContext
from primitives.types import YMLStrEnum


class EligbilityValueAbstract(Protocol):
    ...

@dataclass(frozen=True)
class EligibilityResult(EvaluationResult):

    @cached_property
    def is_eligible(self) -> bool:
        if False in [ev.record.value.value if ev.record.value else False for ev in self.context.evaluation_list]:
            return False 
        return True
            

class EligbilityCriteriaType(YMLStrEnum):
    inclusion = 'inclusion'
    exclusion = 'exclusion'



@dataclass(frozen=True)
class EligibilityVar(AssessmentVar):
    type: str = 'boolean'
    criteria_type: EligbilityCriteriaType = None

@dataclass
class EligibilityRecord(AssessmentRecord):
    var: EligibilityVar

    @property
    def is_eligible(self):
        return self.value


    
    
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

        errs = [] 
        eval_ctx = context or EvaluationContext()
        evaluated_crtiera_records = []

        for criteria in self.criterias:

            try:
                criteria_record = EligibilityRecord(criteria)
                criteria_record.evaluate(records=healthcontext.records, persona=healthcontext.persona)
                eval_ctx.successful_evaluation(criteria_record)
            except Exception as e:
                eval_ctx.failed_evaluation(criteria_record, e)

        # Raise eligibility erros immediately
        if eval_ctx.errors:
            raise ExceptionGroup('EligibilityEvaluationError', eval_ctx.errors)

        result = EligibilityResult(eval_ctx)
        return result




        





