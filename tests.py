#!/usr/bin/env python3

import inspect
import logging

from concordcore.core import concord
from concordcore.core.healthcontext import HealthContext
from concordcore.variables.record import Record
from concordcore.variables.var import Var, VarCategory
from concordcore.variables.value import Value
from clog import *




from rich.logging import RichHandler
from rich import inspect


FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
logger = logging.getLogger("tests")


if __name__ == '__main__':

    from concordcore.core.cpg_registry import get_registry
    cpg = get_registry().get('2019AccPrimaryPreventionASCVD')
    import misc
    manager = concord.Concord(cpg, misc.sample_healthcontext())



    logger.info("Tests...")
    ### ---- ONTOLOGY CHECK ---- 
    from concordcore.ontology.codes import * 
    fcode = CodeGender.female_snomed.value

    # check
    from concordcore.primitives.code import Code
    assert isinstance(fcode, Code)


    ### ---- VALUE -------------
    from concordcore.variables import value, record, var
    val1 = value.Value(1, unit=None, code=fcode)
    logger.info(val1)
    var1= var.Var('LDL', 'LDL', None, code=[fcode], category=VarCategory.vital_sign, type=None)
    var2= var.Var.Sample()
    assert isinstance(var1, type(var2))
    assert isinstance(var1, var.Var)

    rec1= record.Record(var1, [val1])
    logger.debug(rec1)
    assert rec1.value
    rec2= record.Record(var1, None)
    logger.debug(vars(rec2))
    assert rec2.value == None
    assert rec2.values == None
    val2 = value.Value(2, unit=None, code=fcode)
    rec2.attested_value = val2
    assert rec2.value != None
    assert rec2.values[0] == val2.value
    logger.debug(rec2.value)



    from concordcore.core.assessment import AssessmentRecord, AssessmentVar
    av1 = AssessmentVar('TG', expression='$LDL == 1')
    logger.debug(vars(av1))
    logger.debug(av1.expression)

    ar1= AssessmentRecord(av1, None)
    ar1.evaluate([rec1])
    logger.debug(f'{ar1.value}, {rec1.value}')

    logger.debug(f'narrative={ar1.narrative}')



    ldl_var = var.Var('LDL', 'LDL', None, code=[fcode], category=VarCategory.vital_sign, type=None,
                      narrative= {
                            'patient': {
                                    'HasValue': 'we have val $value',
                                    True: 'We are true with $value '
                                        
                                }
                                
                          })
    ldl_rec = record.Record(ldl_var, [val1])

    high_ldl = AssessmentVar('highldl', 'High LDL', expression='$LDL == 1', narrative = {
            'patient': {
                    True: 'ldl is equal  $LDL| $value| $count.',
                    False: 'ldl is low  $LDL, $value $count ..',
                    None: 'annot be ascertained $LDL, $value'
                }
        })
    highldl_rec = AssessmentRecord(high_ldl, None)
    highldl_rec.evaluate([ldl_rec])

    logger.debug(f'highldl_rec={highldl_rec.value}, narr={highldl_rec.narrative}, ldlnarr={ldl_rec.narrative}')

    import misc
    hc = misc.sample_healthcontext()
    # ---- Eligibility Record --- 
    from concordcore.core.eligibility import EligibilityVar, EligibilityRecord, EligibilityEvaluator
    e_var = EligibilityVar('Gender', expression='$Gender == 1')
    eligibility_record = EligibilityRecord(e_var)
    # Note: eligibility_record needs to be evaluated against records containing Gender before accessing is_eligible
    logger.debug(f'Eligibility={eligibility_record.id} (not yet evaluated)')
    logger.info('EligbilityEvaluation:')
    e_eval = EligibilityEvaluator([e_var])
    e_result = e_eval.evaluate(hc)

    




    ht("""
[black on green]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---[/black on green]
[black on green]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- -concord_dateback_v0.1 [/black on green]""")
    fhirvals = misc.sample_fhir_values()
    for fhirval in fhirvals:
        logger.debug(f'fhirvalue={fhirval}')
    from datetime import date
    from concordcore.primitives.types import Persona
    until_2023 = date.today().replace(year=2015)
    # Create placeholder records for demographics
    age_record = Record(var=Var('Age', 'Age'), initial_values=[Value(55)])
    gender_record = Record(var=Var('Gender', 'Gender'), initial_values=[Value(1)])
    race_record = Record(var=Var('Race', 'Race'), initial_values=[Value('white')])
    patientdata = HealthContext.from_values(fhirvals, manager.cpg.variables, age_record, gender_record, race_record, Persona.patient, until_2023)
    # print_records(patientdata.records)

    # latest = healthcontext.HealthContext.from_values(fhir, manager.cpg.variables)
    # print_records(latest.records)

    # --- Test: Verify sample data is accurately matched to CPG variables ---
    ht("[black on green]# --- SAMPLE DATA MATCHING TEST --- [/black on green]")

    from concordcore.core.concord import Concord

    test_cpg = get_registry().get('2019AccPrimaryPreventionASCVD')
    test_hc = misc.sample_healthcontext()
    test_concord = Concord(cpg=test_cpg, healthcontext=test_hc, ignore_eligibility=True)

    # Run sufficiency to see variable matching
    sufficiency_result = test_concord.sufficiency()

    # Check that key variables have values (matched by code)
    critical_vars = ['triglycerides', 'bloodpressure', 'LDL', 'HDL', 'Chol', 'diabetesMellitus']
    for ev in sufficiency_result.context.evaluation_list:
        if ev.record.id in critical_vars:
            has_value = ev.record.has_value
            status = "✓ HAS VALUE" if has_value else "✗ MISSING"
            logger.info(f"  {ev.record.id}: {status} (values={ev.record.values})")
            if ev.record.id in ['triglycerides', 'bloodpressure', 'LDL', 'HDL', 'Chol', 'diabetesMellitus']:
                assert has_value, f"Critical variable {ev.record.id} should have value from sample data"

    logger.info("Sample data matching test PASSED")
    # --- End Sample Data Matching Test ---

    logger.info("tests=PASSED")




    


    

