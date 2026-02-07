#!/usr/bin/env python3

from ontology.definitions import CodeSystemType
from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class Code:

    code: str
    system: str
    display: str = None
    parent_code: 'Code | None' = None

    def __str__(self) -> str:
        return self.display or self.as_string

    def __repr__(self) -> str:
        return self.as_string

    @staticmethod
    def YAML(c, s):
        sys = None
        try:
            sys = CodeSystemType[s].value
        except Exception:
            sys = s
        return Code(c, sys)

    @cached_property
    def as_string(self):
        return self.system + '|' + self.code

    def __eq__(self, __o: object) -> bool:
        # if type(self) == type(right):
        if isinstance(__o, Code):
            return  self.as_string == __o.as_string
        else:
            return super().__eq__(__o)

    def is_descendant_of(self, ancestor: 'Code') -> bool:
        """Check if this code is a descendant of the given ancestor code.

        Walks up the parent_code chain to find a match.

        Args:
            ancestor: The potential ancestor Code to check against

        Returns:
            True if ancestor is found in the parent chain
        """
        current = self.parent_code
        while current is not None:
            if current == ancestor:
                return True
            current = current.parent_code
        return False
    
    @classmethod
    def loinc(cls, code, display=None, parent_code=None):
        return Code(code, CodeSystemType.loinc.value, display, parent_code)

    @classmethod
    def snomed(cls, code, display=None, parent_code=None):
        return Code(code, CodeSystemType.snomed.value, display, parent_code)

    @classmethod
    def cpt(cls, code, display=None, parent_code=None):
        return Code(code, CodeSystemType.cpt.value, display, parent_code)

    @classmethod
    def rxnorm(cls, code, display=None, parent_code=None):
        return Code(code, CodeSystemType.rxnorm.value, display, parent_code)

    @classmethod
    def race_ethnicity(cls, code, display=None, parent_code=None):
        return Code(code, CodeSystemType.CDC_RaceEthnicity.value, display, parent_code)

    @classmethod
    def concord(cls, code, display=None, parent_code=None):
        return Code(code, CodeSystemType.concord.value, display, parent_code)                
    
