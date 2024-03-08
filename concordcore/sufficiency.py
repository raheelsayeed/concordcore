#!/usr/bin/env python3

import logging
from dataclasses import dataclass
from typing import Protocol
from .healthcontext import HealthContext
from .variables.record import Record
from .variables.var import Var
from .evaluation import EvaluationContext, EvaluationResult, SufficiencyResultStatus

log = logging.getLogger(__name__)

@dataclass
class SufficiencyResult(EvaluationResult):

    result: SufficiencyResultStatus

    def __init__(self, context: EvaluationContext, variable_eval_dict: dict = None) -> None:

        self.result = SufficiencyResultStatus.Sufficient
        super().__init__(context)
        for ev in context.evaluation_list:
            if ev.result.value  == SufficiencyResultStatus.Insufficient.value:
                self.result = SufficiencyResultStatus.Insufficient
                break
                
        for er in context.evaluation_list:
            log.debug(f'EvaluatedRec={er.id} res={er.result} status={er.status}  vals={er.record.values}')
    @property
    def is_executable(self) -> bool: 
        return self.result == SufficiencyResultStatus.Sufficient or self.result == SufficiencyResultStatus.SufficientWithUserAttestation

    @property
    def insufficient_variables(self):
        return list(filter(lambda ev: ev.result.value == SufficiencyResultStatus.Insufficient.value, self.context.evaluation_list))

    @property
    def sufficient_variables(self):
        return list(filter(lambda ev: ev.result.value == SufficiencyResultStatus.Sufficient.value, self.context.evaluation_list))

    @property
    def attestation_variables(self):    
        # print('only variables counted in attestable')
        # exit()
        return list(filter(lambda ev: ev.record.var.user_attestable == True and ev.record.has_value == False, self.context.evaluation_list))
        
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
        each variable. Bascially, checks if a cpg could be executed successfully. 
        Always call cpg.is_valid() else where before evaluating for sufficiency!

        Args:
            data_variables (list[Variable]): list of user data
            context (EvaluationContext, optional): Records evaluation context. Defaults to None.

        Returns:
            SufficiencyResult: Sufficiency
        """
        
        eval_ctx = context or EvaluationContext()

        records = []

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

            # set narrative, using the persona
            record.set_narrative(persona=user_context.persona)
            # --- EVALUATE RECORD VALUES in another loop
            eval_ctx.add_evaluated(record=record)
            
        # ---- TODO: 
        # evaluate result

        return SufficiencyResult(eval_ctx)











