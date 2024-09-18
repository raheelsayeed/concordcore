#!/usr/bin/env python3
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from uuid import uuid1
from variables.record import Record

log = logging.getLogger(__name__)

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
    evaluation_result: EvaluationResultStatus
    error: Exception = None
    dependency_vars: list[Record] = None 
    __sufficiency_status: SufficiencyResultStatus = None

    @property
    def id(self):
        return self.record.id

    def __repr__(self) -> str:
        return f'EvalRecord={self.record.id} evaluation_result={self.evaluation_result} status={self.sufficiency_status} error={self.error} dependencies={self.dependency_vars}'

    def __post_init__(self):
        self.date = datetime.now()
        self.__sufficiency_status = self.__get_sufficiency_status()



    @property
    def sufficiency_status(self):
        return self.__sufficiency_status

    def __get_sufficiency_status(self):

        has_val     = self.record.has_value
        is_req      = self.record.var.required
        attestable  = self.record.var.user_attestable
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
            if not self.error:
                return SufficiencyResultStatus.Sufficient
            else:
                if attestable:
                    return SufficiencyResultStatus.SufficientWithUserAttestation
                else:
                    return SufficiencyResultStatus.Insufficient
                    
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
    
    
    def failed_evaluation(self, record, e: Exception):
        self.evaluation_list.append(
            EvaluatedRecord(record=record, evaluation_result=EvaluationResultStatus.Failed, error=e, dependency_vars=None)
        )
        
    def successful_evaluation(self, record, dependency_vars=None):
        self.evaluation_list.append(
            EvaluatedRecord(record=record, evaluation_result=EvaluationResultStatus.Successful ,error=None, dependency_vars=dependency_vars)
        )

 
 

@dataclass(frozen=True)
class EvaluationResult:

    context: EvaluationContext

    def __repr__(self) -> str:
        return f"""
        CannotEval={len(self.insufficient_variables)}
        SuccessfulEval={len(self.sufficient_variables)}
        """
    @property
    def errors(self):
        return self.context.errors

    @property
    def insufficient_variables(self):
        vars = list(filter(lambda ev: ev.sufficiency_status.value == SufficiencyResultStatus.Insufficient.value, self.context.evaluation_list))
        for v in vars:
            log.error(v.error)
        return vars

    @property
    def sufficient_variables(self):
        return list(filter(lambda ev: ev.sufficiency_status.value == SufficiencyResultStatus.Sufficient.value, self.context.evaluation_list))

    @property
    def attestation_variables(self):    
        # print('only variables counted in attestable')
        # exit()
        return list(filter(lambda ev: ev.record.var.user_attestable == True and ev.record.has_value == False, self.context.evaluation_list))
               

        





