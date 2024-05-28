#!/usr/bin/env python3
from datetime import datetime, date, timedelta
from primitives.errors import VariableEvaluationError

today = datetime.now().date()


def get_next_date(test_date, required_interval):
    diff = today - test_date
    interval = required_interval
    if diff.days >= interval:
        return today
    else:
        due_days_from_now = interval - diff.days
        due_date = today + timedelta(due_days_from_now)
        return due_date
       

def nextDatePolicy_PapTest_Alone(healthcontext):
    
    test_date = healthcontext['cervical_cytology_labtest'].date.date()
    if not test_date:
        return today

    interval = 364 * 3
    return get_next_date(test_date, interval)

def nextDatePolicy_hrHPVTest_Alone(healthcontext):
    # 5 years with hrHPV testing alone

    test_date = (healthcontext['hpv_test'].date.date())
    if not test_date:
        return today
    
    interval = 364 * 5
    return get_next_date(test_date, interval) 


def nextDatePolicy_CoTesting(healthcontext): 
    # 5 years with CoTesting alone
    print('Do not know code for co-testing, therefore, checking both Pap and hrHPV')
    pap_date = healthcontext['cervical_cytology_labtest'].date.date()
    hrhpv_date = (healthcontext['hpv_test'].date.date())

    # if both tests done within a month, assume-- Co_tested
    if pap_date and hrhpv_date:
        within_a_month = (pap_date - hrhpv_date).days < 30
        if within_a_month:
            return get_next_date(hrhpv_date, 5 * 365)

    if pap_date:
        #Q: If pap_date done within 3 years, the next cotesting should be done when?
        # Cotesting done after 3 years
        return get_next_date(pap_date, 3 * 365)


    if hrhpv_date:
        # cotesting done after 5 years
        return get_next_date(hrhpv_date, 5 * 365)

    print('no history of tests done')
    return today



    


def nextDate_PapTest_Age21_29(healthcontext):

    print('>>>> age')    
    age = healthcontext['Age'].value
    print('>>>> GIT IT', age)
    
    if age < 21 or age > 29:
        raise VariableEvaluationError([ValueError(f'Function errorAge out of range {age}')], 'nextDate_PapTest_Age21_29')

    print('>>>> age', age)
    return nextDatePolicy_PapTest_Alone(healthcontext)
    

# Age30-65
# Screening for cervical ca:
# 1. 3 years with cytology alone
# 2. 5 years with hrHPV testing alone
# 3. 5 years with cotesting.

def nextDate_HPV(healthcontext):

    today = datetime.now()

    test_date = healthcontext['hpv_test'],date,date()
    if not test_date:
        return today
    

if __name__ == '__main__':
    print('working..')

    nextDate_PapTest_Age21_29('asdf')
