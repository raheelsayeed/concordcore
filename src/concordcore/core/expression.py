#!/usr/bin/env python3
"""Expression evaluation for ConcordCore.

This module provides the Expression class for evaluating CPG expressions
that reference variable values. Expressions use $VarID syntax and are
evaluated using simpleeval for security.

Expression Syntax:
    Variables: $VarID (references record value)
    Functions: in_range($value, 100, 200)
    Accessors: $VarID.count, $VarID.date
    Operators: >, <, >=, <=, ==, !=, and, or, not

Example expressions:
    $LDL > 130                    # Simple comparison
    $Age >= 40 and $Age <= 75     # Compound expression
    $high_ldl == True             # Reference assessment result
    in_range($LDL, 100, 200)      # Use registry function
    $LDL.count > 3                # Count of values
"""

from dataclasses import dataclass
from functools import cached_property
from re import findall
from typing import Any

from concordcore.primitives.errors import ExpressionVariableNotFound, ExpressionEvaluationError, VariableEvaluationError
from concordcore.primitives.varstring import VarString
from concordcore.variables.value import Value
from .record_index import RecordIndex
import simpleeval
import logging

# Import function registry
from .expression_registry import registry as function_registry

log = logging.getLogger(__name__)

# Expression syntax constants
EXPR_VAR_PREFIX = '$'
EXPR_ACCESSOR_SEPARATOR = '.'

# Expression accessor suffixes
EXPR_ACCESSOR_COUNT = 'count'
EXPR_ACCESSOR_DATE = 'date'

# Cache for function registry (avoid rebuilding on every expression)
_cached_functions: dict | None = None


def _get_cached_functions() -> dict:
    """Get cached function registry dict."""
    global _cached_functions
    if _cached_functions is None:
        _cached_functions = function_registry.get_functions()
    return _cached_functions


def clear_function_cache() -> None:
    """Clear the function cache (call after registering new functions)."""
    global _cached_functions
    _cached_functions = None


class Expression:

    def __init__(self, expression_string: str):
        self.string = VarString(expression_string)
        self.__expression_records =  []
        self._result = None
    
    @property
    def expression_records(self):
        return self.__expression_records

    @property
    def result(self):
        return self._result

    def __repr__(self) -> str:
        return f'Expression({self.string})'

    @property
    def variable_identifiers(self):
        return self.string.variable_identifiers

    def evaluate_recommendation(self, evaluated_records):
        """Evaluate expression for recommendation using assessment records.

        Args:
            evaluated_records: List of EvaluatedRecord objects from assessment phase

        Returns:
            bool: The result of the expression evaluation

        Raises:
            ValueError: If no variable identifiers found
            VariableEvaluationError: If required variables are missing
        """
        assessment_ids = self.string.variable_identifiers
        if not assessment_ids:
            raise ValueError(f'Expression must have AssessmentVariable identifiers, none found in {self.string}')

        # Build index for O(1) lookup
        record_index = RecordIndex(evaluated_records)

        self.__expression_records = []
        expression_values = {}
        errors = []

        for assessment_var_id in assessment_ids:
            # O(1) lookup instead of O(n) filter
            filtered = record_index.get_by_id(assessment_var_id)
            if filtered:
                if filtered.record.value:
                    expression_values[assessment_var_id] = filtered.record.value.value
                    self.__expression_records.append(filtered.record)
                else:
                    errors.append(KeyError(f'No value for Assessment={filtered.id} in {self.string}'))
                    continue
            else:
                errors.append(KeyError(f'Cannot find Assessment={assessment_var_id} in {self.string}'))

        if errors:
            raise VariableEvaluationError(errors, f'expression={self.string}')

        try:
            expstr = self.string.replace(EXPR_VAR_PREFIX, '')
            # Use cached functions for better performance
            expression_result = simpleeval.simple_eval(
                expstr,
                names=expression_values,
                functions=_get_cached_functions()
            )
            if not isinstance(expression_result, bool):
                raise ValueError(f'Recommendation.expression result must be a bool-type, got={type(expression_result)}')
            return expression_result
        except Exception:
            raise

    def evaluate(self, records, record_index=None):
        """Evaluate expression against provided records.

        Args:
            records: List of Record objects with values
            record_index: Optional pre-built RecordIndex for O(1) lookups (avoids rebuilding)

        Returns:
            Value: The result wrapped in a Value object

        Raises:
            ValueError: If no variable identifiers found
            ExpressionVariableNotFound: If a referenced variable doesn't exist
            ExpressionEvaluationError: If evaluation fails
        """
        self.__expression_records = []
        expression_tags = self.string.tags
        if not expression_tags:
            raise ValueError(f'Expressions must have variable-identifiers, none found in {self.string}')

        # Use pre-built index if provided, otherwise build it
        if record_index is None:
            record_index = RecordIndex(records)

        expression_values = {}
        dependency_variables_nullValues = []

        for exp_var_id in expression_tags:
            comps = exp_var_id.split(EXPR_ACCESSOR_SEPARATOR)
            var_id = comps[0]
            func = comps[1] if len(comps) == 2 else None

            # O(1) lookup instead of O(n) filter
            filtered_record = record_index.get_by_id(var_id)

            if filtered_record:
                expression_values.update({filtered_record.id: filtered_record.as_dict()})
                var_value = None

                # Handle accessor functions
                if func == EXPR_ACCESSOR_COUNT:
                    var_value = {'count': len(filtered_record.values) if filtered_record.values is not None else 0}
                elif func == EXPR_ACCESSOR_DATE:
                    var_value = {'date': filtered_record.value.date} if filtered_record.value is not None else None
                else:
                    var_value = filtered_record.value.evaluation_val if filtered_record.value else None

                if var_value is None:
                    dependency_variables_nullValues.append(exp_var_id)

                expression_values[var_id] = var_value
                self.__expression_records.append(filtered_record)
            else:
                raise ExpressionVariableNotFound(exp_var_id, self.string)

        try:
            expstr = self.string.replace(EXPR_VAR_PREFIX, '')
            evaluator = simpleeval.SimpleEval(
                names=expression_values,
                functions=_get_cached_functions()
            )
            expression_result = evaluator.eval(expstr)
            self._result = Value(expression_result, source=self.__expression_records)
            log.debug(f'Evaluating values=<{expression_values}>, expression=<{expstr}>, result=<{expression_result}>')
        except TypeError as e:
            raise ExpressionEvaluationError(expstr, expression_values, str(e))
        except Exception as e:
            raise ExpressionEvaluationError(expstr, expression_values, str(e))

        return self._result


