#!/usr/bin/env python3

from asyncio.log import logger
from dataclasses import dataclass, field, InitVar
from functools import cache, cached_property

import logging
from types import NoneType
from typing import Type
from unittest import result

from ..variables import var
from ..variables.value import Value
from ..primitives.vlist import vlist
from ..primitives.types import Persona
from ..expression import Expression


logger = logging.getLogger(__name__)

@dataclass
class Record:

    var: var.Var
    __values: vlist[Value] = None 
    __filtered_values: vlist[Value] = field(init=False)
    __attested_value: Value = field(init=False)
    sanitized_narrative: str = field(init=False)

    def __post_init__(self):
        self.__filtered_values = self.filtered_values
        self.__values = vlist(self.__values) if self.__values else None
        self.__attested_value = None
        self.sanitized_narrative = None

    @cached_property
    def __must_filter_values(self):
        if self.var.value_filter:
            logging.debug(f'{self.id} Record.values are filtered')
            return True
        return False

    @property
    def id(self):
        return self.var.id

    @property
    def title(self):
        return self.var.title

    @property
    def code(self):
        return self.var.code

    @property
    def value(self):
        return self.values[0] if self.values else None

    @property
    def values(self):
        if self.__attested_value:
            return vlist([self.__attested_value])
        elif self.__must_filter_values:
            return self.__filtered_values
        else:
            return self.__values

    # ---- values to be set only on construct
    # @values.setter
    # def values(self, vals):
    #     self.__values = vlist(vals) if vals else None

    @property
    def attested_value(self):
        return self.__attested_value
    
    @attested_value.setter
    def attested_value(self, value):
        if self.var.user_attestable:
            if not isinstance(value, Value):
                raise ValueError(f'record={self.id} invalid value-type {value}')
            self.__attested_value = value
            assert self.__attested_value 
        else:
            raise Exception(f'Cannot set value for record={self.id}')

    @property
    def has_value(self):
        return self.value is not None

    def __filter_values(self, values: vlist[Value]):
        if not values:
            return None
        lst = list(filter(self.__filter_function, values))
        if self.var.value_filter.upper:
            return lst[:self.upper]
        if self.var.value_filter.lower:
            return lst[-int(self.lower):]
        return vlist(lst)

    def __filter_function(self, value: Value):
        bools = []
        if self.var.value_filter.after_date:
            bools.append(value.date >= self.var.value_filter.after_date)
        if self.var.value_filter.before_date:
            bools.append(value.date <= self.var.value_filter.before_date)
        if self.var.value_filter.value_expression:
            exp = str(value.value) + ' ' + self.var.value_filter.value_expression
            bools.append(eval(exp))
        return False if False in bools else True

    @cached_property
    def filtered_values(self):
        if not self.__must_filter_values:
            return None 
        if not self.__values:
            logging.debug('No values to apply valuefilter')
            return None 
        return self.__filter_values(self.__values)


    # --- NARRATIVE ---
        # Narrative POLICY
    # ---------------
    # If expression found, then narrative TRUE/False/None implies expression result
    # If value_filter found, then arrative TRUE/FALSE/NONE implies value_filter_result
    #   - if count,
    #   - 
    # If not value_filter
    def __narrative_values(self): 
        return {
            '$values' :str(self.values),
            '$value': str(self.value.value) if self.value else "n/a",
            '$date': str(self.value.date) if self.value else 'n/a',
            '$count': str(len(self.values)) if self.values else 'n/a',
        }
    def __get_narrative_for_no_value(self, persona_narrative):
        return persona_narrative.get('None', None) or persona_narrative.get('NoValue', None)
    def __get_narrative_for_bool_value(self, persona_narrative):
        return persona_narrative.get(self.value.value, None)
    def __get_narrative_for_value(self, personal_narrative):
        return personal_narrative.get('HasValue', None) or personal_narrative.get(True, None) or personal_narrative.get(str(self.value.value), None)

    def __sanitize_record_narrative(self, n):
        if not n:
            return None
        for k, v in self.__narrative_values().items():
            n = n.replace(k, v)
        return n 
    def __narrative(self, persona: Persona = Persona.patient):
        
        # 1. No narrative, TODO: Build a default?
        if not self.var.narrative:
            return None 
        
        persona_narrative = self.var.narrative.get(persona.value, None)
        if not persona_narrative:
            return None 

        val_type = type(self.value.value) if self.values != None else NoneType

        result_narrative = None

        if val_type == bool:
            result_narrative = self.__get_narrative_for_bool_value(persona_narrative)
            
        elif val_type == NoneType:
            result_narrative = self.__get_narrative_for_no_value(persona_narrative)
            
        elif val_type == list and len(self.values) == 0:
            
            raise Exception('How handle vlist/list?')
        else: # has_value
            result_narrative = self.__get_narrative_for_value(persona_narrative)

        result_narrative = self.__sanitize_record_narrative(result_narrative)

        return result_narrative
    
    def set_narrative(self, persona: Persona = Persona.patient, variable_data_dict: dict = None):

        if not self.var.narrative:
            return None

        narrative_text = self.__narrative(persona)
        if not narrative_text:
            return None

        if variable_data_dict and self.var.narrative_variables:
            for n_var in self.var.narrative_variables:
                val = variable_data_dict.get(n_var, {}).get('value', '<>')
                narrative_text = narrative_text.replace('$'+n_var, str(val))

        logger.debug(f'narrative for {self.id} from variable_dict={variable_data_dict}, sanitized={narrative_text}')

        self.sanitized_narrative = narrative_text
        return narrative_text

    def test_narratives(self):
        narrative_dict = self.var.narrative 
        assert (self.sanitized_narrative == None) == (narrative_dict == None), f'record={self} narr={narrative_dict} _must_have_narrative'
        return 'PASSED'

        

    def as_dict(self):
        var_dict = self.var.as_dict()
        var_dict = {}
        var_dict.update({
                'value': self.value if self.value else None,
                'values': self.values.representation if self.values else None,
                'date': self.value.date if self.value else None,
                'count': len(self.values) if self.values else None,
            })
        return var_dict
