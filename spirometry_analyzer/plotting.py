"""Flow-volume loop plotting with key landmarks annotated."""

from __future__ import annotations

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .curve_metrics import SpirometryMetrics


def plot_flow_volume_loop(metrics: SpirometryMetrics, out_path: str, title: str = "Flow-Volume Loop") -> None:
    wf = metrics.waveform
    t, volume, flow = wf.t, wf.volume, wf.flow

    v0 = float(np.interp(metrics.t0_corrected, t, np.maximum.accumulate(volume)))
    vol_corrected = volume - v0

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.plot(vol_corrected, flow, color="#1f6fb2", linewidth=2, label="Expiratory flow-volume curve")
    ax.axhline(0, color="gray", linewidth=0.8)

    # PEF landmark
    idx_pef = int(np.argmax(flow))
    ax.plot(vol_corrected[idx_pef], flow[idx_pef], "o", color="#d62728", zorder=5)
    ax.annotate(
        f"PEF = {metrics.pef:.2f} L/s",
        xy=(vol_corrected[idx_pef], flow[idx_pef]),
        xytext=(vol_corrected[idx_pef] + 0.05 * metrics.fvc, flow[idx_pef]),
        fontsize=9,
        color="#d62728",
    )

    # FEV1 landmark (volume exhaled at t0+1s)
    v_mono = np.maximum.accumulate(volume)
    v_fev1 = float(np.interp(metrics.t0_corrected + 1.0, t, v_mono)) - v0
    flow_at_fev1 = float(np.interp(v_fev1 + v0, v_mono, flow))
    ax.plot(v_fev1, flow_at_fev1, "s", color="#2ca02c", zorder=5)
    ax.axvline(v_fev1, color="#2ca02c", linestyle="--", linewidth=1, alpha=0.7)
    ax.annotate(
        f"FEV1 = {metrics.fev1:.2f} L",
        xy=(v_fev1, flow_at_fev1),
        xytext=(v_fev1, flow_at_fev1 + 0.08 * metrics.pef),
        fontsize=9,
        color="#2ca02c",
        ha="center",
    )

    # FVC landmark (end of curve)
    ax.plot(metrics.fvc, flow[-1], "^", color="#9467bd", zorder=5)
    ax.annotate(
        f"FVC = {metrics.fvc:.2f} L",
        xy=(metrics.fvc, flow[-1]),
        xytext=(metrics.fvc - 0.02 * metrics.fvc, flow[-1] + 0.08 * metrics.pef),
        fontsize=9,
        color="#9467bd",
        ha="right",
    )

    # FEF25-75 segment
    v25, v75 = 0.25 * metrics.fvc, 0.75 * metrics.fvc
    flow25 = float(np.interp(v25 + v0, v_mono, flow))
    flow75 = float(np.interp(v75 + v0, v_mono, flow))
    ax.plot([v25, v75], [flow25, flow75], color="#ff7f0e", linewidth=2.5, label="FEF25-75 segment")
    ax.annotate(
        f"FEF25-75 = {metrics.fef2575:.2f} L/s",
        xy=((v25 + v75) / 2, (flow25 + flow75) / 2),
        xytext=((v25 + v75) / 2, (flow25 + flow75) / 2 + 0.06 * metrics.pef),
        fontsize=9,
        color="#ff7f0e",
        ha="center",
    )

    ax.set_xlabel("Volume (L)")
    ax.set_ylabel("Flow (L/s)")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
