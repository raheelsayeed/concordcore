"""Converts CPG Var metadata into form field specs for the attestation UI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from variables.var import Var, VarCategory
from primitives.types import ValueType


@dataclass
class FormField:
    variable_id: str
    label: str
    input_type: str  # toggle, number, text, date, select
    required: bool
    help_text: str | None = None
    value_type: str | None = None
    options: list[dict] | None = None
    validation: dict | None = None
    default_value: Any = None

    def to_dict(self) -> dict:
        d = {
            "variable_id": self.variable_id,
            "label": self.label,
            "input_type": self.input_type,
            "required": self.required,
        }
        for key in ("help_text", "value_type", "options", "validation"):
            val = getattr(self, key)
            if val:
                d[key] = val
        if self.default_value is not None:
            d["default_value"] = self.default_value
        return d


_BOOLEAN_CODE_SYSTEMS = {
    "http://snomed.info/sct",
    "http://www.nlm.nih.gov/research/umls/rxnorm",
}

KNOWN_CODED_OPTIONS: dict[str, list[dict]] = {
    "Gender": [
        {"value": "http://snomed.info/sct|248153007", "label": "Male"},
        {"value": "http://snomed.info/sct|248152002", "label": "Female"},
    ],
    "Ethnicity": [
        {"value": "urn:oid:2.16.840.1.113883.6.238|2106-3", "label": "White"},
        {"value": "urn:oid:2.16.840.1.113883.6.238|2058-6", "label": "Black or African American"},
        {"value": "urn:oid:2.16.840.1.113883.6.238|2028-9", "label": "Asian"},
        {"value": "urn:oid:2.16.840.1.113883.6.238|2076-8", "label": "Native Hawaiian or Other Pacific Islander"},
        {"value": "urn:oid:2.16.840.1.113883.6.238|2054-5", "label": "Hispanic or Latino"},
        {"value": "urn:oid:2.16.840.1.113883.6.238|1002-5", "label": "American Indian or Alaska Native"},
    ],
}


def _make_field(var: Var, input_type: str, value_type: str | None = None,
                help_text: str | None = None, **kwargs) -> FormField:
    return FormField(
        variable_id=var.id,
        label=var.title or var.id,
        input_type=input_type,
        required=var.required,
        help_text=help_text,
        value_type=value_type,
        **kwargs,
    )


def _parse_validation(var: Var) -> dict | None:
    """Extract min/max from validator plausible expressions like '$value > 40'."""
    if not var.validator:
        return None
    plausible = var.validator.get("plausible")
    if not plausible:
        return None
    result = {}
    for m in re.finditer(r'\$value\s*(>=?|<=?)\s*(\d+(?:\.\d+)?)', plausible):
        op, num = m.group(1), float(m.group(2))
        if op in (">", ">="):
            result["min"] = num
        elif op in ("<", "<="):
            result["max"] = num
    return result or None


class FormBuilder:
    """Converts missing Var list into FormField specifications."""

    def build_fields(self, missing_vars: list[dict], cpg_variables: list[Var]) -> list[FormField]:
        var_lookup = {v.id: v for v in cpg_variables} if cpg_variables else {}
        fields = []
        for mv in missing_vars:
            var = var_lookup.get(mv["variable_id"])
            if var:
                fields.append(self._var_to_field(var))
            else:
                fields.append(FormField(
                    variable_id=mv["variable_id"],
                    label=mv.get("title", mv["variable_id"]),
                    input_type="text",
                    required=mv.get("required", True),
                    help_text=mv.get("llm_prompt") or mv.get("question"),
                    value_type=mv.get("type"),
                ))
        return fields

    def _var_to_field(self, var: Var) -> FormField:
        help_text = var.llm_prompt or var.question or var.description

        if var.id in KNOWN_CODED_OPTIONS:
            return _make_field(var, "select", "string", help_text,
                               options=KNOWN_CODED_OPTIONS[var.id])

        if var.type:
            return self._from_value_type(var, help_text)

        inferred = self._infer_from_code(var, help_text)
        return inferred if inferred else self._from_category(var, help_text)

    def _from_value_type(self, var: Var, help_text: str | None) -> FormField:
        validation = _parse_validation(var)

        if var.type == ValueType.boolean:
            return _make_field(var, "toggle", "boolean", help_text)

        if var.type == ValueType.integer:
            v = validation or {}
            v.setdefault("step", 1)
            return _make_field(var, "number", "integer", help_text, validation=v)

        if var.type == ValueType.decimal:
            v = validation or {}
            v.setdefault("step", 0.01)
            return _make_field(var, "number", "decimal", help_text, validation=v)

        if var.type == ValueType.date:
            return _make_field(var, "date", "date", help_text)

        return _make_field(var, "text", "string", help_text)

    def _infer_from_code(self, var: Var, help_text: str | None) -> FormField | None:
        if var.code:
            systems = {c.system for c in var.code if c.system}
            if systems & _BOOLEAN_CODE_SYSTEMS:
                return _make_field(var, "toggle", "boolean", help_text)

        if var.llm_prompt and var.user_attestable:
            prompt = var.llm_prompt.lower()
            if "return: true" in prompt or "yes/no" in prompt:
                return _make_field(var, "toggle", "boolean", help_text)

        return None

    def _from_category(self, var: Var, help_text: str | None) -> FormField:
        if var.category == VarCategory.condition:
            return _make_field(var, "toggle", "boolean", help_text)
        if var.category == VarCategory.demographics:
            return _make_field(var, "text", "string", help_text)
        return _make_field(var, "text", None, help_text)
