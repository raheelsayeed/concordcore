#!/usr/bin/env python3

import json, os, logging

log = logging.getLogger(__name__)

SAMPLE_FHIR_DATA_PATH = 'samples/fhir_r4/'
SAMPLE_NDJSON_FILES = SAMPLE_FHIR_DATA_PATH + '/ndjson/'


def sample_fhir_values():

    from fhir_variables.fhirvalue import FHIRValue

    obs = read_ndjson(SAMPLE_NDJSON_FILES + 'Observation.ndjson')
    conditions = read_ndjson(SAMPLE_NDJSON_FILES + 'Condition.ndjson')
    medreq = read_ndjson(SAMPLE_NDJSON_FILES + 'MedicationRequest.ndjson')
    procedures = read_ndjson(SAMPLE_NDJSON_FILES + 'Procedure.ndjson')

    all = obs + conditions + medreq + procedures
    errs = [] 
    fhir_values = [] 

    for jsn in all:
        try: 
            v = FHIRValue.from_fhir(jsn)
            fhir_values.append(v) 
        except Exception as e:
            errs.append(e) 

    log.error(errs)
    return fhir_values



def read_ndjson(filepath):
    # Reduce mem load, can use "YEILD"
    
    fhirresources = []
    try:
        with open (filepath, 'r') as file_:
            for line in file_:
                json_ = json.loads(line)
                fhirresources.append(json_)
        return fhirresources if len(fhirresources) > 0 else None
    except Exception as e:
        raise e

def readsample(fn):
    fn = f'{SAMPLE_FHIR_DATA_PATH}' + fn 
    try:
        with open(fn, 'r') as f:
            jsn = json.load(f)
            return jsn 
    except Exception as e:
        log.error(e)


def sample_data():
    jsons = [pos_json for pos_json in os.listdir(SAMPLE_FHIR_DATA_PATH) if pos_json.endswith('.json')]
    bundle = []
    for fn in jsons:
        log.info(f'Sample-data-from={fn}')
        try:
            jsn = readsample(fn)
            bundle.append(jsn)
        except Exception as e:
            log.error(e)
    return bundle



def sample_healthcontext():

    from concordcore.healthcontext import HealthContext, Persona
    from concordcore.variables.record import Record
    from concordcore.variables.value import Value
    from concordcore.variables.var import Var 
    from concordcore.primitives.code import Code
    from ontology.presets import Age
    from ontology.codes import ConcordDefinition, CodeRaceEthnicity, CodeGender, Code_LabLoinc
    from datetime import datetime, timedelta


    age     = Age(50)
    gender  = ConcordDefinition.code_Gender.as_record(CodeGender.female_snomed.value)
    race    = ConcordDefinition.code_Ethnicity.as_record(CodeRaceEthnicity.White.value)

    dm      = Record(Var('DM',code=[Code.snomed('44054006')]), [Value(True)])
    chol    = Record(Var('Chol', code=[Code_LabLoinc.cholesterol.value]), [Value(200),Value(198),Value(231)])
    bp    = Record(Var('BP', code=[Code.loinc('55284-4')]), [Value((130, 90))])

    ldl     = Record(Var('LDL', code=[Code.loinc('13457-7')]), [
        Value(123, date=datetime.today() - timedelta(days=1200)),
        Value(222),
        Value(155),
        Value(122),
        Value(232),
        Value(230),
        Value(144)
        ])
    hdl     = Record(Var('HDL', code=[Code.loinc('2085-9')]),  [Value(55),Value(66),Value(76)])
    tg     = Record(Var('TG', code=[Code_LabLoinc.triglycerides_1.value, Code_LabLoinc.triglycerides_2.value]),  [Value(255),Value(266),Value(276)])
    cr      = Record(Var('Cr'), [Value(1.2), Value(1.0), Value(1.22)])

    

    # scc vars 
    scc_vars = [ #51925
            Record(Var('cc_symptoms', code=[Code.snomed('symptoms_cc')]), [Value(True)]),
            Record(Var('CervicalCytology', code=[Code.snomed('168406009')]), [Value(True)]),
            Record(Var('Hysterecmey No Cervix', code=[Code.cpt('51925')]), [Value(False)])
                
            ]


    lung_cc = [

            Record(Var('smoking_duration_years', code=[Code.loinc('67741-9')]),
                        [Value(16)]),
            Record(Var('smoking_per_day', code=[Code.loinc('63640-7')]),
                        [Value(23)]),
            Record(Var('smoking_status_loinc', code=[Code.loinc('72166-2')]), 
                        [Value(Code.snomed('8517006'))])
            

        ]

    recs = [
        age, gender, race,
        dm, chol, ldl, hdl, cr, 
        tg, 
        bp
    ]

    return HealthContext(recs, Persona.patient)


if __name__ == '__main__':

    dat = sample_fhir_values()
    print(dat)
