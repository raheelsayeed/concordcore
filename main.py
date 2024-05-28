#!/usr/bin/env python3

import argparse
from typing import final
from core import cpg, healthcontext
from core.concord import Concord, NeedAttestationError
from clog import *
import misc

import logging
from rich.logging import RichHandler

from renderer.templates import Sheet


level = 'DEBUG'
logging.basicConfig(level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("tests")





parser = argparse.ArgumentParser("concordcore_")
parser.add_argument('-f', dest='filepath', type=str, help='Path to Concord.CPG file')
parser.add_argument('-t', dest='template_name', type=str, help='Name of the template')
parser.add_argument('-p', dest='persona', type=str, help='patient or provider persona')
parser.add_argument('--inspect', action=argparse.BooleanOptionalAction, help='Inspect output')

args = parser.parse_args()
fp = args.filepath
inspect_output = args.inspect
logger.info(f'File={fp}')


ht("""
[black on green]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---[/black on green]
[black on green]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --concordcore v0.1 [/black on green]
# [b]User Data (sample)[/b]
#       Health context holds all the user data
#       can be a person/patient/?physician


""")



user_context = misc.sample_healthcontext(args.persona)
print_records(user_context.records)

if not fp:
    logger.error('Please enter CPG file `-f <path/to/cpg.yaml>`, exiting..')
    exit() 
ht(
"""
[white on blue]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
[white on blue]# I. Initialise Concord - --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
#       IN:     CPG
#       OUT:    Checks(Validity, Eligibility, Sufficiency, Execution, Recommendations)
""")
mycpg = cpg.BaseCPG.from_document_path(fp)
concord = Concord(mycpg, user_context)
logger.info(f'Initialized with with cpg: [bold]{mycpg.title}')
logger.info(f'Publisher={mycpg.publisher}')
logger.info(f'doi ={mycpg.publisher}')
logger.info(f'doi ={mycpg.publisher}')
is_cpg_valid = None
try:
    is_cpg_valid = concord.cpg.validate()
    print_variables(concord.cpg.variables)
except Exception as e:
        logger.error(e)
        raise e
finally:
    logger.debug(f'CPG Validation={"PASSED" if is_cpg_valid else "[bold]FAILED"}')



        

ht("""
[white on blue]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
[white on blue]# II. Eligibility Check - --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
# Concord evaluates if CPG is applicable to the user.
#       IN:     CPG Criterias, Sufficiency
#       out:    Is Eligible?
#               Why Not? (collect exceptions)
""")
try:
    result = concord.eligibility()
    logger.info(f'IS_Eligibility: {result.is_eligible}')
    print_evaluatedrecords(result.context.evaluation_list)
    if inspect_output:
        inspect(result)

except Exception as e:
    raise e








    
ht("""
[white on blue]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
[white on blue]# III. Sufficiency Check- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
# Concord evaluates if user-data is sufficient to execute CPG
#       IN:     CPG Variables, Person Health Context
#       out:    Is CPG Executable?
#               Why Not? (collect exceptions)
    """)
    # Get all evaluated records.
try:

    result = concord.sufficiency()
    logger.info(f'SufficiencyResult: IS_EXECUTABLE={result.is_executable}')
    if inspect_output:
        inspect(result)
        
    print_evaluatedrecords(result.context.evaluation_list, 'Sufficiency Checked Variables')
except Exception as e:
    raise e



ht("""


[white on blue]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
[white on blue]# IV. ASSESSMENT- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
# Concord assess risk based on [u]CPG Guidance[/u]
#       IN:     CPG.Assessment, Person Health Context
#       out:    Is CPG Executable?
#               Why Not? (collect exceptions)
""")   
# need to associate person_data with the variable values. 
try: 
    result = concord.assess()
except NeedAttestationError as e:
    from inputsession.cli import CLI
    session = CLI(concord)
    if session.run(debug_skip=True):
        result = concord.assess()

logger.info(f'Assessment Complete?={result.successful}')
print_evaluatedrecords(result.context.evaluation_list, title="AssessmentVariables")
if not result.successful:
    logger.error(f'Assessment could not be completed, is insufficient. Must stop here.')
    for insuff_record in result.insufficient_variables:
        logger.error(insuff_record)
    exit()


if inspect_output:
    inspect(result)



    # for a in concord.assessment_result.context.evaluation_list:
        # con.print(a.record.var.evaluation_function)
        # con.print(vars(a.record.var))



ht("""


[white on blue]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
[white on blue]# V. RECOMMENDATIONS  --- --- --- --- --- --- --- --- --- --- --- --- --- --- [/white on blue]
# Concord assess risk based on assessment definitions
#       IN:     CPG.Assessment Result
#       out:    [Recommendations]
#               
    """)

result = concord.recommendations()
logger.debug([er if er.error else None for er in result.recommendations])
logger.info(f'There are {len(result.recommendations)} RECOMMENDATION(s) for this `Person`')

if result.recommendations:    
    from rich.panel import Panel
    from rich.columns import Columns

    for i, applied in enumerate(result.recommendations):

        # inspect(applied)
        based_on_text = ", ".join([f'{record.var.id}:{record.value}' for record in applied.based_on]) if applied.based_on else ''
        
        
        panel = Panel(
f'''{i+1}. id: {applied.recommendation.id}
[b]Recommendation: {applied.recommendation.title}[/b]
[yellow]Narrative: {applied.narrative or ""}[/yellow]
COR: {applied.recommendation.class_of_recommendation}
LOE: {applied.recommendation.level_of_evidence}
Based-On: {based_on_text}''',style="on deep_sky_blue4")


        con.print(Columns([panel]))

if inspect_output:
    inspect(result.recommendations)



## Narrative tests 
for record in concord.sufficiency_result.context.evaluation_list:
    logger.debug(f'VARIABLE:narrative test record={record.record.test_narratives()}')
## Narrative tests 
for record in concord.assessment_result.context.evaluation_list:
    logger.debug(f'ASSESSMENT:narrative test record={record.record.test_narratives()}')

    
if args.template_name:
    

    ht("""
[black on green]# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---[/black on green]
[black on green]# concord_rendering_v0.1--- --- --- --- --- --- --- --- --- --- --- --- --- --- ---  [/black on green]
""")


    from renderer.templates import Cards, Document, Sheet, Tree
    temp = None 
    if args.template_name == "cards":
        temp = Cards("cards",  concord)
    elif args.template_name == "document":
        temp = Document("document",  concord)
    elif args.template_name == "sheet":
        temp = Sheet("sheet", concord)
    elif args.template_name == 'tree':
        temp = Tree("tree", concord)
    else:
        logger.error(f'Cannot find template={args.template_name}. Only "cards" and "document" supported')
        exit()
    page_html = temp.render_page()



from outomes.outcome import Advisory

print(Advisory.All())
