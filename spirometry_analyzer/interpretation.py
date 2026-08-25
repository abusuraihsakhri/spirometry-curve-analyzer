"""ATS/ERS 2019 spirometry interpretive algorithm.

Implements the standard obstructive / restrictive / mixed decision tree
(Pellegrino et al. 2005, retained and refined by the 2019 ATS/ERS technical
standard and its companion interpretive-strategies update) driven by
GLI-2012 z-scores / lower limits of normal (LLN) rather than fixed
percent-predicted or the outdated fixed FEV1/FVC < 0.70 cutoff:

    1. Airflow obstruction is present when the FEV1/FVC z-score is below the
       LLN (z < -1.645).
    2. A restrictive ventilatory pattern can only be SUGGESTED by spirometry
       (FVC z-score below LLN) -- confirmation requires a reduced Total Lung
       Capacity (TLC) on full body plethysmography, which spirometry cannot
       measure.
    3. Combining both findings yields a "mixed" pattern classification,
       again with restriction only suggested pending TLC confirmation.

Severity grading uses the z-score bands adopted in the ATS/ERS interpretive
strategy update (in place of the older fixed %-predicted bands), applied to
FEV1 z-score for obstruction and to FVC z-score for suggested restriction:

    LLN <= z            -> Normal
    -2.5 <= z < LLN      -> Mild
    -4.0 <= z < -2.5     -> Moderate
    z < -4.0             -> Severe
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import gli2012 as gli

Z_LLN = gli.Z_LLN


def severity_grade(z: float) -> str:
    if z >= Z_LLN:
        return "Normal"
    if z >= -2.5:
        return "Mild"
    if z >= -4.0:
        return "Moderate"
    return "Severe"


@dataclass
class InterpretationResult:
    pattern: str
    severity: str | None
    obstruction_present: bool
    restriction_suggested: bool
    fev1_z: float
    fvc_z: float
    ratio_z: float
    fev1_pct_pred: float
    fvc_pct_pred: float
    ratio_pct_pred: float
    fev1_pred: float
    fvc_pred: float
    ratio_pred: float
    fev1_lln: float
    fvc_lln: float
    ratio_lln: float
    notes: list = field(default_factory=list)


def classify(
    fev1: float,
    fvc: float,
    age: float,
    height_cm: float,
    sex: str,
    ethnicity: str = "caucasian",
) -> InterpretationResult:
    """Classify a spirometry result per the ATS/ERS 2019 algorithm."""
    if fvc <= 0 or fev1 <= 0:
        raise ValueError("fev1 and fvc must be positive")
    if fev1 > fvc * 1.0001:
        raise ValueError("FEV1 cannot exceed FVC")

    ratio = fev1 / fvc

    fev1_z = gli.z_score(fev1, age, height_cm, sex, ethnicity, "FEV1")
    fvc_z = gli.z_score(fvc, age, height_cm, sex, ethnicity, "FVC")
    ratio_z = gli.z_score(ratio, age, height_cm, sex, ethnicity, "FEV1_FVC")

    fev1_pred = gli.predicted(age, height_cm, sex, ethnicity, "FEV1")
    fvc_pred = gli.predicted(age, height_cm, sex, ethnicity, "FVC")
    ratio_pred = gli.predicted(age, height_cm, sex, ethnicity, "FEV1_FVC")

    fev1_lln = gli.lln(age, height_cm, sex, ethnicity, "FEV1")
    fvc_lln = gli.lln(age, height_cm, sex, ethnicity, "FVC")
    ratio_lln = gli.lln(age, height_cm, sex, ethnicity, "FEV1_FVC")

    obstruction = ratio_z < Z_LLN
    restriction_suggested = fvc_z < Z_LLN

    notes = []
    if obstruction and restriction_suggested:
        pattern = "Mixed obstructive/restrictive pattern (restriction suggested)"
        severity = severity_grade(fev1_z)
        notes.append(
            "Reduced FEV1/FVC with reduced FVC: consistent with a mixed defect, "
            "but a true restrictive component cannot be confirmed by spirometry "
            "alone. Recommend body plethysmography (TLC) to confirm restriction."
        )
    elif obstruction:
        pattern = "Obstructive pattern"
        severity = severity_grade(fev1_z)
    elif restriction_suggested:
        pattern = "Restrictive pattern suggested"
        severity = severity_grade(fvc_z)
        notes.append(
            "FEV1/FVC is normal but FVC is reduced below the lower limit of "
            "normal. Spirometry can only suggest restriction; confirmation "
            "requires a reduced TLC on body plethysmography."
        )
    else:
        pattern = "Normal spirometry"
        severity = None

    return InterpretationResult(
        pattern=pattern,
        severity=severity,
        obstruction_present=obstruction,
        restriction_suggested=restriction_suggested,
        fev1_z=fev1_z,
        fvc_z=fvc_z,
        ratio_z=ratio_z,
        fev1_pct_pred=100.0 * fev1 / fev1_pred,
        fvc_pct_pred=100.0 * fvc / fvc_pred,
        ratio_pct_pred=100.0 * ratio / ratio_pred,
        fev1_pred=fev1_pred,
        fvc_pred=fvc_pred,
        ratio_pred=ratio_pred,
        fev1_lln=fev1_lln,
        fvc_lln=fvc_lln,
        ratio_lln=ratio_lln,
        notes=notes,
    )
