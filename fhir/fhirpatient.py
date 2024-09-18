
#!/usr/bin/env python3

from functools import cached_property

from fhirclient.models import patient
from primitives.code import Code, CodeSystemType
from variables import record, value, var, age




class FHIRPatient:

    def __init__(self, pt: patient.Patient) -> None:
        """Creates `Record`(s) from FHIR Patient resource"""

        self.pt = pt

        (_race, _eth) = self.race_ethnicity()

        self.race = _race

        self.ethnicity = _eth


    @cached_property
    def name(self):
        return "Name"
    
    @cached_property
    def gender(self): 
        if self.pt.gender:
            v = var.Var.Gender()
            val_code = Code(self.pt.gender, CodeSystemType.concord.value, self.pt.gender)
            val = value.Value(val_code, source=[self.pt])
            rec = record.Record(v, [val])
            return rec
        return None


    @cached_property
    def age(self):
        if self.pt.birthDate:
            from datetime import date
            bd = self.pt.birthDate.date
            today = date.today()
            _age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
            return age.Age(_age)
        else:
            return None        
        

    def race_ethnicity(self):
        exts = self.pt.extension
        if not exts:
            return (None, None)
        
        from ontology.codes import Code
        from ontology.definitions import CodeSystemType
        from ontology.codes import CodeGender, CodeRaceEthnicity
        _race = None 
        _eth = None
        for ex in exts:
            if ex.url == CodeSystemType.USCore_Race.value:
                race_code = ex.extension[0].valueCoding
                if race_code.system == CodeSystemType.CDC_RaceEthnicity.value:
                    raceCode = Code(race_code.code, CodeSystemType.CDC_RaceEthnicity.value, race_code.display)
                    v = var.Var.RaceEthnicity()
                    val = value.Value(raceCode, source=[self.pt])
                    _race = record.Record(v, [val])
            
            if ex.url == CodeSystemType.USCore_Ethnicity.value:
                race_code = ex.extension[0].valueCoding
                if race_code.system == CodeSystemType.CDC_RaceEthnicity.value:
                    raceCode = Code(race_code.code, CodeSystemType.CDC_RaceEthnicity.value, race_code.display)
                    v = var.Var.RaceEthnicity()
                    val = value.Value(raceCode, source=[self.pt])
                    _eth = record.Record(v, [val])
            
        return (_race, _eth)


    def records(self):
        return [
            self.age,
            self.gender,
            self.race,
            self.ethnicity
        ]

        


        


    
    


