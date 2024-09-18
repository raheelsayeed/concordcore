#!/usr/bin/env python3

from functools import cached_property
import logging
from dataclasses import dataclass
from typing import Protocol

from .healthcontext import HealthContext
from variables.record import Record
from variables.var import Var
from .evaluation import EvaluationContext, EvaluationResult, SufficiencyResultStatus

log = logging.getLogger(__name__)

@dataclass(frozen=True)
class SufficiencyResult(EvaluationResult):
  
    def __repr__(self) -> str:
            return f"""
            is_executable: {self.is_executable}
            {super().__repr__()}
            """

    @cached_property
    def result(self):
        for ev in self.context.evaluation_list:
            if ev.sufficiency_status.value  == SufficiencyResultStatus.Insufficient.value:
                return SufficiencyResultStatus.Insufficient
        
        return SufficiencyResultStatus.Sufficient

    @property
    def is_executable(self) -> bool: 
        return self.result == SufficiencyResultStatus.Sufficient or self.result == SufficiencyResultStatus.SufficientWithUserAttestation

 
class SufficiencyEvaluatorProtocol(Protocol):

    def __init__(self, identifier: str, cpg_variables: list[Var]):
        ...

    def evaluate(self,
                user_context: HealthContext,
                context: EvaluationContext = None) -> SufficiencyResult:
        ...


class SufficiencyEvaluator(SufficiencyEvaluatorProtocol):

    def __init__(self, identifier: str, cpg_variables: list[Var]):

        self.id = identifier
        self.cpg_variables = cpg_variables


    def evaluate(self,
                user_context: HealthContext,
                context: EvaluationContext = None) -> SufficiencyResult:
        """Evalutes a given list of variables for sufficiency to execute a CPG and categorizes 
        each variable.
        Note: Always call cpg.is_valid() else where before evaluating for sufficiency!

        Args:
            user_context: HealthContext 
            context (EvaluationContext, optional): Records evaluation context. Defaults to None.

        Returns:
            SufficiencyResult: Sufficiency
        """
        
        eval_ctx = context or EvaluationContext()

        records: list[Record] = []
        # --- Sufficiency only checks of `cpg.Variables`
        # --- Assessments, Eligibility, Recommendations rely on Sufficiency of cpg.Variables to execute
        for var in self.cpg_variables:
            
            record = None
            
            user_record = next(filter(lambda user_record: user_record.var == var, user_context.records), None)

            # Assign Values to Concord Record
            if user_record and user_record.has_value:
                record = Record(var, user_record.values)
            else:
                record = Record(var, None)
            
            # record.set_narrative(persona=user_context.persona)
            records.append(record)


        # --- PERFORM EVALUATION CHECKS --- 
        for record in records:

            try:
                if record.validate(records=records, strict=True):
                    eval_ctx.successful_evaluation(record)
            except Exception as e:
        
                eval_ctx.failed_evaluation(record, e)   
                

            record.set_narrative(persona=user_context.persona)
            
        return SufficiencyResult(eval_ctx)











