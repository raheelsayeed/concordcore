
#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class ValueDate:
    dt: datetime


    def date(self):
        return self.dt.date()

    def __str__(self) -> str:
        return self.dt.strftime('%Y-%m-%d')
    def __lt__(self, other) -> bool:
        return self.dt < other.dt
    def __gt__(self, other) -> bool:
        return self.dt > other.dt