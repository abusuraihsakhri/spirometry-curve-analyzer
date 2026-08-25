#!/usr/bin/env python
"""Generate synthetic flow-time spirometry CSVs for demonstration/testing.

Models a forced expiration as a single-exponential volume approach to FVC:

    V(t) = FVC * (1 - exp(-k * t))

so that FEV1 = V(1) is controlled exactly by choosing
k = -ln(1 - FEV1/FVC), and flow = dV/dt = FVC * k * exp(-k * t), giving
PEF = FVC * k at t = 0. This is a simplified but genuine closed-form model
useful for generating waveforms with known ground-truth FVC/FEV1/PEF.
"""
import csv
import math
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def generate(path, fvc, fev1, duration=8.0, n=1600):
    k = -math.log(1 - fev1 / fvc)
    dt = duration / (n - 1)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "flow_Lps"])
        for i in range(n):
            t = i * dt
            flow = fvc * k * math.exp(-k * t)
            writer.writerow([f"{t:.4f}", f"{flow:.5f}"])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # Healthy adult male, 42y, 178cm: FVC 5.10L, FEV1 4.20L (ratio 0.82)
    generate(os.path.join(OUT_DIR, "normal_male_42y.csv"), fvc=5.10, fev1=4.20)
    # Obstructive pattern: FVC preserved-ish, FEV1 markedly reduced (ratio 0.55)
    generate(os.path.join(OUT_DIR, "obstructive_male_60y.csv"), fvc=4.60, fev1=2.53)
    # Restrictive pattern suggested: both FVC and FEV1 reduced, ratio preserved (0.85)
    generate(os.path.join(OUT_DIR, "restrictive_female_50y.csv"), fvc=2.40, fev1=2.04)
    print(f"Wrote sample CSVs to {os.path.abspath(OUT_DIR)}")


if __name__ == "__main__":
    main()
