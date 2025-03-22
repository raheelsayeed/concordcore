#!/usr/bin/env python3

from .code import Code

UOM_SYSTEM = 'http://unitsofmeasure.org'


class Unit(Code):


    def __str__(self):
        return self.display or self.code

    def __repr__(self):
        return f'Unit: {self.code}|{self.system} display:{self.display}'

    @classmethod
    def mg_dl(cls): return Unit('mg/dL', UOM_SYSTEM)

    @classmethod
    def mmHg(cls): return Unit('mm[Hg]', UOM_SYSTEM, 'mmHg')

    @classmethod
    def uom(cls, code: str, display: str = None):
        return Unit(code, UOM_SYSTEM, display)

    @classmethod 
    def AgeYears(cls): return Unit('a', UOM_SYSTEM, 'years')


if __name__ == '__main__':
    
    print(Unit.mg_dl())
