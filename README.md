# Spirometry Curve Analyzer

Real spirometry interpretation calculators for pulmonary function testing. Stdlib-only Python.

## Calculators

| Calculator | Description | Reference |
|:-----------|:------------|:----------|
| **FEV1/FVC Ratio** | Normal ≥ 0.70 (or age-adjusted LLN) | ATS/ERS 2005 |
| **Obstructive Pattern** | FEV1/FVC < 0.70; severity by FEV1 %pred | GOLD 2023 |
| **Restrictive Pattern** | FEV1/FVC ≥ 0.70 but FVC < 80% predicted | ATS/ERS |
| **Mixed Pattern** | FEV1/FVC < 0.70 AND FVC < 80% predicted | Combined |
| **GOLD Staging** | 1(Mild)≥80%, 2(Moderate)50-79%, 3(Severe)30-49%, 4(Very Severe)<30% | GOLD 2023 |
| **Bronchodilator Response** | ≥12% AND ≥200 mL improvement in FEV1 | ATS/ERS 2005 |
| **Predicted Values** | NHANES III reference equations (age, height, sex) | Hankinson 1999 |

## Quick Start

```bash
# Interpret spirometry
python spiro_analyze.py single --fev1 2.5 --fvc 4.0 --age 60 --height 175 --sex M

# With bronchodilator response
python spiro_analyze.py single --fev1 2.5 --fvc 4.0 --age 60 --height 175 --sex M --fev1-post 2.8

# Predicted values
python spiro_analyze.py predicted --age 40 --height 175 --sex M

# Batch CSV processing
python spiro_analyze.py batch -i spirometry.csv -o results.csv
```

## Python API

```python
from spiro_analyze import (
    interpret_spirometry, bronchodilator_response,
    predicted_fev1, predicted_fvc, percent_predicted,
)

# Full interpretation
result = interpret_spirometry(fev1=2.5, fvc=4.0, age=60, height_cm=175, sex="M")
# pattern="Obstructive pattern", severity="Moderate", gold_stage="GOLD 2"

# Bronchodilator response
bd = bronchodilator_response(fev1_pre=2.5, fev1_post=2.8)
# is_significant=True, change_ml=300, change_percent=12.0
```

## Tests

```bash
python -m pytest test_spirometry_analyzer.py -v
```

## License

MIT
