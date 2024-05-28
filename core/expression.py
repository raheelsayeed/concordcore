#!/usr/bin/env python3

from dataclasses import dataclass
from functools import cached_property
from re import findall
from primitives.errors import ExpressionVariableNotFound, ExpressionEvaluationError, VariableEvaluationError
from primitives.varstring import VarString
from variables.value import Value
import simpleeval, logging

log = logging.getLogger(__name__)


class Expression:

    def __init__(self, expression_string: str):
        self.string = VarString(expression_string)
        self.__expression_records =  []
        self._result = None
    
    @property
    def expression_records(self):
        return self.__expression_records

    @property
    def result(self):
        return self._result

    def __str__(self) -> str:
        return f'Expression({self.string})'

    @property
    def variable_identifiers(self):
        return self.string.variable_identifiers

    def evaluate_recommendation(self, evaluated_records):

        assessment_ids = self.string.variable_identifiers
        if not assessment_ids:
            raise ValueError(f'Expression must have AssessmentVariable identifiers, none fouund in {self.string}')
        
        self.__expression_records = []
        expression_values = {}
        errors = []
        for assessment_var_id in assessment_ids:
            filtered = next(filter(lambda ea_record: ea_record.id == assessment_var_id, evaluated_records), None)
            if filtered:
                if filtered.record.value:
                    if not isinstance(filtered.record.value.value, bool):
                        message = f'POLICY CHANGE WARNING, Assessments are not just Boolean. Assessments in a recommendation must have bool-type value, found:{type(filtered.record.value.value)}'
                        log.warning(message)
                        # errors.append(ValueError(f'Assessments in a recommendation must have bool-type value, found:{type(filtered.record.value.value)}')) 
                        # continue 
                    expression_values[assessment_var_id] = filtered.record.value.value
                    self.__expression_records.append(filtered.record)
                else:
                    errors.append(KeyError(f'No value for Assessment={filtered.id} in {self.string}'))
                    continue
            else:
                errors.append(KeyError(f'Cannot find Assessment={assessment_var_id} in {self.string}'))
        
        log.info(expression_values)

        if errors:
            raise VariableEvaluationError(errors, f'expression={self.string}')

        try:
            expstr = self.string.replace('$', '')
            expression_result = simpleeval.simple_eval(expstr, names=expression_values)
            if not isinstance(expression_result, bool):
                raise ValueError(f'Recommendation.expression result must be a bool-type, got={type(expression_result)}')
            return expression_result
        except Exception as e:
            raise e

    def evaluate(self, records):

        self.__expression_records = []  
        expression_tags = self.string.tags
        if not expression_tags:
            raise ValueError(f'Expressions must have variable-identifiers, none found in {self.string}')

        expression_values = {}
        dependency_variables_nullValues = [] 
        
        

        
        for exp_var_id in expression_tags:
            comps = exp_var_id.split('.')
            var_id = comps[0]
            func = comps[1] if len(comps) == 2 else None 
            filtered_record = next(filter(lambda record: record.id == var_id, records), None)
            
            if filtered_record:
                expression_values.update({filtered_record.id: filtered_record.as_dict()})
                var_value = None
                # 1. count of values
                if func == 'count':
                    var_value = {'count':len(filtered_record.values)} if filtered_record.values != None else None
                # 2. date of latest value
                elif func == 'date':
                    var_value = {'date':filtered_record.value.date} if filtered_record.value != None else None
                # 3. value!
                else:
                    var_value = filtered_record.value.evaluation_val if filtered_record.value  else None

                if var_value == None:
                    dependency_variables_nullValues.append(exp_var_id)


                expression_values[var_id] = var_value
                self.__expression_records.append(filtered_record)

            # Cannot find the variable: Raise ERROR!
            else:
                raise ExpressionVariableNotFound(exp_var_id, self.string)
        try:
            expstr = self.string.replace('$', '')
            evaluator = simpleeval.SimpleEval(names=expression_values)
            # evaluator.ATTR_INDEX_FALLBACK=True 
            expression_result = evaluator.eval(expstr)
            self._result = Value(expression_result, source=self.__expression_records)
            log.debug(f'Evaluatingvalues={expression_values}, expression={expstr}, result={expression_result}')
        except TypeError as e:
            ve = ExpressionEvaluationError(expstr, expression_values,  str(e))
            raise ve
        except Exception as e:
            ve = ExpressionEvaluationError(expstr, expression_values,  str(e))
            raise ve
            
        return self._result


