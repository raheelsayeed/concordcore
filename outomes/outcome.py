
#!/usr/bin/env python3

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from concordcore.recommendation import Recommendation

# Refereals and advisories
class Advisories(Enum):

    recommendation_discussion = auto()
    
    lab_stale = auto() 
    lab_notfound = auto() 

    medication_recommended = auto()


    def referral(self):

        # ---  a referral action, advise class 
        # if medicaiton --> point to pharmacies
        # if lab test   --> point to lab test services
        # if doc-advise --> point to near-by primary care services
        # 

    

@dataclass
class PossibleOutcome:
    recommendation: Recommendation


@dataclass
class RecommendationEffect:
    for_recommendation: Recommendation
    effect: Any

    