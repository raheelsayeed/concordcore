#!/usr/bin/env python3
import logging

from concordcore.evaluation import EvaluatedRecord
from concordcore.concord import Concord
from concordcore.variables.value import Value
from .inputprotocol import InputProtocol

log = logging.getLogger(__name__)

# command line input
class CLI(InputProtocol):

    def __init__(self, concord: Concord):
        self.concord = concord
        
    def run(self, default=True, debug_skip=True):

        self.prepare()

        from clog import pt
        attestable_vars = self.concord.sufficiency_result.attestation_variables
        if not attestable_vars:
            return True 

        for av in attestable_vars:
            # if not av.record.var.required:
            #     continue
            if debug_skip:
                self.get_input(av, default, True)
                log.warning(f' DebugMode: Assigned {av.record.var.id} value:{default} recordtype={type(av.record)}')
                # assert av.record.value
        return True

        
    def get_input(self, av: EvaluatedRecord, default, force=False):

        if force:
            av.record.attested_value = Value(True, source=['attested-force-debug'])
            # av.record.values = [Value(True, source=['attested-force-debug'])]
            
            return 

        try:
            input_value = input(f'Enter True or False--> {av.record.var.title or av.record.var.id}: ')
            if not input_value:
                input_value = default
                log.warning(f' defaulting to {default}')
            # add a method to validate answer from CLI 
            # method should be in ... 
            
            av.record.values = [Value(input_value, source='attested')]
            # return input_value
        except Exception as e:
                log.error(e, 'Please try again: ')
                return self.get_input(av)
        
