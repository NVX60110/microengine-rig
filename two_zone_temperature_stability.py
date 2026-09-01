#!/usr/bin/env python3
"""Push the Beta 2.4 core through 1000 K and test branch continuity.

This directly tests whether the cool partial branch survives beyond the core
temperature range where it was first observed. Compression ratio is used as
the forcing variable at two intake pressures. Mixing and boundary-zone inputs
remain prescribed uncertainty parameters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import csv
import json

import cantera as ct

from microengine_rig import RigConfig
from two_zone_model import TwoZoneOptions, simulate_two_zone


PROFILES = {
    "zhao_sk39": ("dme_zhao_sk39", "CH4"),
    "zhao_full55": ("dme_zhao_full", "CH4"),
    "llnl79": ("dme_llnl_2004", "ch4"),
}


def _case(profile_label: str, compression_ratio: float, intake_pressure_bar: float,
          step_deg: float) -> dict[str, Any]:
    profile, partner = PROFILES[profile_label]
    config = RigConfig(
        bore_mm=8.5, stroke_mm=7.0, compression_ratio=compression_ratio,
        rpm=1200.0, fuel_profile=profile, fuel_blend_partner=partner,
        fuel_primary_mole_fraction=0.25, equivalence_ratio=0.40,
        intake_pressure_bar=intake_pressure_bar, intake_temperature_K=300.0,
        wall_mode="fixed", wall_temperature_K=560.0,
        effective_h_W_m2K=300.0, blowby_mode="annular",
        annular_radial_clearance_um=3.0, annular_skirt_length_mm=8.0,
        annular_eccentricity_ratio=0.0, step_deg=step_deg,
    )
    options = TwoZoneOptions(
        boundary_mass_fraction=0.20, mixing_time_ms=10.0,
        interzone_heat_transfer_coeff_W_m2K=100.0,
        pressure_equalization_coeff_m_s_Pa=7.0e-5,
    )
    base = {
        "profile": profile_label,
        "compression_ratio": compression_ratio,
        "intake_pressure_bar": intake_pressure_bar,
        "step_deg": step_deg,
        "boundary_mass_fraction": options.boundary_mass_fraction,
        "mixing_time_ms": options.mixing_time_ms,
        "interzone_heat_transfer_coeff_W_m2K": (
            options.interzone_heat_transfer_coeff_W_m2K
        ),
    }
    try:
        _, summary = simulate_two_zone(config, options)
    except (ct.CanteraError, RuntimeError, ValueError) as exc:
        return {**base, "status": "solver_error",
                "error": f"{type(exc).__name__}: {exc}"}
    valid = (
        summary["max_interzone_pressure_difference_bar"] <= 0.10
        and summary["max_volume_closure_error_mm3"] <= 0.20
        and abs(summary["mass_balance_residual_mg"]) <= 1e-3
        and all(
            abs(value) <= 1e-3
            for key, value in summary.items()
            if key.endswith("_mass_balance_residual_mg")
        )
    )
    return {
        **base,
        "status": "ok" if valid else "numerical_invalid",
        "error": "",
        **{key: value for key, value in summary.items()
           if not isinstance(value, (list, dict))},
    }


def _transition_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for profile in PROFILES:
        for pressure in sorted({row["intake_pressure_bar"] for row in rows}):
            series = sorted(
                (row for row in rows if row["profile"] == profile
                 and row["intake_pressure_bar"] == pressure and row["status"] == "ok"),
                key=lambda row: row["compression_ratio"],
            )
            first_hot = next(
                (row for row in series if row["peak_core_temperature_K"] >= 1000.0),
                None,
            )
            transitions.append({
                "profile": profile,
                "intake_pressure_bar": pressure,
                "first_sample_at_or_above_1000K_CR": (
                    first_hot["compression_ratio"] if first_hot else None
                ),
                "branch_at_first_hot_sample": (
                    first_hot["branch"] if first_hot else None
                ),
                "conversion_at_first_hot_sample": (
                    first_hot["max_fuel_consumed_fraction"] if first_hot else None
                ),
                "max_pressure_rise_at_first_hot_sample": (
                    first_hot["max_pressure_rise_bar_per_deg"] if first_hot else None
                ),
            })
    return transitions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compression-ratios", default="7,8,9,10,11,12,13")
    parser.add_argument("--intake-pressures-bar", default="2.3,3.0")
    parser.add_argument("--step-deg", type=float, default=0.25)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--csv", default="two_zone_temperature_stability.csv")
    parser.add_argument("--json", default="two_zone_temperature_stability.json")
    args = parser.parse_args()
    compression_ratios = [float(value) for value in args.compression_ratios.split(",")]
    pressures = [float(value) for value in args.intake_pressures_bar.split(",")]
    cases = [
        (profile, ratio, pressure, args.step_deg)
        for profile in PROFILES
        for pressure in pressures
        for ratio in compression_ratios
    ]
    if args.jobs == 1:
        rows = [_case(*case) for case in cases]
    else:
        from joblib import Parallel, delayed
        rows = Parallel(n_jobs=args.jobs, backend="loky")(
            delayed(_case)(*case) for case in cases
        )
    with open(args.csv, "w", newline="", encoding="utf-8") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "conditions": {
            "geometry_mm": "8.5 bore x 7.0 stroke",
            "rpm": 1200.0,
            "fuel": "25/75 mol% DME/methane",
            "equivalence_ratio": 0.40,
            "wall_temperature_K": 560.0,
            "annular_clearance_um": 3.0,
            "boundary_mass_fraction": 0.20,
            "mixing_time_ms": 10.0,
            "compression_ratios": compression_ratios,
            "intake_pressures_bar": pressures,
        },
        "transitions": _transition_summary(rows),
        "rows": rows,
        "warning": (
            "This tests one prescribed two-zone closure. A branch transition is "
            "model evidence, not a measured stability boundary."
        ),
    }
    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(rows), "transitions": report["transitions"]}, indent=2))


if __name__ == "__main__":
    main()
