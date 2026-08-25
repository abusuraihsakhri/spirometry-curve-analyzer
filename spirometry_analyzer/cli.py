"""Command-line interface for the Spirometry Curve Analyzer."""

from __future__ import annotations

import argparse
import sys

from . import gli2012 as gli
from .curve_metrics import analyze_csv
from .interpretation import classify


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spiro-analyze",
        description=(
            "Analyze a digitized flow-volume spirometry curve: derive FVC, FEV1, "
            "FEV1/FVC and PEF, and classify the pattern (obstructive / restrictive "
            "/ mixed / normal) per the ATS/ERS 2019 interpretive algorithm using "
            "GLI-2012 reference equations."
        ),
    )
    p.add_argument("input", help="CSV file with a 'time' column and a 'flow' or 'volume' column")
    p.add_argument("--age", type=float, required=True, help="Age in years (3-95)")
    p.add_argument("--height", type=float, required=True, help="Standing height in cm")
    p.add_argument("--sex", choices=["M", "F"], required=True, help="Biological sex used for GLI-2012 equations")
    p.add_argument(
        "--ethnicity",
        choices=list(gli.ETHNICITIES),
        default="caucasian",
        help="Ethnic group for GLI-2012 reference equations (default: caucasian)",
    )
    p.add_argument("--plot", metavar="PNG_PATH", help="Save an annotated flow-volume loop plot to this path")
    p.add_argument("--patient-id", default=None, help="Optional patient identifier to include in the report header")
    return p


def format_report(patient_id, age, height, sex, ethnicity, metrics, result) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("SPIROMETRY REPORT")
    if patient_id:
        lines.append(f"Patient: {patient_id}")
    lines.append(f"Age: {age:.0f} y   Height: {height:.0f} cm   Sex: {sex}   Ethnicity: {ethnicity}")
    lines.append("-" * 60)
    lines.append("Measured curve metrics:")
    lines.append(f"  FVC              {metrics.fvc:6.2f} L")
    lines.append(f"  FEV1             {metrics.fev1:6.2f} L")
    lines.append(f"  FEV1/FVC         {metrics.fev1_fvc_ratio:6.3f}")
    lines.append(f"  PEF              {metrics.pef:6.2f} L/s")
    lines.append(f"  FEF25-75         {metrics.fef2575:6.2f} L/s")
    lines.append(
        f"  Back-extrapolated volume  {metrics.back_extrapolated_volume:5.3f} L "
        f"({metrics.back_extrapolated_pct_fvc:4.1f}% of FVC)"
        + ("  [WARNING: exceeds ATS/ERS 5%/0.150L acceptability limit]"
           if metrics.back_extrapolated_volume > 0.150 and metrics.back_extrapolated_pct_fvc > 5.0
           else "")
    )
    lines.append("-" * 60)
    lines.append("GLI-2012 predicted values / % predicted / z-score / LLN:")
    lines.append(
        f"  FEV1      pred {result.fev1_pred:5.2f} L   %pred {result.fev1_pct_pred:6.1f}%   "
        f"z {result.fev1_z:+5.2f}   LLN {result.fev1_lln:5.2f} L"
    )
    lines.append(
        f"  FVC       pred {result.fvc_pred:5.2f} L   %pred {result.fvc_pct_pred:6.1f}%   "
        f"z {result.fvc_z:+5.2f}   LLN {result.fvc_lln:5.2f} L"
    )
    lines.append(
        f"  FEV1/FVC  pred {result.ratio_pred:5.3f}     %pred {result.ratio_pct_pred:6.1f}%   "
        f"z {result.ratio_z:+5.2f}   LLN {result.ratio_lln:5.3f}"
    )
    lines.append("-" * 60)
    lines.append(f"Interpretation: {result.pattern}")
    if result.severity:
        lines.append(f"Severity: {result.severity}")
    for note in result.notes:
        lines.append(f"Note: {note}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        metrics = analyze_csv(args.input)
        result = classify(
            fev1=metrics.fev1,
            fvc=metrics.fvc,
            age=args.age,
            height_cm=args.height,
            sex=args.sex,
            ethnicity=args.ethnicity,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(format_report(args.patient_id, args.age, args.height, args.sex, args.ethnicity, metrics, result))

    if args.plot:
        from .plotting import plot_flow_volume_loop

        plot_flow_volume_loop(metrics, args.plot, title=f"Flow-Volume Loop — {result.pattern}")
        print(f"\nPlot saved to {args.plot}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
