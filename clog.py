#!/usr/bin/env python3

from core.assessment import AssessmentRecord
from core.recommendation import RecommendationVar
from variables import record
from rich import console, table, box

from variables.var import Var
from variables.value import Value
from variables.record import Record

from rich.panel import Panel
from rich.markdown import Markdown
from rich.columns import Columns


con = console.Console() 
p = con.print


def ht(*values: object):
    con.print(f'[green]{values[0]}')
    
def pt(*values: object):
    con.print(f'{",".join(values)}')


def variables_table(variables: list[Var], title=None):

    table_ = table.Table(box=box.SIMPLE_HEAD, title_justify='left', highlight=True, title_style="bold blue", show_header=True, show_edge=False, header_style="dim", 
    title=f'# VarList {title or ""} << ')
    table_.add_column('No.', style="dim")
    table_.add_column('id', justify="left", style="white", no_wrap=False)
    table_.add_column('type', justify="left", style="white", no_wrap=False)
    table_.add_column('required', justify="left", style="white", no_wrap=False)
    table_.add_column('attestable', justify="left", style="white", no_wrap=False)

    for (i, var) in enumerate(variables):
        
        table_.add_row(
            str(i+1), 
            str(var.id),
            str(var.type),
            str(var.required),  
            str(var.user_attestable),
        )
    
    return table_


def print_variables(variables: list[Var], title=None):
    con.print(variables_table(variables, title))

def print_records(records: list[Record], title=None):
    table_ = table.Table(box=box.SIMPLE_HEAD, title_justify='left', highlight=True, title_style="bold blue", show_header=True, show_edge=False, header_style="dim", title=f'Records: {title} -- ')
    table_.add_column('No.', style="dim")
    table_.add_column('id', justify="left", style="white", no_wrap=False)
    table_.add_column('type', justify="left", style="white", no_wrap=False)
    table_.add_column('required', justify="left", style="white", no_wrap=False)
    table_.add_column('attestable', justify="left", style="white", no_wrap=False)
    table_.add_column('values', justify="left", style="white", no_wrap=False)


    for (i, r) in enumerate(records):

        table_.add_row(
            str(i+1), 
            str(r.id),
            str(r.var.value_type),
            str(r.var.required),  
            str(r.var.user_attestable),
            str(r.values),
        )

    con.print(table_)


def print_evaluatedrecords(variables, title = None, subtitle = None):
    from core.sufficiency import SufficiencyResultStatus
    from core.evaluation import EvaluationResultStatus

    table_ = table.Table(box=box.SIMPLE_HEAD, title_justify='left', highlight=True, title_style="bold blue", show_header=True, show_edge=False, header_style="dim", title=f'Evaluated: {title} -- ')
    table_.add_column('No.', style="dim")
    table_.add_column('id', justify="left", style="white", no_wrap=False)
    table_.add_column('type', justify="left", style="white", no_wrap=False)
    table_.add_column('required', justify="left", style="white", no_wrap=False)
    table_.add_column('attestable', justify="left", style="white", no_wrap=False)
    table_.add_column('val', justify="left", style="white", no_wrap=False)
    table_.add_column('Sufficiency', justify="left", no_wrap=False)
    table_.add_column('valS', justify="left", style="white", no_wrap=False)
    table_.add_column('eval_method', justify="left", style="white", no_wrap=False)
    table_.add_column('eval', justify="left", no_wrap=False)
    table_.add_column('reason', justify="left", style="white", no_wrap=False)
    # table_.add_column('narrative', justify="left", style="white", no_wrap=False)



    for (i, ev) in enumerate(variables):
# style="white on blue"
        try:
            sufficiency = '-'
            if ev.sufficiency_status is not None:
                if ev.sufficiency_status.value ==  SufficiencyResultStatus.Sufficient.value:
                    sufficiency = '[green] Sufficient '
                elif ev.sufficiency_status.value ==  SufficiencyResultStatus.Insufficient.value:
                    sufficiency = '[white on red] Insufficient '
                elif ev.sufficiency_status.value == SufficiencyResultStatus.Optional.value:
                    sufficiency = ' Optional '
                elif ev.sufficiency_status.value == SufficiencyResultStatus.SufficientWithUserAttestation.value:
                    sufficiency = '[cyan] Suff.Att '
            
            could_eval = '-'
            if ev.evaluation_result is not None:
                if ev.evaluation_result.value ==  EvaluationResultStatus.Successful.value:
                    could_eval = '[green] S '
                else:
                    could_eval = '[white on red] F '
            
            eval_method_expression = ev.record.expression if hasattr(ev.record, 'expression') else None
            eval_method_function   = ev.record.function if hasattr(ev.record, 'function') else None

            table_.add_row(str(i+1), ev.record.id,
                (ev.record.var.value_type),
                str(ev.record.var.required),  
                str(ev.record.var.user_attestable),
                str(ev.record.value),
                str(sufficiency),
                str(ev.record.values.representation if ev.record.values else None),
                str(eval_method_expression or eval_method_function or ''),
                str(could_eval),
                str(ev.error),
                # ev.record.get_narrative()

            )
        except Exception as e:
            con.print(f'error: {ev}')
            raise e

    con.print(table_)



   
   
    
