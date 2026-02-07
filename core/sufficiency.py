#!/usr/bin/env python3
"""Sufficiency evaluation for ConcordCore.

This module provides the SufficiencyEvaluator which checks if patient data
is sufficient to execute a CPG.
"""

from functools import cached_property
import logging
from dataclasses import dataclass
from typing import Protocol

from .healthcontext import HealthContext
from .record_index import RecordIndex
from variables.record import Record
from variables.var import Var
from .evaluation import EvaluationContext, EvaluationResult, SufficiencyResultStatus

log = logging.getLogger(__name__)

@dataclass(frozen=True)
class SufficiencyResult(EvaluationResult):
  
    def __repr__(self) -> str:
            return f"is_executable: {self.is_executable}\n{super().__repr__()}"

    @cached_property
    def result(self):
        for ev in self.context.evaluation_list:
            if ev.sufficiency_status.value  == SufficiencyResultStatus.Insufficient.value:
                return SufficiencyResultStatus.Insufficient
        
        return SufficiencyResultStatus.Sufficient

    @property
    def is_executable(self) -> bool: 
        return self.result == SufficiencyResultStatus.Sufficient or self.result == SufficiencyResultStatus.SufficientWithUserAttestation

 
class SufficiencyEvaluatorProtocol(Protocol):

    def __init__(self, identifier: str, cpg_variables: list[Var]):
        ...

    def evaluate(self,
                user_context: HealthContext,
                context: EvaluationContext = None,
                strict = True) -> SufficiencyResult:
        ...


class SufficiencyEvaluator(SufficiencyEvaluatorProtocol):

    def __init__(self, identifier: str, cpg_variables: list[Var]):

        self.id = identifier
        self.cpg_variables = cpg_variables

    def _build_code_index(self, user_records: list[Record]) -> dict[str, Record]:
        """Build index mapping code strings to records for O(1) lookup."""
        index = {}
        for record in user_records:
            if record.var.code:
                for c in record.var.code:
                    index[c.as_string] = record
        return index

    def _find_record_by_code(self, var: Var, code_index: dict[str, Record]) -> Record | None:
        """Find a user record matching CPG variable by code using pre-built index.

        Args:
            var: The CPG variable to match
            code_index: Pre-built dict mapping code strings to records

        Returns:
            Matching Record or None
        """
        if not var.code:
            return None

        for c in var.code:
            if c.as_string in code_index:
                record = code_index[c.as_string]
                log.debug(f"Matched {var.id} to {record.id} by code {c.as_string}")
                return record

        return None

    def evaluate(self,
                user_context: HealthContext,
                context: EvaluationContext = None,
                strict = True) -> SufficiencyResult:
        """Evalutes a given list of variables for sufficiency to execute a CPG and categorizes 
        each variable.
        Note: Always call cpg.is_valid() else where before evaluating for sufficiency!

        Args:
            user_context: HealthContext 
            context (EvaluationContext, optional): Records evaluation context. Defaults to None.
            strict: If True- plausibility and panel evaluation raises evaluation error

        Returns:
            SufficiencyResult: Sufficiency
        """
        
        eval_ctx = context or EvaluationContext()

        # Build indexes once for O(1) lookups
        user_record_index = RecordIndex(user_context.records)
        code_index = self._build_code_index(user_context.records)

        records: list[Record] = []
        # --- Sufficiency only checks of `cpg.Variables`
        # --- Assessments, Eligibility, Recommendations rely on Sufficiency of cpg.Variables to execute
        for var in self.cpg_variables:
            # O(1) lookup by var.id first
            user_record = user_record_index.get_by_var_id(var.id)

            # If not found by ID, try code-based matching using pre-built index
            if not user_record:
                user_record = self._find_record_by_code(var, code_index)

            # Assign Values to Concord Record
            if user_record and user_record.has_value:
                record = Record(var, initial_values=user_record.values)
            else:
                record = Record(var, initial_values=None)

            records.append(record)


        # --- PERFORM EVALUATION CHECKS --- 
        for record in records:

            try:
                if record.validate(records=records, strict=strict):
                    eval_ctx.successful_evaluation(record)
            except Exception as e:
                log.debug(f"Validation failed for {record.id}: {e}")
                eval_ctx.failed_evaluation(record, e)   
                

            record.set_narrative(persona=user_context.persona)
            
        return SufficiencyResult(eval_ctx)











