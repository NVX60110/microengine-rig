#!/usr/bin/env python3
"""Fit CFD-01 tracer decay to the TwoZoneOptions diffusion-strain closure."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


BORE_M = 0.0085
STROKE_M = 0.007
ROD_M = 1.6 * STROKE_M
CRANK_M = STROKE_M / 2.0
RPM = 1200.0
OMEGA = 2.0 * math.pi * RPM / 60.0


def piston_speed(angle_deg: float) -> float:
    theta = math.radians(angle_deg)
    root = math.sqrt(ROD_M**2 - CRANK_M**2 * math.sin(theta) ** 2)
    derivative = CRANK_M * math.sin(theta) + CRANK_M**2 * math.sin(theta) * math.cos(theta) / root
    return derivative * OMEGA


def fit(rows: list[dict[str, str]], mixing_length_m: float) -> dict[str, object]:
    samples = []
    for row in rows:
        try:
            k = float(row["k_mix_1_s"])
            angle = float(row["crank_angle_deg_atdc"])
        except (KeyError, ValueError):
            continue
        if math.isfinite(k) and k > 0:
            samples.append((abs(piston_speed(angle)) / BORE_M, k))
    if len(samples) < 3:
        raise ValueError("need at least three positive finite k_mix samples")
    sx = sum(x for x, _ in samples)
    sy = sum(y for _, y in samples)
    sxx = sum(x * x for x, _ in samples)
    sxy = sum(x * y for x, y in samples)
    denominator = len(samples) * sxx - sx * sx
    if denominator <= 0:
        raise ValueError("piston-strain regressor has zero variance")
    unconstrained_strain = (len(samples) * sxy - sx * sy) / denominator
    # TwoZoneOptions rejects a negative piston-strain coefficient.  A negative
    # unconstrained slope means this closed-cylinder baseline does not resolve
    # a positive strain contribution over the selected cycle; use the bounded
    # physical fit (Cs >= 0) and retain the mean rate in the diffusion term.
    strain_coefficient = max(0.0, unconstrained_strain)
    diffusion_rate = max(0.0, (sy - strain_coefficient * sx) / len(samples))
    diffusivity = diffusion_rate * mixing_length_m**2 / math.pi**2
    taus = [1000.0 / k for _, k in samples]
    return {
        "fit_model": "k_mix = pi^2 D/L^2 + C_s abs(u_p)/B",
        "source": "CFD-01 fine passive-tracer history",
        "sample_count": len(samples),
        "mixing_length_mm": mixing_length_m * 1000.0,
        "molecular_diffusivity_m2_s": diffusivity,
        "piston_strain_coefficient": strain_coefficient,
        "mixing_min_time_ms": min(taus),
        "mixing_max_time_ms": max(taus),
        "TwoZoneOptions": {
            "mixing_model": "diffusion-strain",
            "mixing_length_mm": mixing_length_m * 1000.0,
            "molecular_diffusivity_m2_s": diffusivity,
            "piston_strain_coefficient": strain_coefficient,
            "mixing_min_time_ms": min(taus),
            "mixing_max_time_ms": max(taus),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("history", type=Path)
    parser.add_argument("--mixing-length-mm", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.history.open(newline="") as handle:
        payload = fit(list(csv.DictReader(handle)), args.mixing_length_mm / 1000.0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["TwoZoneOptions"], indent=2))


if __name__ == "__main__":
    main()
