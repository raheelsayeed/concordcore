
#!/usr/bin/env python3

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from core.recommendation import RecommendationResult


class MarketPlaceCategory(Enum):
    LabServices          = auto() 
    CareProviderServices = auto()

class UserAdvisoryCategory(Enum):
    Email               = auto()
    Ask                 = auto() 
    NotifyCareProvider  = auto() 

class ProviderAdvisoryCategory(Enum):
    NotifyPatient       = auto() 
    NotifyProvider      = auto() 

class ContextObserver(Enum):
    Lab_Stale = auto()
    Lab_NotFound = auto()

class AdvisoryActions(Enum):
    NOTIFYPROVIDER              = ('Send to my doctor', '')
    
    BOOK_CARE_APPOINTMENT       = ('Book an appointment', '')
    BOOK_LAB_APPOINT            = ('Book a Lab test', '')

    MEDICATION_INFORMATION      = ('More about medication', '')
    MEDICATION_COST             = ('Tell me more about costs', '')

    RECOMMENDATION_EFFECT       = ('Medication for how long', '')
    OTHERS_LIKE_ME              = ('People like me', '')

@dataclass
class Advisory:
    title: str 
    description: str 
    cateogry: Any = None 


    @staticmethod
    def All():
        return [Advisory(t.value[0], t.value[1]) for t in AdvisoryActions]

    
    @classmethod
    def get_for(cls, recommendation_result: RecommendationResult):
        return Advisory.All()




