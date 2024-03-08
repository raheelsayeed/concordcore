#!/usr/bin/env python3

from dataclasses import dataclass, field
from datetime import datetime, date
from functools import cached_property
import logging

from .cpg import CPG
from .eligibility import EligibilityResult, EligibilityEvaluator, EligibilityEvaluatorProtocol
from .assessment import AssessmentEvaluatorProtocol, AssessmentResult, AssessmentEvaluator, AssessmentEvaluatorProtocol
from .recommendation import EvaluatedRecommendation, RecommendationResult, RecommendationEvaluatorProtocol, BaseRecommendationEvaluator
from .sufficiency import SufficiencyResult, SufficiencyEvaluator, SufficiencyEvaluatorProtocol
from .evaluation import EvaluatedRecord, EvaluationContext
from .variables.value import Value
from .healthcontext import HealthContext

log = logging.getLogger(__name__)

@dataclass
class NeedAttestationError(Exception):
    records: list
    def __str__(self) -> str:
        return f'Need user attestation for records={[ev.record.var.id for ev in self.records]}'

@dataclass
class Concord:

    cpg: CPG
    healthcontext: HealthContext
    until_year: int = None
    __eligibility_result: EligibilityResult = field(init=False) 
    __assessment_result: AssessmentResult = field(init=False)
    __recommendations_result: RecommendationResult = field(init=False)
    __sufficiency_result: SufficiencyResult = field(init=False)
    __evaluated_records: list[EvaluatedRecord] = field(init=False)

    @cached_property
    def until_date(self) -> date|None:
        return datetime(self.until_year, 12, 31).date if self.until_year else None
    @property
    def eligibility_result(self):
        return self.__eligibility_result
    @property
    def assessment_result(self):
        return self.__assessment_result
    @property
    def recommendation_result(self):
        return self.__recommendations_result
    @property
    def evaluated_records(self):            
        return self.__evaluated_records
    @property
    def sufficiency_result(self):
        return self.__sufficiency_result

    def eligibility(self, 
                    evaluator: EligibilityEvaluatorProtocol = None,
                    context: EvaluationContext = None) -> EligibilityResult:

        if not self.cpg.eligibility_criterias:
            raise Exception('Concord: no criterias defined to evaluate for this CPG')
        
        eligibility_eval = evaluator or EligibilityEvaluator(self.cpg.eligibility_criterias)
        # evalute eligibility
        self.__eligibility_result = eligibility_eval.evaluate(self.healthcontext, context=context)

        return self.__eligibility_result


    def sufficiency(self, 
                    sufficiency_evaluator: SufficiencyEvaluatorProtocol = None, 
                    context: EvaluationContext = None) -> SufficiencyResult:
        
        if not self.cpg.variables:
            raise Exception('Concord: no variables defined to evaluate for this CPG')

        # initialize an evaluator 
        sufficiency_eval = sufficiency_evaluator or SufficiencyEvaluator('se', cpg_variables=self.cpg.variables)
        # evaluate sufficiency
        self.__sufficiency_result = sufficiency_eval.evaluate(self.healthcontext, context)

        return self.__sufficiency_result

    def assess(self,
                assessment_evaluator: AssessmentEvaluatorProtocol = None
                ) -> AssessmentResult:

        """Get all evaluated_records

        1. if suff.result == insuff, abort
        2. get evalauted records, send to assessment variables
        3. check if needs PGHD.
        4. evalate Assessment variables after collection of PGHD.
        """
        errs = []
        if self.__eligibility_result == None:
            errs.append(Exception('Eligibility evaluation should be completed before risk assessment'))

        if self.__eligibility_result.is_eligible == False: 
            errs.append(Exception('Eligibility criteria not met, cannot execute CPG'))
        
        if self.__sufficiency_result.result == None:
            errs.append(Exception('Userdata sufficiency not evaluated'))

        if self.__sufficiency_result.is_executable == False:
            suff_errors = [ev.error for ev in self.__sufficiency_result.insufficient_variables]
            errs.append(ExceptionGroup(f'Userdata is insufficient to execute CPG<{self.cpg.identifier}', suff_errors))

        log.debug(f'Sufficiency check complete; IS-Executable={self.__sufficiency_result.is_executable}')
        if errs:
            raise ExceptionGroup('Cannot Execute CPG', errs)

        # --> Get all evaluated records
        self.__evaluated_records = self.__sufficiency_result.context.evaluation_list

        # --> check if they need Input
        need_attestation = self.__sufficiency_result.attestation_variables
        log.info(f'Attestation needed for {len(need_attestation)} variables')
        if need_attestation:
            for n in need_attestation:
                log.error(f'Need Input for record={n.record.id}')
            raise NeedAttestationError(need_attestation)
        else:
            log.debug('UserAttestation/PGHD Not Needed, proceeding..to evaluation')


        

        evaluator = assessment_evaluator or AssessmentEvaluator()
        ctx = EvaluationContext()

        self.__assessment_result = evaluator.assess(
            self.cpg.assessments_variables,
            self.evaluated_records,
            functions_module=self.cpg.functions_module,
            context=ctx
        )

        return self.__assessment_result

    


    def recommendations(self, context: EvaluationContext = None) -> RecommendationResult:


        context = context or    EvaluationContext() 
        evaluated_recommendations = []
        for recommendation in self.cpg.recommendation_variables:

            eval_rec = EvaluatedRecommendation(recommendation=recommendation)
            eval_rec.evaluate(self.assessment_result.context.evaluation_list, variables=self.evaluated_records)
            evaluated_recommendations.append(eval_rec)
            log.debug(eval_rec)

        self.__recommendations_result = RecommendationResult(
                context=context, 
                recommendations=sorted(evaluated_recommendations, key=lambda er: er.applies if er.applies else False, reverse=True)
            )
        return self.__recommendations_result

    
    @property
    def applied_recommendations(self):
        if not self.__recommendations_result:
            return None
        return self.recommendation_result.applied


    
    def build_and_sanitize_narratives(self):

        if not self.__assessment_result:
            return 
        # get all records
        all_variables = self.evaluated_records
        evaluated_records = self.__assessment_result.context.evaluation_list
        for er in evaluated_records + all_variables:
            log.debug(er.record.var.narrative_variables)
            ls = list(filter(lambda ev: ev.id in er.record.var.narrative_variables if er.record.var.narrative_variables else [], all_variables + evaluated_records))
            d = dict(map(lambda er: {er.id: er.record.value.value}, ls))
            log.debug(d)

        





