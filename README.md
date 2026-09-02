# Spirometry Curve Analyzer

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Spirometry Curve Analyzer
==========================
Real spirometry interpretation calculators:

- FEV1/FVC ratio: Normal >= 0.70
- Obstructive pattern: FEV1/FVC < 0.70
    Mild:         FEV1 >= 80% predicted
    Moderate:     FEV1 50-79% predicted
    Severe:       FEV1 30-49% predicted
    Very severe:  FEV1 < 30% predicted
- Restrictive pattern: FEV1/FVC >= 0.70 but FVC < 80% predicted
- Mixed pattern: FEV1/FVC < 0.70 AND FVC < 80% predicted
- GOLD staging for COPD (based on FEV1 %predicted post-bronchodilator)
    GOLD 1 (Mild):       FEV1 >= 80%
    GOLD 2 (Moderate):   50-79%
    GOLD 3 (Severe):     30-49%
    GOLD 4 (Very Severe): < 30%
- Bronchodilator response: >= 12% AND >= 200 mL improvement in FEV1
- Predicted values using reference equations (age, height, sex)

Stdlib only. Author: Dr. Abu Suraih Sakhri. License: MIT.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`BronchodilatorResponse`**: Result of bronchodilator response assessment.
- **`SpirometryResult`**: Complete spirometry interpretation result.

---

## 📐 Mathematical Formulation & Logic

```text
  """Calculate predicted FEV1 using NHANES III reference equations.
  """Calculate predicted FVC using NHANES III reference equations.
  """Calculate predicted FEV1/FVC ratio.
  """Calculate percent of predicted value.
  return (measured / predicted) * 100.0
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --input data.csv
```

### Parameter Reference
- `--interactive`: Launch guided terminal interactive wizard.
- `--input <path>`: Evaluate input from JSON or CSV specification.
- `--json`: Output deterministic structured results in JSON format.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `suite_name` | Parameter / observation metric | Required |
| `system_slug` | Parameter / observation metric | Required |
| `standard_reference` | Parameter / observation metric | Required |
| `test_cases` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t spirometry-curve-analyzer .
docker run -p 8000:8000 spirometry-curve-analyzer
```
