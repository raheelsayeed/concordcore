#!/usr/bin/env python3

from primitives.definitions import CodeType
from variables.record import Record
from variables.value import Value
from .codes import *

class Age(Record):

    def __init__(self, ageValue: int):
        super().__init__(
            Var(id=ConcordDefinition.code_Age.value, 
            code=[Code(ConcordDefinition.code_Age.value,CodeType.concord.value,'Age')]), 
        [Value(
            ageValue, 
            code=[Code(ConcordDefinition.code_Age.value,CodeType.concord.value,'Age')])])