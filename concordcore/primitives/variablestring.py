#!/usr/bin/env python3

from dataclasses import dataclass, field
from functools import cached_property
from re import findall

from concordcore.persona import Persona


class vstr(str):

    __replace_cached: str = field(init=False)

    @property
    def replaced(self):
        return self.__replace_cached

    @cached_property
    def only_variables(self):
        matches = self.variable_identifiers
        found = [m.split('.')[0] for m in matches] if matches else None 
        if found:
            return list(set(found))
        else:
            return None

    @cached_property
    def variable_identifiers(self):
        if not self:
            return None 
        pattrn = r"\$([A-Za-z][A-Za-z_.0-9]+)"
        matches = findall(pattrn, self)
        return matches if matches else None

    def replaced_with_data_from(self, data_dict):
        txt = self
        for var_id in self.only_variables:
            txt = self.replace('$'+var_id, data_dict.get(var_id, '<>'))
        
        self.__replace_cached = txt
        return self.__replace_cached



@dataclass
class VariableNarrative:
    
    persona: Persona



    
