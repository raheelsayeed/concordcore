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
        raise ValueError('Age needs to be between 40-75')
        
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
    try: 
        isMale = healthcontext['Gender'].value.as_string == "248153007|http://snomed.info/sct"
        isAfricanAmerican = healthcontext['Race_Is_Black_AfricanAmerican'].value == True
        onHtnMeds = False
        dm   = False
        age = healthcontext['Age'].value
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
    try: 
        isMale = healthcontext['Gender'].value.as_string == "248153007|http://snomed.info/sct"
        isAfricanAmerican = healthcontext['Race_Is_Black_AfricanAmerican'].value == True
        onHtnMeds = healthcontext['med_for_htn'].value
        dm   = healthcontext['diabetesMellitus'].value
        age = healthcontext['Age'].value
        sbp = healthcontext['bloodpressure'].value[0]
        chol = healthcontext['Chol'].value
        hdl = healthcontext['HDL'].value
        isSmoker = healthcontext['is_smoker'].value

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


   


