#!/usr/bin/env python3

import inspect
import logging

from concordcore import concord

from concordcore.healthcontext import HealthContext
from concordcore.primitives.types import ValueTypePrimitives
from concordcore.variables.record import Record
from concordcore.variables.var import Var, VarType
from concordcore.variables.value import Value
from ontology.presets import *




from rich.logging import RichHandler
from rich import inspect


FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
logger = logging.getLogger("tests")


if __name__ == '__main__':

    from concordcore.cpg import BaseCPG
    cpg = BaseCPG.from_document_path('cpgs/cholesterol.yaml')


    exit()

    print("Tests...")
    ### ---- ONTOLOGY CHECK ---- 
    from ontology.codes import * 
    fcode = CodeGender.female_snomed.value

    # check
    from concordcore.primitives.code import Code
    assert isinstance(fcode, Code)


    ### ---- VALUE -------------
    from concordcore.variables import value, record, var
    val1 = value.Value(1, unit=None, code=fcode)
    print(val1)
    var1= var.Var('LDL', 'LDL', None, code=[fcode], category=VarType.vital_sign, type=ValueTypePrimitives.string)
    var2= var.Var.Sample()
    assert isinstance(var1, type(var2))
    assert isinstance(var1, var.Var)

    rec1= record.Record(var1, [val1])
    print(rec1)
    assert rec1.value
    rec2= record.Record(var1, None)
    print(vars(rec2))
    assert rec2.value == None
    assert rec2.values == None
    val2 = value.Value(2, unit=None, code=fcode)
    rec2.attested_value = val2
    assert rec2.value != None
    assert rec2.values[0] == val2.value
    print(rec2.value)



    from concordcore.assessment import AssessmentRecord, AssessmentVar
    av1 = AssessmentVar('TG', expression='$LDL == 1')
    print(vars(av1))
    print(av1.expression)

    ar1= AssessmentRecord(av1, None)
    ar1.evaluate([rec1])
    print(ar1.value, rec1.value)

    print('narrative', ar1.sanitized_narrative)



    ldl_var = var.Var('LDL', 'LDL', None, code=[fcode], category=VarType.vital_sign, type=ValueTypePrimitives.string,
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

    print(highldl_rec.value, highldl_rec.sanitized_narrative, ldl_rec.sanitized_narrative)

    import misc
    hc = misc.sample_healthcontext
    # ---- Eligibility Record --- 
    from concordcore.eligibility import EligibilityVar, EligibilityRecord, EligibilityEvaluator
    e_var = EligibilityVar('Gender', expression='$Gender == 1')
    eligibility_record = EligibilityRecord(e_var)
    # eligibility_record.evaluate([ldl_rec])
    logger.debug(f'Eligibiltiy={eligibility_record.id} is_eligiblity={eligibility_record.is_eligible}')
    logger.info('EligbilityEvaluation:')
    e_eval = EligibilityEvaluator([e_var])
    e_result = e_eval.evaluate(hc)

    inspect(e_result)
    
    import cpgstore
    from concordcore.cpg import BaseCPG
    tup = cpgstore.read_cpg('cholesterol.yaml')
    mycpg  = BaseCPG.from_document(tup[0], tup[1])


    mycpg.validate()

    con = concord.Concord(mycpg)
    con.eligibility(None, hc)
    con.sufficiency(user_context=hc)
    con.assess()
    con.recommendations()
    



    print("passed..")




    


    

