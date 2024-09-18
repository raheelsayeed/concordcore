#!/usr/bin/env python3

from enum import Enum
from .renderer import BaseRenderer

class LocalRenderer(BaseRenderer):

    def rendering_folder_path(self):
        import os
        path = os.path.dirname(__file__) + f'/{self.id}'
        return path


    
