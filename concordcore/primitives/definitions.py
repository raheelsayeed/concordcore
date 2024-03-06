#!/usr/bin/env python3

from enum import Enum


class CodeType(Enum):

    loinc   = 'http://loinc.org'
    snomed  = 'http://snomed.info/sct'
    rxnorm  = 'http://www.nlm.nih.gov/research/umls/rxnorm'
    concord = 'http://concord.health/terminologies/variables'
    cpt_hl7 = 'http://hl7.org/fhir/us/carin-bb/ValueSet/AMACPTCMSHCPCSProcedureCodes'
    # https://terminology.hl7.org/4.0.0/CodeSystem-CPT.html
    # urn:oid:2.16.840.1.113883.6.12
    cpt     = 'http://www.ama-assn.org/go/cpt'
    # https://phinvads.cdc.gov/vads/ViewCodeSystem.action?id=2.16.840.1.113883.6.238
    cdc_re  = 'urn:oid:2.16.840.1.113883.6.238' # CDC Race Ethnicity
    # https://terminology.hl7.org/2.1.0/CodeSystem-icd10CM.html
    icd10cm = 'urn:oid:2.16.840.1.113883.6.90'



# ValueSets
# USCDI VS for Race/Ethnicity: https://phinvads.cdc.gov/vads/ViewCodeSystemConcept.action?oid=2.16.840.1.113883.6.238&code=2106-3
# https://terminology.hl7.org/3.1.0/CodeSystem-CDCREC.html
# Patient-Extension-http://hl7.org/fhir/us/core/StructureDefinition/us-core-race
# Patient-Extension-http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity


