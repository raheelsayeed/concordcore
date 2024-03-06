#!/usr/bin/env python3

from enum import Enum
from .renderer import BaseRenderer



class Cards(BaseRenderer):

    def rendering_folder_path(self):
        import os
        path = os.path.dirname(__file__) + '/cards'
        return path

class Document(BaseRenderer):

    def rendering_folder_path(self):
        import os
        path = os.path.dirname(__file__) + '/document'
        return path


