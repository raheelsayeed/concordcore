#!/usr/bin/env python3


class vlist(list):
    """Optimized value list with optional pre-sorting and cached representation."""
    __slots__ = ('_repr_cache',)

    def __init__(self, iterable, presorted=False):
        if presorted:
            super().__init__(iterable)
        else:
            super().__init__(sorted(iterable, key=lambda v: v.date, reverse=True))
        object.__setattr__(self, '_repr_cache', None)

    def __str__(self) -> str:
        return self.representation

    @property
    def representation(self) -> str:
        if not self:
            return None
        # Use cached representation
        cache = object.__getattribute__(self, '_repr_cache')
        if cache is None:
            cache = ', '.join(str(v.value) for v in self)
            object.__setattr__(self, '_repr_cache', cache)
        return cache