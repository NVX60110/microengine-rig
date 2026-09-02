#!/usr/bin/env python3
"""Compare geometry-independent tracer mixing between two CFD histories.

Use only after both histories were regenerated with the current
postprocess_history.py so the mass-weighted RMS fields are available.

For cross-geometry transport, the primary amplitude metric is each case's
mass-weighted tracer RMS normalized by its own initial RMS.  This removes the
trivial initial-amplitude offset created when the same radial tracer seed
occupies a different mass/volume fraction in a changed chamber geometry.
Raw RMS is retained as a secondary physical-amplitude diagnostic.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

DEFAULT_TARGETS = (-20.0, 0.0, 20.0)
MAX_TRACER_INVENTORY_DRIFT_REL = 1e-4


def load(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row = {
                key: float(value) if value not in ("", "nan", "NaN") else math.nan
                for key, value in raw.items()
            }
            rows.append(row)
    required = {
        "crank_angle_deg_atdc",
        "time_s",
        "tracer_mass_rms",
        "tracer_mass_rms_normalized",
        "tracer_inventory_error_percent",
        "wall_shell_volume_fraction",
    }
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else {}))
        raise ValueError(f"{path} is not a current mixing-metric history; missing {missing}")
    return rows


def nearest(rows: list[dict[str, float]], target: float) -> dict[str, float]:
    return min(rows, key=lambda row: abs(row["crank_angle_deg_atdc"] - target))


def window_fit(rows: list[dict[str, float]], target: float, half_width_cad: float) -> dict[str, float]:
    chosen = [
        row for row in rows
        if abs(row["crank_angle_deg_atdc"] - target) <= half_width_cad
        and row["tracer_mass_rms_normalized"] > 0
        and math.isfinite(row["tracer_mass_rms_normalized"])
    ]
    if len(chosen) < 3:
        return {"n": len(chosen), "k_1_s": math.nan, "tau_ms": math.nan, "r2": math.nan}

    xs = [row["time_s"] for row in chosen]
    ys = [math.log(row["tracer_mass_rms_normalized"]) for row in chosen]
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    sxx = sum((x - xbar) ** 2 for x in xs)
    if sxx <= 0:
        return {"n": len(chosen), "k_1_s": math.nan, "tau_ms": math.nan, "r2": math.nan}
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
    intercept = ybar - slope * xbar
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    total = sum((y - ybar) ** 2 for y in ys)
    r2 = 1.0 - residual / total if total > 0 else 1.0
    k = -slope
    tau = 1000.0 / k if k > 0 else math.nan
    return {"n": len(chosen), "k_1_s": k, "tau_ms": tau, "r2": r2}


def summarize(rows: list[dict[str, float]], target: float, window: float) -> dict[str, float]:
    point = nearest(rows, target)
    fit = window_fit(rows, target, window)
    return {
        "sampled_cad": point["crank_angle_deg_atdc"],
        "rms": point["tracer_mass_rms"],
        "rms_normalized": point["tracer_mass_rms_normalized"],
        "global_tau_point_ms": point.get("tau_global_mix_ms", math.nan),
        "shell_volume_fraction": point["wall_shell_volume_fraction"],
        "tracer_inventory_error_percent": point["tracer_inventory_error_percent"],
        "fit_n": fit["n"],
        "fit_k_1_s": fit["k_1_s"],
        "fit_tau_ms": fit["tau_ms"],
        "fit_r2": fit["r2"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path, help="flat-piston history")
    parser.add_argument("candidate", type=Path, help="squish/candidate history")
    parser.add_argument("--targets", nargs="+", type=float, default=list(DEFAULT_TARGETS))
    parser.add_argument("--window-cad", type=float, default=5.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    reference = load(args.reference)
    candidate = load(args.candidate)
    ref_initial_rms = reference[0]["tracer_mass_rms"]
    cand_initial_rms = candidate[0]["tracer_mass_rms"]
    initial_rms_ratio = (
        cand_initial_rms / ref_initial_rms if ref_initial_rms > 0 else math.nan
    )
    reference_max_inventory = max(
        abs(r["tracer_inventory_error_percent"]) for r in reference
    )
    candidate_max_inventory = max(
        abs(r["tracer_inventory_error_percent"]) for r in candidate
    )
    inventory_gate_percent = 100.0 * MAX_TRACER_INVENTORY_DRIFT_REL
    gate_failures = []
    if reference_max_inventory > inventory_gate_percent:
        gate_failures.append("reference tracer inventory gate failed")
    if candidate_max_inventory > inventory_gate_percent:
        gate_failures.append("candidate tracer inventory gate failed")

    result: dict[str, object] = {
        "reference": str(args.reference),
        "candidate": str(args.candidate),
        "window_half_width_cad": args.window_cad,
        "primary_metric": "candidate_over_reference_normalized_rms",
        "primary_metric_reason": (
            "each case starts from a different raw tracer RMS when the fixed radial seed occupies "
            "a different chamber mass/volume fraction; normalize by each case's initial RMS before "
            "comparing the fraction of segregation remaining"
        ),
        "status": "ok" if not gate_failures else "gate_failed",
        "gate_failures": gate_failures,
        "tracer_inventory_gate_relative": MAX_TRACER_INVENTORY_DRIFT_REL,
        "targets": {},
        "global": {
            "reference_initial_rms": ref_initial_rms,
            "candidate_initial_rms": cand_initial_rms,
            "candidate_over_reference_initial_rms": initial_rms_ratio,
            "reference_shell_fraction_min": min(r["wall_shell_volume_fraction"] for r in reference),
            "reference_shell_fraction_max": max(r["wall_shell_volume_fraction"] for r in reference),
            "candidate_shell_fraction_min": min(r["wall_shell_volume_fraction"] for r in candidate),
            "candidate_shell_fraction_max": max(r["wall_shell_volume_fraction"] for r in candidate),
            "reference_max_tracer_inventory_error_percent": reference_max_inventory,
            "candidate_max_tracer_inventory_error_percent": candidate_max_inventory,
        },
    }

    targets = result["targets"]
    assert isinstance(targets, dict)
    for target in args.targets:
        ref = summarize(reference, target, args.window_cad)
        cand = summarize(candidate, target, args.window_cad)
        raw_rms_ratio = (
            cand["rms"] / ref["rms"]
            if ref["rms"] > 0 else math.nan
        )
        normalized_rms_ratio = (
            cand["rms_normalized"] / ref["rms_normalized"]
            if ref["rms_normalized"] > 0 else math.nan
        )
        targets[f"{target:+g}"] = {
            "reference": ref,
            "candidate": cand,
            "candidate_over_reference_rms": raw_rms_ratio,
            "candidate_over_reference_normalized_rms": normalized_rms_ratio,
            "interpretation": (
                "candidate has less initial-normalized segregation remaining"
                if math.isfinite(normalized_rms_ratio) and normalized_rms_ratio < 1.0
                else "candidate has more initial-normalized segregation remaining"
                if math.isfinite(normalized_rms_ratio) and normalized_rms_ratio > 1.0
                else "equal/undefined"
            ),
        }

    text = json.dumps(result, indent=2, allow_nan=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
