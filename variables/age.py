#!/usr/bin/env python3

from ontology.codes import Code, CodeSystemType, Concord_Code_Age
from variables import record, var, value


class Age(record.Record):

    def __init__(self, ageValue: int):

        val_code = Code(Concord_Code_Age, CodeSystemType.concord.value, Concord_Code_Age)
        var_age = var.Var(Concord_Code_Age, 'Age', code=[val_code])
        val = value.Value(ageValue)
        super().__init__(var_age, [val])
        
        