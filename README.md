`Concord_`
=========

--- not ready for use ---

Python framework to compute and yeild recommendations based on published evidence, clinical practice guideline(s),for a given longitudinal health record. 

1. __IN__
    - `CPG-YAML`: A clinical practise guideline (CPG) definition file, encoded in `YAML` and accompanying `<file-name>.py` module if necessary.
    - `HealthContext`: a longtidinal health record consisting of `concordcore.variables.record(s)`
2. __OUT__ 
    - Eligibility: Does the CPG apply to the given `healthcontext`?
    - Sufficiency: Is the data in `healthcontext` sufficient or partly sufficient to successfully execute the given CPG
    - Assessments: CPG defined evaluation of health based on given health data
    - Recommendations: Personalized to the given `healthcontext`


----
<!-- ### `concord_` modules and protocols -->


| concord_modules_ | description |
| --- | --- |
| `concordcore.primitives` | list of primitives types `code`,`unit` |
| `concordcore.variables` | list of variables– `value`,`var`,`record` |
| `concordcore.eligibility` | eligibility evaluation `eligibilityVar` |
| `concordcore.sufficiency`| Checks all `var(s) and record(s)` for sufficiency |
| `concordcore.assessment`| `AssessmentVar`, `AssessmentRecord`, `AssessmentResult` |
| `concordcore.recommendation` | Recommendation protocol module 
| `inputsession`| Patient-Reported Health Data caputuring protocol |
| `ontology`| convinience `presets`, `codes` for ontological codes |
| `renderer`|`jinja` based templating module for creating mutli-modal data (apps,voice, in-context LLM data) |
| `fhir_variables`| `FHIRValue`, `FHIRRecommendation` for FHIR packaging |
| `outcomes`| Todo |



# defining_ clinical practise guideline

Sample versions of a defined cpg are in `cpgs/`

## 1. Creating variables

```yaml
variables:
    - id: LDL
      title: Low density lipoprotein
      user_attestable: False
      required: True
      code:
        loinc: ['13457-7']
```

Creating variables in py:

```python
from concordcore.variables import value, var, record

ldl_val     = value.Value(121)
ldl_var     = var.Var(id="LDL", title="Low Density Lipoprotein", code=[Code.loinc('loinc_code')])
ldl_record  = record.Record(ldl_var, [ldl_val,...,...])
```

## 1. Construct a CPG

```python
# path to Concord_defined_CPG file yaml file.
# ../cholesterol.yaml
# ../cholesterol.py ---> functions module accompanying the CPG

cpg_filepath = '../cpgs/statin_cholesterol.yaml'
statin_cholesterol_cpg = cpg.BaseCPG.from_document_path(cpg_filepath)

# check if cpg is valid
try:
  is_cpg_valid = cpg.validate()
except Exception as e:
  print(e)

from clog import *
print_variables(cpg.variables)

<< insert picture >>
```

## 2. Initialize a cpg-manager class 

`concordcore.concord.Concord` is the core management class that takes in user data `healthcontext` and `CPG` and parses through eligibility check, sufficiency check, assessment evaluation and recommendations.

```python
from concordcore.concord import Concord
manager = Concord(statin_cholesterol_cpg)
```

## 2. Eligibility variables

Checks for the eligibility and applicability of `CPG` for a given `HealthContext` as specificed in the cpg definition file. See `concordcore.eligibility`

Policy

- Value __shall__ only be a `boolean`

```yaml
eligibility:

    - id: age_range
      title: This CPG is fit for people aged between 40 and 75 years
      expression: $Age > 39 and $Age < 76
      # only applicable for individuals with age over 39 and less than 76
```
Use `Concord` to check parse eligibility check

```python
try:
    
    result = concord.eligibility(user_context= <`healthcontext.HealthContext`> )
    print(f'IS_Eligibility: {result.is_eligible}')

except Exception as e:
    raise e
```
Check `concordcore.eligbility.EligibilityResult` class for a list of eligibilited specific records that were evaluated



## 3. Sufficiency variables

Checks for the sufficiency of health data (`HealthContext`) to __execute__ a CPG as specified in the definition file. See `concordcore.sufficiency`. Based on defined charateristics (`var.required` and `var.user_attestable`), each variable is evaluated to one of the following:

```python
class SufficiencyResultStatus(Enum):
    SufficientWithUserAttestation    = auto()
    Sufficient                       = auto()
    Insufficient                     = auto()
    Optional                         = auto()
```

```python

try:
    result = concord.sufficiency(user_context=<`healthcontext.HealthContext`>)
    print(f'SufficiencyResult: IS_EXECUTABLE={result.is_executable}')

except Exception as e:
    raise e
```

## 3. Assessment variables

Checks for the eligibility and applicability of `CPG` for a given `HealthContext` as specificed in the cpg definition file. See `concordcore.assessment`. 

Policy: 

- __Shall__ have an `expression` or a `function` attribute
- __Shall__ have references to other variables within `expression` witha `$` sign.(eg. `$LDL` or `$age_range`)
- __Shall__ reference variables defined in `variables` or `assessments`.

```yaml
assessments:

    - id: ldl_over_189
      title: LDL is greater than 189
      expression: $LDL > 189
      narrative:
        patient:
          True: |
            Your LDL-Cholesterol is $LDL mg/dL.
            A value of __190 mg/dL or more__ is a high risk state that increases the risk of developing heart attack or stroke or other cardiovascular event.
          None: Could not be determined.
          False: Your recent LDL is below 189 mg/dL
```

## 3. Recommendations

Checks for the eligibility and applicability of `CPG` for a given `HealthContext` as specificed in the cpg definition file. See `concordcore.recommendations`

Policy: 

- `type=display` are notices only. `expression` for evaluation will be ignored
- __Shall__ evaluate to resulting value-type of `boolean`
- __Shall__ evaluate only `AssessmentVar` variable-type. 

Recommendation objects have the following attributes:

```yaml
recommendations:
# --- Example of a recommendation type "Display" --- #
  - id: display_uc
    type: display
    title: Understanding Cholesterol
    narrative:
      patient:
        True: |
          Elevated cholesterol (a fat-like substance that comes from animal foods or is made in your body) can clog arteries that reduce blood flow to the organs and may lead to heart attack or stroke or other cardiovascular event.
```
```yaml
recommendations:
# --- Example of a recommendation based on evaluated expression
  - id: sbp_1_ldl
    title: Recommendation based on High LDL
    type: medication
    description: LDL over 189 enhances the risk of developing a heart attack, stroke or other cardiovascular event.
    expression: $ldl_over_189 == True
    narrative:
      patient:
        True: Evidence suggests that starting a __high intensity statin__ medication to control blood cholesterol has been helpful. Your LDL is $LDL
    citations: a list of citations supporting this
    class_of_recommendation: II_B
```










# Under review - consideration

- __Narratives__:
  - [ ] In-context QA data generation
- __Rendering__:
  - [ ] practitioner, single cpg, default tempalte
  - [ ] patient, single cpg, default template
  - [ ] practitioner, combined cpgs, default template
  - [ ] patient, combined-cpgs, default template
- __Variables__:
  - [ ]`validation`: Specify checks for validity and plausibility of a given value for that variable. Usecase: LDL value must be less than or equal to the difference between total-cholesterol and HDL.
  - [ ] `value-capture-method`: Custom cpg-module-function to define key-path or keymap to get data for a given data-model. Forexample: SBP-loinc within a BP Observation FHIR resource
  - [ ] `Code` Hierarchy: 