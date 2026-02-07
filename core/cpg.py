#!/usr/bin/env python3

from dataclasses import dataclass, field
from functools import cached_property
import logging

from typing import Any, Protocol
from typing_extensions import Self
from .assessment import AssessmentVar
from .eligibility import EligibilityVar
from .recommendation import RecommendationVar
from .security import SecurityError, sanitize_module_name, validate_module_path, validate_cpg_filepath
from primitives.code import Code
from variables import var
from .expression import Expression

log = logging.getLogger(__name__)

# Expression cache for reuse across CPG validation
_expression_cache: dict[str, Expression] = {}


def get_cached_expression(expression_string: str) -> Expression:
    """Get or create cached Expression object."""
    if expression_string not in _expression_cache:
        _expression_cache[expression_string] = Expression(expression_string)
    return _expression_cache[expression_string]

@dataclass
class CPG():

    identifier: str
    title: str
    doi: str = None
    parent: Self = None
    code: list[Code] = None
    publisher: str = None
    version: str = None  # Semantic version (e.g., "1.0.0")
    last_updated: str = None  # ISO date string (e.g., "2024-01-15")
    source_url: str = None  # Original guideline URL
    variables: list[var.Var] = None
    eligibility_variables: list[EligibilityVar] = None
    assessment_variables: list[AssessmentVar] = None
    recommendation_variables: list[RecommendationVar] = None
    rendering_template_path: str = None
    functions_module_name: str = None
    functions_module: Any = None

    # for rendering reasons
    def as_dict(self):
        return {
                'cpg_title': self.title,
                'cpg_doi': self.doi,
                'cpg_publisher': self.publisher,
                'cpg_version': self.version,
                'cpg_last_updated': self.last_updated,
                'cpg_source_url': self.source_url,
                }

    # --- Cached indexes for O(1) lookups ---
    @cached_property
    def _var_by_id(self) -> dict[str, var.Var]:
        """Index variables by id for O(1) lookup."""
        return {v.id: v for v in (self.variables or [])}

    @cached_property
    def _var_by_code(self) -> dict[str, var.Var]:
        """Index variables by code string for O(1) lookup."""
        index = {}
        for v in (self.variables or []):
            if v.code:
                for c in v.code:
                    index[c.as_string] = v
        return index

    @cached_property
    def _all_var_ids(self) -> set[str]:
        """Set of all variable IDs for O(1) membership check."""
        all_vars = (self.variables or []) + (self.eligibility_variables or []) + (self.assessment_variables or [])
        return {v.id for v in all_vars}

    @cached_property
    def non_optional_variables(self) -> list[var.Var] | None:
        """Required variables (cached)."""
        if not self.variables:
            return None
        result = [v for v in self.variables if v.required]
        return result if result else None

    @cached_property
    def optional_variables(self) -> list[var.Var] | None:
        """Optional variables (cached)."""
        if not self.variables:
            return None
        result = [v for v in self.variables if not v.required]
        return result if result else None

    @cached_property
    def attestable_variables(self) -> list[var.Var] | None:
        """User-attestable variables (cached)."""
        if not self.variables:
            return None
        result = [v for v in self.variables if v.user_attestable]
        return result if result else None


    def __str__(self):
        return  '''
                CPG: {self.identifier}
                Name: {self.title}
                Vars: {len(self.variables)}
                Assessments: {len(self.assessments)}
                Recommendations: {len(self.recommendations)}
                '''



    @classmethod
    def from_document_path(cls, cpg_filepath: str):
        """Load a CPG from a YAML file path.

        Args:
            cpg_filepath: Path to the CPG YAML definition file

        Returns:
            CPG instance

        Raises:
            SecurityError: If the filepath or module path fails security validation
            yaml.YAMLError: If the YAML file cannot be parsed
            FileNotFoundError: If the CPG file does not exist
        """
        from os import path
        import sys
        import yaml

        # Validate CPG filepath for security
        is_valid, error_msg = validate_cpg_filepath(cpg_filepath)
        if not is_valid:
            raise SecurityError(f"Invalid CPG filepath: {error_msg}")

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

        yaml_filename = path.basename(cpg_filepath)
        directory = path.dirname(cpg_filepath) or '.'
        function_module = yml['CPG'].get('functions_module_name', None) or yaml_filename[:-5].replace('/', '.')

        # Sanitize and validate module name
        function_module = sanitize_module_name(function_module)
        if function_module is None:
            raise SecurityError(f"Invalid function module name in CPG")

        # Validate module path for security
        is_valid, error_msg = validate_module_path(directory, function_module)
        if not is_valid:
            raise SecurityError(f"Cannot load module: {error_msg}")

        functions_module_path = path.join(directory, function_module + '.py')

        log.info(cpg_filepath)
        log.info(yaml_filename)
        log.info(directory)
        log.info(function_module)
        log.debug(functions_module_path)
        raise_error = path.exists(functions_module_path)
        import importlib
        try:
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
            publisher=cpg_dict.get('publisher', None),
            version=cpg_dict.get('version', '1.0.0'),
            last_updated=cpg_dict.get('last_updated', None),
            source_url=cpg_dict.get('uri', None) or cpg_dict.get('source_url', None),
            doi=cpg_dict.get('doi', None),
            variables=[var.Var.instantiate_from_yaml(d) for d in variables_dict],
            eligibility_variables=[EligibilityVar.instantiate_from_yaml(d) for d in eligibility_dict],
            assessment_variables=[AssessmentVar.instantiate_from_yaml(d) for d in assessments_dict],
            recommendation_variables=[RecommendationVar.instantiate_from_yaml(d) for d in recommendations_dict],
            functions_module=module
        )

    def get_var_by_id(self, identifier: str) -> var.Var | None:
        """O(1) variable lookup by id."""
        return self._var_by_id.get(identifier)

    def get_var_by_code(self, code_string: str) -> var.Var | None:
        """O(1) variable lookup by code string."""
        return self._var_by_code.get(code_string)

    @staticmethod
    def get_var(identifier: str, variables: list[var.Var]):
        """Legacy O(n) lookup - prefer get_var_by_id for CPG variables."""
        for er in variables:
            if er.id == identifier:
                return er
        return None

    def get_recommendation(self, identifier: str):
        return CPG.get_var(identifier=identifier, variables=self.recommendation_variables)


    def contexts(self, eligibility_identifiers=None, assessment_identifiers=None, recommendation_identifiers=None):
        ctx = self.assessment_context(identifiers=assessment_identifiers)
        ctx.extend(self.recommendation_context(identifiers=recommendation_identifiers))
        return ctx
        

    def eligibility_context(self, identifiers=None) -> list[str] | None: 
        if self.eligibility_variables:
            if identifiers:
                contexts = [ev.title for ev in self.eligibility_variables if ev.title is not None and ev.id in identifiers]
            else:
                contexts = [ev.title for ev in self.eligibility_variables if ev.title is not None]
            return contexts 

        return None


    def assessment_context(self, identifiers=None) -> list[str] | None:
        if self.assessment_variables:
            if identifiers:
                contexts = [av.reference for av in self.assessment_variables if av.reference is not None and av.id in identifiers]
            else:
                contexts = [av.reference for av in self.assessment_variables if av.reference is not None]
            return contexts
        return None

    def recommendation_context(self, identifiers=None) -> list[str] | None: 
        if self.recommendation_variables:
            if identifiers:
                contexts = [rv.citations for rv in self.recommendation_variables if rv.citations_text is not None and rv.id in identifiers]
            else:
                contexts = [rv.citations for rv in self.recommendation_variables if rv.citations_text is not None]


            

            return [ctx for ctexes in contexts for ctx in ctexes]
        return None


    def validate(self) -> bool:
        """Validate CPG definition."""
        from primitives.errors import ExpressionVariableNotFound

        errors = []
        dups = set()
        distinct_ids = set()

        # Use cached set for O(1) membership checks
        all_var_ids = self._all_var_ids

        # Check for duplicate IDs in variables
        for vr in (self.variables or []):
            if vr.id in distinct_ids:
                dups.add(vr.id)
            else:
                distinct_ids.add(vr.id)

        # Check eligibility, assessment, recommendation variables
        for vr in ((self.eligibility_variables or []) + (self.assessment_variables or []) + (self.recommendation_variables or [])):
            if vr.id in distinct_ids:
                dups.add(vr.id)
            else:
                distinct_ids.add(vr.id)

            # Validate expression references using cached expressions
            if vr.expression:
                exp = get_cached_expression(vr.expression)
                identifiers = exp.variable_identifiers
                if identifiers:
                    for idn in identifiers:
                        if idn not in all_var_ids:
                            errors.append(ExpressionVariableNotFound(idn, vr.expression))

        if dups:
            errors.append(
                    Exception('CPG.variables cannot have duplicate variable `id`s: ', dups)
                 )

        if not self.assessment_variables:
            errors.append(
                    Exception('CPG.assessment_variables not found;  all CPGs must have risk `assessment` variables defined')
            )

        for assessment in self.assessment_variables:
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

        a_var_ids = [a.id for a in self.assessment_variables] 
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



        
