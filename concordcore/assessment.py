#!/usr/bin/env python3

from csv import DictReader
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any, Protocol

from concordcore.expression import Expression
from .evaluation import EvaluatedRecord, EvaluationContext, EvaluationResult
from .primitives.errors import VariableEvaluationError
from .primitives.types import Persona 
from .primitives.vlist import vlist
from .variables import record, var, value


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssessmentVar(var.Var):

    show_if_negative: bool = False 
    expression: str = None
    function: str = None 
    dated: datetime = None
    references: Any = None

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

        # has evaluation function
        if self.var.function:
            

            function_input_context = {r.id: r.value if r.value else None for r in records}
            log.debug(f'Evaluating record={self.id} function_input={function_input_context}')
            func = getattr(functions_module, self.var.function)
            result = func(function_input_context)
            log.debug(f'Evaluating record={self.id} function={self.var.function} result={result}')
            if result != None:
                self.__assessed_value = value.Value(result)
            else:
                ve =  ValueError(f'EvaluationFunction failed for AssessmentVar:{self.var.id}')
                log.error(ve)
                raise ve 

        # has evaluating `expression`
        elif self.__expression:
            try:
                res = self.__expression.evaluate(records)
                log.debug(f'ExpressionEvaluated record={self.id} expression={self.var.expression} result={res}')
                if res:
                    self.__assessed_value = self.__expression.result
            except Exception as e:
                raise VariableEvaluationError([e], self.id)
                
        self.__sanitize_assessment_narrative(records, persona)
        return self.__assessed_value

    
    def __sanitize_assessment_narrative(self, records, persona: Persona = Persona.patient):

         nvars = self.var.narrative_variables
         self.sanitized_narrative = self.set_narrative(persona=persona)
         if nvars:
            records_for_filter = list(filter(lambda ea: ea.id in nvars, records))
            dict_record_values = {r.id: r.as_dict() for r in records_for_filter}
            self.sanitized_narrative = self.set_narrative(persona=persona, variable_data_dict=dict_record_values)
            log.debug(f'nvars={nvars}; dict={dict_record_values} sanitized_narrative={self.sanitized_narrative}')

    @property
    def value(self):
        return self.__assessed_value

    @property
    def values(self):
        return vlist([self.__assessed_value]) if self.__assessed_value else None



@dataclass
class EvaluatedAssessmentRecord(EvaluatedRecord):
    pass



@dataclass
class AssessmentResult(EvaluationResult):
    
    @property
    def completed(self) -> bool:
        if self.context.errors:
            return False 
        else:
            return True
    

class AssessmentEvaluatorProtocol(Protocol):

    result: EvaluationResult = None

    def assess(self, 
                assessment_variables: list[AssessmentVar], 
                evaluated_records: list[EvaluatedRecord], 
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
                eval_context.add_evaluated(assessment_record)
            except VariableEvaluationError as e:
                evaluated_assessment_records.append(assessment_record)
                eval_context.add_unevaluated(assessment_record, e)
            except Exception as e:
                raise e
                

        return AssessmentResult(context=eval_context)

