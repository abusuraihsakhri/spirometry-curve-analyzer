"""Parse digitized spirometry waveforms and derive FVC, FEV1, PEF, FEF25-75.

Accepts either a flow-time curve (expiratory flow in L/s vs time in s) or a
volume-time curve (expired volume in L vs time in s). Flow is integrated to
volume (or volume differentiated to flow) with `scipy.integrate` /
`scipy.signal`, the true start of the forced expiration is located by
back-extrapolation from the point of peak flow (the standard ATS/ERS
technique), and FVC, FEV1, PEF and FEF25-75 are computed from the corrected
volume-time curve.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

import numpy as np
from scipy.integrate import cumulative_trapezoid
from scipy.signal import savgol_filter

FEV1_TIME_S = 1.0


@dataclass
class Waveform:
    t: np.ndarray          # seconds, from 0
    volume: np.ndarray      # litres, expired volume (uncorrected baseline)
    flow: np.ndarray        # L/s


@dataclass
class SpirometryMetrics:
    fvc: float
    fev1: float
    fev1_fvc_ratio: float
    pef: float
    fef2575: float
    back_extrapolated_volume: float
    back_extrapolated_pct_fvc: float
    t0_corrected: float
    waveform: Waveform


def load_waveform_csv(path: str) -> Waveform:
    """Load a CSV with a `time` column and either a `flow` or `volume` column.

    Header matching is case-insensitive and tolerant of underscores/units,
    e.g. "time_s", "flow (L/s)", "Volume_L" are all recognized.
    """
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]

    norm = [h.strip().lower() for h in header]

    def find(*keywords):
        for i, h in enumerate(norm):
            if any(k in h for k in keywords):
                return i
        return None

    t_idx = find("time", "sec", "t(")
    flow_idx = find("flow")
    vol_idx = find("volume", "vol")

    if t_idx is None:
        raise ValueError("CSV must have a time column")
    if flow_idx is None and vol_idx is None:
        raise ValueError("CSV must have a 'flow' or 'volume' column")

    t = np.array([float(r[t_idx]) for r in rows], dtype=float)
    order = np.argsort(t)
    t = t[order]

    if flow_idx is not None:
        flow = np.array([float(r[flow_idx]) for r in rows], dtype=float)[order]
        volume = np.concatenate(([0.0], cumulative_trapezoid(flow, t)))
    else:
        volume = np.array([float(r[vol_idx]) for r in rows], dtype=float)[order]
        volume = volume - volume[0]
        window = min(11, len(t) if len(t) % 2 == 1 else len(t) - 1)
        if window >= 5:
            smoothed = savgol_filter(volume, window_length=window, polyorder=2)
        else:
            smoothed = volume
        flow = np.gradient(smoothed, t)

    return Waveform(t=t, volume=volume, flow=flow)


def compute_metrics(waveform: Waveform) -> SpirometryMetrics:
    """Compute FVC, FEV1, PEF and FEF25-75 from a parsed waveform.

    Uses back-extrapolation from the point of peak expiratory flow to locate
    the true (corrected) zero time of the forced maneuver, per standard
    ATS/ERS technique, so FEV1 is measured from true test start rather than
    from an arbitrary recording trigger.
    """
    t, volume, flow = waveform.t, waveform.volume, waveform.flow

    idx_pef = int(np.argmax(flow))
    pef = float(flow[idx_pef])
    if pef <= 0:
        raise ValueError("No positive expiratory flow found in waveform")
    t_pef = t[idx_pef]
    v_pef = volume[idx_pef]

    t0 = t_pef - v_pef / pef
    t0 = max(t0, float(t[0]))

    v_mono = np.maximum.accumulate(volume)

    v0 = float(np.interp(t0, t, v_mono))
    fvc = float(np.max(v_mono) - v0)
    if fvc <= 0:
        raise ValueError("Computed FVC is not positive; check waveform data")

    bev = v0 - float(v_mono[0])
    bev = max(bev, 0.0)
    bev_pct = 100.0 * bev / fvc

    v_at_fev1_time = float(np.interp(t0 + FEV1_TIME_S, t, v_mono))
    fev1 = v_at_fev1_time - v0
    fev1 = min(fev1, fvc)

    v25 = v0 + 0.25 * fvc
    v75 = v0 + 0.75 * fvc
    t25 = float(np.interp(v25, v_mono, t))
    t75 = float(np.interp(v75, v_mono, t))
    fef2575 = 0.5 * fvc / (t75 - t25) if t75 > t25 else float("nan")

    return SpirometryMetrics(
        fvc=fvc,
        fev1=fev1,
        fev1_fvc_ratio=fev1 / fvc,
        pef=pef,
        fef2575=fef2575,
        back_extrapolated_volume=bev,
        back_extrapolated_pct_fvc=bev_pct,
        t0_corrected=t0,
        waveform=waveform,
    )


def analyze_csv(path: str) -> SpirometryMetrics:
    return compute_metrics(load_waveform_csv(path))
