# Spirometry Curve Analyzer

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** ATS/ERS 2019, GLI-2012 (Quanjer et al.)

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Spirometry Curve Analyzer is a clinical decision support tool that interprets spirometry results:

- **FEV1/FVC ratio analysis**: Normal >= LLN (Lower Limit of Normal)
- **Obstructive pattern detection**: FEV1/FVC < LLN
  - Mild: FEV1 >= 80% predicted
  - Moderate: FEV1 50-79% predicted
  - Severe: FEV1 30-49% predicted
  - Very severe: FEV1 < 30% predicted
- **Restrictive pattern suggestion**: FEV1/FVC >= LLN but FVC < 80% predicted
- **Mixed pattern**: FEV1/FVC < LLN AND FVC < 80% predicted
- **GOLD staging for COPD** (based on FEV1 %predicted post-bronchodilator)
- **Bronchodilator response**: >= 12% AND >= 200 mL improvement in FEV1
- **Predicted values** using GLI-2012 reference equations (age, height, sex, ethnicity)
- **Waveform analysis**: Parse digitized flow-time or volume-time curves to derive FVC, FEV1, PEF, FEF25-75

Author: Dr. Abu Suraih Sakhri. License: MIT.

---

## ⚙️ Key Components

### Core Spirometry Package (`spirometry_analyzer/`)

- **`gli2012.py`**: GLI-2012 LMS reference equations for predicted values and z-scores
- **`curve_metrics.py`**: Parse digitized waveforms and derive FVC, FEV1, PEF, FEF25-75 with ATS/ERS back-extrapolation
- **`interpretation.py`**: ATS/ERS 2019 interpretive algorithm using z-scores
- **`cli.py`**: Command-line interface for waveform analysis
- **`plotting.py`**: Flow-volume loop visualization with landmarks

### Legacy CLI (`spiro_analyze.py`)

Standalone NHANES III-based calculator with single/batch processing modes.

### Enterprise Agent System (`agents/`)

- **PHI Guard**: Outbound PHI detection and redaction (HIPAA Safe Harbor)
- **HMAC-SHA256 Audit Trail**: Tamper-evident cryptographic audit logging
- **Multi-worker evaluation**: QC, Safety, and Protocol Conformance workers
- **FastAPI REST API**: `/health`, `/metrics`, `/api/audit`, `/api/chat`, `/api/audit/logs`

---

## 💻 Installation

```bash
pip install -r requirements.txt
```

---

## 🧪 Testing & Verification

Run the full test suite:

```bash
pytest -v
```

Run specific test files:

```bash
pytest tests/ -v              # Enterprise agent tests
pytest test_spirometry_analyzer.py -v  # Core spirometry tests
```

---

## 💻 CLI Usage

### 1. Single Interpretation (Legacy)
```bash
python cli.py single --fev1 3.5 --fvc 4.5 --age 40 --height 175 --sex M
```

### 2. Predicted Values
```bash
python cli.py predicted --age 40 --height 175 --sex M
```

### 3. Batch CSV Processing
```bash
python cli.py batch -i input.csv -o results.csv
```

### 4. Waveform Analysis (Core Package)
```bash
python -m spiro_analyze single --fev1 3.5 --fvc 4.5 --age 40 --height 175 --sex M
```

### 5. Enterprise Audit
```bash
python cli.py audit --task-id TASK-001
python cli.py chat "Explain the interpretation"
python cli.py verify-audit
```

### 6. REST API Server
```bash
python cli.py serve --host 0.0.0.0 --port 8000
```

---

## 🐳 Container Deployment

```bash
docker build -t spirometry-curve-analyzer .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key spirometry-curve-analyzer
```

Or with docker-compose:

```bash
docker-compose up
```

---

## 🛡️ Security

- **Zero-PHI Outbound Interceptor**: Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
- **Tamper-Evident HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs
- **Configurable Audit Secret**: Set `AUDIT_SECRET_KEY` environment variable in production (a development default is used otherwise with a warning)

---

## 📐 Mathematical Foundation

### GLI-2012 LMS Equations
```
z = ((Y / M) ** L - 1) / (L * S)      when L != 0
z = ln(Y / M) / S                     when L == 0
```

Where M (median), S (coefficient of variation), and L (skewness) are modeled as functions of height, age, and sex.

### ATS/ERS Interpretive Algorithm
1. Airflow obstruction: FEV1/FVC z-score < LLN (z < -1.645)
2. Restrictive pattern: FVC z-score < LLN (suggested, requires TLC confirmation)
3. Mixed pattern: Both obstruction and restriction present

---

## 📁 Project Structure

```
spirometry-curve-analyzer/
├── agents/                  # Enterprise agent system
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # PHI Guard, Audit Trail
│   ├── models.py           # Pydantic schemas
│   ├── supervisor.py       # Multi-agent orchestrator
│   ├── workers.py          # QC, Safety, Conformance workers
│   └── ...
├── spirometry_analyzer/     # Core analysis package
│   ├── gli2012.py          # GLI-2012 reference equations
│   ├── curve_metrics.py    # Waveform parsing
│   ├── interpretation.py   # ATS/ERS algorithm
│   ├── cli.py              # Package CLI
│   └── plotting.py         # Visualization
├── tests/                   # Pytest test suite
├── sample_data/             # Example spirometry waveforms
├── scripts/                 # Data generation utilities
├── cli.py                   # Unified CLI entry point
├── spiro_analyze.py         # Legacy standalone CLI
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project metadata
├── Dockerfile               # Container build
└── docker-compose.yml       # Container orchestration
```
