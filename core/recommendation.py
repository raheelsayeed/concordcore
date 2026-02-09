#!/usr/bin/env python3

from dataclasses import dataclass, field
from enum import Enum, auto, StrEnum
from functools import cached_property

from typing import Any, Protocol
from variables import var
from .errors import CPGDefinitionError
from .assessment import AssessedRecord
from .evaluation import EvaluatedRecord
from .expression import Expression
from .evaluation import EvaluationContext
from primitives import vlist
from primitives.types import Persona, YMLStrEnum

import logging

log = logging.getLogger(__name__)

# ------ USPSTF Classifications -------
# https://www.uspreventiveservicestaskforce.org/uspstf/about-uspstf/methods-and-processes/grade-definitions
class RecommendationType(YMLStrEnum):
    MEDICATION              = 'medication'
    DISPLAY                 = 'display'
    DISPLAY_PROVIDER        = 'display_provider'
    DISPLAY_PATIENT         = 'display_patient'
    EVALUATION              = 'evaluation'
        


class RecommendationActionType(StrEnum):
    """Type of clinical action a recommendation suggests."""
    prescribe = 'prescribe'
    order_test = 'order-test'
    schedule_screening = 'schedule-screening'
    counseling = 'counseling'
    referral = 'referral'
    lifestyle_modification = 'lifestyle-modification'
    monitoring = 'monitoring'


class RecommendationAction(StrEnum):
    """Provider response to a recommendation."""
    pending = 'pending'
    accepted = 'accepted'
    rejected = 'rejected'
    deferred = 'deferred'
    not_applicable = 'not-applicable'


# --- Strength of evidence
class ClassOfRecommendation(StrEnum):
    I             = 'I'               # benefit >>> risk 
    II_A           = 'IIa'             # benefit >> risk
    II_B            = "IIb"             # benefit >= risk
    III             = 'III: Harm'
    III_Moderate  = "III Moderate"    # benefit = risk
    III_Strong    = "III Strong"      # risk > 

    def color_code_html(self):
        if self == 'I':
            return 'green'
        if self == 'IIb':
            return 'orange'
        if self == 'IIa':
            return 'yellow'
        if self == 'III: Harm':
            return 'red'
        
    @classmethod
    def from_yaml(cls, cor):
        return ClassOfRecommendation(cor) if cor else None


# ---- Quality of evidence ---- 
class LevelOfEvidence(StrEnum):
    A       = "A"           # high quality
    B_R     = "B-R"          # Moderate - Randomized
    B_NR    = "B-NR"        # Moderate - Nonrandomized 
    C_LD    = "C-LD"        # Limited data
    C_EO    = "C_EO"        # Consensus of expert opinion

    @classmethod
    def from_yaml(cls, loe):
        return LevelOfEvidence(loe) if loe else None
    
    def color_code_html(self):
        if self == 'A':
            return 'blue'
        if self == 'B-R':
            return 'light-blue'
        if self == 'B-NR':
            return 'light-blue'
        return 'purple'

    

class USPSTFQualityOfEvidence(Enum):
    Good = auto() 
    Fair = auto() 
    Poor = auto() 

class USPSTFGrading(Enum):

    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    I = 'I'

    def meaning(self):
        if self == USPSTFGrading.A:
            return 'Strongly Recommended'
        if self == USPSTFGrading.B:
            return 'Recommended'
        if self == USPSTFGrading.C:
            return 'No recommendation'
        if self == USPSTFGrading.D:
            return 'Not Recommended'
        if self == USPSTFGrading.I:
            return 'Insufficient Evidence to make Recommendation'

    @classmethod
    def from_yaml(cls, g):
        return USPSTFGrading(g) if g else None


@dataclass(frozen=True)
class RecommendationVar(var.Var):

    expression: str | None = None
    class_of_recommendation: ClassOfRecommendation | None = None
    level_of_evidence: LevelOfEvidence | None = None
    uspstf_grade: USPSTFGrading | None = None
    type: str | None = None
    citations: list = field(default_factory=list)
    references: Any | None = None
    compliance_expression: str | None = None
   
    def __hash__(self):
        return hash(self.id)

    def citations_text(self):
        if self.citations:
            return '\n\n'.join(self.citations)
        return None

    @classmethod
    def instantiate_from_yaml(cls, yml, InstantiationContext=None):

        # because the classes are frozen, we pass the values along within yml
        yml['class_of_recommendation'] = ClassOfRecommendation.from_yaml(yml.get('class_of_recommendation', None))
        yml['level_of_evidence'] = LevelOfEvidence.from_yaml(yml.get('level_of_evidence', None))
        yml['uspstf_grade'] = USPSTFGrading.from_yaml(yml.get('uspstf_grade', None))
        yml['category'] = RecommendationType.YAML(yml.get('category', None))

        return super(RecommendationVar, cls).instantiate_from_yaml(yml)

    def as_dict(self):

        d = super().as_dict()
        d.update({
            'level_of_evidence': self.level_of_evidence or None,
            'class_of_recommendation': self.class_of_recommendation or None,
            'uspstf_grade': self.uspstf_grade or None 
        })
        return d


@dataclass
class EvaluatedRecommendation:

    recommendation: RecommendationVar
    based_on: list[AssessedRecord] | None = None
    compliance: Expression | None = None
    expression: Expression | None = None
    applies: bool | None = None
    compliant: bool | None = None
    error: Exception | None = None
    narrative: str | None = None
    compliance_narrative: str | None = None
    non_compliance_evidence: list[EvaluatedRecord] | None = None

    @property
    def title(self):
        return self.recommendation.title

    @property 
    def description(self):
        return self.recommendation.description
    
    @cached_property
    def based_on_records(self):
        """Returns nested record of all assessment records for which this recommendation was based on."""
        from collections.abc import Iterable
        all_records = []

        log.debug(f'> {self.recommendation.id}')
        for record in self.based_on:
            rec = record.record if isinstance(record, EvaluatedRecord) else record
            all_records.append(rec)
            all_records.extend(rec.value.source)
            log.debug(f' ---> {rec.id}')
            #log.debug(f' --- ---> {[r.id for r in rec.value.source]}')
            log.debug(f' --- ---> {rec.value.source}')
            if not rec.value.source:
                log.error('rec has no value.source')
            else:
                for s_rec in rec.value.source:
                    log.debug(f' --- --- ---> {s_rec}')
        
        return all_records
            
    def __post_init__(self):
        
        if self.recommendation.expression:
            self.expression = Expression(self.recommendation.expression)
        if self.recommendation.compliance_expression:
            self.compliance = Expression(self.recommendation.compliance_expression)

    def evaluate(self, evaluated_assessments: vlist.vlist[AssessedRecord],
                 evaluated_records: list[EvaluatedRecord] = None,
                 persona: Persona = Persona.patient,
                 assessment_index: dict = None,
                 record_index: dict = None):
        """Evaluates recommendations.

        Args:
            evaluated_assessments: List of AssessedRecords
            evaluated_records: List of evaluated Patient Records (EvaluatedRecord)
            persona: Persona for narrative generation
            assessment_index: Optional pre-built dict mapping id to AssessedRecord
            record_index: Optional pre-built dict mapping id to EvaluatedRecord
        """
        rectype = self.recommendation.type
        show_if_patient = rectype == RecommendationType.DISPLAY_PATIENT
        show_if_provider = rectype == RecommendationType.DISPLAY_PROVIDER
        show_for_both = rectype == RecommendationType.DISPLAY

        if show_for_both:
            self.applies = True
        elif show_if_provider:
            self.applies = persona == Persona.provider
        elif show_if_patient:
            self.applies = persona == Persona.patient
        elif not self.expression:
            raise CPGDefinitionError(f'Cannot evaluate, no expression found for recommendation={self.recommendation.id}')
        else:
            try:
                self.applies = self.expression.evaluate_recommendation(evaluated_assessments)
                self.based_on = self.expression.expression_records
                if self.compliance:
                    self.compliant = self.compliance.evaluate([v.record for v in evaluated_records])
                    self.based_on.extend(self.compliance.expression_records)
                    if self.compliant is False or (hasattr(self.compliant, 'value') and self.compliant.value is False):
                        self.non_compliance_evidence = [
                            er for er in (evaluated_records or [])
                            if er.record.id in {r.id for r in self.compliance.expression_records}
                        ]
            except Exception as e:
                raise e

        variable_value_dict = None
        if self.recommendation.narr and self.recommendation.narr.variables:
            # Use pre-built indexes for O(1) lookup if available
            narr_vars = self.recommendation.narr.variables
            if assessment_index and record_index:
                records = []
                for var_id in narr_vars:
                    if var_id in assessment_index:
                        records.append(assessment_index[var_id])
                    elif var_id in record_index:
                        records.append(record_index[var_id])
            else:
                # Fallback to O(n) filter if no indexes provided
                narr_var_set = set(narr_vars)
                records = [ea for ea in evaluated_assessments if ea.id in narr_var_set]
                if evaluated_records:
                    records.extend([er for er in evaluated_records if er.id in narr_var_set])

            variable_value_dict = {r.id: r.record.as_dict() for r in records}
            log.debug(f'Narrative vars for {self.recommendation.id}: {variable_value_dict.keys()}')

        self.narrative = self.recommendation.narr.get_text(self.applies, persona=persona, sanitization_dict=variable_value_dict) if self.recommendation.narr else None
        self.compliance_narrative = self.recommendation.narr.get_compliance_text(self.compliant, persona=persona, sanitization_dict=variable_value_dict) if self.recommendation.narr else None
        log.debug(f'{self.applies}; {type(self.applies)}; narr={self.narrative}')
        

    


@dataclass(frozen=True)
class RecommendationResult:

    context: EvaluationContext
    recommendations: list[EvaluatedRecommendation]

    
    @property
    def applied(self):
        return [er for er in self.recommendations if er.applies is True]




