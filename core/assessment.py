#!/usr/bin/env python3

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Protocol



from .expression import Expression
from .evaluation import EvaluatedRecord, EvaluationContext, EvaluationResult, SufficiencyResultStatus
from primitives.errors import VariableEvaluationError
from primitives.types import Persona 
from primitives.vlist import vlist
from variables import record, var, value


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssessmentVar(var.Var):
    
    # default: boolean type value expected
    # type: str = 'boolean'
    show_if_negative: bool = False 
    expression: str = None
    function: str = None 
    dated: datetime = None
    references: Any = None
    user_attestable: bool = False

    def __post_init__(self):
        if not self.expression and not self.function:
            raise Exception(f'AssesmentVar<{self.id}> must have either an expression or a function')

    def __hash__(self):
        return hash(self.__repr__)

    @classmethod
    def instantiate_from_yaml(cls, yml):
        return super(AssessmentVar, cls).instantiate_from_yaml(yml)

@dataclass
class AssessmentRecord(record.Record):

    var: AssessmentVar
    __expression: Expression = field(init=False)
    __assessed_value: value.Value = None

    def __post_init__(self):
        super().__post_init__()
        
        self.__expression = Expression(self.var.expression) if self.var.expression else None
        self.__assessed_value = None
        # return 

    @property 
    def expression(self):
        return self.__expression if self.__expression else None

    def evaluate(self, records, persona: Persona = Persona.patient, functions_module=None):

        record_dict = {r.id: r.value if r.value else None for r in records}
        try:
            if self.var.function:
                func = getattr(functions_module, self.var.function)
                result = func(record_dict)
                if result == None:
                    ve =  ValueError(f'EvaluationFunction failed for AssessmentVar:{self.var.id}')
                    raise ve 
                else:

                    self.__assessed_value = value.Value(result)


            elif self.__expression:
                result = self.__expression.evaluate(records)
                if result:
                    # already result is a value.Value type
                    self.__assessed_value = self.__expression.result
        except Exception as e:
            raise VariableEvaluationError([e], self.id)
        finally:
            # assign narrative
            var_dict = None
            if self.var.narr:
                var_dict = None 
                if self.var.narr.variables:
                    records_for_filter = list(filter(lambda ea: ea.id in self.var.narr.variables, records))
                    var_dict = {r.id: r.as_dict() for r in records_for_filter}
            
            self.set_narrative(persona=persona, variable_data_dict=var_dict)
                
            log.debug(f'AssessmentEval={self.id} expression={self.var.expression} function={self.var.function} result={self.value} narrative={self.narrative}')
            # if self.id == "metabolic_syndrome":
            #     exit()
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
    def successful(self) -> bool:
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
            
    def assess(self, 
                assessment_variables: list[AssessmentVar], 
                evaluated_records: list[EvaluatedRecord],
                persona: Persona = Persona.patient,
                functions_module=None,
                context: EvaluationContext = None) -> AssessmentResult:
        
        eval_context = context or EvaluationContext() 

        # holder for AssessmentRecord that are evaluated
        evaluated_assessment_records = []
        # given records, pull record from the EV
        records = [e.record for e in evaluated_records]
        # evaluate each AV
        for var in assessment_variables:

            # convert to a Record
            assessment_record = AssessmentRecord(var=var)
            try:
                success = assessment_record.evaluate(records + evaluated_assessment_records, persona=persona, functions_module=functions_module)
                evaluated_assessment_records.append(assessment_record)
                eval_context.successful_evaluation(assessment_record)
            except VariableEvaluationError as e:
                evaluated_assessment_records.append(assessment_record)
                eval_context.failed_evaluation(assessment_record, e)
            except Exception as e:
                raise e
                

        return AssessmentResult(context=eval_context)

