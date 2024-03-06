#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .primitives.code import Code 
from .variables.value import Value
from .variables.var import Var
from .variables.record import Record



@dataclass(frozen=True)
class HealthContext:

    records: list[Record]

    @classmethod
    def from_values(cls, values: list[Value], for_variables: list[Var], until_date: date = None):
        
        var_values = [[Var('-',code=v.code), v] for v in values]
        till_date = until_date or date.today().replace(month=12, day=31)
        # FOR EACH VAR, BUILD A RECORD WITH VALUES
        records = [] 

        for variable in for_variables:
            
            filtered_values = list(filter(lambda value: value[0] == variable, var_values))
            vals = [t[1] for t in filtered_values] if filtered_values else None
            if vals:
                vals = list(filter(lambda v: v.date.date() <= till_date, vals))

            record = Record(variable, vals if vals else None)
            records.append(record)
       
        return HealthContext(records=records)


