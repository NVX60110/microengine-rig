#!/usr/bin/env python3
"""Recompute CFD-01 answer-level diagnostics from stored scalar histories.

Pure stdlib so it can run in CI or WSL without NumPy/Pandas.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "cfd" / "results"
TARGETS = (-90.0, -20.0, 0.0, 20.0, 45.0, 90.0)
MESHES = ("coarse", "medium", "fine")


def load_history(mesh: str):
    path = RESULTS / f"cfd01_scalar_history_{mesh}.csv"
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            row = {
                k: float(v) if v not in ("", "nan", "NaN") else math.nan
                for k, v in raw.items()
            }
            rows.append(row)
    return rows


def nearest(rows, target):
    return min(rows, key=lambda r: abs(r["crank_angle_deg_atdc"] - target))


def finite(x):
    return math.isfinite(x)


def main():
    histories = {mesh: load_history(mesh) for mesh in MESHES}

    points = {}
    for target in TARGETS:
        key = f"{target:+.0f}"
        points[key] = {}
        for mesh, rows in histories.items():
            r = nearest(rows, target)
            points[key][mesh] = {
                "sampled_cad": r["crank_angle_deg_atdc"],
                "delta_c": r["delta_c"],
                "k_mix_1_s": r["k_mix_1_s"],
                "tau_mix_ms": r["tau_mix_ms"],
                "volume_error_percent": r["volume_error_percent"],
                "wall_volume_fraction": (
                    r["wall_shell_volume_mm3"] / r["total_volume_mm3"]
                    if r["total_volume_mm3"]
                    else math.nan
                ),
            }

        c = points[key]["coarse"]["tau_mix_ms"]
        m = points[key]["medium"]["tau_mix_ms"]
        f = points[key]["fine"]["tau_mix_ms"]
        points[key]["coarse_over_fine_tau"] = (
            c / f if finite(c) and finite(f) and f else math.nan
        )
        points[key]["medium_over_fine_tau"] = (
            m / f if finite(m) and finite(f) and f else math.nan
        )

    fine = histories["fine"]
    increases = 0
    max_increase = 0.0
    for a, b in zip(fine, fine[1:]):
        d = b["delta_c"] - a["delta_c"]
        if d > 0:
            increases += 1
            max_increase = max(max_increase, d)

    wall_fracs = [
        r["wall_shell_volume_mm3"] / r["total_volume_mm3"]
        for r in fine
        if r["total_volume_mm3"]
    ]
    volume_errors = [abs(r["volume_error_percent"]) for r in fine]

    out = {
        "targets": points,
        "fine_history": {
            "rows": len(fine),
            "delta_c_positive_step_count": increases,
            "max_positive_delta_c_step": max_increase,
            "delta_c_start": fine[0]["delta_c"],
            "delta_c_end": fine[-1]["delta_c"],
            "wall_volume_fraction_min": min(wall_fracs),
            "wall_volume_fraction_max": max(wall_fracs),
            "max_abs_volume_error_percent": max(volume_errors),
        },
        "interpretation": {
            "tdc_mesh_gate": "pass if coarse/fine and medium/fine are within the predeclared tolerance",
            "plus45": "do not promote if tau continues to increase materially with refinement",
            "plus90": "inspect delta_c directly before interpreting a noisy differentiated local k_mix",
            "mass_conservation": "not evaluated by this scalar-history audit; add a separate closed-domain mass diagnostic",
        },
    }

    print(json.dumps(out, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
