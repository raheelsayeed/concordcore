#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import logging

from primitives import code, unit, valuedate

log = logging.getLogger(__name__)



# ------------- WORKING MODEL ------------ #

# ------------- VALUE ------------ #
class Value:

    def __init__(self, value, unit: unit.Unit = None, code: list[code.Code] = None, date: datetime = None, source: list[Any] = None):

        if value == None:
            raise ValueError('requires a value')

        dt = date or datetime.now()
        dt = valuedate.ValueDate(dt)

        self.value = value 
        self.unit = unit
        self.date = dt
        self.source = source
        self.code = code
        if source and type(source) is not list:
            raise KeyError(f'value.source must be a list-type. found={type(source)}')


    @property
    def evaluation_val(self):
        if isinstance(self.value, code.Code):
            return self.value.as_string
        else:
            return self.value

    @property
    def representation(self):
        if isinstance(self.value, bool):
            return 'Yes' if self.value == True else 'No'
        return f'{str(self.value)} {self.unit if self.unit else ""}'

        
    def __repr__(self) -> str:
        return f'Val={self.value}'
        return str(self.value)


    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.value == other.value
        elif isinstance(other, type(self.value)):
            return self.value == other
        else:
            return super().__eq__(other)
            
    def __lt__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.value < other.value
        elif isinstance(other, type(self.value)):
            return self.value < other
        else:
            raise TypeError(f'value type mismatch. Given: {type(other)} for {type(self.value)}')


    def  __gt__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.value > other.value
        elif isinstance(other, type(self.value)):
            return self.value > other
        else:
            raise TypeError(f'value type mismatch. Given: {type(other)} for {type(self.value)}')


    def  __gte__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.value >= other.value
        elif isinstance(other, type(self.value)):
            return self.value >= other
        else:
            raise TypeError(f'value type mismatch. Given: {type(other)} for {type(self.value)}')

    def __lte__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.value <= other.value
        elif isinstance(other, type(self.value)):
            return self.value <= other
        else:
            raise TypeError(f'value type mismatch. Given: {type(other)} for {type(self.value)}')




if __name__ == '__main__':

    glu_121 = Value(121, unit.Unit('code', 'mg/dL', 'measure_system'))
    diab = Value(True)
    # test
    assert glu_121.value == 121
    assert diab.value == True 
    assert isinstance(diab.value, bool)

    other = Value(121)
    assert other == glu_121

    greater = Value(122)
    assert greater > glu_121

    lesser = Value(111)
    assert lesser < greater

    # decimals
    decimal = Value(111.1)
    assert decimal > lesser
    assert lesser < decimal






