#!/usr/bin/env python3

from primitives.code import Code
from ontology.definitions import CodeSystemType
from variables.var import Var
from variables.value import Value
from variables.record import Record
from enum import Enum

class CodeRaceEthnicity(Enum):
    White               = Code.race_ethnicity('2106-3', 'White')
    AfricanAmerican     = Code.race_ethnicity('2058-6', 'African American')
    African             = Code.race_ethnicity('2060-2', 'African')
    Asian               = Code.race_ethnicity('2186-5', 'Asian')

# http://fhir.ch/ig/ch-ems/ValueSet-IVR-VS-sex.html
class CodeGender(Enum):
    female_snomed       = Code.snomed('248152002', 'Female')
    male_snomed         = Code.snomed('248153007', 'Male')
    unknown_sex         = Code.snomed('184115007', 'Patient sex unknown')

# https://clinicaltables.nlm.nih.gov/apidoc/loinc/v3/doc.html
# https://clinicaltables.nlm.nih.gov/loinc_items/v3/search\?terms\=2089-1

Concord_Code_Age         = 'Age'
Concord_Code_Gender      = 'Gender'
Concord_Code_Ethnicity   = 'Ethnicity'

# ----- Static Private Variables ----- #
class ConcordDefinition(Enum):
    code_Age         = 'Age'
    code_Gender      = 'Gender'
    code_Ethnicity   = 'Ethnicity'
    
    def as_code(self):
        """Preset Code"""
        return Code(self.value, CodeSystemType.concord.value, self.value)

    def as_record(self, value_code: Code):
        return Record(Var(self.value, self.value, code=[self.as_code()]), [Value(value_code)])


class Code_LabLoinc(Enum):
    triglycerides_1 = Code.loinc('2571-8', 'Triglycerides')
    triglycerides_2 = Code.loinc('3043-7', 'Triglycerides')
    cholesterol     = Code.loinc('2093-3', 'Cholesterol [Mass/volume] in Serum or Plasma')



    
