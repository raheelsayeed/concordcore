#!/usr/bin/env python3

# --- Singleton Meta class to enable interactions 
# --- apps should subclass 

from typing import Protocol



class InputProtocol(Protocol):

    def validate(self, value, variable, structure_definition = None):
        ... 

    def prepare(self):
        ...  

    def run(self):
        ...  


