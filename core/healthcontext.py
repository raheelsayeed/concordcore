#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import date


from primitives.types import Persona
from variables import var, value, record


@dataclass(frozen=True)
class HealthContext:

    records: list[record.Record]
    persona: Persona

    @classmethod
    def from_values(cls, values: list[value.Value], for_variables: list[var.Var], age: record.Record, gender: record.Record, race: record.Record, persona: Persona, until_date: date = None):
        
        var_values = [[var.Var('-',code=v.code), v] for v in values]
        till_date = until_date or date.today().replace(month=12, day=31)
        # FOR EACH VAR, BUILD A RECORD WITH VALUES
        records = [] 

        if age:
            records.append(age)
        if gender:
            records.append(gender)
        if race:
            records.append(race)
            
        for variable in for_variables:
            
            filtered_values = list(filter(lambda value: value[0] == variable, var_values))
            vals = [t[1] for t in filtered_values] if filtered_values else None
            if vals:
                vals = list(filter(lambda v: v.date.date() <= till_date, vals))

            rec = record.Record(variable, vals if vals else None)
            records.append(rec)
       


        return HealthContext(records=records, persona=persona)


