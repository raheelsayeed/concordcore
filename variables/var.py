#!/usr/bin/env python3


from dataclasses import dataclass, field
from functools import cache, cached_property
from re import findall
from typing import Any

import logging, humanize

from datetime import datetime, timedelta
from primitives.errors import VarError
from primitives.types import Persona, ValueType, YMLStrEnum
from primitives.code import Code
from primitives.varstring import VarString

log = logging.getLogger(__name__)

class VarType(YMLStrEnum):
    Undetermined = 'undetermined'
    laboratory = 'laboratory-blood-test'
    vital_sign = 'vital-sign'
    question = 'question'
    condition = 'condition'
    demographics = 'demographics'
    eligibility_criteria = 'eligibility_criteria'
    display = 'display'

class ValueFilter:

    def __init__(self, before:int=None, after:int=None, count:int=None, value_expression:str=None, upper=None, lower=None):
        if before and after and before >= after:
            raise ValueError(f'ValueFilter error; before:{before} cannot be >= to after:{after}')
        today = datetime.today()
        self.after_date = today - timedelta(days=after) if after else None 
        self.before_date = today - timedelta(days=before) if before else None 
        self.count = count
        self.value_expression = value_expression
        self.upper = upper 
        self.lower = lower


@dataclass(frozen=True)
class Narrative:

    FORMAT_VALUE = True
    DEFAULT_LAB_HASVALUE    = 'Lab Results: `$self.values`'
    DEFAULT_LAB_NOVALUE     = 'Lab Results: N/F'
    
    data: dict
    value_span_class_tag = '<span class="ch-value">{}</span>'
    def formatted_value(self, value):
        return self.value_span_class_tag.format(value)
    @property
    def _compliance_dict(self):
        return self.data.get('compliance', None)
    @property
    def variables(self):
        return self.__narrative_singleline_text.variable_identifiers
    @property
    def tags(self):
        return self.__narrative_singleline_text.tags

    def __nested_values(self, d):
        for v in d.values():
            if isinstance(v, dict):
                yield from self.__nested_values(v)
            else:
                yield v 

    @cached_property
    def __narrative_singleline_text(self):
        all_narratives = list(self.__nested_values(self.data))
        if all_narratives:
            string = ' '.join(all_narratives) 
            var_string = VarString(string)
            log.debug(var_string)
            return var_string
        else:
            return None

    def get_compliance_text(self, for_value: bool, persona: Persona = Persona.patient, sanitization_dict: dict = None):

        if for_value is None or self._compliance_dict is None:
            return None

        return self.__get_text(self._compliance_dict, for_value, persona, sanitization_dict)

    def get_text(self, for_value: Any, persona: Persona = Persona.patient, sanitization_dict: dict = None, default = None):

        return self.__get_text(self.data or default, for_value, persona, sanitization_dict)


    def __get_text(self, narrative_dict: dict, for_value: Any, persona: Persona = Persona.patient, sanitization_dict: dict = None):
        
        text = None
        narrative_dict = narrative_dict.get(persona.value, None)

        if not narrative_dict:
            log.debug('no narrative found')
            return None 

        if for_value != None:
            if type(for_value) == bool:
                text = narrative_dict.get(for_value, None)
            else:
                text = narrative_dict.get(str(for_value), None) or narrative_dict.get('HasValue', None) or narrative_dict.get(True, None)
        else:
            text = narrative_dict.get('NoValue', None)

        log.debug(f'text={text}, n={ narrative_dict},  {for_value}')

        
        # self santized values
        # slf = sanitization_dict.get('self', None)
        if text and self.tags:
            if sanitization_dict:
                for n_var in self.tags:
                    split = n_var.split('.')
                    val = sanitization_dict.get(split[0], {}).get(split[1] if len(split) > 1 else 'value', '-n/a-')
                    if isinstance(val, datetime):
                        val = humanize.naturaldate(val)

                    val = self.formatted_value(str(val)) if self.FORMAT_VALUE else str(val)
                    text = text.replace('$'+n_var, val)
         
        log.debug(f'__get_text_Narrative Tags={self.tags} for text={text}')
        return text

    
@dataclass(frozen=True)
class Var:
    id: str 
    title: str = None 
    description: str = None
    code: Any = None
    category: VarType = VarType.Undetermined
    type: str = None
    user_attestable: bool = True
    required: bool = True
    reconcile: bool = False 
    question: str = None 
    narrative: dict = None 
    value_filter: str = None 
    validator: dict = None
    narr: Narrative = None

    @property
    def code_string(self):
        return ','.join([c.as_string for c in self.code]) if self.code else None

    def __hash__(self):
        return hash(self.__repr__)

    def __eq__(self, __o: object) -> bool:

        if isinstance(__o, Var) == False:
            return super().__eq__(__o)        

        if self.code and __o.code:
            my_codes = set(map(lambda c: c.as_string, self.code))
            right_codes = set(map(lambda c: c.as_string, __o.code))
            matched = (len(list(my_codes & right_codes)) > 0)
            return matched

        return False

    @cached_property
    def value_type(self):
        if not self.type: 
            return None
        
        return ValueType.YAML(self.type)

    @classmethod
    def Sample(cls):
        v = Var('1', 'title', 'descr', None, VarType.condition, ValueType.boolean)
        return v

    @classmethod
    def instantiate_from_yaml(cls, yml):
        try: 

            codes = None
            if 'code' in yml:    
                codes = []
                for key, val in yml['code'].items():
                    for code in val:
                        cd = Code.YAML(code, key)
                        codes.append(cd)
            
            yml['code'] = codes or None 
                
            vf = None
            if 'filter' in yml:
                vfdict = yml['filter']
                vf = ValueFilter(
                        vfdict.get('before', None),
                        vfdict.get('after', None),
                        vfdict.get('count', None),
                        vfdict.get('expression', None),
                        vfdict.get('upper', None),
                        vfdict.get('lower', None)
                )
                yml.pop('filter')
                yml['value_filter'] = vf
            
            if 'narrative' in yml:
                narrative = Narrative(yml['narrative'])
                yml['narr'] = narrative

            cat = yml.get('category', None)
            if cat:
                yml['category'] = VarType.YAML(yml['category'])


            instance = cls(**yml)
            if instance.narrative != None:
                assert isinstance(instance.narr, Narrative)
            return instance

        except Exception as e:
            raise Exception(f'Cannot instantiate {cls.__name__} dict={yml} error={e}')
        


    def as_dict(self):
        return {
                'id': self.id,
                'title': self.title,
                'code': self.code_string[:20] if self.code else '',
                'required': self.required, 
                'attestable': self.user_attestable,
            }



class VarPanelValidationError(VarError):

    def __init__(self, var: Var, value):
        panel = var.validator.get('panel')
        message = f'Value must be="{panel}" got value={value}'
        super(VarPanelValidationError, self).__init__(message, var.id)

class VarImplausibleError(VarError):

    def __init__(self, var: Var, value):
        plausible_expression = var.validator.get('plausible')
        message = f'Value must be="{plausible_expression}" got value={value}'
        super(VarImplausibleError, self).__init__(message, var.id)

