# Risk Factors

From your data, you have {{ positive_risk_factors|count }} factor that could independently or in combination increase your risk of having a heart attack, stroke or other cardiovascular event.

{% for factor in positive_risk_factors %}

1. {{ factor.title }}
   {{ factor.narrative }} 

{% endfor %}


There maybe other factors, discuss with your __doctor to rule out all risk-enhancing factors__.
