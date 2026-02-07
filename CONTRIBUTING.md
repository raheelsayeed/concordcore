# Contributing to Concord

Thank you for your interest in contributing to Concord! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Setting Up Your Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/concordhealth/concord.git
   cd concord
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install dev dependencies
   ```

4. **Verify installation**
   ```bash
   ./main.py -f cpgs/cholesterol.yaml -t document -p patient
   ```

## Code Standards

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Maximum line length: 120 characters
- Use meaningful variable and function names

### Formatting Tools

We use the following tools for code quality:

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy core/ variables/ primitives/
```

### Docstrings

Use Google-style docstrings for all public classes and functions:

```python
def evaluate(self, records: list[Record]) -> Value:
    """Evaluate the expression against the provided records.

    Args:
        records: List of Record objects containing variable values.

    Returns:
        A Value object containing the evaluation result.

    Raises:
        ExpressionVariableNotFound: If a required variable is missing.
        ExpressionEvaluationError: If the expression cannot be evaluated.
    """
```

### Imports

Organize imports in the following order:
1. Standard library imports
2. Third-party imports
3. Local application imports

Use `ruff` to automatically sort imports.

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=core --cov=variables --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_expression.py -v

# Run tests by marker
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m fhir          # FHIR-related tests
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_<what>_<condition>_<expected_result>`
- Use fixtures from `tests/conftest.py` when possible
- Aim for 70% code coverage minimum

### Test Structure

```python
class TestClassName:
    """Tests for ClassName."""

    def test_method_returns_expected_value(self, fixture):
        """Test that method returns expected value under normal conditions."""
        result = fixture.method()
        assert result == expected_value

    def test_method_raises_error_on_invalid_input(self, fixture):
        """Test that method raises appropriate error for invalid input."""
        with pytest.raises(ValueError):
            fixture.method(invalid_input)
```

## Pull Request Process

### Before Submitting

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, concise commit messages
   - Keep commits focused and atomic
   - Add tests for new functionality

3. **Run quality checks**
   ```bash
   black .
   ruff check .
   mypy core/ variables/ primitives/ --ignore-missing-imports
   pytest tests/ -v
   ```

4. **Update documentation**
   - Update docstrings for changed code
   - Update README if adding new features
   - Add examples if appropriate

### Submitting a Pull Request

1. Push your branch to GitHub
2. Create a Pull Request with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to any related issues
   - Test plan describing how to verify the changes

### PR Review Criteria

- Code follows style guidelines
- All tests pass
- New code has appropriate test coverage
- Documentation is updated
- No security vulnerabilities introduced
- Changes are backwards compatible (or breaking changes are documented)

## Project Structure

```
concord/
├── core/               # Core evaluation pipeline
│   ├── concord.py      # Main orchestrator
│   ├── eligibility.py  # Eligibility evaluation
│   ├── sufficiency.py  # Data sufficiency check
│   ├── assessment.py   # Health assessments
│   ├── recommendation.py # Recommendations
│   ├── expression.py   # Expression evaluation
│   ├── cpg.py          # CPG loading
│   └── security.py     # Security utilities
├── variables/          # Data model
│   ├── var.py          # Variable definitions
│   ├── value.py        # Value objects
│   └── record.py       # Records (var + values)
├── primitives/         # Base types
│   ├── code.py         # Medical codes (LOINC, SNOMED, etc.)
│   ├── types.py        # Type definitions
│   └── errors.py       # Custom exceptions
├── fhir/               # FHIR R4 integration
├── renderer/           # Output templates
├── cpgs/               # CPG definitions
├── tests/              # Test suite
├── docs/               # Documentation
└── examples/           # Example scripts
```

## CPG Development

### Creating a New CPG

1. Create a YAML file in `cpgs/` directory
2. Define variables, eligibility, assessments, and recommendations
3. Optionally create a Python module for custom functions
4. Test with: `./main.py -f cpgs/your_cpg.yaml -t document -p patient`

### CPG YAML Structure

```yaml
CPG:
  identifier: unique_id
  title: "CPG Title"
  publisher: "Publisher Name"

variables:
  - id: VariableName
    title: Human Readable Title
    code:
      loinc: ['12345-6']
    required: true

eligibility:
  - id: eligibility_check
    expression: $Age >= 40

assessments:
  - id: risk_assessment
    expression: $LDL > 130
    narrative:
      patient:
        True: "Your LDL is elevated"

recommendations:
  - id: treatment_rec
    expression: $risk_assessment == True
    narrative:
      patient:
        True: "Consider treatment options"
```

## Security

- Never commit sensitive data (patient info, credentials, API keys)
- Report security vulnerabilities privately to maintainers
- Use the security module for path validation and logging
- Review CPG function modules before execution

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Join discussions in GitHub Discussions

## License

By contributing to Concord, you agree that your contributions will be licensed under the project's license.
