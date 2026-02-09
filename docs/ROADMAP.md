# ConcordCore Roadmap

This document outlines the development roadmap for ConcordCore, including completed work, in-progress items, and future plans.

## Completed

### Core Framework
- [x] 5-phase evaluation pipeline (Eligibility → Sufficiency → Assessment → Recommendations)
- [x] YAML-based CPG definition format
- [x] Expression evaluation system using simpleeval
- [x] Persona-aware narrative generation (patient/provider)
- [x] Medical code support (LOINC, SNOMED, RxNorm, CPT)
- [x] FHIR R4 resource parsing (Observation, Condition, MedicationRequest, Procedure)
- [x] Evidence classification (Class of Recommendation, Level of Evidence, USPSTF)

### Variables & Data Model
- [x] Variable hierarchy (Var, EligibilityVar, AssessmentVar, RecommendationVar)
- [x] Value validation (plausible ranges, panel relationships)
- [x] User attestation support for patient-reported data
- [x] Record filtering (date ranges, value expressions)

### Security
- [x] Removed eval() vulnerability - using simpleeval
- [x] Module loading security (path validation, name sanitization)
- [x] Secure logging with PII masking

### Testing
- [x] pytest infrastructure with fixtures
- [x] Unit tests for core modules
- [x] Integration tests for workflow

---

## In Progress

### Documentation
- [ ] Comprehensive docstrings for all public APIs
- [ ] Example scripts for common use cases
- [ ] API reference documentation

### Code Quality
- [x] Type hints for core module (`core/` — `| None` annotations on all nullable fields)
- [x] Consistent error handling in core (`CPGDefinitionError`, `PipelineError` replacing bare `Exception`)
- [x] Core module bug fixes (`.date()` call, class-level UUID, `__str__`, uninitialized field)
- [x] Dead code removal in core (commented blocks, unused classes, duplicate methods)
- [ ] Type hints for remaining modules (`variables/`, `primitives/`, `fhir/`, `renderer/`)
- [ ] Consistent error handling in remaining modules
- [ ] Code style standardization (black, ruff)

---

## Technical Advantage Implementation

These tasks implement the unavoidable technical advantages documented in [Unavoidable Technical Arguments.md](./Unavoidable%20Technical%20Arguments.md).

### Completed (v0.2.0)
- [x] **CPG Version Tracking** - Semantic versioning with `version`, `last_updated`, `source_url` fields
- [x] **Cryptographic Hashing** - SHA-256 hash of input data for reproducibility proof
- [x] **Institutional Configuration** - Threshold overrides, expression overrides, local rules
- [x] **Conflict Detection** - Multi-CPG conflict detection (drug interactions, target mismatches)
- [x] **Gap Analysis** - Preventive care gap identification against catalog
- [x] **Outcome Tracking** - Recommendation → Action → Outcome lifecycle tracking
- [x] **Counter-factual Analysis** - "What-if" calculations with exact re-evaluation

- [x] **#17: Benchmarking Suite** - Prove cost (100-1000x cheaper) and speed (<100ms) claims
  - `BenchmarkRunner` class for comprehensive benchmarking
  - Time per evaluation (avg, min, max, p50, p95, p99)
  - Batch throughput benchmarks (patients/second)
  - Memory usage profiling
  - LLM cost comparison with multiple models (GPT-4, Claude)
  - `BenchmarkReport` with summary generation and JSON export

### Completed (v0.3.0)
- [x] **#18: Batch Processing API** - Population health at scale
  - `BatchProcessor` class with sequential/thread pool/process pool modes
  - Progress callback for monitoring
  - Aggregated statistics in `BatchProcessingReport`
  - Stream processing for memory efficiency

- [x] **#19: Reproducibility Verification** - Cryptographic proof of determinism
  - `ReproducibilityVerifier` class for verification
  - `compute_output_hash()` for evaluation results
  - `VerificationResult` with detailed status
  - Detects CPG version changes, input mismatches

- [x] **#20: Parallel Multi-CPG Evaluation** - 20 CPGs in <1 second
  - `MultiCPGEvaluator` class with concurrent evaluation
  - ThreadPoolExecutor for parallelism
  - Integrated conflict detection
  - `MultiCPGResult` with aggregated recommendations

- [x] **#21: CI/CD Templates** - Unit testing for clinical logic
  - `.github/workflows/cpg-tests.yml` - Full GitHub Actions workflow
  - `.pre-commit-config.yaml` - Pre-commit hooks
  - CPG YAML validation, expression validation
  - CPG diff reporting on PRs, benchmark tests

- [x] **#24: Institutional Config Validation** - Control & customization
  - `ConfigValidator` class with comprehensive validation
  - Schema validation for config YAML (required fields, types)
  - Override conflict detection (duplicates, circular inheritance)
  - Expression validation (syntax, variable references)
  - Safe range checks for clinical thresholds
  - Inheritance chain visualization
  - Impact analysis for changes
  - MCP tools: `validate_institution_config`, `get_institution_config_impact`

- [x] **#22: CPG Changelog Generation** - Semantic versioning tooling
  - `CPGDiffer` class for comparing CPG versions
  - `ChangelogGenerator` for markdown/text/JSON output
  - `ExpressionDiffer` for detailed expression analysis
  - Breaking change detection with severity levels
  - Version bump recommendations (major/minor/patch)
  - Metadata, variable, and expression change tracking

- [x] **#23: Offline Deployment Documentation** - Air-gapped environments
  - Complete offline installation guide (`docs/offline-deployment.md`)
  - Three deployment methods (wheels, Docker, venv bundle)
  - Local CPG repository setup and version control
  - Health check and verification scripts
  - Disaster recovery procedures
  - Security considerations for air-gap compliance

### Completed (v0.4.0) - Demo Application
- [x] **Multi-CPG Demo UI** - Web application for demonstration
  - FastAPI backend (`app/server.py`)
  - Interactive HTML/JS frontend (`app/index.html`)
  - Real-time multi-CPG evaluation
  - Conflict detection visualization
  - LLM cost comparison display
  - Performance benchmarking in browser

### Planned

---

## Planned

### Short Term (Next Release)

#### HealthContext Improvements
- [ ] Direct FHIR JSON to Value conversion (skip fhirclient dependency)
- [ ] `value-capture-method`: Custom keypath for nested FHIR resources
- [ ] Better support for historical data analysis

#### Variables
- [ ] Code hierarchy support (parent/child relationships)
- [ ] Improved validation error messages
- [ ] Variable dependency tracking

#### Recommendations
- [ ] Non-compliance evidence capture
- [ ] Provider-facing evidence rejection module
- [ ] Action recommendation enums

### Medium Term

#### PGHD (Patient-Generated Health Data)
- [ ] Module to isolate attestable values
- [ ] Improved patient input session
- [ ] Validation for patient-provided data

#### Narratives
- [ ] In-context QA data generation for LLM integration
- [ ] Multi-language support
- [ ] Template inheritance

#### Rendering
- [ ] Cached templates for performance
- [ ] Practitioner single/combined CPG templates
- [ ] Patient single/combined CPG templates

### Long Term

#### Ontology
- [ ] ValueSet store for code lookup
- [ ] FHIR ValueSet API integration
- [ ] Terminology service integration

#### Evidence Module
- [ ] Provider evidence capture for guideline exceptions
- [ ] Patient evidence capture for non-applicability
- [ ] LLM-based suggestion system for quick selection

#### FHIR Output
- [ ] Generate FHIR CarePlan from recommendations
- [ ] FHIR ClinicalRecommendation resource support
- [ ] CDS Hooks integration

#### Performance
- [ ] Lazy evaluation for large datasets
- [ ] Caching for repeated evaluations
- [ ] Async evaluation support

---

## Feature Requests

Community-requested features (submit via GitHub Issues):

1. ~~**Multi-CPG Evaluation**: Run multiple CPGs simultaneously~~ → **In Progress** (Task #20)
2. **Longitudinal Analysis**: Track changes over time
3. **Risk Score Visualization**: Generate charts for risk scores
4. **Mobile SDK**: React Native / Flutter bindings
5. **Cloud API**: REST API for SaaS deployment

---

## Version History

### v0.1.0 (Current)
- Initial release with core evaluation pipeline
- Cholesterol CPG implementation
- FHIR R4 parsing
- Basic rendering

### v0.2.0 (Planned)
- Security improvements
- Testing infrastructure
- Documentation
- Extensibility features

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to contribute to the roadmap.

To request a feature:
1. Check if it's already on the roadmap
2. Open a GitHub Issue with the `feature-request` label
3. Describe the use case and expected behavior
