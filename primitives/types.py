#!/usr/bin/env python3

import logging
from enum import StrEnum
from typing import final
from unicodedata import decimal
from datetime import date

log = logging.getLogger(__name__)

class YMLStrEnum(StrEnum):
    
    @classmethod
    def YAML(cls, e_num):
        vt = None 
        try:
            vt = cls(e_num)
        except Exception as e:
            log.error(e)
            raise e
        finally:
            return vt
    
class Persona(YMLStrEnum):
    provider     = 'provider'
    patient      = 'patient'
    guardian     = 'guardian'


class ValueType(YMLStrEnum):
    string = "string"
    decimal= "decimal"
    integer= "integer"
    date   = "date" 
    boolean= "boolean"

    @property
    def type(self):
        if self == 'boolean':
            return bool 
        if self == 'date':
            
            return date 
        if self == 'integer':
            return int 
        if self == 'string':
            return str 
        if self == 'decimal':
            return decimal
        else:
            raise Exception('Need configuration')



