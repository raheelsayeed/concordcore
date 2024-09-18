#!/usr/bin/env python3

from dataclasses import dataclass
import logging

from typing import Any, Protocol
from typing_extensions import Self
from .assessment import AssessmentVar
from .eligibility import EligibilityVar
from .recommendation import RecommendationVar
from primitives.code import Code
from variables import var
from .expression import Expression

log = logging.getLogger(__name__)

@dataclass
class CPG():

    identifier: str
    title: str
    doi: str = None 
    parent: Self = None 
    code: list[Code] = None 
    publisher: str = None
    variables: list[var.Var] = None
    eligibility_criterias: list[EligibilityVar] = None
    assessments_variables: list[AssessmentVar] = None 
    recommendation_variables: list[RecommendationVar] = None
    rendering_template_path: str = None
    functions_module: Any = None

    # for rendering reasons
    def as_dict(self):
        return {
                'cpg_title': self.title,
                'cpg_doi': self.doi, 
                'cpg_publisher': self.publisher,
                }



    @classmethod
    def from_document_path(cls, cpg_filepath: str):
        
        from os import path
        import sys
        import yaml
        yaml_filename = path.basename(cpg_filepath)
        directory = path.dirname(cpg_filepath)
        function_module =yaml_filename[:-5].replace('/', '.')
        functions_module_path = directory + '/' + function_module + '.py'

        log.info(cpg_filepath)
        log.info(yaml_filename)
        log.info(directory)
        log.info(function_module)
        log.debug(functions_module_path)

        yml = None
        with open(cpg_filepath, 'r') as cpgs_doc:
            try:
                yml = yaml.safe_load(cpgs_doc)
            except yaml.YAMLError as exc:
                log.error(exc)
                raise exc
            except Exception as e:
                log.error(e)
                raise e
        
        raise_error = path.exists(functions_module_path)
        import importlib
        log.warning('SAFETY-ISSUE: make sure functions module has not malicious-ness. INTERNAL-PROVISION-ONLY')
        try:
            # fn_module = importlib.import_module(functions_module_path) if functions_module_path else None
            from importlib.util import spec_from_file_location as sf
            spec = sf(function_module, functions_module_path)
            fn_module = importlib.util.module_from_spec(spec)
            sys.modules[function_module] = fn_module
            spec.loader.exec_module(fn_module)
            log.debug(fn_module)
            return cls.from_document(yml, fn_module)
        except Exception as e:
            log.debug(e)
            if raise_error:
                raise e
            return cls.from_document(yml, None)

    @classmethod
    def from_document(cls, document_dict: dict, module=None):

        cpg_dict                = document_dict['CPG']
        variables_dict          = document_dict['variables']
        eligibility_dict        = document_dict['eligibility']
        assessments_dict        = document_dict['assessments']
        recommendations_dict    = document_dict['recommendations']

        log.debug(f'Functions module={module} for CPG={cpg_dict["identifier"]}')

        return cls(
            identifier=cpg_dict['identifier'],
            title=cpg_dict['title'],
            variables=[var.Var.instantiate_from_yaml(d) for d in variables_dict],
            eligibility_criterias=[EligibilityVar.instantiate_from_yaml(d) for d in eligibility_dict],
            assessments_variables=[AssessmentVar.instantiate_from_yaml(d) for d in assessments_dict],
            recommendation_variables=[RecommendationVar.instantiate_from_yaml(d) for d in recommendations_dict],
            functions_module=module
        )

    def non_optional_variables(self):
        if self.variables:
            non_optionals = list(filter(lambda v: v.required == True, self.variables), None)
            if non_optionals:
                return non_optionals 
        else:
            return None

    def optional_variables(self):
        if self.variables:
            optionals = list(filter(lambda v: v.required == False, self.variables), None)
            if optionals:
                return optionals 
        else:
            return None

    def attestable_variables(self):
        if self.variables:
            attestables = list(filter(lambda v: v.user_attestable == True, self.variables), None)
            if attestables:
                return attestables 
        else:
            return None


    def validate(self) -> bool:

         # check if they exist in variable list.
        all_vars = self.variables + self.eligibility_criterias + self.assessments_variables
        all_vars_Identifiers = list(map(lambda v: v.id, all_vars))
        errors = []
        # --- duplicates
        # All variables must have a unique `id` 
        # 
        dups = set() 
        distinct_vars = set()
        similar_code = set()

        all_codes = [vr.code_string  for vr in all_vars if vr.code is not None]

        for vr in self.variables:

            # Two variables cavnnot have same `id`
            if vr not in distinct_vars:
                distinct_vars.add(vr)
            else:
                dups.add(vr) 


            # # all codes for a variable must be unqiue. Two variables cannot share a codeable concept
            # if var.code:
            #     for cd in var.code:
            #         # find if the code occurs in more than two places in all_codes 
            #         filt = list(filter(lambda code_str: code_str != None and cd.as_string in code_str, all_codes))
            #         if len(filt) > 1:
            #             err = ValueError(f'CPG.var: {var.id} contains code:{cd.as_string} found in other variables. Definitions require codes to be unique')
            #             errors.append(err)

            # Vars with expressions or functions must have var.identifiers already defined 
        distinct_vars = set()
        from primitives.errors import ExpressionVariableNotFound
        for vr in (self.eligibility_criterias + self.assessments_variables + self.recommendation_variables):

            # Two variables cavnnot have same `id`

            if vr not in distinct_vars:
                distinct_vars.add(vr)
            else:
                dups.add(vr) 

            if vr.expression:
                exp = Expression(vr.expression)
                identifiers = exp.variable_identifiers 
                if identifiers:
                    for idn in identifiers:

                        if idn not in all_vars_Identifiers:
                            err = ExpressionVariableNotFound( idn, vr.expression)
                            errors.append(err)

        if dups:
            errors.append(
                    Exception('CPG.variables cannot have duplicate variable `id`s: ', dups)
                 )

        if not self.assessments_variables:
            errors.append(
                    Exception('CPG.assessment_variables not found;  all CPGs must have risk `assessment` variables defined')
            )

        for assessment in self.assessments_variables:
            if assessment.expression and assessment.function:
                errors.append(
                    ValueError(f'CPG.assessment {assessment.id} cannot have both `expression` and `function`')
                )

        if not self.recommendation_variables:
            errors.append(
                    Exception('CPG.recommendations not found;  all CPGs must have recommendation variables defined')
            )


        # Recommendations must be based on  Assessments only
        def flatten(xss):
            return [x for xs in xss for x in xs]
        based_on_identifiers = []
        # for recommendation in self.recommendation_variables:
        #     if recommendation.based_on:
        #         based_on = flatten(recommendation.based_on.values())
        #         based_on_identifiers.extend(based_on)

        a_var_ids = [a.id for a in self.assessments_variables] 
        for assessment_id in set(based_on_identifiers):
            if assessment_id not in a_var_ids:
                errors.append(
                        KeyError(f'CPG.recommendation has `{assessment_id}` Not declaired in assessment_variables')
                        )

        if errors:
            raise ExceptionGroup('Error validating CPG definition', errors)



        log.debug('CPG Validation successful')
        return True
        

    # HELPERS
    
    def lab_test_codes(self):
        codes = [v.code_string for v in self.variables if v.code_string is not None and 'loinc' in v.code_string]
        return codes

    def conditions_codes(self):
        codes = [v.code_string for v in self.variables if v.code_string is not None and 'snomed' in v.code_string]
        return codes


    def medication_codes(self):
        codes = [v.code_string for v in self.variables if v.code_string is not None and 'rxnorm' in v.code_string]
        return codes



        
