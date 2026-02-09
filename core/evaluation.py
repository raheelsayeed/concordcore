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
    error: Exception | None = None
    dependency_vars: list[Record] | None = None
    __sufficiency_status: SufficiencyResultStatus | None = None
    date: datetime = field(default_factory=datetime.now)

    @property
    def id(self):
        return self.record.id

    def __repr__(self) -> str:
        return f'EvalRecord={self.record.id} evaluation_result={self.evaluation_result} status={self.sufficiency_status} error={self.error} dependencies={self.dependency_vars}'

    def __post_init__(self):
        self.__sufficiency_status = self.__get_sufficiency_status()



    @property
    def sufficiency_status(self):
        return self.__sufficiency_status

    def __get_sufficiency_status(self):

        has_val     = self.record.has_value
        is_req      = self.record.var.required
        attestable  = self.record.var.user_attestable
        if is_req and has_val:
            if not self.error:
                return SufficiencyResultStatus.Sufficient
            else:
                if attestable:
                    return SufficiencyResultStatus.SufficientWithUserAttestation
                else:
                    return SufficiencyResultStatus.Insufficient
                    
        elif not is_req and has_val:
            return SufficiencyResultStatus.Sufficient

        elif is_req and not has_val:
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
          
@dataclass(slots=True)
class EvaluationContext:

    id: str = field(default_factory=lambda: str(uuid1()))
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

 
 

@dataclass(frozen=True, slots=True)
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
        return list(filter(lambda ev: ev.record.var.user_attestable and not ev.record.has_value, self.context.evaluation_list))

