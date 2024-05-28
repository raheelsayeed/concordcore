#!/usr/bin/env python3
import logging
from primitives.types import ValueType            
from datetime import datetime

from core.evaluation import EvaluatedRecord
from core.concord import Concord
from variables.value import Value
from .inputprotocol import InputProtocol

log = logging.getLogger(__name__)

# command line input
class CLI(InputProtocol):

    def __init__(self, concord: Concord):
        self.concord = concord
        
    def run(self, default=True, debug_skip=False):

        self.prepare()

        from clog import pt
        attestable_vars = self.concord.sufficiency_result.attestation_variables
        if not attestable_vars:
            return True 

        for av in attestable_vars:
            # if not av.record.var.required:
            #     continue
            if debug_skip:
                _val = True
                if av.record.var.value_type == ValueType.date:
                    _val = datetime.today()
                val = Value(_val, source=['attested-force-debug'])
                av.record.attested_value = val
                log.warning(f' DebugMode: Assigned record_id={av.record.var.id} value={_val} recordtype={type(av.record)}')
            else:
                log.warning(f'Please enter values for the attestable user records:')
                self.get_input(av, None)
        return True

        
    def get_input(self, av: EvaluatedRecord, default):

        while True:
            input_value = input(f'Enter value {av.record.var.value_type or ""} or {av.record.var.title or av.record.id}: ')
            try: 
                av.record.attested_value = Value(input_value, source=['attested'])
                assert av.record.has_value
                return True
            except Exception as e:
                log.error(e)
                print('Please try again')
                
        return True




