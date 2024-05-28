## Screening Cervical Cancer

```mermaid
flowchart TD;

subgraph ages
    EligibileAge[ 21 - 65 ];
end

subgraph procedures_and_symptoms
subgraph procedures
hysterectemy[hysterectemy with cervix]
end 
subgraph symptoms
cervical_ca[Symptoms of CC]
end
subgraph diagnosis
cervical_cancer
lsil
hsil
end
end
EligibileAge --> procedures_and_symptoms
subgraph eligible_to_screen_ages[Eligible for screening agegroups]
 29[Age 21-29]
 65[Age 30-65]
 Over65[Over 65]
end 
subgraph recommendations
    r_no_screening
    r_pap_3Years[Pap Every 3Y]
    r_hpv[HrHPV every 5Y]
    r_cotesting[Cotesting every 5Y]
end
procedures_and_symptoms --> has_symptoms_procs_diagnosis{Yes}
procedures_and_symptoms --> no_symptoms_procs_diagnosis{No}
no_symptoms_procs_diagnosis --> 29[Age 21-29]
no_symptoms_procs_diagnosis --> 65[Age 30-65]
no_symptoms_procs_diagnosis --> Over65[Over 65]
has_symptoms_procs_diagnosis --> ineligibile[Only for primary prevention]

29 --> r_pap_3Years
65 --> OR65[OR]
OR65 --> r_pap_3Years
OR65 --> r_hpv
OR65 --> r_cotesting

Over65 --> AdequateTesting(AdequateTesting?)
AdequateTesting -- Yes --> r_no_screening
AdequateTesting -- NO --> ?{??}

``` 

```mermaid
flowchart TD;


```



