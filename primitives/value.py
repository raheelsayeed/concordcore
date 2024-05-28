#!/usr/bin/env python3

from typing import Protocol


class ValueProtocol(Protocol):

    def representation(self):
        ...
