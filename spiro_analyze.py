#!/usr/bin/env python3
"""
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
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Reference equations (NHANES III / GLI-2012 simplified)
# ---------------------------------------------------------------------------

def predicted_fev1(age: float, height_cm: float, sex: str) -> float:
    """Calculate predicted FEV1 using NHANES III reference equations.

    Uses the standard regression equations for Caucasian adults.
    Sex: 'M' or 'F'.

    Args:
        age: Age in years.
        height_cm: Height in centimetres.
        sex: 'M' or 'F'.

    Returns:
        Predicted FEV1 in litres.
    """
    sex = sex.upper().strip()
    h = height_cm / 100.0  # convert to metres for some equations
    if sex == "M":
        # NHANES III male: FEV1 = 0.5536 - 0.01303*age - 0.000172*age^2 + 0.00014107*ht^2
        return 0.5536 - 0.01303 * age - 0.000172 * (age ** 2) + 0.00014107 * (height_cm ** 2)
    elif sex == "F":
        # NHANES III female
        return 0.4333 - 0.01283 * age - 0.000097 * (age ** 2) + 0.00011384 * (height_cm ** 2)
    else:
        raise ValueError(f"Sex must be 'M' or 'F', got '{sex}'")


def predicted_fvc(age: float, height_cm: float, sex: str) -> float:
    """Calculate predicted FVC using NHANES III reference equations.

    Args:
        age: Age in years.
        height_cm: Height in centimetres.
        sex: 'M' or 'F'.

    Returns:
        Predicted FVC in litres.
    """
    sex = sex.upper().strip()
    if sex == "M":
        return 0.7220 - 0.01163 * age - 0.000164 * (age ** 2) + 0.00015813 * (height_cm ** 2)
    elif sex == "F":
        return 0.5745 - 0.01340 * age - 0.000084 * (age ** 2) + 0.00012648 * (height_cm ** 2)
    else:
        raise ValueError(f"Sex must be 'M' or 'F', got '{sex}'")


def predicted_fev1_fvc(age: float, height_cm: float, sex: str) -> float:
    """Calculate predicted FEV1/FVC ratio.

    For simplicity, returns the ratio of predicted values.
    In practice, the LLN (Lower Limit of Normal) is preferred.

    Args:
        age: Age in years.
        height_cm: Height in centimetres.
        sex: 'M' or 'F'.

    Returns:
        Predicted FEV1/FVC ratio.
    """
    fev1 = predicted_fev1(age, height_cm, sex)
    fvc = predicted_fvc(age, height_cm, sex)
    return fev1 / fvc if fvc > 0 else 0.0


def lln_fev1_fvc(age: float, sex: str) -> float:
    """Estimate Lower Limit of Normal (LLN) for FEV1/FVC ratio.

    Uses the simplified approach: LLN ≈ predicted - 1.645 * 0.05
    (approximate standard deviation of FEV1/FVC ratio).

    More accurate: LLN ≈ 0.70 for age < 45, decreases with age.
    Using the GLI-2012 approach: fixed ratio of 0.70 is a reasonable
    clinical approximation for adults.

    Args:
        age: Age in years.
        sex: 'M' or 'F'.

    Returns:
        LLN for FEV1/FVC ratio.
    """
    # Simplified LLN estimation based on age
    # The fixed 0.70 threshold over-diagnoses obstruction in elderly
    # and under-diagnoses in young adults. This is a common clinical compromise.
    if age < 40:
        return 0.75
    elif age < 50:
        return 0.73
    elif age < 60:
        return 0.71
    elif age < 70:
        return 0.69
    else:
        return 0.67


# ---------------------------------------------------------------------------
# Percent predicted
# ---------------------------------------------------------------------------

def percent_predicted(measured: float, predicted: float) -> float:
    """Calculate percent of predicted value.

    Args:
        measured: Measured value.
        predicted: Predicted (reference) value.

    Returns:
        Percent predicted (%).
    """
    if predicted <= 0:
        raise ValueError("Predicted value must be > 0")
    return (measured / predicted) * 100.0


# ---------------------------------------------------------------------------
# Bronchodilator response
# ---------------------------------------------------------------------------

@dataclass
class BronchodilatorResponse:
    """Result of bronchodilator response assessment."""
    fev1_pre: float
    fev1_post: float
    fev1_change_ml: float
    fev1_change_percent: float
    is_significant: bool
    interpretation: str


def bronchodilator_response(fev1_pre: float, fev1_post: float) -> BronchodilatorResponse:
    """Assess bronchodilator response.

    Significant response: >= 12% improvement AND >= 200 mL increase in FEV1.
    (ATS/ERS criteria)

    Args:
        fev1_pre: FEV1 before bronchodilator (litres).
        fev1_post: FEV1 after bronchodilator (litres).

    Returns:
        BronchodilatorResponse dataclass.
    """
    change_l = fev1_post - fev1_pre
    change_ml = change_l * 1000.0
    change_pct = (change_l / fev1_pre * 100.0) if fev1_pre > 0 else 0.0

    significant = change_pct >= 12.0 and change_ml >= 200.0

    if significant:
        interp = "Significant bronchodilator response (>=12% and >=200 mL improvement)"
    else:
        reasons = []
        if change_pct < 12.0:
            reasons.append(f"percent change {change_pct:.1f}% < 12%")
        if change_ml < 200.0:
            reasons.append(f"absolute change {change_ml:.0f} mL < 200 mL")
        interp = f"Not significant ({'; '.join(reasons)})"

    return BronchodilatorResponse(
        fev1_pre=fev1_pre,
        fev1_post=fev1_post,
        fev1_change_ml=round(change_ml, 1),
        fev1_change_percent=round(change_pct, 1),
        is_significant=significant,
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Pattern classification
# ---------------------------------------------------------------------------

@dataclass
class SpirometryResult:
    """Complete spirometry interpretation result."""
    fev1: float
    fvc: float
    fev1_fvc_ratio: float
    fev1_percent_predicted: float
    fvc_percent_predicted: float
    pattern: str
    severity: Optional[str]
    gold_stage: Optional[str]
    obstruction_present: bool
    restriction_suggested: bool
    notes: List[str] = field(default_factory=list)


def interpret_spirometry(
    fev1: float,
    fvc: float,
    age: float,
    height_cm: float,
    sex: str,
    use_lln: bool = True,
) -> SpirometryResult:
    """Interpret spirometry results.

    Classifies as Normal, Obstructive, Restrictive (suggested), or Mixed.

    Args:
        fev1: Measured FEV1 in litres.
        fvc: Measured FVC in litres.
        age: Patient age in years.
        height_cm: Patient height in cm.
        sex: 'M' or 'F'.
        use_lln: If True, use age-adjusted LLN instead of fixed 0.70.

    Returns:
        SpirometryResult dataclass.
    """
    if fev1 < 0 or fvc < 0:
        raise ValueError("FEV1 and FVC must be >= 0")
    if fev1 > fvc * 1.1:  # allow small measurement tolerance
        raise ValueError(f"FEV1 ({fev1}) cannot exceed FVC ({fvc})")
    if age <= 0 or height_cm <= 0:
        raise ValueError("Age and height must be > 0")

    ratio = fev1 / fvc if fvc > 0 else 0.0

    pred_fev1 = predicted_fev1(age, height_cm, sex)
    pred_fvc = predicted_fvc(age, height_cm, sex)

    fev1_pct = percent_predicted(fev1, pred_fev1)
    fvc_pct = percent_predicted(fvc, pred_fvc)

    # Determine threshold
    if use_lln:
        threshold = lln_fev1_fvc(age, sex)
    else:
        threshold = 0.70

    obstruction = ratio < threshold
    restriction = (not obstruction) and (fvc_pct < 80.0)
    mixed = obstruction and (fvc_pct < 80.0)

    notes: List[str] = []

    if mixed:
        pattern = "Mixed obstructive-restrictive pattern"
        severity = _obstructive_severity(fev1_pct)
        notes.append("Both obstruction and restriction present. Consider full pulmonary function testing with lung volumes.")
    elif obstruction:
        pattern = "Obstructive pattern"
        severity = _obstructive_severity(fev1_pct)
    elif restriction:
        pattern = "Restrictive pattern (suggested)"
        severity = _restrictive_severity(fvc_pct)
        notes.append("Restriction suggested by low FVC with normal ratio. Confirm with lung volumes (TLC measurement).")
    else:
        pattern = "Normal spirometry"
        severity = None

    # GOLD staging (for COPD, post-bronchodilator)
    gold = None
    if obstruction:
        gold = _gold_stage(fev1_pct)

    return SpirometryResult(
        fev1=fev1,
        fvc=fvc,
        fev1_fvc_ratio=round(ratio, 4),
        fev1_percent_predicted=round(fev1_pct, 1),
        fvc_percent_predicted=round(fvc_pct, 1),
        pattern=pattern,
        severity=severity,
        gold_stage=gold,
        obstruction_present=obstruction,
        restriction_suggested=restriction or mixed,
        notes=notes,
    )


def _obstructive_severity(fev1_pct: float) -> str:
    """Classify obstructive severity by FEV1 % predicted."""
    if fev1_pct >= 80.0:
        return "Mild"
    elif fev1_pct >= 50.0:
        return "Moderate"
    elif fev1_pct >= 30.0:
        return "Severe"
    else:
        return "Very severe"


def _restrictive_severity(fvc_pct: float) -> str:
    """Classify restrictive severity by FVC % predicted."""
    if fvc_pct >= 70.0:
        return "Mild"
    elif fvc_pct >= 60.0:
        return "Moderate"
    elif fvc_pct >= 50.0:
        return "Moderately severe"
    else:
        return "Severe"


def _gold_stage(fev1_pct: float) -> str:
    """GOLD staging for COPD based on FEV1 % predicted (post-BD)."""
    if fev1_pct >= 80.0:
        return "GOLD 1 (Mild)"
    elif fev1_pct >= 50.0:
        return "GOLD 2 (Moderate)"
    elif fev1_pct >= 30.0:
        return "GOLD 3 (Severe)"
    else:
        return "GOLD 4 (Very Severe)"


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_csv(input_path: str, output_path: str) -> int:
    """Process a CSV of spirometry data.

    Expected columns: fev1, fvc, age, height_cm, sex
    Optional: fev1_post (for bronchodilator response), patient_id
    """
    results: List[Dict[str, Any]] = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fev1 = float(row["fev1"])
            fvc = float(row["fvc"])
            age = float(row["age"])
            height_cm = float(row["height_cm"])
            sex = row["sex"].strip()
            pid = row.get("patient_id", "")

            res = interpret_spirometry(fev1, fvc, age, height_cm, sex)
            d: Dict[str, Any] = {
                "patient_id": pid,
                "fev1": fev1, "fvc": fvc,
                "fev1_fvc_ratio": res.fev1_fvc_ratio,
                "fev1_pct_pred": res.fev1_percent_predicted,
                "fvc_pct_pred": res.fvc_percent_predicted,
                "pattern": res.pattern,
                "severity": res.severity,
                "gold_stage": res.gold_stage,
                "obstruction": res.obstruction_present,
                "restriction": res.restriction_suggested,
            }

            # Bronchodilator response if post-BD FEV1 available
            fev1_post = row.get("fev1_post", "")
            if fev1_post not in ("", None):
                bd = bronchodilator_response(fev1, float(fev1_post))
                d["bd_response_ml"] = bd.fev1_change_ml
                d["bd_response_pct"] = bd.fev1_change_percent
                d["bd_significant"] = bd.is_significant

            results.append(d)

    if results:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
    return len(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spiro_analyze",
        description="Spirometry interpretation — pattern classification, severity, GOLD staging, bronchodilator response.",
    )
    sub = p.add_subparsers(dest="cmd")

    # Single interpretation
    s = sub.add_parser("single", help="Interpret single spirometry result")
    s.add_argument("--fev1", type=float, required=True, help="FEV1 (litres)")
    s.add_argument("--fvc", type=float, required=True, help="FVC (litres)")
    s.add_argument("--age", type=float, required=True, help="Age (years)")
    s.add_argument("--height", type=float, required=True, help="Height (cm)")
    s.add_argument("--sex", required=True, choices=["M", "F"], help="Sex (M/F)")
    s.add_argument("--fev1-post", type=float, default=None, help="Post-BD FEV1 (litres)")
    s.add_argument("--use-fixed-ratio", action="store_true", help="Use fixed 0.70 instead of LLN")

    # Predicted values
    pv = sub.add_parser("predicted", help="Calculate predicted values")
    pv.add_argument("--age", type=float, required=True)
    pv.add_argument("--height", type=float, required=True)
    pv.add_argument("--sex", required=True, choices=["M", "F"])

    # Batch
    b = sub.add_parser("batch", help="Batch process CSV")
    b.add_argument("-i", "--input", required=True)
    b.add_argument("-o", "--output", default="results.csv")

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "single":
        res = interpret_spirometry(
            args.fev1, args.fvc, args.age, args.height, args.sex,
            use_lln=not args.use_fixed_ratio,
        )
        out: Dict[str, Any] = {
            "fev1": res.fev1, "fvc": res.fvc,
            "fev1_fvc_ratio": res.fev1_fvc_ratio,
            "fev1_percent_predicted": res.fev1_percent_predicted,
            "fvc_percent_predicted": res.fvc_percent_predicted,
            "pattern": res.pattern,
            "severity": res.severity,
            "gold_stage": res.gold_stage,
            "obstruction_present": res.obstruction_present,
            "restriction_suggested": res.restriction_suggested,
            "notes": res.notes,
        }
        if args.fev1_post is not None:
            bd = bronchodilator_response(args.fev1, args.fev1_post)
            out["bronchodilator_response"] = {
                "change_ml": bd.fev1_change_ml,
                "change_percent": bd.fev1_change_percent,
                "significant": bd.is_significant,
                "interpretation": bd.interpretation,
            }
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "predicted":
        fev1_p = predicted_fev1(args.age, args.height, args.sex)
        fvc_p = predicted_fvc(args.age, args.height, args.sex)
        ratio_p = fev1_p / fvc_p if fvc_p > 0 else 0
        print(json.dumps({
            "predicted_fev1": round(fev1_p, 2),
            "predicted_fvc": round(fvc_p, 2),
            "predicted_ratio": round(ratio_p, 4),
        }, indent=2))
        return 0

    if args.cmd == "batch":
        n = process_csv(args.input, args.output)
        print(f"Processed {n} records -> {args.output}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
