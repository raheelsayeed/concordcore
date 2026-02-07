# ConcordCore MCP Server - Quick Start Guide

Get clinical decision support in your AI assistant in 5 minutes.

## What is This?

The ConcordCore MCP Server lets AI assistants (Claude Desktop, Claude Code, etc.) evaluate patient health data against evidence-based clinical practice guidelines and generate recommendations.

## Prerequisites

- Python 3.10+
- An MCP-compatible client (Claude Desktop, Claude Code)

## Setup (2 minutes)

```bash
# 1. Clone and setup
git clone https://github.com/your-org/concordcore.git
cd concordcore
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Verify it works
python -c "from mcp_server import serve; print('Ready!')"
```

## Configure Claude Desktop (1 minute)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "concord": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/full/path/to/concordcore"
    }
  }
}
```

Restart Claude Desktop.

## Try It Out

Ask Claude:

> "List all the clinical practice guidelines you can evaluate"

> "I'm a 55-year-old male with LDL 165, HDL 42, blood pressure 140/90,
> and I have diabetes. What do the guidelines recommend?"

> "Explain why statin therapy is recommended for this patient"

## What Can It Do?

| Capability | Example |
|------------|---------|
| List Guidelines | "What CPGs are available?" |
| Evaluate Patient | "Evaluate against cholesterol guideline" |
| All Guidelines | "Check all guidelines for this patient" |
| Recommendations | "What are the top recommendations?" |
| Explanations | "Why is depression screening recommended?" |
| Missing Data | "What information is missing?" |
| FHIR Support | "Use this FHIR bundle..." |

## Available Guidelines

- **Cholesterol** (ACC/AHA 2019) - Statin therapy decisions
- **Depression Screening** (USPSTF) - Adult depression screening
- **Diabetes Screening** (USPSTF) - Prediabetes/T2DM screening
- **Hepatitis B/C** (USPSTF) - Viral hepatitis screening
- **HIV Screening** (USPSTF) - HIV testing recommendations
- **Hypertension** (USPSTF) - Blood pressure screening
- **Colorectal Cancer** (USPSTF) - Cancer screening

## Common Variables

When providing patient data, use these variable names:

```
Age, Gender, LDL, HDL, TotalCholesterol, triglycerides,
systolic_bp, diastolic_bp, is_smoker, diabetesMellitus,
Ethnicity, HbA1c, BMI
```

## Next Steps

- Read the full [MCP Server README](../mcp_server/README.md) for detailed API docs
- See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- Explore CPG YAML files in `cpgs/` directory

## Troubleshooting

**Claude doesn't see the tools?**
- Restart Claude Desktop after config changes
- Check the path in config is absolute and correct
- Run `python -m mcp_server` manually to test

**Evaluation fails?**
- Use `get_missing_data` to see what's needed
- Submit missing values with `submit_attestation`
- Check variable names match (case-sensitive)

## Support

- Issues: https://github.com/your-org/concordcore/issues
- Docs: See `docs/` and `mcp_server/README.md`
