#!/usr/bin/env python3

from enum import Enum

class Persona(Enum):
    practitioner = 'pracitioner'
    patient      = 'patient'
    guardian     = 'guardian'

class ValueTypePrimitives(Enum):
    string = "string"
    decimal= "decimal"
    integer= "integer"
    date   = "date" 
    boolean= "boolean"


