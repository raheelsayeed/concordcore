#!/usr/bin/env python3

# Jan, 2024     
# raheel

from dataclasses import dataclass, field
from enum import Enum, auto, StrEnum
from functools import cached_property

from typing import Any, Protocol
from variables import var
from .assessment import EvaluatedAssessmentRecord
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
    DISPLAY_PATIENT          = 'display_patient'
    EVALUATION              = 'evaluation'

class ProviderDirective(Enum):
    # Do this, do that, ??
    pass 

class UserDirective(Enum):
    discussion_with_provider = auto()
    information = auto()

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

    expression: str = None
    class_of_recommendation: ClassOfRecommendation = None 
    level_of_evidence: LevelOfEvidence = None 
    uspstf_grade: USPSTFGrading = None 
    type: str = None
    citations: list = field(default_factory=list)
    references: Any = None
    compliance_expression: str = None
   
    def __hash__(self):
        return super().__hash__()

    @classmethod
    def instantiate_from_yaml(cls, yml, InstantiationContext=None):

        yml['class_of_recommendation'] = ClassOfRecommendation.from_yaml(yml.get('class_of_recommendation', None))
        yml['level_of_evidence'] = LevelOfEvidence.from_yaml(yml.get('level_of_evidence', None))
        yml['uspstf_grade'] = USPSTFGrading.from_yaml(yml.get('uspstf_grade', None))
        yml['type'] = RecommendationType.YAML(yml.get('type', None))

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
    based_on: list[EvaluatedAssessmentRecord] = None 
    compliance: Expression = None
    expression: Expression = None 
    applies: bool = None 
    compliant: bool  = None
    error: Exception = None
    narrative: str = None
    compliance_narrative = None

        
    @property
    def title(self):
        return self.recommendation.title
    
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

    def evaluate(self, evaluated_assessments: vlist.vlist[EvaluatedAssessmentRecord], evaluated_records: list[EvaluatedRecord] = None, persona: Persona = Persona.patient):
        """Evaluates recommendations

        evaluated_assessments: List of EvaluatedAssessmentRecords 
        evaluated_records: List of evaluated Patient Records `EvaluatedRecord`  
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
            raise Exception(f'Cannot evaluate, no expression found for recommendation={self.recommendation.id}') 
        else:
            try:
                self.applies =  self.expression.evaluate_recommendation(evaluated_assessments)
                self.based_on = self.expression.expression_records
                if self.compliance:
                    self.compliant = self.compliance.evaluate([v.record for v in evaluated_records])
                    self.based_on.extend(self.compliance.expression_records)
            except Exception as e:
                raise e

        varible_value_dict = None 
        if self.recommendation.narr.variables:
            records = list(filter(lambda ea: ea.id in self.recommendation.narr.variables, evaluated_assessments + (evaluated_records or [])))
            varible_value_dict = {r.id: r.record.as_dict() for r in records}
            log.info(varible_value_dict)
        self.narrative = self.recommendation.narr.get_text(self.applies, persona=persona, sanitization_dict=varible_value_dict)
        self.compliance_narrative = self.recommendation.narr.get_compliance_text(self.compliant, persona=persona, sanitization_dict=varible_value_dict)
        



@dataclass(frozen=True)
class RecommendationResult:

    context: EvaluationContext
    recommendations: list[EvaluatedRecommendation]
    
    @property
    def applied(self):
        return list(filter(lambda er: er.applies == True, self.recommendations))








