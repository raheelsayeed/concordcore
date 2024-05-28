#!/usr/bin/env python3

import logging

from fhir.resources import observation, procedure, condition, medication, medicationrequest, questionnaire, questionnaireresponse
from variables.value import Value
from primitives.unit import Unit
from primitives.code import Code

log = logging.getLogger(__name__)

class FHIRValue(Value):

    @property
    def fhirtype(self):
        return self.source[0].resource_type

    @classmethod
    def from_medicationRequest(cls, mr: medicationrequest.MedicationRequest):
        date = mr.authoredOn.date
        coding = mr.medicationCodeableConcept.coding
        codes = [Code(c.coding,c.system,c.display) for c in coding]
        return cls(value=codes, date=date, source=mr)
    
    @classmethod
    def from_procedure(cls, pr):
        log.error(f'unsupported ={pr}')

    @classmethod 
    def from_observation(cls, ob:observation.Observation):
        date = ob.effectiveDateTime or ob.issued or ob.meta.lastUpdate.date
        unit = None
        cd = None
        if ob.code.coding:
            cd = [Code(cc.code, cc.system, cc.display) for cc in ob.code.coding]
        
        # decimal
        if ob.valueQuantity:
            vq = ob.valueQuantity
            value = vq.value
            unit = Unit(vq.code, vq.system, vq.unit)

        # boolean
        elif ob.valueBoolean:
            value = ob.valueBoolean
        # blood pressure
        elif ob.component and (ob.code.coding[0].code == '55284-4' or ob.code.coding[0].code == '85354-9'):
            # value == tuple(sbp, dbp)
            components = ob.component 
            sbp_value = None
            dbp_value = None
            for c in components:
                scode = c.code.coding[0].code
                if scode == '8480-6':
                    sbp_value = c.valueQuantity.value 
                elif scode == '8462-4':
                    dbp_value = c.valueQuantity.value
            if sbp_value == None or dbp_value == None:
                raise ValueError('BP does not have both sbp and dbp')
            value = (sbp_value, dbp_value)
            unit = Unit('mm[Hg]', 'http://unitsofmeasure.org', 'mmHg')

        # codeableconcept
        elif ob.valueCodeableConcept:
            coding = ob.valueCodeableConcept.coding[0]
            cod = Code(coding.code, coding.system, coding.display)
            value = cod
        else:
            raise Exception(f'FHIRValue: Observation value not assigned {ob.id}')

        instance = cls(value=value, unit=unit, date=date, source=[ob])
        instance.code = cd

        return instance

    @property
    def title(self):
        return ",".join([c.display or c.code for c in self.code])

    @classmethod
    def from_condition(cls, c:condition.Condition):
        date = c.recordedDate.date
        if c.code.coding:
            cd = [Code(cc.code, cc.system, cc.display) for cc in c.code.coding]

        instance = cls(value=True, unit=None, date=date, source=[c])
        instance.code = cd
        return instance
    
    @classmethod
    def from_questionnaireResponse(cls, qr: questionnaireresponse.QuestionnaireResponse):
        # 
        # 
        log.info(' ******************* TODO: GET CONCORD Coded AnswersL')
        #
        #
        itm = qr.item
        value = None
        if itm:
            cnt = len(itm)
            if cnt == 1:
                first = itm[0]
                if first and first.answer:
                    ans = first.answer[0]
                    if ans.valueBoolean is not None:
                        value = ans.valueBoolean
                    elif ans.valueQuantity:
                        value = ans.valueQuantity.value 
                    elif ans.valueCoding:
                        value = ans.valueCoding.code 

        date = qr.authored.date
        if not value:
            raise ValueError('Cannot get value from QuestionnarieResponse')
        
        return cls(value=value, unit=None, date=date, source=[qr])



    @classmethod 
    def from_fhir(cls, fhirjson):

        resource_type = fhirjson['resourceType']
        if not resource_type:
            raise ValueError(f'Unknown file, missing resourceType: {fhirjson}')


        unit = None

        # Observation
        if resource_type == 'Observation':
            try:
                ob = observation.Observation.parse_obj(fhirjson)
                return cls.from_observation(ob)
            except Exception as e:
                log.error("error",fhirjson)
                raise e
            

        # Condition
        elif resource_type == 'Condition':
            c = condition.Condition.parse_obj(fhirjson)
            return cls.from_condition(c)
            
        # QuestionnaireResponse
        elif resource_type == 'QuestionnaireResponse':
            qr = questionnaireresponse.QuestionnaireResponse.parse_obj(fhirjson)
            return cls.from_questionnaireResponse(qr)

        elif resource_type == 'MedicationRequest':
            mr = medicationrequest.MedicationRequest.parse_obj(fhirjson)
            return cls.from_medicationRequest(mr)
        
        elif resource_type == 'Procedure':
            pr = procedure.Procedure.parse_obj(fhirjson)
            return cls.from_procedure(pr)

        else:
            raise ValueError(f'Unknown FHIR resource type: {resource_type}')