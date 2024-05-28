#!/usr/bin/env python3

from dataclasses import dataclass, field, InitVar
from functools import cache, cached_property
from datetime import datetime

import logging, humanize


from types import NoneType
from typing_extensions import Self
from primitives.errors import VarError


from primitives.varstring import EvaluatorString, ValidationExpression
from variables.var import Narrative, Var, VarError, VarImplausibleError, VarPanelValidationError
from variables.value import Value
from primitives.vlist import vlist
from primitives.types import Persona

logger = logging.getLogger(__name__)

@dataclass
class Record:

    var: Var
    __values: vlist[Value] = None 
    __attested_value: Value = field(init=False, default=None)
    __narrative: str = field(init=False, default=None)
    __plausible_validator: ValidationExpression = field(init=False)
    __panel_validator: EvaluatorString = field(init=False)
    __persona: Persona = field(init=False)

    def __post_init__(self):
        self.__values = vlist(self.__values) if self.__values else None
        if self.var.validator:
            logger.debug(self.var.validator)
            self.__panel_validator = EvaluatorString(self.var.validator['panel']) if 'panel' in self.var.validator else None 
            self.__plausible_validator = ValidationExpression(self.var.validator['plausible']) if 'plausible' in self.var.validator else None 
        else:
            self.__panel_validator = None
            self.__plausible_validator = None
        # debug purpose:
        self.__persona = None


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
            return self.filtered_values
        else:
            return self.__values

    @property
    def attested_value(self):
        return self.__attested_value
    
    @attested_value.setter
    def attested_value(self, value):
        if self.var.user_attestable:
            if self.validate(value=value):
                self.__attested_value = value
                assert self.__attested_value 
        else:
            raise ValueError(f'Variable is not attestable var={self.id}')
        self.set_narrative(persona=self.__persona)

    @property 
    def narrative(self):
        return self.__narrative
    @property
    def has_value(self):
        return self.value is not None

    def __filter_values(self, values: vlist[Value]):
        if not values:
            logging.debug('No values to apply valuefilter')
            return None
        lst = list(filter(self.__function_filter, values))
        if self.var.value_filter.upper:
            return lst[:self.upper]
        if self.var.value_filter.lower:
            return lst[-int(self.lower):]
        return vlist(lst)

    def __function_filter(self, value: Value):
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
        if self.__must_filter_values == False:
            return None
        return self.__filter_values(self.__values)
    
    def set_narrative(self, persona: Persona = Persona.patient, variable_data_dict: dict = None):


        narr = self.var.narr or self.default_narratives

        if not narr:
            raise Exception('this is a problem, self.var.narr == nil ? then check if default narr available')
            return None 

        if variable_data_dict:
            variable_data_dict.update({"self": self.as_dict()})
        else:
            variable_data_dict = {"self": self.as_dict()}

        self.__narrative = narr.get_text(self.value.value if self.value else None, persona, variable_data_dict, default=self.default_narratives.data)
        logger.debug(f'Santized-Narrative={self.id} variable_dict={variable_data_dict}, narrative_text={self.narrative}, tags={self.var.narr}, default={self.default_narratives.data}')
        # exit()

        # only for debug reasons
        self.__persona = persona
        return self.__narrative

    @cached_property
    def default_narratives(self):

        data = {
            Persona.patient.value: {
                "HasValue": "Following results in your record: $self.values",
                "NoValue": "Not found in your record",
                True: "Following results in your record: $self.values",
                False: "Not found in your record"


            },
            Persona.provider.value: {
                "HasValue": "Values: $self.values",
                True: "Values: $self.values",
                "NoValue": "Not in record",
                False: "Not in record"
            }

        }
        return Narrative(data)

        


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

    def validate(self, value: Value = None, records: list[Self] = None, strict:bool = True):

        val = value or self.value

        if val is None:
            logger.warning(f'Record={self.id} has no value to validate')
            return True
        
        if self.var.value_type:
            vtype = self.var.value_type.type
            if vtype == bool and type(val.value) == str and (val.value not in ['False', 'True']):
                raise VarError(f'Invalid value_type={type(val.value)}; need={vtype}', self.id)
            if vtype(val.value) == None:
                raise VarError(f'Invalid value_type={type(val.value)}; need={vtype}', self.id)


        if self.__plausible_validator:
            try:
                res = self.__plausible_validator.evaluate(value=val.value)
                if not res:
                    e = VarImplausibleError(self.var, val.value)
                    if strict:
                        raise e
                    else: 
                        logger.warning(e)
            except Exception as e:
                raise e

        if self.__panel_validator and records:
            try:
                expression_vars = self.__panel_validator.variables
                filtered = list(filter(lambda r: r.id in expression_vars, records))
                f_dict = {r.id: r.value.value for r in filtered}
                f_dict.update({'value': self.value.value})
                res = self.__panel_validator.evaluate(f_dict)
                if not res:
                    e = VarPanelValidationError(self.var, val.value)
                    if strict:
                        raise e 
                    else: 
                        logger.warning(e)
            except Exception as e:
                raise e
        
        return True


        

    def test_narratives(self):
        
        return
        if not self.var.narr:
            return 'NO-NARRATIVE'

        d = self.var.narr.data
        patient = d.get('patient', None)
        provider = d.get('provider', None)

        if self.__persona == Persona.patient:
            assert self.narrative if patient else None,  f'record={self.id} value={self.value}, narr={patient} _must_have_narrative'

        if self.__persona == Persona.practitioner:
            assert self.narrative if provider else None,  f'record={self.id} value={self.value}, narr={provider} _must_have_narrative'

        return 'PASSED'
            



        assert (self.narrative == None) == (narrative_dict == None), f'record={self} narr={narrative_dict} _must_have_narrative'
        return 'PASSED'
