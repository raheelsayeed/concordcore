#!/usr/bin/env python3

from dataclasses import dataclass
from functools import cached_property
from re import findall
from concordcore.primitives.errors import VariableEvaluationError
from .variables.value import Value
import simpleeval, logging

log = logging.getLogger(__name__)

@dataclass
class Expression:
    
    Operators = ['and', 'or', 'if', 'else', 'True', 'False']
    string: str
    value_dict = None
    _result = None
    __expression_records = []

    @property
    def records(self):
        return self.__expression_records

    @property
    def result(self):
        return self._result

    def __str__(self) -> str:
        return self.string

    def __repr__(self) -> str:
        return f'<Expression({self.string})>'

    @cached_property
    def variable_identifiers(self):
        matches = self.__get_variable_identifiers 
        return [m.split('.')[0] for m in matches] if matches else None 


    @cached_property
    def __get_variable_identifiers(self):

        if not self.string:
            return None 
        
        pattrn = r"\$([A-Za-z][A-Za-z_.0-9]+)"
        matches = findall(pattrn, self.string)
        return matches if matches else None
        

    def evaluate_recommendation(self, evaluated_records):

        assessment_ids = self.__get_variable_identifiers
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
                        errors.append(ValueError(f'Assessments in a recommendation must have bool-type value, found:{type(filtered.value.value)}')) 
                        continue 
                    expression_values[assessment_var_id] = filtered.record.value.value
                    self.__expression_records.append(filtered)
                else:
                    errors.append(KeyError(f'No value for Assessment={filtered.id} in {self.string}'))
                    continue
            else:
                errors.append(KeyError(f'Cannot find Assessment={assessment_var_id} in {self.string}'))
        
        log.info(expression_values)
        log.error(errors)

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

    def evaluate(self, records, filter_by=None):

        self.__expression_records = []  
        expression_var_ids = self.__get_variable_identifiers
        if not expression_var_ids:
            raise ValueError(f'Expressions must have variable-identifiers, none found in {self.string}')

        expression_values = {}
        dependency_variables_nullValues = [] 
        not_found = []
        exceptions = []
        for exp_var_id in expression_var_ids:
            comps = exp_var_id.split('.')
            var_id = comps[0]
            func = comps[1] if len(comps) == 2 else None 
            filtered_record = next(filter(lambda record: record.id == var_id, records), None)
            if filtered_record:
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

            # Cannot find the variable -- Undeclared
            else:
                not_found.append('$'+exp_var_id)              


        try:
            expstr = self.string.replace('$', '')
            evaluator = simpleeval.SimpleEval(names=expression_values)
            # evaluator.ATTR_INDEX_FALLBACK=True 
            expression_result = evaluator.eval(expstr)
            self._result = Value(expression_result, source=self.records)
            log.debug(f'values={expression_values}, exp={expstr}, result={expression_result}')
        except Exception as e:
            # print(f'{e}; -null:{dependency_variables_nullValues}; undeclared:{dependency_variables_undeclared}, values:{dependency_variables_values}, exp_ids:{expression_var_ids}, exp: {expstr}')
            log.error(e)
            exceptions.append(e)
            # raise e
        
        if exceptions:
            # eg = ExceptionGroup('Unable to evaluate with errors', exceptions)
            raise VariableEvaluationError(exceptions, self.string)

        self.dependency_variables_values = expression_values
        self.dependency_variables_nullValues = dependency_variables_nullValues
        self.dependency_variables_undeclared = not_found

        return self._result













        
