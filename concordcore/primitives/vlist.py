#!/usr/bin/env python3


class vlist(list):

    def __init__(self, iterable):
        super().__init__(sorted(iterable, key=lambda v:v.date, reverse=True))

    def __str__(self) -> str:
        return self.representation

    @property
    def representation(self) -> str:
        if self == None:
            return None             
        return ', '.join([str(v.value) for v in self])