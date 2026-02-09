#!/usr/bin/env python3
"""Record class for ConcordCore.

A Record combines a variable definition (Var) with actual patient values.
"""

from dataclasses import dataclass, field, InitVar
from functools import cache, cached_property
from datetime import datetime
from typing import Any

import logging, humanize
from simpleeval import simple_eval

from typing_extensions import Self
from concordcore.primitives.errors import VarError

from concordcore.primitives.varstring import EvaluatorString, ValidationExpression
from concordcore.variables.var import Narrative, Var, VarError, VarImplausibleError, VarPanelValidationError
from concordcore.variables.value import Value
from concordcore.primitives.vlist import vlist
from concordcore.primitives.types import Persona

logger = logging.getLogger(__name__)

# Validator dict keys
VALIDATOR_PANEL = 'panel'
VALIDATOR_PLAUSIBLE = 'plausible'

# Comparison operators for value filtering
COMPARISON_OPERATORS = '<>=!'


@dataclass
class Record:
    """A record combining a variable definition with patient values.

    Attributes:
        var: The variable definition
        initial_values: Optional list of values to initialize record with
    """

    var: Var
    initial_values: InitVar[list[Value] | None] = None
    # Internal storage for values
    _stored_values: vlist[Value] = field(init=False, default=None)
    _attested_value: Value = field(init=False, default=None)
    _narrative: str = field(init=False, default=None)
    _plausible_validator: ValidationExpression = field(init=False, default=None)
    _panel_validator: EvaluatorString = field(init=False, default=None)
    _persona: Persona = field(init=False, default=None)

    def __post_init__(self, initial_values: list[Value] | None):
        # Accept values parameter directly (cleaner API)
        self._stored_values = vlist(initial_values) if initial_values else None

        # Initialize validators
        if self.var.validator:
            logger.debug(self.var.validator)
            self._panel_validator = (
                EvaluatorString(self.var.validator[VALIDATOR_PANEL])
                if VALIDATOR_PANEL in self.var.validator else None
            )
            self._plausible_validator = (
                ValidationExpression(self.var.validator[VALIDATOR_PLAUSIBLE])
                if VALIDATOR_PLAUSIBLE in self.var.validator else None
            )
        else:
            self._panel_validator = None
            self._plausible_validator = None

        self._persona = None

    def __repr__(self) -> str:
        return f'Record<{self.var.id}; values={self.get_values() or ""}>'

    @cached_property
    def _must_filter_values(self) -> bool:
        """Check if values need filtering based on value_filter."""
        if self.var.value_filter:
            logging.debug(f'{self.id} Record.values are filtered')
            return True
        return False

    @property
    def id(self) -> str:
        """Variable identifier."""
        return self.var.id

    @property
    def title(self) -> str | None:
        """Variable title."""
        return self.var.title

    @property
    def code(self):
        """Variable code(s)."""
        return self.var.code

    @property
    def value(self) -> Value | None:
        """Most recent/primary value."""
        vals = self.get_values()
        return vals[0] if vals else None

    def get_values(self) -> vlist[Value] | None:
        """Get all values, applying filters and attestations.

        Returns:
            vlist of Value objects, or None if no values
        """
        if self._attested_value:
            return vlist([self._attested_value])
        elif self._must_filter_values:
            return self.filtered_values
        else:
            return self._stored_values

    # Backward compatible property
    @property
    def values(self) -> vlist[Value] | None:
        """Get all values (alias for get_values)."""
        return self.get_values()

    @property
    def attested_value(self) -> Value | None:
        """User-attested value."""
        return self._attested_value

    @attested_value.setter
    def attested_value(self, value: Value):
        """Set user-attested value."""
        if self.var.user_attestable:
            if self.validate(value=value):
                self._attested_value = value
                assert self._attested_value
        else:
            raise ValueError(f'Variable is not attestable var={self.id}')
        self.set_narrative(persona=self._persona)

    @property
    def narrative(self) -> str | None:
        """Generated narrative text."""
        return self._narrative

    @property
    def has_value(self) -> bool:
        """Check if record has at least one value."""
        return self.value is not None

    def _filter_values(self, values: vlist[Value]) -> vlist[Value] | None:
        """Apply value filters to the values list."""
        if not values:
            logging.debug('No values to apply valuefilter')
            return None
        lst = list(filter(self._function_filter, values))
        if self.var.value_filter.upper:
            return vlist(lst[:self.var.value_filter.upper])
        if self.var.value_filter.lower:
            return vlist(lst[-int(self.var.value_filter.lower):])
        return vlist(lst)

    def _function_filter(self, value: Value) -> bool:
        """Filter function for individual values."""
        bools = []
        if self.var.value_filter.after_date:
            bools.append(value.date >= self.var.value_filter.after_date)
        if self.var.value_filter.before_date:
            bools.append(value.date <= self.var.value_filter.before_date)
        if self.var.value_filter.value_expression:
            exp = self.var.value_filter.value_expression.strip()
            # Backward compatibility: if expression starts with operator, prepend 'value'
            if exp and exp[0] in COMPARISON_OPERATORS:
                exp = 'value ' + exp
            result = simple_eval(exp, names={'value': value.value})
            bools.append(result)
        return False not in bools

    @cached_property
    def filtered_values(self) -> vlist[Value] | None:
        """Values after applying filters."""
        if not self._must_filter_values:
            return None
        return self._filter_values(self._stored_values)
    
    def set_narrative(self, persona: Persona = None, variable_data_dict: dict = None):
        """Generate and set narrative text for this record.

        Args:
            persona: The persona (patient/provider) for narrative style. Defaults to patient.
            variable_data_dict: Optional dict of variable data for substitution

        Returns:
            The generated narrative text, or None if no narrative defined
        """
        # Use default persona if None passed
        persona = persona or Persona.patient

        narr = self.var.narr or self.default_narratives

        if not narr:
            return None

        if variable_data_dict:
            variable_data_dict.update({"self": self.as_dict()})
        else:
            variable_data_dict = {"self": self.as_dict()}

        self._narrative = narr.get_text(
            self.value.value if self.value else None,
            persona,
            variable_data_dict,
            default=self.default_narratives.data
        )

        self._persona = persona
        return self._narrative

    @cached_property
    def default_narratives(self):

        data = {
            Persona.patient.value: {
                "HasValue": "Following results in your record: $self.values",
                "NoValue": "Not found in your record",
                True: "Following results in your record: $self.values",
                False: "Not found in your record"
            },
            Persona.provider.value: {
                "HasValue": "Values: $self.values",
                True: "Values: $self.values",
                "NoValue": "Not in record",
                False: "Not in record"
            }
        }
        return Narrative(data)

        


    def as_dict(self):
        var_dict = self.var.as_dict()
        var_dict.update({
                'value': self.value.value if self.value else None,
                'values': self.values.representation if self.values else None,
                'date': self.value.date if self.value else None,
                'count': len(self.values) if self.values else None,
            })
        return var_dict

    def validate(self, value: Value = None, records: list[Self] = None, strict:bool = True):

        val = value or self.value

        if val is None:
            logger.warning(f'Record={self.id} has no value to validate')
            return True
        
        if not isinstance(val, Value):
            ve = VarError(f'Record={self.id}.value.type = {type(val)}')
            raise ve

        if self.var.value_type:
            vtype = self.var.value_type.type
            if vtype == bool and isinstance(val.value, str) and (val.value not in ['False', 'True']):
                raise VarError(f'Record=<{self.id}> invalid value_type={type(val.value)}; need={vtype}', self.id)
            if vtype(val.value) is None:
                raise VarError(f'Record=<{self.id}> invalid value_type={type(val.value)}; need={vtype}', self.id)


        if self._plausible_validator:
            try:
                res = self._plausible_validator.evaluate(value=val.value)
                if not res:
                    e = VarImplausibleError(self.var, val.value)
                    if strict:
                        raise e
                    else:
                        logger.warning(e)
            except Exception as e:
                if strict:
                    raise e
                else:
                    logger.warning(e)

        if self._panel_validator and records:
            try:
                expression_vars = self._panel_validator.variables
                # Use set for O(1) lookup instead of list membership
                expr_var_set = set(expression_vars)
                filtered = [r for r in records if r.id in expr_var_set]
                f_dict = {r.id: r.value.value if r.value else None for r in filtered}
                f_dict.update({'value': self.value.value})
                if None in f_dict.values():
                    e = VarError(self.var.id, f'Cannot evaluate expression, missing values={f_dict}')
                    if strict:
                        raise e
                    else:
                        logger.warning(e)

                res = self._panel_validator.evaluate(f_dict)
                if not res:
                    e = VarPanelValidationError(self.var, val.value)
                    if strict:
                        raise e
                    else:
                        logger.warning(e)
            except Exception as e:
                if strict:
                    raise e
                else:
                    logger.warning(e)

        return True
