#!/usr/bin/env python3
"""Beta 2.4 two-zone uncertainty campaign and single-zone reconciliation."""
from __future__ import annotations

from dataclasses import asdict
import argparse
import json
import math
from pathlib import Path
from typing import Any

from boost_system_screen import boost_metrics
from mechanical_screen import mechanical_metrics
from microengine_rig import RigConfig, simulate, write_csv
from two_zone_model import TwoZoneOptions, simulate_two_zone


PROFILES = {
    "skeletal_39": ("dme_zhao_sk39", "CH4"),
    "llnl_79": ("dme_llnl_2004", "ch4"),
}

ANCHORS = {
    "shared": (0.40, 2.30),
    "lower_overlap": (0.35, 2.60),
    "mechanism_divergent": (0.35, 3.00),
}


def _single_branch(summary: dict[str, Any]) -> str:
    if summary["gross_imep_bar"] <= 0:
        return "no_positive_gross_work"
    if summary["max_pressure_rise_bar_per_deg"] > 10.0:
        return "rapid_heat_release"
    temperature = summary["peak_temperature_K"]
    conversion = summary["max_fuel_consumed_fraction"]
    ca50 = summary["CA50_deg_atdc"]
    if temperature < 1300.0 and 0.10 <= conversion < 0.90:
        if ca50 is not None and -15.0 <= ca50 <= 20.0:
            return "cool_partial_candidate"
        return "cool_partial_outside_phase_window"
    if temperature < 1600.0:
        return "intermediate_temperature"
    return "hot_combustion"


def _config(mechanism_label: str, anchor: str, clearance_um: float,
            eccentricity: float, step_deg: float) -> RigConfig:
    profile, partner = PROFILES[mechanism_label]
    phi, boost = ANCHORS[anchor]
    return RigConfig(
        bore_mm=8.5, stroke_mm=7.0, compression_ratio=7.0, rpm=1200.0,
        fuel_profile=profile, fuel_blend_partner=partner,
        fuel_primary_mole_fraction=0.25, equivalence_ratio=phi,
        intake_pressure_bar=boost, intake_temperature_K=300.0,
        wall_mode="fixed", wall_temperature_K=560.0,
        effective_h_W_m2K=300.0, blowby_mode="annular",
        annular_radial_clearance_um=clearance_um,
        annular_skirt_length_mm=8.0,
        annular_eccentricity_ratio=eccentricity,
        step_deg=step_deg,
    )


def _case(suite: str, mechanism_label: str, anchor: str,
          clearance_um: float, eccentricity: float,
          boundary_fraction: float, mixing_time_ms: float,
          equalization_coeff: float, step_deg: float) -> dict[str, Any]:
    config = _config(mechanism_label, anchor, clearance_um, eccentricity, step_deg)
    row: dict[str, Any] = {
        "suite": suite,
        "mechanism_label": mechanism_label,
        "anchor": anchor,
        "equivalence_ratio": config.equivalence_ratio,
        "intake_pressure_bar": config.intake_pressure_bar,
        "annular_radial_clearance_um": clearance_um,
        "annular_eccentricity_ratio": eccentricity,
        "boundary_mass_fraction": boundary_fraction,
        "mixing_time_ms": mixing_time_ms,
        "pressure_equalization_coeff_m_s_Pa": equalization_coeff,
        "step_deg": step_deg,
    }
    candidate_coefficients = [equalization_coeff]
    if suite != "pressure_coupling_sensitivity":
        candidate_coefficients.extend(
            value for value in (7.0e-5, 1.0e-4, 3.0e-5)
            if not math.isclose(value, equalization_coeff)
        )
    two = None
    best_pressure_difference = float("inf")
    last_error: Exception | None = None
    used_coefficient = equalization_coeff
    attempts = 0
    for candidate in candidate_coefficients:
        attempts += 1
        options = TwoZoneOptions(
            boundary_mass_fraction=boundary_fraction,
            mixing_time_ms=mixing_time_ms,
            pressure_equalization_coeff_m_s_Pa=candidate,
        )
        try:
            _, candidate_summary = simulate_two_zone(config, options)
        except Exception as exc:
            last_error = exc
            continue
        pressure_difference = candidate_summary["max_interzone_pressure_difference_bar"]
        if pressure_difference < best_pressure_difference:
            two = candidate_summary
            used_coefficient = candidate
            best_pressure_difference = pressure_difference
        # Retry only pressure-coupling failures; other acceptance criteria are
        # unaffected by making the internal wall stiffer.
        if pressure_difference <= 0.10:
            two = candidate_summary
            used_coefficient = candidate
            break
    if two is None:
        exc = last_error or RuntimeError("No pressure-coupling attempt completed.")
        row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        return row
    _, single = simulate(config)

    valid = (
        two["max_interzone_pressure_difference_bar"] <= 0.10
        and two["max_volume_closure_error_mm3"] <= 0.20
        and abs(two["mass_balance_residual_mg"]) <= 1.0e-3
        and all(
            abs(value) <= 1.0e-3
            for key, value in two.items()
            if key.endswith("_mass_balance_residual_mg")
        )
    )
    boost = boost_metrics(
        initial_trapped_mass_mg_per_cylinder=two["initial_trapped_mass_mg"],
        intake_pressure_bar=config.intake_pressure_bar,
        intake_temperature_K=config.intake_temperature_K,
        rpm=config.rpm,
        cycle_revolutions=config.cycle_revolutions,
    )
    mechanics = mechanical_metrics(
        peak_pressure_bar=two["peak_pressure_bar"],
        peak_temperature_K=two["peak_temperature_K"],
        max_pressure_rise_bar_per_deg=two["max_pressure_rise_bar_per_deg"],
        peak_pressure_deg_atdc=two["peak_pressure_deg_atdc"],
        bore_mm=config.bore_mm, stroke_mm=config.stroke_mm,
        rod_stroke_ratio=config.rod_stroke_ratio, rpm=config.rpm,
        crankcase_pressure_bar=config.crankcase_pressure_bar,
    )
    two_v6 = 6.0 * two["gross_indicated_power_W_per_cylinder"]
    single_v6 = 6.0 * single["gross_indicated_power_W_per_cylinder"]
    row.update({
        "status": "ok" if valid else "numerical_invalid",
        "error": "",
        "pressure_equalization_coeff_used_m_s_Pa": used_coefficient,
        "pressure_equalization_attempts": attempts,
        **{f"two_{key}": value for key, value in two.items()
           if not isinstance(value, (dict, list))},
        "single_branch": _single_branch(single),
        "single_gross_imep_bar": single["gross_imep_bar"],
        "single_peak_pressure_bar": single["peak_pressure_bar"],
        "single_peak_temperature_K": single["peak_temperature_K"],
        "single_max_pressure_rise_bar_per_deg": single[
            "max_pressure_rise_bar_per_deg"
        ],
        "single_max_fuel_consumed_fraction": single[
            "max_fuel_consumed_fraction"
        ],
        "single_CA50_deg_atdc": single["CA50_deg_atdc"],
        "two_minus_single_imep_bar": (
            two["gross_imep_bar"] - single["gross_imep_bar"]
        ),
        "two_minus_single_fuel_consumed_fraction": (
            two["max_fuel_consumed_fraction"]
            - single["max_fuel_consumed_fraction"]
        ),
        "two_zone_v6_gross_indicated_power_W": two_v6,
        "single_zone_v6_gross_indicated_power_W": single_v6,
        "compressor_electrical_power_W": boost[
            "estimated_compressor_electrical_power_W"
        ],
        "two_zone_power_proxy_W": (
            two_v6 - boost["estimated_compressor_electrical_power_W"]
        ),
        "single_zone_power_proxy_W": (
            single_v6 - boost["estimated_compressor_electrical_power_W"]
        ),
        **{f"mechanical_{key}": value for key, value in mechanics.items()
           if not isinstance(value, (dict, list))},
    })
    return row


def _build_cases(step_deg: float) -> list[tuple[Any, ...]]:
    cases: list[tuple[Any, ...]] = []
    # Direct test of the three Beta 2.3 anchors versus clearance and eccentricity.
    for mechanism in PROFILES:
        for anchor in ANCHORS:
            for clearance in (2.0, 3.0, 5.0):
                for eccentricity in (0.0, 0.5):
                    cases.append((
                        "anchor_clearance_eccentricity", mechanism, anchor,
                        clearance, eccentricity, 0.20, 10.0, 5.0e-5, step_deg,
                    ))
    # Bracket uncertain boundary-zone mass and inter-zone mixing at shared point.
    for mechanism in PROFILES:
        for boundary_fraction in (0.10, 0.20, 0.30):
            for mixing_time in (0.0, 5.0, 10.0, 20.0):
                cases.append((
                    "zone_mixing_sensitivity", mechanism, "shared",
                    3.0, 0.0, boundary_fraction, mixing_time,
                    5.0e-5, step_deg,
                ))
    # Numerical convergence of the pressure-equalizing interface.
    for mechanism in PROFILES:
        for coefficient in (3.0e-5, 5.0e-5, 7.0e-5):
            cases.append((
                "pressure_coupling_sensitivity", mechanism, "shared",
                3.0, 0.0, 0.20, 10.0, coefficient, step_deg,
            ))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--step-deg", type=float, default=0.125)
    args = parser.parse_args()
    cases = _build_cases(args.step_deg)
    if args.jobs == 1:
        results = [_case(*case) for case in cases]
    else:
        from joblib import Parallel, delayed
        results = Parallel(n_jobs=args.jobs, backend="loky")(
            delayed(_case)(*case) for case in cases
        )
    for run_id, row in enumerate(results, 1):
        row["run_id"] = run_id
    write_csv("two_zone_campaign.csv", results)

    traces = {}
    for mechanism_label in PROFILES:
        for anchor in ANCHORS:
            config = _config(mechanism_label, anchor, 3.0, 0.0, 0.0625)
            options = TwoZoneOptions(
                boundary_mass_fraction=0.20, mixing_time_ms=10.0,
                pressure_equalization_coeff_m_s_Pa=5.0e-5,
            )
            trace, summary = simulate_two_zone(config, options)
            name = f"two_zone_trace_{mechanism_label}_{anchor}.csv"
            write_csv(name, trace)
            traces[f"{mechanism_label}:{anchor}"] = {
                "trace": name,
                "summary": summary,
            }

    valid = [row for row in results if row["status"] == "ok"]
    report = {
        "status": "experimental two-zone spatial-uncertainty bracket",
        "runs": len(results),
        "valid_runs": len(valid),
        "errors": [row for row in results if row["status"] != "ok"],
        "campaign_definition": {
            "anchors": ANCHORS,
            "profiles": PROFILES,
            "step_deg": args.step_deg,
            "cases": len(cases),
        },
        "numerical_acceptance": {
            "max_interzone_pressure_difference_bar": 0.10,
            "max_volume_closure_error_mm3": 0.20,
            "max_mass_balance_residual_mg": 1.0e-3,
        },
        "traces": traces,
        "model_limit": (
            "Two homogeneous reactors with prescribed interface, wall-zone mass, "
            "mixing, and leakage allocation. This is not a resolved boundary layer, "
            "flame model, turbulence model, or CFD validation."
        ),
    }
    Path("two_zone_results.json").write_text(
        json.dumps(report, indent=2, allow_nan=True), encoding="utf-8"
    )
    print(json.dumps({
        "runs": len(results),
        "valid": len(valid),
        "invalid_or_error": len(results) - len(valid),
        "csv": "two_zone_campaign.csv",
        "json": "two_zone_results.json",
    }, indent=2))


if __name__ == "__main__":
    main()
