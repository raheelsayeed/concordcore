#!/usr/bin/env python3

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from uuid import uuid1
from .variables.record import Record

# --- Common Evaluation Result Enum
class SufficiencyResultStatus(Enum):
    SufficientWithUserAttestation    = auto()
    Sufficient                       = auto()
    Insufficient                     = auto()
    Optional                         = auto()

class EvaluationResultStatus(Enum):
    Successful          = auto()
    Failed              = auto()

@dataclass 
class EvaluatedRecord:
    record: Record
    result: EvaluationResultStatus
    status: SufficiencyResultStatus = None
    error: Exception = None
    dependency_vars: list[Record] = None 

    @property
    def id(self):
        return self.record.id

    def __repr__(self) -> str:
        return f'EvalRecord={self.record.id} result={self.result} status={self.status} error={self.error} dependencies={self.dependency_vars}'

    def __post_init__(self):
        self.status = self.sufficiency_status()
        self.date = datetime.now()

    def sufficiency_status(self):

        has_val     = self.record.has_value
        is_req      = self.record.var.required
        attestable  = self.record.var.user_attestable
        # get a list of all `required'
        # try:
            # required_vars = list(filter(lambda v: v.required == True,  self.cpg_variables))
            # inspect(required_vars)

            # user_attestable_vars = list(filter(lambda v: v.user_attestable == True,  self.cpg_variables))
            # inspect(user_attestable_vars)

            # basically Age is required but is not user_attestable.
            # patient_context Needs to have AGE from her EHR data!
            #   - if found    --> sufficient
            #   - if notFound --> insufficient
            # so,
            #   1. cpg.required == True,     person.v.has_value == True              -> Sufficient
            #   2. cpg.required == False,    person.v.has_value == True              -> Sufficient
            #   3. cpg.required == True,     person.v.has_value == False:
            #                                       - cpg.user_attestable == True   -> SufficientWithAttestation | UserAugmentable
            #                                       - cpg.user_attestable == False  -> Insufficient <Breaks CPG Trigger>

            #   Desirables: Good to know but not necessary, less important
            #   4. cpg.required == False,    person.v.has_value == False             -> Optional
        if is_req and has_val:
            return SufficiencyResultStatus.Sufficient
        
        elif is_req == False and has_val:
            return SufficiencyResultStatus.Sufficient
        
        elif is_req and has_val == False:
            if attestable:
                status = SufficiencyResultStatus.SufficientWithUserAttestation 
                return status
            else:
                status = SufficiencyResultStatus.Insufficient 
                if not self.error:
                    self.error = ValueError(f'Var<{self.record.var.id}> has no value(s)')
                return status
        else:
            return SufficiencyResultStatus.Optional
          
@dataclass
class EvaluationContext:

    id = uuid1()
    evaluation_list: list[EvaluatedRecord] = field(default_factory=list[EvaluatedRecord])

    @property 
    def errors(self):
        errs = [] 
        for ev in self.evaluation_list:
            if ev.error:
                errs.append(ev.error) 

        return errs
    
    
    def add_unevaluated(self, record, e: Exception):
        self.evaluation_list.append(
            EvaluatedRecord(record=record, result=EvaluationResultStatus.Failed, error=e, dependency_vars=None)
        )
        
    def add_evaluated(self, record, dependency_vars=None):
        self.evaluation_list.append(
            EvaluatedRecord(record=record, result=EvaluationResultStatus.Successful ,error=None, dependency_vars=dependency_vars)
        )

    # def errors(self):
    #     return [ev.error if ev.error else None for ev in self.evaluation_list]


    @property
    def success(self) -> bool:
        pass 

    


@dataclass
class EvaluationResult:
    context: EvaluationContext
    
    @property
    def errors(self):
        return self.context.errors
        

        





