# Offline Deployment Guide

This guide explains how to deploy Concord in air-gapped or offline environments where internet connectivity is not available.

## Overview

Concord is designed to run completely offline. Unlike LLM-based clinical decision support systems, Concord:

- **Requires no internet connection** for clinical logic evaluation
- **Has no external API dependencies** for core functionality
- **Can be deployed in air-gapped environments** (military, high-security healthcare)
- **Continues functioning during network outages** for disaster recovery

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OFFLINE DEPLOYMENT ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                    AIR-GAPPED NETWORK                       │  │
│   │                                                             │  │
│   │   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │  │
│   │   │ EHR System  │────►│  Concord    │────►│ Clinical    │  │  │
│   │   │             │     │  Server     │     │ Dashboard   │  │  │
│   │   └─────────────┘     └─────────────┘     └─────────────┘  │  │
│   │                              │                              │  │
│   │                              ▼                              │  │
│   │                       ┌─────────────┐                      │  │
│   │                       │ Local CPG   │                      │  │
│   │                       │ Repository  │                      │  │
│   │                       └─────────────┘                      │  │
│   │                                                             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│                     [No Internet Required]                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 4+ GB |
| Disk | 500 MB | 2+ GB |
| Network | None required | LAN only |

### Software Requirements

- Python 3.10 or higher
- No external runtime dependencies
- All packages can be pre-installed

## Installation Methods

### Method 1: Offline Package Installation

1. **On a connected machine**, download all dependencies:

```bash
# Create a wheel directory
mkdir -p wheels

# Download Concord and all dependencies
pip download -d wheels -r requirements.txt

# Download Concord itself (if published to PyPI)
pip download -d wheels concordcore

# Or copy the source directory
cp -r concordcore/ offline-package/
```

2. **Transfer to offline machine** via USB, secure file transfer, or approved media.

3. **Install from local files**:

```bash
# Install from wheels
pip install --no-index --find-links=wheels -r requirements.txt

# Install Concord
pip install --no-index --find-links=wheels concordcore
# Or from source
cd concordcore && pip install -e .
```

### Method 2: Docker Image

1. **On a connected machine**, build and save the Docker image:

```bash
# Build the image
docker build -t concordcore:latest .

# Save to a tar file
docker save concordcore:latest > concordcore-image.tar
```

2. **Transfer the tar file** to the offline machine.

3. **Load and run**:

```bash
# Load the image
docker load < concordcore-image.tar

# Run Concord
docker run -p 8000:8000 concordcore:latest
```

### Method 3: Virtual Environment Bundle

1. **Create a portable virtual environment**:

```bash
# Create venv
python -m venv concord-venv

# Activate and install
source concord-venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Create relocatable bundle
pip install virtualenv-clone
virtualenv-clone concord-venv concord-bundle
```

2. **Transfer the entire bundle** to the offline machine.

3. **Activate and use**:

```bash
source concord-bundle/bin/activate
python -m apps.mcp  # Start MCP server
```

## CPG Repository Setup

### Local CPG Directory Structure

```
/opt/concord/
├── cpgs/                    # Clinical Practice Guidelines
│   ├── cholesterol.yaml
│   ├── uspstf_statinuse.yaml
│   ├── diabetes-child.yaml
│   └── custom/              # Institution-specific CPGs
│       └── local_protocol.yaml
├── configs/                 # Institution configs
│   ├── hospital.yaml
│   └── department_cardio.yaml
├── templates/               # Rendering templates
│   └── custom/
└── logs/                    # Audit logs
```

### CPG Version Control

Even offline, maintain version control for CPGs:

```bash
# Initialize local git repo
cd /opt/concord/cpgs
git init
git add .
git commit -m "Initial CPG deployment"

# Create version tag
git tag -a v1.0.0 -m "Production release 1.0.0"
```

### CPG Update Process

1. **Prepare updates** on a connected machine:
   - Test new CPGs thoroughly
   - Generate changelog (`python -m core.changelog old.yaml new.yaml`)
   - Package updates

2. **Review and approve** through your change management process

3. **Deploy to offline system**:
   ```bash
   # Backup current CPGs
   cp -r cpgs/ cpgs-backup-$(date +%Y%m%d)/

   # Deploy new CPGs
   cp -r new-cpgs/* cpgs/

   # Verify integrity
   python -m scripts.validate_cpg_yaml cpgs/*.yaml

   # Run tests
   python -m pytest tests/ -v
   ```

## Configuration

### Environment Variables

```bash
# No API keys needed!
export CONCORD_CPG_DIR=/opt/concord/cpgs
export CONCORD_CONFIG_DIR=/opt/concord/configs
export CONCORD_LOG_DIR=/opt/concord/logs
export CONCORD_LOG_LEVEL=INFO
```

### Offline Mode Verification

Verify Concord runs without network:

```python
#!/usr/bin/env python3
"""Verify offline operation."""

import socket

# Block network (for testing)
def guard(*args, **kwargs):
    raise RuntimeError("Network access attempted!")

socket.socket = guard

# Now test Concord
from core.cpg import CPG
from core.concord import Concord
from misc import sample_healthcontext

cpg = CPG.from_document_path("cpgs/cholesterol/cholesterol.yaml")
hc = sample_healthcontext()

concord = Concord(cpg=cpg, healthcontext=hc)
result = concord.evaluate()

print("✓ Offline evaluation successful!")
print(f"  Eligible: {result.is_eligible}")
print(f"  Recommendations: {len(result.applied_recommendations or [])}")
```

### Health Check Script

```bash
#!/bin/bash
# /opt/concord/healthcheck.sh

echo "Concord Offline Health Check"
echo "============================"

# Check Python
python3 --version || exit 1

# Check Concord import
python3 -c "from core import Concord; print('✓ Concord module OK')" || exit 1

# Check CPG loading
python3 -c "
from core.cpg import CPG
import os
cpg_dir = os.environ.get('CONCORD_CPG_DIR', 'cpgs')
cpgs = list(p for p in os.listdir(cpg_dir) if p.endswith('.yaml'))
print(f'✓ Found {len(cpgs)} CPGs')
" || exit 1

# Check evaluation
python3 -c "
from core import CPG, Concord
from misc import sample_healthcontext
cpg = CPG.from_document_path('cpgs/cholesterol/cholesterol.yaml')
hc = sample_healthcontext()
result = Concord(cpg=cpg, healthcontext=hc).evaluate()
print('✓ Evaluation successful')
" || exit 1

echo "============================"
echo "All checks passed!"
```

## Disaster Recovery

### Backup Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKUP STRATEGY                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Daily Backups:                                                    │
│   ├── /opt/concord/logs/          → Audit trail                    │
│   └── /opt/concord/configs/       → Institution settings           │
│                                                                     │
│   Weekly Backups:                                                   │
│   └── /opt/concord/cpgs/          → Clinical guidelines            │
│                                                                     │
│   On-Change Backups:                                                │
│   └── Git commits for CPG changes                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Recovery Procedure

1. **System failure recovery**:
   ```bash
   # Restore from backup
   rsync -av /backup/concord/ /opt/concord/

   # Verify integrity
   python -m scripts.validate_cpg_yaml cpgs/*.yaml

   # Restart services
   systemctl restart concord
   ```

2. **CPG corruption recovery**:
   ```bash
   # Restore specific CPG version
   git checkout v1.0.0 -- cpgs/cholesterol/cholesterol.yaml

   # Or restore from backup
   cp /backup/cpgs/cholesterol/cholesterol.yaml cpgs/
   ```

3. **Full system recovery**:
   ```bash
   # Install from offline package
   pip install --no-index --find-links=/backup/wheels -r requirements.txt

   # Restore configuration and CPGs
   rsync -av /backup/concord/ /opt/concord/

   # Run health check
   /opt/concord/healthcheck.sh
   ```

## Security Considerations

### Air-Gap Compliance

| Requirement | Concord Status |
|-------------|----------------|
| No outbound connections | ✓ Verified |
| No telemetry/analytics | ✓ None included |
| Local-only processing | ✓ All computation local |
| No license servers | ✓ Open source |
| Audit logging | ✓ Local file logs |

### Data Protection

```python
# Enable secure logging (PII masking)
from core.secure_logging import configure_secure_logging

configure_secure_logging(
    log_dir="/opt/concord/logs",
    mask_patient_ids=True,
    mask_phi=True,
)
```

### Access Control

```bash
# Restrict CPG directory
chmod 755 /opt/concord/cpgs
chown -R concord:concord /opt/concord/cpgs

# Protect configs
chmod 640 /opt/concord/configs/*.yaml
```

## Integration Examples

### Integration with Local EHR

```python
#!/usr/bin/env python3
"""Example: Local EHR integration."""

from core import CPG, Concord, HealthContext
from primitives.types import Persona

def evaluate_patient(patient_data: dict, cpg_id: str) -> dict:
    """Evaluate a patient from local EHR data."""

    # Load CPG (cached after first load)
    cpg = CPG.from_document_path(f"/opt/concord/cpgs/{cpg_id}.yaml")

    # Create health context from EHR data
    hc = HealthContext.from_dict(
        patient_data,
        persona=Persona.provider,
    )

    # Evaluate
    concord = Concord(cpg=cpg, healthcontext=hc)
    result = concord.evaluate(
        skip_eligibility=False,
        ignore_attestations=True,
    )

    return {
        "eligible": result.is_eligible,
        "recommendations": [
            {
                "id": rec.recommendation.id,
                "title": rec.recommendation.title,
                "applies": rec.applies,
            }
            for rec in (result.applied_recommendations or [])
        ],
    }
```

### Batch Processing (Nightly)

```bash
#!/bin/bash
# /opt/concord/nightly-batch.sh

echo "Starting nightly CPG evaluation batch..."
date

python3 << 'EOF'
from core import CPG
from core.batch_processor import BatchProcessor, ProcessingMode

# Load CPG
cpg = CPG.from_document_path("/opt/concord/cpgs/cholesterol/cholesterol.yaml")

# Load patients from local database
from local_ehr import get_all_patients
patients = get_all_patients()

# Process
processor = BatchProcessor(cpg=cpg)
report = processor.process(
    patients=patients,
    mode=ProcessingMode.THREAD_POOL,
    workers=4,
)

print(f"Processed: {report.successful_count} successful, {report.failed_count} failed")
print(f"Throughput: {report.patients_per_second:.0f} patients/second")

# Save report
report.save("/opt/concord/logs/nightly-batch-$(date +%Y%m%d).json")
EOF

echo "Batch complete."
```

## Monitoring (Offline)

### Local Metrics Collection

```python
#!/usr/bin/env python3
"""Collect and store metrics locally."""

import json
from datetime import datetime
from pathlib import Path

METRICS_DIR = Path("/opt/concord/metrics")
METRICS_DIR.mkdir(exist_ok=True)

def record_evaluation_metric(cpg_id: str, elapsed_ms: float, success: bool):
    """Record a single evaluation metric."""
    metric = {
        "timestamp": datetime.now().isoformat(),
        "cpg_id": cpg_id,
        "elapsed_ms": elapsed_ms,
        "success": success,
    }

    # Append to daily metrics file
    date_str = datetime.now().strftime("%Y%m%d")
    metrics_file = METRICS_DIR / f"metrics-{date_str}.jsonl"

    with open(metrics_file, "a") as f:
        f.write(json.dumps(metric) + "\n")
```

### Daily Report Script

```bash
#!/bin/bash
# Generate daily metrics report

python3 << 'EOF'
import json
from datetime import datetime
from pathlib import Path

metrics_file = Path(f"/opt/concord/metrics/metrics-{datetime.now():%Y%m%d}.jsonl")

if not metrics_file.exists():
    print("No metrics for today")
    exit(0)

metrics = [json.loads(line) for line in metrics_file.read_text().splitlines()]

total = len(metrics)
successful = sum(1 for m in metrics if m["success"])
avg_time = sum(m["elapsed_ms"] for m in metrics) / total if total else 0

print(f"Daily Metrics Report - {datetime.now():%Y-%m-%d}")
print("=" * 40)
print(f"Total evaluations: {total}")
print(f"Successful: {successful} ({100*successful/total:.1f}%)")
print(f"Average time: {avg_time:.1f}ms")
EOF
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Module not found" | Verify all wheels installed: `pip list` |
| "CPG not found" | Check CONCORD_CPG_DIR environment variable |
| Slow performance | Ensure CPGs are cached (first load is slower) |
| Permission denied | Check file ownership and permissions |

### Debug Mode

```bash
# Enable debug logging
export CONCORD_LOG_LEVEL=DEBUG

# Run with verbose output
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from core import CPG, Concord
# ... rest of code
"
```

## Summary

Concord's offline capability provides:

- **Zero network dependency** for clinical evaluation
- **Full functionality** without internet access
- **Disaster recovery** resilience
- **Air-gap compliance** for secure environments
- **Local audit trail** for compliance

This makes Concord suitable for:
- Military and defense healthcare
- Remote/rural clinics
- High-security environments
- Disaster response scenarios
- Network outage resilience
