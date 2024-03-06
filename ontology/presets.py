#!/usr/bin/env python3

from concordcore.primitives.definitions import CodeType
from concordcore.variables.record import Record
from concordcore.variables.value import Value
from .codes import *

class Age(Record):

    def __init__(self, ageValue: int):
        super().__init__(
            Var(id=ConcordDefinition.code_Age.value, 
            code=[Code(ConcordDefinition.code_Age.value,CodeType.concord.value,'Age')]), 
        [Value(
            ageValue, 
            code=[Code(ConcordDefinition.code_Age.value,CodeType.concord.value,'Age')])])