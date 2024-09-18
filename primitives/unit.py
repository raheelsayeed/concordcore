#!/usr/bin/env python3

from .code import Code

class Unit(Code):

    def __str__(self):
        return self.display or self.code

    def __repr__(self):
        return f'Unit: {self.code}|{self.system} display:{self.display}'

    @classmethod
    def mg_dl(cls): return Unit('mg/dL', 'http://unitsofmeasure.org')

    @classmethod
    def uom(cls, code: str, display: str = None):
        return Unit(code, 'http://unitsofmeasure.org', display)


if __name__ == '__main__':
    
    print(Unit.mg_dl())