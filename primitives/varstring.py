#!/usr/bin/env python3

from enum import StrEnum, auto
import logging

from dataclasses import dataclass, field
from functools import cached_property
from re import findall

l = logging.getLogger(__name__)

class VarString(str):

    __replace_cached: str = field(init=False)

    @property
    def replaced(self):
        return self.__replace_cached

    @cached_property
    def variable_identifiers(self):
        matches = self.tags
        found = [m.split('.')[0] for m in matches] if matches else None 
        if found:
            return list(set(found))
        else:
            return None

    @cached_property
    def tags(self):
        if not self:
            return None 
        pattrn = r"\$([A-Za-z][A-Za-z_.0-9]+[A-Za-z0-9])+"
        matches = findall(pattrn, self)
        if matches:
            return sorted(list(set(matches)), key=lambda tag: '.' in tag, reverse=True)
        else:
            return None

    def replaced_with_data_from(self, data_dict):
        txt = self
        for var_id in self.variable_identifiers:
            txt = self.replace('$'+var_id, data_dict.get(var_id, '<>'))
        
        self.__replace_cached = txt
        return self.__replace_cached

    @cached_property
    def has_variables(self):
        return  self.variable_identifiers != None



class ExpressionVariable(StrEnum):
    value = auto()
    values = auto() 
    date = auto()



from simpleeval import simple_eval
class EvaluatorString:

    def __init__(self, string: str):

        self.string = VarString(string)
        self.__result = None
        self.__functions = None # Pass on functions? {'count': len} ??
        self.__value_dict = None
        if self.variables == None:
            raise ValueError('EvaluatorString must contain variable_identifiers, none found')

    @property
    def result(self):
        return self.__result
    
    @property
    def variables(self):
        return self.string.variable_identifiers
    
    def __repr__(self) -> str:
        return f'<Expression({self.string}) result={self.result}>'

    def evaluate(self, values: dict = None):
        try:
            self.__value_dict = values
            expstr = self.string.replace('$', '')
            self.__result = simple_eval(expstr, names=values)
            return self.result
        except Exception as e:
            raise e
        
            


class ValidationExpression(EvaluatorString):

    __allowed_variables = ['value']

    def __init__(self, string: str):
        super().__init__(string)
        if self.variables != ['value']:
            raise ValueError(f'expression={self.string} can only contain `$value`. found={self.variables}')

    def evaluate(self, value):
        res = super().evaluate({'value': value})
        if not isinstance(res, bool):
            raise TypeError(f'ValidatorExpression error: must evaluate to type `bool`, is={type(self.result)}')
        return res









if __name__ == '__main__':

    test = VarString('THis is a $value thing')
    assert test.variable_identifiers == ['value']

    test = EvaluatorString('1 == $value')
    assert test.variables == ['value']
    assert test.result == None
    assert test.evaluate({'value': 1}) == True
    print(test)
    print(test.string.variable_identifiers)

    test = EvaluatorString('2 + $value')
    assert test.variables == ['value']
    assert test.result == None
    assert test.evaluate({'value': 1}) == 3


    test = ValidationExpression('2 == $value and $value == 1')
    assert test.variables == ['value']
    assert test.result == None
    assert test.evaluate({'value': 1}) == False

    test = EvaluatorString('1 + $va')
    

    






