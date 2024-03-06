#!/usr/bin/env python3

from dataclasses import dataclass, field
from functools import cached_property
from re import findall
from typing import Any
from enum import Enum
from datetime import datetime, timedelta
from ..primitives.types import ValueTypePrimitives
from ..primitives.code import Code

class VarType(Enum):
    Undetermined = 'undetermined'
    laboratory = 'laboratory-blood-test'
    vital_sign = 'vital-sign'
    question = 'question'
    condition = 'condition'
    demographics = 'demographics'
    eligibility_criteria = 'eligibility_criteria'
    display = 'display'

    @staticmethod
    def YAML(t):
        vt = None 
        try:
            vt = VarType[t]
        except Exception:
            vt = VarType.Undetermined
        return vt
    

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


def Variable_Identifiers_IN(text):
    matches = Get_Variable_Identifiers(text=text)
    found = [m.split('.')[0] for m in matches] if matches else None 
    if found:
        return list(set(found))
def Get_Variable_Identifiers(text):
    if not text:
        return None 
    pattrn = r"\$([A-Za-z][A-Za-z_.0-9]+[A-Za-z0-9])+"
    matches = findall(pattrn, text)
    return matches if matches else None


@dataclass(frozen=True)
class Var:
    id: str 
    title: str = None 
    description: str = None
    code: Any = None
    category: VarType  = VarType.Undetermined
    type: ValueTypePrimitives = None
    user_attestable: bool = True
    required: bool = True
    reconcile: bool = False 
    question: str = None 
    narrative: dict = None 
    value_filter: str = None 
    validator: dict = None

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
    def narrative_variables(self):
        if self.narrative:
            _all_narratives = []
            for k, v in self.narrative.items():
                if not isinstance(v, dict):
                    raise TypeError(f'Excepted narrative value to be a dict, found {type(v)} var={yml["id"]}')
                narratives = v.values() 
                if narratives:
                    _all_narratives.extend(narratives)
            _all_narratives = ' '.join(_all_narratives)
            return Variable_Identifiers_IN(_all_narratives)
        else:
            return None

    @classmethod
    def Sample(cls):
        v = Var('1', 'title', 'descr', None, VarType.condition, ValueTypePrimitives.boolean)
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

            cat = yml.get('category', None)
            if cat:
                yml['category'] = VarType.YAML(yml['category'])


            return cls(**yml)

        except Exception as e:
            raise Exception(f'Cannot instantiate {cls.__name__} dict={yml} error={e}')



        instance = cls(
            id=                 yml['id'],
            title=              yml.get('title', None),
            category=           yml.get('category', None),
            description=        yml.get('description', None),
            type=               yml.get('type', None),
            narrative=          yml.get('narrative', None),
            required=           yml.get('required', None),
            question=           yml.get('question', None),
            user_attestable=    yml.get('user_attestable', None),
            reconcile=          yml.get('reconcile', None),
            value_filter=       vf,
            validator=          yml.get('validate', None)
        )

        return instance


    def as_dict(self):
        return {
                'id': self.id,
                'title': self.title,
                'code': self.code_string[:20] if self.code else '',
                'required': self.required, 
                'attestable': self.user_attestable,
            }

