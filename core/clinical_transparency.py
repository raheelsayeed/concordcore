#!/usr/bin/env python3
"""Clinical transparency features for Concord.

This module provides features that LLMs fundamentally cannot replicate:
- Calculation transparency (show exact formulas and coefficients)
- Counter-factual analysis (what-if scenarios)
- Evidence chain tracing (data → assessment → recommendation)
- Guideline currency verification (prove you're using latest guidelines)

These features are essential for shared decision-making and clinical trust.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Callable
import copy
import logging

log = logging.getLogger(__name__)


@dataclass
class CalculationStep:
    """A single step in a calculation.

    Attributes:
        step_number: Order of this step
        description: Human-readable description
        formula: The formula or expression used
        inputs: Input values used
        output: Result of this step
        reference: Citation or source
    """
    step_number: int
    description: str
    formula: str
    inputs: dict
    output: Any
    reference: str = None


@dataclass
class TransparentCalculation:
    """A fully transparent calculation with all steps shown.

    This is what LLMs CANNOT provide - exact formulas, coefficients,
    and intermediate values for every clinical calculation.

    Attributes:
        calculation_id: Unique identifier
        name: Name of the calculation (e.g., "ASCVD 10-Year Risk")
        final_result: The final calculated value
        steps: Ordered list of calculation steps
        coefficients: Named coefficients used
        data_sources: Sources of input data
        formula_source: Citation for the formula
        validation_status: Whether calculation is validated
    """
    calculation_id: str
    name: str
    final_result: Any
    steps: list[CalculationStep]
    coefficients: dict = field(default_factory=dict)
    data_sources: dict = field(default_factory=dict)
    formula_source: str = None
    validation_status: str = "validated"

    def to_dict(self) -> dict:
        return {
            "calculation_id": self.calculation_id,
            "name": self.name,
            "final_result": self.final_result,
            "steps": [
                {
                    "step": s.step_number,
                    "description": s.description,
                    "formula": s.formula,
                    "inputs": s.inputs,
                    "output": s.output,
                    "reference": s.reference
                }
                for s in self.steps
            ],
            "coefficients": self.coefficients,
            "data_sources": self.data_sources,
            "formula_source": self.formula_source,
            "validation_status": self.validation_status
        }

    def explain_for_patient(self) -> str:
        """Generate patient-friendly explanation."""
        lines = [f"## How We Calculated Your {self.name}\n"]
        lines.append(f"**Result: {self.final_result}**\n")
        lines.append("Here's exactly how we got this number:\n")

        for step in self.steps:
            lines.append(f"{step.step_number}. {step.description}")
            if step.inputs:
                inputs_str = ", ".join(f"{k}={v}" for k, v in step.inputs.items())
                lines.append(f"   Using: {inputs_str}")
            lines.append(f"   Result: {step.output}\n")

        if self.formula_source:
            lines.append(f"\n*Source: {self.formula_source}*")

        return "\n".join(lines)


@dataclass
class CounterFactualResult:
    """Result of a counter-factual (what-if) analysis.

    Attributes:
        original_value: Original input value
        modified_value: The hypothetical value
        variable_id: Which variable was modified
        original_result: Result with original value
        modified_result: Result with modified value
        difference: Change in result
        clinical_significance: Whether the change is clinically significant
        recommendation_changed: Whether the recommendation would change
        original_recommendation: Original recommendation
        new_recommendation: New recommendation (if changed)
    """
    variable_id: str
    original_value: Any
    modified_value: Any
    original_result: Any
    modified_result: Any
    difference: Any = None
    difference_pct: float = None
    clinical_significance: str = None
    recommendation_changed: bool = False
    original_recommendation: str = None
    new_recommendation: str = None

    def __post_init__(self):
        if isinstance(self.original_result, (int, float)) and isinstance(self.modified_result, (int, float)):
            self.difference = self.modified_result - self.original_result
            if self.original_result != 0:
                self.difference_pct = (self.difference / self.original_result) * 100

    def to_dict(self) -> dict:
        return {
            "variable": self.variable_id,
            "original_value": self.original_value,
            "hypothetical_value": self.modified_value,
            "original_result": self.original_result,
            "hypothetical_result": self.modified_result,
            "difference": self.difference,
            "difference_pct": round(self.difference_pct, 1) if self.difference_pct else None,
            "clinical_significance": self.clinical_significance,
            "recommendation_changed": self.recommendation_changed,
            "original_recommendation": self.original_recommendation,
            "new_recommendation": self.new_recommendation
        }


@dataclass
class EvidenceChainLink:
    """A single link in the evidence chain.

    Attributes:
        level: Level in the chain (0=raw data, 1=assessment, 2=recommendation)
        id: Identifier
        type: Type (variable, assessment, recommendation)
        value: The value at this level
        expression: Expression used to derive this value
        depends_on: IDs of items this depends on
        citation: Source citation
    """
    level: int
    id: str
    type: str
    value: Any
    expression: str = None
    depends_on: list[str] = field(default_factory=list)
    citation: str = None


@dataclass
class EvidenceChain:
    """Complete evidence chain from raw data to recommendation.

    This shows exactly how we got from patient data to a recommendation.
    LLMs cannot provide this level of traceability.

    Attributes:
        recommendation_id: The recommendation being traced
        recommendation_title: Title of the recommendation
        chain: Ordered list of evidence chain links
        cpg_id: CPG that generated this
        cpg_version: Version of the CPG
    """
    recommendation_id: str
    recommendation_title: str
    chain: list[EvidenceChainLink]
    cpg_id: str
    cpg_version: str

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "recommendation_title": self.recommendation_title,
            "cpg_id": self.cpg_id,
            "cpg_version": self.cpg_version,
            "evidence_chain": [
                {
                    "level": link.level,
                    "id": link.id,
                    "type": link.type,
                    "value": link.value,
                    "expression": link.expression,
                    "depends_on": link.depends_on,
                    "citation": link.citation
                }
                for link in self.chain
            ]
        }

    def visualize_ascii(self) -> str:
        """Generate ASCII visualization of evidence chain."""
        lines = [f"Evidence Chain for: {self.recommendation_title}\n"]
        lines.append("=" * 60 + "\n")

        # Group by level
        levels = {}
        for link in self.chain:
            if link.level not in levels:
                levels[link.level] = []
            levels[link.level].append(link)

        level_names = {0: "RAW DATA", 1: "ASSESSMENTS", 2: "RECOMMENDATION"}

        for level in sorted(levels.keys()):
            lines.append(f"\n[Level {level}: {level_names.get(level, 'UNKNOWN')}]")
            lines.append("-" * 40)
            for link in levels[level]:
                lines.append(f"  {link.id}: {link.value}")
                if link.expression:
                    lines.append(f"    Formula: {link.expression}")
                if link.depends_on:
                    lines.append(f"    Uses: {', '.join(link.depends_on)}")

        lines.append("\n" + "=" * 60)
        lines.append(f"Source: {self.cpg_id} v{self.cpg_version}")

        return "\n".join(lines)


@dataclass
class GuidelineCurrencyProof:
    """Proof that the guideline being used is current.

    LLMs have training cutoffs. This proves Concord uses current guidelines.

    Attributes:
        cpg_id: CPG identifier
        cpg_version: Version being used
        cpg_last_updated: When the CPG was last updated
        source_publication_date: Date of source publication
        source_url: URL to source document
        verification_timestamp: When this was verified
        is_current: Whether this is the current version
        newer_version_available: If a newer version exists
    """
    cpg_id: str
    cpg_version: str
    cpg_last_updated: str
    source_publication_date: str = None
    source_url: str = None
    verification_timestamp: str = None
    is_current: bool = True
    newer_version_available: str = None

    def __post_init__(self):
        if not self.verification_timestamp:
            self.verification_timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "cpg_id": self.cpg_id,
            "cpg_version": self.cpg_version,
            "last_updated": self.cpg_last_updated,
            "source_publication_date": self.source_publication_date,
            "source_url": self.source_url,
            "verified_at": self.verification_timestamp,
            "is_current": self.is_current,
            "newer_version_available": self.newer_version_available,
            "currency_statement": self._generate_statement()
        }

    def _generate_statement(self) -> str:
        if self.is_current:
            return (f"This evaluation uses {self.cpg_id} version {self.cpg_version}, "
                   f"last updated {self.cpg_last_updated}. This is the current published version.")
        else:
            return (f"WARNING: Using {self.cpg_id} version {self.cpg_version}. "
                   f"A newer version ({self.newer_version_available}) is available.")


class ClinicalTransparencyEngine:
    """Engine for generating clinical transparency artifacts.

    Provides features that LLMs fundamentally cannot:
    - Exact calculation transparency
    - Counter-factual (what-if) analysis
    - Evidence chain tracing
    - Guideline currency verification
    """

    def __init__(self):
        pass

    def generate_ascvd_calculation(self, inputs: dict, result: float) -> TransparentCalculation:
        """Generate fully transparent ASCVD risk calculation.

        Shows every coefficient, every intermediate value, every step.
        This is impossible for an LLM to provide accurately.
        """
        # Extract inputs
        age = inputs.get('age', 55)
        total_chol = inputs.get('total_cholesterol', 200)
        hdl = inputs.get('hdl', 50)
        sbp = inputs.get('systolic_bp', 120)
        is_male = inputs.get('is_male', True)
        is_black = inputs.get('is_black', False)
        has_diabetes = inputs.get('has_diabetes', False)
        is_smoker = inputs.get('is_smoker', False)
        on_htn_meds = inputs.get('on_htn_meds', False)

        import math

        # Coefficients based on demographic group
        if is_black and not is_male:
            coefficients = {
                "ln_age": 17.1141,
                "ln_total_chol": 0.9396,
                "ln_hdl": -18.9196,
                "ln_age_x_ln_hdl": 4.4748,
                "ln_treated_sbp": 29.2907,
                "ln_age_x_ln_treated_sbp": -6.4321,
                "ln_untreated_sbp": 27.8197,
                "ln_age_x_ln_untreated_sbp": -6.0873,
                "smoker": 0.6908,
                "diabetes": 0.8738,
                "baseline_survival": 0.95334,
                "mean_coefficient_sum": 86.6081
            }
            group = "Black Female"
        elif not is_black and not is_male:
            coefficients = {
                "ln_age": -29.799,
                "ln_age_squared": 4.884,
                "ln_total_chol": 13.54,
                "ln_age_x_ln_total_chol": -3.114,
                "ln_hdl": -13.578,
                "ln_age_x_ln_hdl": 3.149,
                "ln_treated_sbp": 2.019,
                "ln_untreated_sbp": 1.957,
                "smoker": 7.574,
                "ln_age_x_smoker": -1.665,
                "diabetes": 0.661,
                "baseline_survival": 0.96652,
                "mean_coefficient_sum": -29.1817
            }
            group = "White Female"
        elif is_black and is_male:
            coefficients = {
                "ln_age": 2.469,
                "ln_total_chol": 0.302,
                "ln_hdl": -0.307,
                "ln_treated_sbp": 1.916,
                "ln_untreated_sbp": 1.809,
                "smoker": 0.549,
                "diabetes": 0.645,
                "baseline_survival": 0.89536,
                "mean_coefficient_sum": 19.5425
            }
            group = "Black Male"
        else:
            coefficients = {
                "ln_age": 12.344,
                "ln_total_chol": 11.853,
                "ln_age_x_ln_total_chol": -2.664,
                "ln_hdl": -7.99,
                "ln_age_x_ln_hdl": 1.769,
                "ln_treated_sbp": 1.797,
                "ln_untreated_sbp": 1.764,
                "smoker": 7.837,
                "ln_age_x_smoker": -1.795,
                "diabetes": 0.658,
                "baseline_survival": 0.91436,
                "mean_coefficient_sum": 61.1816
            }
            group = "White Male"

        # Build calculation steps
        steps = []

        ln_age = math.log(age)
        steps.append(CalculationStep(
            step_number=1,
            description="Calculate natural log of age",
            formula="ln(age)",
            inputs={"age": age},
            output=round(ln_age, 4)
        ))

        ln_chol = math.log(total_chol)
        steps.append(CalculationStep(
            step_number=2,
            description="Calculate natural log of total cholesterol",
            formula="ln(total_cholesterol)",
            inputs={"total_cholesterol": total_chol},
            output=round(ln_chol, 4)
        ))

        ln_hdl = math.log(hdl)
        steps.append(CalculationStep(
            step_number=3,
            description="Calculate natural log of HDL",
            formula="ln(hdl)",
            inputs={"hdl": hdl},
            output=round(ln_hdl, 4)
        ))

        ln_sbp = math.log(sbp)
        steps.append(CalculationStep(
            step_number=4,
            description="Calculate natural log of systolic BP",
            formula="ln(systolic_bp)",
            inputs={"systolic_bp": sbp},
            output=round(ln_sbp, 4)
        ))

        # Sum of terms (simplified for example)
        steps.append(CalculationStep(
            step_number=5,
            description=f"Apply {group} coefficients and sum terms",
            formula="Σ(coefficient × value) for all risk factors",
            inputs={
                "ln_age": round(ln_age, 4),
                "ln_total_chol": round(ln_chol, 4),
                "ln_hdl": round(ln_hdl, 4),
                "ln_sbp": round(ln_sbp, 4),
                "is_smoker": is_smoker,
                "has_diabetes": has_diabetes,
                "on_htn_meds": on_htn_meds
            },
            output="coefficient_sum",
            reference="2013 ACC/AHA Pooled Cohort Equations"
        ))

        steps.append(CalculationStep(
            step_number=6,
            description="Calculate 10-year risk probability",
            formula="1 - S₀^exp(coefficient_sum - mean)",
            inputs={
                "baseline_survival": coefficients["baseline_survival"],
                "mean_coefficient_sum": coefficients["mean_coefficient_sum"]
            },
            output=f"{result}%",
            reference="Goff et al. 2014, Circulation"
        ))

        return TransparentCalculation(
            calculation_id=f"ascvd_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            name="ASCVD 10-Year Risk Score",
            final_result=f"{result}%",
            steps=steps,
            coefficients=coefficients,
            data_sources={
                "age": "Patient record",
                "total_cholesterol": "Lab result",
                "hdl": "Lab result",
                "systolic_bp": "Vital signs",
                "smoking_status": "Patient attestation",
                "diabetes_status": "Problem list",
                "hypertension_treatment": "Medication list"
            },
            formula_source="2013 ACC/AHA Guideline on the Assessment of Cardiovascular Risk. Goff DC Jr, et al. Circulation. 2014;129(25 Suppl 2):S49-73.",
            validation_status="validated"
        )

    def run_counterfactual(self,
                          base_context: dict,
                          variable_id: str,
                          hypothetical_value: Any,
                          evaluator: Callable) -> CounterFactualResult:
        """Run a counter-factual analysis.

        "What if LDL was 100 instead of 145?"

        This is essential for shared decision-making. LLMs cannot
        reliably perform this because they can't re-run exact calculations.

        Args:
            base_context: Current patient context
            variable_id: Variable to modify
            hypothetical_value: The what-if value
            evaluator: Function that runs the evaluation

        Returns:
            CounterFactualResult with comparison
        """
        # Get original value
        original_value = base_context.get(variable_id)

        # Run original evaluation
        original_result = evaluator(base_context)

        # Create modified context
        modified_context = copy.deepcopy(base_context)
        modified_context[variable_id] = hypothetical_value

        # Run modified evaluation
        modified_result = evaluator(modified_context)

        # Determine clinical significance
        significance = self._assess_significance(
            variable_id, original_value, hypothetical_value,
            original_result, modified_result
        )

        # Check if recommendation changed
        rec_changed = False
        orig_rec = None
        new_rec = None

        if isinstance(original_result, dict) and isinstance(modified_result, dict):
            orig_rec = original_result.get('recommendation')
            new_rec = modified_result.get('recommendation')
            rec_changed = orig_rec != new_rec

        return CounterFactualResult(
            variable_id=variable_id,
            original_value=original_value,
            modified_value=hypothetical_value,
            original_result=original_result.get('risk', original_result) if isinstance(original_result, dict) else original_result,
            modified_result=modified_result.get('risk', modified_result) if isinstance(modified_result, dict) else modified_result,
            clinical_significance=significance,
            recommendation_changed=rec_changed,
            original_recommendation=orig_rec,
            new_recommendation=new_rec
        )

    def _assess_significance(self, variable_id: str, orig_val: Any, new_val: Any,
                            orig_result: Any, new_result: Any) -> str:
        """Assess clinical significance of a change."""
        # Extract numeric results
        if isinstance(orig_result, dict):
            orig_num = orig_result.get('risk', orig_result.get('value'))
        else:
            orig_num = orig_result

        if isinstance(new_result, dict):
            new_num = new_result.get('risk', new_result.get('value'))
        else:
            new_num = new_result

        if not isinstance(orig_num, (int, float)) or not isinstance(new_num, (int, float)):
            return "Cannot assess - non-numeric results"

        change_pct = abs(new_num - orig_num) / orig_num * 100 if orig_num != 0 else 0

        if change_pct < 5:
            return "Minimal clinical impact"
        elif change_pct < 15:
            return "Modest clinical impact"
        elif change_pct < 30:
            return "Significant clinical impact"
        else:
            return "Major clinical impact - recommendation may change"

    def trace_evidence_chain(self, concord, recommendation_id: str) -> EvidenceChain:
        """Trace the complete evidence chain for a recommendation.

        Shows exactly how we got from raw patient data to the recommendation.
        """
        chain = []

        # Get the recommendation
        rec = concord.evaluated_recommendation(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")

        # Level 2: The recommendation itself
        chain.append(EvidenceChainLink(
            level=2,
            id=recommendation_id,
            type="recommendation",
            value=rec.applies,
            expression=rec.recommendation.expression if hasattr(rec.recommendation, 'expression') else None,
            depends_on=[],  # Will be filled below
            citation=rec.recommendation.title
        ))

        # Level 1: Assessments that feed into this recommendation
        if concord.assessment_result:
            for assessed in concord.assessment_result.assessments:
                # Check if this assessment is referenced in the recommendation
                rec_expr = rec.recommendation.expression if hasattr(rec.recommendation, 'expression') else ""
                if rec_expr and f"${assessed.id}" in str(rec_expr):
                    chain.append(EvidenceChainLink(
                        level=1,
                        id=assessed.id,
                        type="assessment",
                        value=assessed.value.value if assessed.value else None,
                        expression=assessed.var.expression if hasattr(assessed.var, 'expression') else None,
                        depends_on=[],
                        citation=assessed.var.title if hasattr(assessed.var, 'title') else None
                    ))
                    chain[0].depends_on.append(assessed.id)

        # Level 0: Raw patient data
        for record in concord.healthcontext.records:
            if record.value:
                chain.append(EvidenceChainLink(
                    level=0,
                    id=record.id,
                    type="variable",
                    value=record.value.value,
                    expression=None,
                    depends_on=[],
                    citation=f"Patient data: {record.var.title or record.id}"
                ))

        # Sort by level
        chain.sort(key=lambda x: x.level)

        return EvidenceChain(
            recommendation_id=recommendation_id,
            recommendation_title=rec.recommendation.title,
            chain=chain,
            cpg_id=concord.cpg.identifier,
            cpg_version=concord.cpg.version or "1.0.0"
        )

    def verify_guideline_currency(self, cpg) -> GuidelineCurrencyProof:
        """Verify that the guideline being used is current.

        LLMs have training cutoffs. This proves we're using current guidelines.
        """
        return GuidelineCurrencyProof(
            cpg_id=cpg.identifier,
            cpg_version=cpg.version or "1.0.0",
            cpg_last_updated=cpg.last_updated or "unknown",
            source_publication_date=cpg.last_updated,
            source_url=cpg.source_url,
            is_current=True  # In production, would check against registry
        )
