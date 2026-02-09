#!/usr/bin/env python3
import math


def compute_ten_year_score(
    isMale,
    isAfricanAmerican,
    smoker,
    hypertensive,
    diabetic,
    age,
    systolicBloodPressure,
    totalCholesterol,
    hdl,
):
    """
    Args:
        isMale (bool)
        isAfricanAmerican (bool)
        smoker (bool)
        hypertensive (bool)
        diabetic (bool)
        age (int)
        systolicBloodPressure (int)
        totalCholesterol (int)
        hdl (int)
    """
    if age < 40 or age > 79:
        raise ValueError('Age needs to be between 40-79')
        
    lnAge = math.log(age)
    lnTotalChol = math.log(totalCholesterol)
    lnHdl = math.log(hdl)
    trlnsbp = math.log(systolicBloodPressure) if hypertensive else 0
    ntlnsbp = 0 if hypertensive else math.log(systolicBloodPressure)
    ageTotalChol = lnAge * lnTotalChol
    ageHdl = lnAge * lnHdl
    agetSbp = lnAge * trlnsbp
    agentSbp = lnAge * ntlnsbp
    ageSmoke = lnAge if smoker else 0
    if isAfricanAmerican and not isMale:
        s010Ret = 0.95334
        mnxbRet = 86.6081
        predictRet = (
            17.1141 * lnAge
            + 0.9396 * lnTotalChol
            + -18.9196 * lnHdl
            + 4.4748 * ageHdl
            + 29.2907 * trlnsbp
            + -6.4321 * agetSbp
            + 27.8197 * ntlnsbp
            + -6.0873 * agentSbp
            + (0.6908 if smoker else 0)
            + (0.8738 if diabetic else 0)
        )
    elif not isAfricanAmerican and not isMale:
        s010Ret = 0.96652
        mnxbRet = -29.1817
        predictRet = (
            -29.799 * lnAge
            + 4.884 * lnAge ** 2
            + 13.54 * lnTotalChol
            + -3.114 * ageTotalChol
            + -13.578 * lnHdl
            + 3.149 * ageHdl
            + 2.019 * trlnsbp
            + 1.957 * ntlnsbp
            + (7.574 if smoker else 0)
            + -1.665 * ageSmoke
            + (0.661 if diabetic else 0)
        )
    elif isAfricanAmerican and isMale:
        s010Ret = 0.89536
        mnxbRet = 19.5425
        predictRet = (
            2.469 * lnAge
            + 0.302 * lnTotalChol
            + -0.307 * lnHdl
            + 1.916 * trlnsbp
            + 1.809 * ntlnsbp
            + (0.549 if smoker else 0)
            + (0.645 if diabetic else 0)
        )
    else:
        s010Ret = 0.91436
        mnxbRet = 61.1816
        predictRet = (
            12.344 * lnAge
            + 11.853 * lnTotalChol
            + -2.664 * ageTotalChol
            + -7.99 * lnHdl
            + 1.769 * ageHdl
            + 1.797 * trlnsbp
            + 1.764 * ntlnsbp
            + (7.837 if smoker else 0)
            + -1.795 * ageSmoke
            + (0.658 if diabetic else 0)
        )

    pct = 1 - s010Ret ** math.exp(predictRet - mnxbRet)
    return round(pct * 100 * 10) / 10


def optimal_tenyearriskscore(healthcontext):
    """Calculate optimal ASCVD 10-year risk score (with ideal values).

    Uses patient's demographics but assumes optimal health metrics.

    Args:
        healthcontext: Dict of {variable_id: Value} where Value has a .value property

    Returns:
        float: Optimal 10-year ASCVD risk percentage
    """
    try:
        # Extract gender
        gender_val = healthcontext['Gender'].value
        if hasattr(gender_val, 'as_string'):
            gender_str = gender_val.as_string
        else:
            gender_str = str(gender_val)
        isMale = gender_str == "http://snomed.info/sct|248153007"

        # Race - check assessment result or ethnicity
        race_val = healthcontext.get('Race_Is_Black_AfricanAmerican')
        if race_val is not None:
            isAfricanAmerican = race_val.value == True if hasattr(race_val, 'value') else race_val == True
        else:
            ethnicity_val = healthcontext.get('Ethnicity')
            if ethnicity_val:
                eth_str = ethnicity_val.value if hasattr(ethnicity_val, 'value') else str(ethnicity_val)
                isAfricanAmerican = eth_str in [
                    "urn:oid:2.16.840.1.113883.6.238|2058-6",
                    "urn:oid:2.16.840.1.113883.6.238|2060-2"
                ]
            else:
                isAfricanAmerican = False

        # Get age
        age_val = healthcontext['Age']
        age = int(age_val.value if hasattr(age_val, 'value') else age_val)

        # Optimal values
        onHtnMeds = False
        dm = False
        sbp = 110
        chol = 170
        hdl = 50
        isSmoker = False

        return compute_ten_year_score(
            isMale,
            isAfricanAmerican,
            isSmoker,
            onHtnMeds,
            dm,
            age,
            sbp,
            chol,
            hdl
        )

    except Exception as e:
        raise e


def tenyearriskscore(healthcontext):
    """Calculate ASCVD 10-year risk score.

    Args:
        healthcontext: Dict of {variable_id: Value} where Value has a .value property

    Returns:
        float: 10-year ASCVD risk percentage
    """
    try:
        # Extract values - healthcontext[key] is a Value object, .value gets the raw value
        gender_val = healthcontext['Gender'].value
        # Handle both string and Code object formats
        if hasattr(gender_val, 'as_string'):
            gender_str = gender_val.as_string
        else:
            gender_str = str(gender_val)
        isMale = gender_str == "http://snomed.info/sct|248153007"

        # Race_Is_Black_AfricanAmerican is an assessment result (Value with bool)
        race_val = healthcontext.get('Race_Is_Black_AfricanAmerican')
        if race_val is not None:
            isAfricanAmerican = race_val.value == True if hasattr(race_val, 'value') else race_val == True
        else:
            # Fallback: check Ethnicity directly for African American codes
            ethnicity_val = healthcontext.get('Ethnicity')
            if ethnicity_val:
                eth_str = ethnicity_val.value if hasattr(ethnicity_val, 'value') else str(ethnicity_val)
                isAfricanAmerican = eth_str in [
                    "urn:oid:2.16.840.1.113883.6.238|2058-6",
                    "urn:oid:2.16.840.1.113883.6.238|2060-2"
                ]
            else:
                isAfricanAmerican = False

        # Extract other values
        def get_val(key):
            v = healthcontext.get(key)
            if v is None:
                return None
            return v.value if hasattr(v, 'value') else v

        onHtnMeds = bool(get_val('med_for_htn'))
        dm = bool(get_val('diabetesMellitus'))
        age = int(get_val('Age'))
        isSmoker = bool(get_val('is_smoker'))
        chol = float(get_val('Chol'))
        hdl = float(get_val('HDL'))

        # Blood pressure can be tuple (systolic, diastolic) or just systolic
        bp_val = get_val('bloodpressure')
        if isinstance(bp_val, (list, tuple)):
            sbp = int(bp_val[0])
        else:
            sbp = int(bp_val)

        return compute_ten_year_score(
            isMale,
            isAfricanAmerican,
            isSmoker,
            onHtnMeds,
            dm,
            age,
            sbp,
            chol,
            hdl
        )

    except Exception as e:
        raise e


   


