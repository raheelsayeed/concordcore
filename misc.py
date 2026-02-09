#!/usr/bin/env python3

import json, os, logging

log = logging.getLogger(__name__)

SAMPLE_FHIR_DATA_PATH = 'samples/fhir_r4/'
SAMPLE_NDJSON_FILES = SAMPLE_FHIR_DATA_PATH + '/ndjson/'


def sample_fhir_values():

    from concordcore.fhir_parsers.fhirvalue import FHIRValue

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



def sample_healthcontext(persona_text = 'patient'):

    from concordcore.core.healthcontext import HealthContext, Persona
    from concordcore.variables.record import Record
    from concordcore.variables.value import Value
    from concordcore.variables.var import Var
    from concordcore.variables.age import Age
    from concordcore.primitives.code import Code
    from concordcore.ontology.codes import ConcordDefinition, CodeRaceEthnicity, CodeGender, Code_LabLoinc
    from datetime import datetime, timedelta


    age     = Age(50)
    gender  = ConcordDefinition.code_Gender.as_record(CodeGender.female_snomed.value)
    race    = ConcordDefinition.code_Ethnicity.as_record(CodeRaceEthnicity.White.value)

    dm      = Record(Var('DM',code=[Code.snomed('44054006')]), [Value(True)])
    chol    = Record(Var('Chol', code=[Code_LabLoinc.cholesterol.value]), [Value(300),Value(311),Value(310)])
    bp    = Record(Var('BP', code=[Code.loinc('55284-4')]), [Value((130, 90))])

    ldl     = Record(Var('LDL', code=[Code.loinc('13457-7')]), [
        Value(123, date=datetime.today() - timedelta(days=1200)),
        Value(122),
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

    # USPSTF Hypertension Screening variables
    hypertension_vars = [
        Record(Var('systolic_bp', code=[Code.loinc('8480-6')]), [Value(138)]),
        Record(Var('diastolic_bp', code=[Code.loinc('8462-4')]), [Value(88)]),
        Record(Var('known_hypertension'), [Value(False)]),
        Record(Var('cardiovascular_disease'), [Value(False)]),
        Record(Var('chronic_kidney_disease'), [Value(False)]),
        Record(Var('diabetes_mellitus'), [Value(True)]),  # From DM above
        Record(Var('is_smoker'), [Value(False)]),
        Record(Var('family_history_hypertension'), [Value(True)]),
        Record(Var('overweight_obese'), [Value(True)]),
        Record(Var('physically_inactive'), [Value(False)]),
        Record(Var('high_sodium_diet'), [Value(False)]),
        Record(Var('excessive_alcohol'), [Value(False)]),
        Record(Var('antihypertensive_medications'), [Value(False)]),
    ]

    # USPSTF HIV Screening variables
    hiv_vars = [
        Record(Var('is_pregnant'), [Value(False)]),
        Record(Var('in_labor'), [Value(False)]),
        Record(Var('known_hiv_positive'), [Value(False)]),
        Record(Var('has_had_hiv_test'), [Value(False)]),
        Record(Var('last_hiv_test_negative'), [Value(False)]),
        Record(Var('msm'), [Value(False)]),
        Record(Var('multiple_sex_partners'), [Value(False)]),
        Record(Var('unprotected_sex'), [Value(False)]),
        Record(Var('transactional_sex'), [Value(False)]),
        Record(Var('partner_hiv_positive'), [Value(False)]),
        Record(Var('partner_high_risk'), [Value(False)]),
        Record(Var('injection_drug_use'), [Value(False)]),
        Record(Var('shares_needles'), [Value(False)]),
        Record(Var('has_sti'), [Value(False)]),
        Record(Var('requested_sti_testing'), [Value(False)]),
        Record(Var('high_prevalence_setting'), [Value(False)]),
    ]

    # USPSTF Diabetes Screening variables
    diabetes_vars = [
        Record(Var('BMI', code=[Code.loinc('39156-5')]), [Value(28.5)]),
        Record(Var('known_diabetes'), [Value(False)]),
        Record(Var('fasting_glucose', code=[Code.loinc('1558-6')]), [Value(105)]),
        Record(Var('hba1c', code=[Code.loinc('4548-4')]), [Value(5.9)]),
        Record(Var('gestational_diabetes_history'), [Value(False)]),
        Record(Var('pcos'), [Value(False)]),
        Record(Var('is_asian_american'), [Value(False)]),
    ]

    # USPSTF Colorectal Cancer Screening variables
    crc_vars = [
        Record(Var('prior_colorectal_cancer'), [Value(False)]),
        Record(Var('inflammatory_bowel_disease'), [Value(False)]),
        Record(Var('lynch_syndrome'), [Value(False)]),
        Record(Var('familial_adenomatous_polyposis'), [Value(False)]),
        Record(Var('prior_adenomatous_polyps'), [Value(False)]),
        Record(Var('family_history_crc'), [Value(False)]),
        Record(Var('rectal_bleeding'), [Value(False)]),
        Record(Var('unexplained_weight_loss'), [Value(False)]),
        Record(Var('change_in_bowel_habits'), [Value(False)]),
        Record(Var('abdominal_pain'), [Value(False)]),
        Record(Var('iron_deficiency_anemia'), [Value(False)]),
    ]

    # USPSTF Hepatitis C Screening variables
    hcv_vars = [
        Record(Var('known_hcv_positive'), [Value(False)]),
        Record(Var('has_had_hcv_test'), [Value(False)]),
        Record(Var('last_hcv_test_negative'), [Value(False)]),
        Record(Var('current_injection_drug_use'), [Value(False)]),
        Record(Var('past_injection_drug_use'), [Value(False)]),
        Record(Var('received_blood_transfusion_before_1992'), [Value(False)]),
        Record(Var('long_term_hemodialysis'), [Value(False)]),
        Record(Var('born_to_hcv_positive_mother'), [Value(False)]),
        Record(Var('incarceration_history'), [Value(False)]),
        Record(Var('intranasal_drug_use'), [Value(False)]),
        Record(Var('unregulated_tattoo'), [Value(False)]),
        Record(Var('hiv_positive'), [Value(False)]),
    ]

    # USPSTF Hepatitis B Screening variables
    hbv_vars = [
        Record(Var('known_hbv_positive'), [Value(False)]),
        Record(Var('has_had_hbv_test'), [Value(False)]),
        Record(Var('last_hbv_test_negative'), [Value(False)]),
        Record(Var('hbv_vaccinated'), [Value(False)]),
        Record(Var('born_in_high_prevalence_region'), [Value(False)]),
        Record(Var('parents_born_high_prevalence_region'), [Value(False)]),
        Record(Var('on_hemodialysis'), [Value(False)]),
        Record(Var('on_immunosuppressive_therapy'), [Value(False)]),
        Record(Var('household_contact_hbv'), [Value(False)]),
        Record(Var('sexual_contact_hbv'), [Value(False)]),
        Record(Var('needle_sharing_contact_hbv'), [Value(False)]),
    ]

    # USPSTF Depression Screening variables
    depression_vars = [
        Record(Var('is_postpartum'), [Value(False)]),
        Record(Var('known_depression_diagnosis'), [Value(False)]),
        Record(Var('currently_in_treatment'), [Value(False)]),
        Record(Var('has_been_screened_past_year'), [Value(False)]),
        Record(Var('last_screening_negative'), [Value(False)]),
        Record(Var('family_history_depression'), [Value(False)]),
        Record(Var('history_of_depression'), [Value(False)]),
        Record(Var('chronic_medical_condition'), [Value(True)]),
        Record(Var('recent_major_life_stressor'), [Value(False)]),
        Record(Var('substance_use_disorder'), [Value(False)]),
    ]

    recs = [
        age, gender, race,
        dm, chol, ldl, hdl, cr,
        tg,
        bp
    ] + hypertension_vars + hiv_vars + diabetes_vars + crc_vars + hcv_vars + hbv_vars + depression_vars
    
    p = Persona(persona_text)

    return HealthContext(recs, p)


if __name__ == '__main__':

    # dat = sample_fhir_values()
    # print(dat)
    
    hc = sample_healthcontext('patient')
    print(len((hc.records)))

    from renderer.templates import LocalRenderer
    r = LocalRenderer()

