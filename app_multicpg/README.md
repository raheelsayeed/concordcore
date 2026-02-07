# Multi-CPG Evaluation App

A standalone Streamlit application demonstrating multi-CPG evaluation with the Concord framework. Provides separate optimized views for healthcare providers (clinicians) and patients.

## Features

### Provider View (Clinical Decision Support)
- **Dashboard Overview**: Summary metrics for all evaluated CPGs
- **Priority-Ranked Recommendations**: Evidence-graded recommendations sorted by clinical priority
- **Cross-CPG Conflict Detection**: Identifies and explains conflicts between guidelines
- **Detailed CPG Results**: Drill-down into individual CPG evaluations
- **Filtering & Sorting**: Filter by priority, category, or conflict status
- **Evidence Display**: Class of Recommendation (ACC/AHA) and USPSTF grades

### Patient View (Health Recommendations)
- **Health Summary**: Easy-to-understand overview of health status
- **Action Items**: Clear, actionable steps organized by urgency
- **Questions for Doctor**: Generated conversation starters for appointments
- **Educational Resources**: Links to trusted health information sources
- **Conflict Explanations**: Patient-friendly explanations of guideline differences

## Installation

1. Ensure ConcordCore dependencies are installed:
```bash
cd /path/to/concordcore
pip install -r requirements.txt
```

2. Install Streamlit:
```bash
pip install streamlit
```

Or install from the app's requirements:
```bash
pip install -r app_multicpg/requirements.txt
```

## Running the App

From the project root directory:

```bash
streamlit run app_multicpg/run.py
```

The app will open in your default web browser at `http://localhost:8501`.

## Usage

### Provider Mode

1. **Select Patient Data**
   - Choose from sample patients or enter custom patient data
   - Sample patients include various risk profiles for demonstration

2. **Select CPGs**
   - Choose which clinical practice guidelines to evaluate
   - Select by category (Cardiovascular, Cancer Screening, etc.)
   - Or use quick-select options (All, Cardiovascular only, etc.)

3. **Run Evaluation**
   - Click "Run Evaluation" to process all selected CPGs
   - Results are evaluated in parallel for performance

4. **Review Results**
   - **Overview**: Summary dashboard with key metrics
   - **Recommendations**: Priority-ranked list with evidence grades
   - **CPG Details**: Individual CPG results with assessments
   - **Conflicts**: Cross-guideline conflict analysis

### Patient Mode

1. **View Health Summary**
   - See an overview of your health check results
   - Understand what's going well and what needs attention

2. **Action Items**
   - Get clear steps you can take, organized by urgency
   - Actions categorized as "Talk to Doctor Soon" vs "At Next Appointment"

3. **Questions for Doctor**
   - Review suggested questions to ask your healthcare provider
   - Checkbox format for easy tracking

4. **Learn More**
   - Access educational resources relevant to your health topics
   - Links to trusted sources (AHA, CDC, NIH, etc.)

## Sample Patients

The app includes 5 sample patients with varying risk profiles:

| Patient | Age | Key Characteristics |
|---------|-----|---------------------|
| John Smith | 55 | Male, CV risk factors, former smoker |
| Maria Garcia | 48 | Female, metabolic syndrome indicators |
| Robert Johnson | 62 | Male, multiple risk factors, current smoker |
| Sarah Williams | 35 | Female, generally healthy |
| David Chen | 70 | Male, controlled conditions, on medications |

## Available CPGs

The app can evaluate 11 clinical practice guidelines:

- **Cardiovascular**: Cholesterol (ACC/AHA), Statin Use (USPSTF), Hypertension Screening
- **Cancer Screening**: Lung, Colorectal, Cervical
- **Metabolic**: Diabetes Screening
- **Infectious Disease**: HIV, Hepatitis B, Hepatitis C
- **Mental Health**: Depression Screening

## Architecture

```
app_multicpg/
├── run.py                    # Main Streamlit entry point
├── config.py                 # App configuration
├── components/               # Reusable UI components
│   ├── header.py
│   ├── patient_selector.py
│   ├── cpg_selector.py
│   ├── evaluation_card.py
│   ├── recommendation_panel.py
│   ├── conflict_panel.py
│   └── health_summary.py
├── views/                    # Main view modules
│   ├── provider_view.py
│   └── patient_view.py
├── services/                 # Business logic
│   ├── evaluator.py          # Multi-CPG evaluation
│   ├── cpg_loader.py         # CPG loading
│   ├── priority_ranker.py    # Recommendation ranking
│   └── explanation_service.py # Patient explanations
└── data/                     # Sample data
    └── sample_patients.py
```

## Key Services

### MultiCPGService
Evaluates multiple CPGs against patient data with optional conflict detection:
```python
service = MultiCPGService(detect_conflicts=True, max_workers=4)
summary = service.evaluate_multiple_cpgs(
    cpg_ids=["cholesterol", "statin", "diabetes"],
    health_context=patient_context,
    patient_id="p123",
    patient_name="John Smith",
    parallel=True
)
```

### PriorityRanker
Ranks recommendations by clinical priority based on evidence grades:
```python
ranker = PriorityRanker()
ranked = ranker.rank_recommendations(summary)
# Returns list sorted by priority (CRITICAL, HIGH, MODERATE, LOW, INFORMATIONAL)
```

### ExplanationService
Generates patient-friendly explanations:
```python
service = ExplanationService()
explanation = service.explain_recommendation(ranked_rec)
# Returns PatientExplanation with title, summary, actions, questions
```

## Customization

### Adding New CPGs
1. Add CPG YAML file to `cpgs/` directory
2. Add entry to `AVAILABLE_CPGS` in `config.py`
3. CPG will automatically appear in the selector

### Modifying Evidence Weights
Edit `PriorityRanker.EVIDENCE_WEIGHTS` in `services/priority_ranker.py`:
```python
EVIDENCE_WEIGHTS = {
    "I": 100,    # Class I (ACC/AHA)
    "A": 100,    # Grade A (USPSTF)
    # ... etc
}
```

### Custom Patient Data
Use the custom patient form in the app, or programmatically:
```python
from app_multicpg.data import create_custom_patient
patient_info, context = create_custom_patient({
    "Age": 55,
    "LDL": 165,
    "HDL": 42,
    # ... more data
})
```

## Notes

- The app uses Streamlit session state for persistence during a session
- Evaluations run in parallel using ThreadPoolExecutor
- Conflict detection uses the framework's ConflictDetector
- All recommendations are sorted by a computed priority score (0-100)
- Print functionality is optimized with CSS @media print rules

## License

Part of the ConcordCore project.
