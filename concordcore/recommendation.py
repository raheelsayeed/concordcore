#!/usr/bin/env python3

# Jan, 2024     
# raheel




from dataclasses import dataclass, field
from email.policy import default

from enum import Enum, auto

from typing import Any, Protocol
from .variables import var, value
from .assessment import EvaluatedAssessmentRecord
from .evaluation import EvaluatedRecord
from .expression import Expression
from .evaluation import EvaluationContext
from .persona import Persona
from .primitives import vlist


# ------ USPSTF Classifications -------
# https://www.uspreventiveservicestaskforce.org/uspstf/about-uspstf/methods-and-processes/grade-definitions

class RecommendationType(Enum):
    medication              = 'medication'
    behavioral              = 'behavioral'
    moreEvaluation          = 'evaluation_needed'
    display                 = 'display'
    display_provider        = 'display_provider'
    display_person          = 'display_person'
    evaluation              = 'evaluation'

class ProviderDirective(Enum):
    # Do this, do that, ??
    pass 

class UserDirective(Enum):
    discussion_with_provider = auto()
    information = auto()

# --- Strength of evidence
class ClassOfRecommendation(Enum):
    one             = 'I'               # benefit >>> risk 
    two_A           = 'II_A'             # benefit >> risk
    two_B           = "II_B"             # benefit >= risk
    three_Moderate  = "III_Moderate"    # benefit = risk
    three_Strong    = "III_Strong"      # risk > 
    
    @classmethod
    def from_yaml(cls, cor):
        return ClassOfRecommendation(cor) if cor else None


# ---- Quality of evidence ---- 
class LevelOfEvidence(Enum):
    A       = "A"           # high quality
    B_R     = "BR"          # Moderate - Randomized
    B_NR    = "B-NR"        # Moderate - Nonrandomized 
    C_LD    = "C-LD"        # Limited data
    C_EO    = "C_EO"        # Consensus of expert opinion

    @classmethod
    def from_yaml(cls, loe):
        return LevelOfEvidence(loe) if loe else None

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
    class_of_recommendation: str = None 
    level_of_evidence: str = None 
    uspstf_grade: USPSTFGrading = None 
    type: str = None
    citations: list = field(default_factory=list)
    references: Any = None


   
    def __hash__(self):
        return super().__hash__()

    @classmethod
    def instantiate_from_yaml(cls, yml, InstantiationContext=None):

        rec_type = yml.get('type', None)
        if rec_type:
            yml['type'] = RecommendationType(rec_type)
        yml['class_of_recommendation'] = ClassOfRecommendation.from_yaml(yml.get('class_of_recommendation', None))
        yml['level_of_evidence'] = LevelOfEvidence.from_yaml(yml.get('level_of_evidence', None))
        yml['uspstf_grade'] = USPSTFGrading.from_yaml(yml.get('uspstf_grade', None))
        return super(RecommendationVar, cls).instantiate_from_yaml(yml)

    def as_dict(self):

        d = super().as_dict()
        d.update({
            'class_of_recommendation': self.class_of_recommendation.value if self.class_of_recommendation else None,
            'uspstf_grade': self.uspstf_grade or None 
        })
        return d


@dataclass
class EvaluatedRecommendation:
    
    recommendation: RecommendationVar
    based_on: list[EvaluatedAssessmentRecord] = None 
    expression: Expression = None 
    applies: bool = None 
    error: Exception = None
    sanitized_narrative: str = None

    def __post_init__(self):
        
        if self.recommendation.expression:
            self.expression = Expression(self.recommendation.expression)

    def evaluate(self, evaluated_assessments: vlist.vlist[EvaluatedAssessmentRecord], variables: list[EvaluatedRecord] = None, persona: Persona = Persona.patient):

        if self.recommendation.type and self.recommendation.type.value == RecommendationType.display.value:
            self.applies = True 
            self.sanitized_narrative = self.get_narrative(persona=persona)
            return

        if not self.expression:
            self.error = Exception('Cannot evaluate, no expression found')
            return 

        try:
            eval_result =  self.expression.evaluate_recommendation(evaluated_assessments)
            self.applies = eval_result
        except Exception as e:
            self.error = e
        
        self.based_on = self.expression.records

        n_vars = self.recommendation.narrative_variables
        self.sanitized_narrative = self.get_narrative()
        
        if not n_vars:       
            return 
        
        # sanitize text?
        try:
            records = list(filter(lambda ea: ea.id in n_vars, evaluated_assessments + (variables or [])))
            dict_record_values = {r.id: r.record.as_dict() for r in records}
            self.sanitized_narrative = self.get_narrative(variable_data_dict=dict_record_values)
            
        except Exception as e:
            raise e
        


        


        


        
    @property
    def title(self):
        return self.recommendation.title

    def get_narrative(self, persona: Persona = Persona.patient, variable_data_dict: dict = None):

        if not self.recommendation.narrative:
            return None
        txt = self.recommendation.narrative.get(persona.value, {}).get(self.applies, None)
        if not txt:
            return None
        if variable_data_dict and self.recommendation.narrative_variables:
            for n_var in self.recommendation.narrative_variables:
                val = variable_data_dict.get(n_var, {}).get('value', '<>')
                txt = txt.replace('$'+n_var, str(val))
            
        return txt




@dataclass(frozen=True)
class RecommendationResult:

    context: EvaluationContext
    recommendations: list[EvaluatedRecommendation]
    
    @property
    def applied(self):
        return list(filter(lambda er: er.applies == True, self.recommendations))


class RecommendationEvaluatorProtocol(Protocol):

    def validate(self) -> bool:
        ...

    def recommendations(self, evaluated_assessments, context: EvaluationContext = None) -> RecommendationResult:
        ... 



class BaseRecommendationEvaluator(RecommendationEvaluatorProtocol):

    def validate(self) -> bool:
        return True

    def recommendations(self, evaluated_assessments, context: EvaluationContext = None) -> RecommendationResult:
        return None






