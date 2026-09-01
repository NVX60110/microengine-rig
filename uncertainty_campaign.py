#!/usr/bin/env python3
"""Beta 2.6 mechanism x mixing x sealing robustness campaign."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from dataclasses import asdict
import itertools
import json
from pathlib import Path
from typing import Any

from microengine_rig import RigConfig, apply_config_patch
from sealing_prior import SealingCase, sealing_cases
from two_zone_model import TwoZoneOptions, simulate_two_zone


MECHANISMS = ("dme_zhao_sk39", "dme_zhao_full", "dme_llnl_2004")


def mixing_cases() -> dict[str, TwoZoneOptions]:
    common = dict(
        boundary_mass_fraction=0.20,
        interzone_heat_transfer_coeff_W_m2K=100.0,
        mixing_model="diffusion-strain",
        mixing_min_time_ms=0.10,
        mixing_max_time_ms=100.0,
    )
    return {
        "slow": TwoZoneOptions(
            **common, mixing_length_mm=1.5, molecular_diffusivity_m2_s=1.0e-6,
            piston_strain_coefficient=0.10,
        ),
        "central": TwoZoneOptions(
            **common, mixing_length_mm=1.0, molecular_diffusivity_m2_s=3.0e-6,
            piston_strain_coefficient=1.0,
        ),
        "fast": TwoZoneOptions(
            **common, mixing_length_mm=0.5, molecular_diffusivity_m2_s=8.0e-6,
            piston_strain_coefficient=2.0,
        ),
    }


def base_config() -> RigConfig:
    return RigConfig(
        bore_mm=8.5, stroke_mm=7.0, rod_stroke_ratio=1.6,
        compression_ratio=7.75, rpm=1200.0,
        intake_pressure_bar=3.0, intake_temperature_K=300.0,
        equivalence_ratio=0.40, wall_mode="fixed", wall_temperature_K=560.0,
        effective_h_W_m2K=300.0, ignition_mode="cantera-auto",
        fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
        fuel_primary_mole_fraction=0.25, crankcase_pressure_bar=1.0,
        crankcase_temperature_K=350.0, step_deg=0.25,
    )


def acceptable(summary: dict[str, Any]) -> bool:
    """Conservative display-engine operability screen, not a strength limit."""
    ca50 = summary.get("CA50_deg_atdc")
    return bool(
        summary["gross_imep_bar"] > 0
        and 0.10 <= summary["max_fuel_consumed_fraction"] < 0.90
        and summary["peak_temperature_K"] < 1600.0
        and summary["max_pressure_rise_bar_per_deg"] <= 10.0
        and ca50 is not None and -15.0 <= ca50 <= 20.0
    )


def _one(job: dict[str, Any]) -> dict[str, Any]:
    try:
        cfg = apply_config_patch(base_config(), job["config_patch"])
        options = TwoZoneOptions(**job["zone_options"])
        retry_step = None
        try:
            _, summary = simulate_two_zone(cfg, options)
        except Exception as first_exc:
            # Stiff LLNL transition cases can exhaust CVODE's internal-step
            # ceiling between coarse output points. Retry once at twice the
            # crank-angle resolution and preserve that fact in the result.
            if cfg.step_deg <= 0.125 or "Maximum number of timesteps" not in str(first_exc):
                raise
            retry_step = 0.125
            cfg = apply_config_patch(cfg, {"step_deg": retry_step})
            _, summary = simulate_two_zone(cfg, options)
        return {
            **job["identity"], "status": "ok", "error": "",
            "retry_step_deg": retry_step,
            "acceptable": acceptable(summary), **summary,
        }
    except Exception as exc:  # recorded per case; aggregate refuses clean nulls
        return {
            **job["identity"], "status": "error",
            "error": f"{type(exc).__name__}: {exc}", "acceptable": False,
        }


def _selected_seals(scope: str) -> tuple[SealingCase, ...]:
    cases = sealing_cases()
    if scope == "full":
        return cases
    names = {
        "sealed_reference", "annular_3um_e05",
        "annular_5um_e05", "ringpack_area_0p006",
    }
    return tuple(case for case in cases if case.name in names)


def jobs(scope: str) -> list[dict[str, Any]]:
    cr_values = (7.5, 7.75, 8.0, 8.25) if scope == "full" else (7.75, 8.0)
    boosts = (2.3, 3.0) if scope == "full" else (3.0,)
    result = []
    for mechanism, cr, boost, seal, (mix_name, options) in itertools.product(
        MECHANISMS, cr_values, boosts, _selected_seals(scope), mixing_cases().items()
    ):
        patch = {
            "fuel_profile": mechanism,
            "compression_ratio": cr,
            "intake_pressure_bar": boost,
            **seal.config_patch,
        }
        result.append({
            "identity": {
                "mechanism_case": mechanism, "compression_ratio": cr,
                "intake_pressure_bar": boost, "sealing_case": seal.name,
                "sealing_model_class": seal.model_class, "mixing_case": mix_name,
            },
            "config_patch": patch,
            "zone_options": asdict(options),
        })
    return result


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[float, float], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(
            (row["compression_ratio"], row["intake_pressure_bar"]), []
        ).append(row)
    output = []
    for (cr, boost), group in sorted(grouped.items()):
        good = [row for row in group if row["status"] == "ok"]
        output.append({
            "compression_ratio": cr,
            "intake_pressure_bar": boost,
            "cases_expected": len(group),
            "cases_completed": len(good),
            "acceptable_fraction": (
                sum(bool(row["acceptable"]) for row in good) / len(good) if good else 0.0
            ),
            "robust_all_cases": bool(good) and len(good) == len(group)
            and all(row["acceptable"] for row in good),
            "branch_set": sorted({row["branch"] for row in good}),
            "imep_min_bar": min((row["gross_imep_bar"] for row in good), default=None),
            "imep_max_bar": max((row["gross_imep_bar"] for row in good), default=None),
            "peak_temperature_max_K": max(
                (row["peak_temperature_K"] for row in good), default=None
            ),
            "pressure_rise_max_bar_per_deg": max(
                (row["max_pressure_rise_bar_per_deg"] for row in good), default=None
            ),
            "mass_retention_min": min(
                (row["mass_retained_end_fraction"] for row in good), default=None
            ),
        })
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("pilot", "full"), default="pilot")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out-prefix", default="beta26_uncertainty")
    args = parser.parse_args()
    work = jobs(args.scope)
    if args.jobs <= 1:
        rows = [_one(item) for item in work]
    else:
        rows = []
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(_one, item) for item in work]
            for future in as_completed(futures):
                rows.append(future.result())
        rows.sort(key=lambda row: (
            row["compression_ratio"], row["intake_pressure_bar"],
            row["mechanism_case"], row["sealing_case"], row["mixing_case"],
        ))
    summary = aggregate(rows)
    prefix = Path(args.out_prefix)
    write_csv(prefix.with_suffix(".csv"), rows)
    write_csv(prefix.with_name(prefix.name + "_summary.csv"), summary)
    payload = {
        "scope": args.scope, "case_count": len(rows),
        "null_or_error_count": sum(row["status"] != "ok" for row in rows),
        "robust_points": [row for row in summary if row["robust_all_cases"]],
        "summary": summary, "rows": rows,
    }
    prefix.with_suffix(".json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({key: payload[key] for key in (
        "scope", "case_count", "null_or_error_count", "robust_points"
    )}, indent=2))


if __name__ == "__main__":
    main()
