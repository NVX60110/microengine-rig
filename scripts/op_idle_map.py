#!/usr/bin/env python3
"""Bounded low-idle operating map for the accepted Beta 2.6 two-zone state.

This is deliberately a screening campaign.  It uses the existing central
diffusion/strain closure and 3 um/e=0.5 annular bracket as its reference and
does not infer a stable engine from positive gross work.  The model covers the
closed compression/expansion segment only; friction, pumping, gas exchange,
and cycle-to-cycle dynamics remain unresolved.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

# Allow the documented ``python scripts/op_idle_map.py`` invocation to resolve
# the repository's top-level model modules on every platform.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from microengine_rig import RigConfig
from two_zone_model import TwoZoneOptions, simulate_two_zone


RPM_GRID = (800.0, 1000.0, 1200.0, 1500.0, 2000.0, 3000.0, 5000.0, 7500.0, 10000.0)
MECHANISMS = ("dme_zhao_sk39", "dme_zhao_full", "dme_llnl_2004")
STRICT_STEP_DEG = 0.125


def base_config(**patch: Any) -> RigConfig:
    """Return the accepted Beta 2.6 DME/CH4 geometry and operating state."""
    values = dict(
        bore_mm=8.5, stroke_mm=7.0, rod_stroke_ratio=1.6,
        compression_ratio=7.75, rpm=1200.0,
        intake_pressure_bar=3.0, intake_temperature_K=300.0,
        equivalence_ratio=0.40, wall_mode="fixed", wall_temperature_K=560.0,
        effective_h_W_m2K=300.0, ignition_mode="cantera-auto",
        fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
        fuel_primary_mole_fraction=0.25, crankcase_pressure_bar=1.0,
        crankcase_temperature_K=350.0, blowby_mode="annular",
        annular_radial_clearance_um=3.0, annular_skirt_length_mm=8.0,
        annular_eccentricity_ratio=0.5, step_deg=STRICT_STEP_DEG,
    )
    values.update(patch)
    if values["step_deg"] > STRICT_STEP_DEG:
        raise ValueError("transition campaign requires step_deg <= 0.125 CAD")
    return RigConfig(**values)


def central_options() -> TwoZoneOptions:
    """Existing Beta 2.6 central mixing, with strict transition controls."""
    return TwoZoneOptions(
        boundary_mass_fraction=0.20,
        interzone_heat_transfer_coeff_W_m2K=100.0,
        mixing_model="diffusion-strain", mixing_length_mm=1.0,
        molecular_diffusivity_m2_s=3.0e-6, piston_strain_coefficient=1.0,
        mixing_min_time_ms=0.10, mixing_max_time_ms=100.0,
        integrator_rtol=1.0e-9, integrator_atol=1.0e-15,
    )


def _value(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    return None if value is None else float(value)


def classify(summary: dict[str, Any]) -> dict[str, Any]:
    """Apply transparent screening gates; stability is intentionally unresolved."""
    conversion = float(summary["max_fuel_consumed_fraction"])
    ca50 = _value(summary, "CA50_deg_atdc")
    gates = {
        "positive_gross_imep": float(summary["gross_imep_bar"]) > 0.0,
        "conversion_10_to_90pct": 0.10 <= conversion < 0.90,
        "peak_temperature_below_1600K": float(summary["peak_temperature_K"]) < 1600.0,
        "max_pressure_rise_at_most_10_bar_per_deg": float(summary["max_pressure_rise_bar_per_deg"]) <= 10.0,
        "CA50_in_minus15_to_plus20_CAD": ca50 is not None and -15.0 <= ca50 <= 20.0,
        "pressure_coupling_at_most_0p10_bar": float(summary["max_interzone_pressure_difference_bar"]) <= 0.10,
        # This is a Beta 2.6 necessary-condition screen, not a universal seal target.
        "end_mass_retention_at_least_0p87": float(summary["mass_retained_end_fraction"]) >= 0.87,
    }
    required = tuple(gates)
    passed = all(gates[name] for name in required)
    positive = gates["positive_gross_imep"]
    # Marginal means a positive-work case with one or more bounded screen misses;
    # implausible is no positive work or a severe reaction branch.
    severe = (
        conversion >= 0.90
        or float(summary["peak_temperature_K"]) >= 1600.0
        or float(summary["max_pressure_rise_bar_per_deg"]) > 10.0
    )
    if passed:
        screen_class = "robust"
    elif positive and not severe:
        screen_class = "marginal"
    else:
        screen_class = "implausible"

    # Ordered by the first physical mechanism that prevents promotion under the
    # existing gates.  A clean row has no demonstrated limiting mechanism.
    if not gates["positive_gross_imep"]:
        limiter = "nonpositive_gross_work"
    elif not gates["conversion_10_to_90pct"]:
        limiter = "low_or_over_conversion"
    elif not gates["peak_temperature_below_1600K"]:
        limiter = "high_temperature"
    elif not gates["max_pressure_rise_at_most_10_bar_per_deg"]:
        limiter = "rapid_heat_release"
    elif not gates["CA50_in_minus15_to_plus20_CAD"]:
        limiter = "phasing_outside_window"
    elif not gates["pressure_coupling_at_most_0p10_bar"]:
        limiter = "zone_pressure_coupling"
    elif not gates["end_mass_retention_at_least_0p87"]:
        limiter = "trapped_mass_loss"
    else:
        limiter = "none_within_screen"
    return {
        "screen_class": screen_class,
        "stable_idle_status": "unresolved",
        "limiting_mechanism": limiter,
        "gate_pass": passed,
        "gates": gates,
        "failed_gates": [name for name, ok in gates.items() if not ok],
        "classification_note": (
            "Robust/marginal/implausible are bounded reacting-screen labels only. "
            "Stable idle is unresolved because friction, pumping, 720-degree gas "
            "exchange and cycle-to-cycle variability are not modeled."
        ),
    }


def _trace_digest(rows: list[dict[str, Any]]) -> dict[str, float]:
    wanted = (-180.0, -90.0, -45.0, 0.0, 45.0, 90.0, 180.0)
    return {
        f"P_bar_at_{int(deg):+d}_CAD": float(min(rows, key=lambda row: abs(row["deg"] - deg))["effectivePressure_bar"])
        for deg in wanted
    }


def _elapsed_from_start(deg: float, rpm: float) -> float:
    """Elapsed seconds from modeled -180 CAD start (one 360 CAD segment)."""
    return (deg + 180.0) / 360.0 * (60.0 / rpm)


def _event_times(rows: list[dict[str, Any]], summary: dict[str, Any], rpm: float) -> dict[str, Any]:
    onset = next((row["deg"] for row in rows if float(row.get("fuelConsumedFraction", 0.0)) >= 0.01), None)
    out: dict[str, Any] = {
        "first_inventory_conversion_onset_1pct_deg_atdc": onset,
        "first_inventory_conversion_onset_1pct_elapsed_s": (
            _elapsed_from_start(float(onset), rpm) if onset is not None else None
        ),
        "CA10_elapsed_s": (
            _elapsed_from_start(float(summary["CA10_deg_atdc"]), rpm)
            if summary.get("CA10_deg_atdc") is not None else None
        ),
        "criterion": "global fuel inventory >= 1% for onset; CA10 from cumulative heat release",
    }
    for angle in (-40.0, -20.0, 0.0, 20.0, 40.0):
        out[f"elapsed_at_{int(angle):+d}_CAD_s"] = _elapsed_from_start(angle, rpm)
    return out


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    try:
        config = base_config(**job["config_patch"])
        options = central_options()
        rows, summary = simulate_two_zone(config, options)
        tdc = min(rows, key=lambda row: abs(row["deg"]))
        compression_start = rows[0]
        result = {
            "status": "ok", "error": "", **job["identity"],
            "config": asdict(config), "zone_options": asdict(options),
            "rpm": float(config.rpm),
            "revolution_period_s": 60.0 / config.rpm,
            "four_stroke_period_s": 120.0 / config.rpm,
            "modeled_compression_expansion_period_s": 60.0 / config.rpm,
            "transition_step_deg": float(config.step_deg),
            # This is the actual evolving state at TDC; ignition may already
            # have started, so it is not mislabeled as an unburned compression
            # state.
            "reacting_tdc_pressure_bar": float(tdc["effectivePressure_bar"]),
            "reacting_tdc_core_temperature_K": float(tdc["coreTemperature_K"]),
            "reacting_tdc_boundary_temperature_K": float(tdc["boundaryTemperature_K"]),
            "compression_start_pressure_bar": float(compression_start["effectivePressure_bar"]),
            "compression_start_core_temperature_K": float(compression_start["coreTemperature_K"]),
            "compression_start_boundary_temperature_K": float(compression_start["boundaryTemperature_K"]),
            "gross_work_supported_mJ": float(summary["gross_indicated_work_mJ"]),
            "minimum_motor_work_proxy_mJ": max(0.0, -float(summary["gross_indicated_work_mJ"])),
            # Full-four-stroke average lower bound: spread any negative work
            # from the modeled 360-CAD closed pass over 720 CAD (4*pi rad),
            # while deliberately assigning zero load to the unmodeled gas-
            # exchange revolution. This is not instantaneous motor torque.
            "minimum_motor_torque_proxy_Nm": max(
                0.0, -float(summary["gross_indicated_work_mJ"]) * 1e-3 / (4.0 * 3.141592653589793)
            ),
            "pressure_trace_digest": _trace_digest(rows),
            "wall_heat_mJ": float(summary["wall_energy_gas_to_wall_mJ"]),
            "trapped_mass_mg": float(summary["initial_trapped_mass_mg"]),
            "cycle_event_times": _event_times(rows, summary, config.rpm),
        }
        for key in (
            "fuel_profile", "mechanism", "fuel_composition", "peak_pressure_bar",
            "peak_pressure_deg_atdc", "peak_temperature_K", "peak_core_temperature_K",
            "peak_boundary_temperature_K", "max_pressure_rise_bar_per_deg",
            "max_pressure_rise_deg_atdc", "max_fuel_consumed_fraction",
            "mass_retained_end_fraction", "mass_balance_residual_mg", "blowby_mass_out_mg",
            "blowby_mass_in_mg", "gross_indicated_work_mJ", "gross_imep_bar",
            "gross_indicated_power_W_per_cylinder", "wall_energy_gas_to_wall_mJ",
            "mixing_time_min_observed_ms", "mixing_time_max_observed_ms",
            "max_interzone_pressure_difference_bar", "max_volume_closure_error_mm3",
            "CA10_deg_atdc", "CA50_deg_atdc", "CA90_deg_atdc", "branch",
        ):
            result[key] = summary.get(key)
        result.update(classify(summary))
        return result
    except Exception as exc:  # never turn a solver failure into physics
        return {
            "status": "error", "error": f"{type(exc).__name__}: {exc}",
            **job["identity"], "rpm": job["config_patch"].get("rpm"),
            "stable_idle_status": "unresolved",
            "screen_class": "numerical_failure", "limiting_mechanism": "numerical_failure",
        }


def jobs(scope: str = "baseline", baseline_rows: list[dict[str, Any]] | None = None,
         candidate_rpm: float | None = None) -> list[dict[str, Any]]:
    """Build baseline RPM map or one-factor-at-a-time uncertainty jobs."""
    result = []
    if scope == "baseline":
        for mechanism in MECHANISMS:
            for rpm in RPM_GRID:
                result.append({
                    "identity": {"case": "rpm_baseline", "mechanism_case": mechanism, "uncertainty_factor": "none"},
                    "config_patch": {"rpm": rpm, "fuel_profile": mechanism},
                })
        return result
    if scope == "refine":
        if not baseline_rows:
            raise ValueError("refine scope requires completed baseline rows")
        # Find the first all-mechanism robust point and refine only the bracket
        # immediately below it. If 800 rpm is robust, extend below the declared
        # floor instead of silently calling it the minimum.
        by_rpm: dict[float, list[dict[str, Any]]] = {}
        for row in baseline_rows:
            if row.get("status") == "ok" and row.get("rpm") is not None:
                by_rpm.setdefault(float(row["rpm"]), []).append(row)
        ordered = sorted(by_rpm)
        robust = [rpm for rpm in ordered if len(by_rpm[rpm]) >= len(MECHANISMS)
                  and all(row.get("screen_class") == "robust" for row in by_rpm[rpm])]
        if robust:
            first = robust[0]
            lower = [rpm for rpm in ordered if rpm < first]
            if lower:
                previous = max(lower)
                refine_rpms = tuple(previous + (first - previous) * fraction for fraction in (0.25, 0.5, 0.75))
            elif first == RPM_GRID[0]:
                refine_rpms = (600.0, 400.0)
            else:
                refine_rpms = ()
        else:
            refine_rpms = ()
        for mechanism in MECHANISMS:
            for rpm in refine_rpms:
                result.append({
                    "identity": {"case": "rpm_refinement", "mechanism_case": mechanism, "uncertainty_factor": "none"},
                    "config_patch": {"rpm": rpm, "fuel_profile": mechanism},
                })
        return result
    if scope == "retry":
        return [{
            "identity": {"case": "numerical_retry", "mechanism_case": "dme_llnl_2004", "uncertainty_factor": "step_halved"},
            "config_patch": {"rpm": 1500.0, "fuel_profile": "dme_llnl_2004", "step_deg": 0.0625},
        }]
    if scope != "uncertainty":
        raise ValueError("scope must be baseline, refine, retry, or uncertainty")
    # The reference mechanism is retained for the uncertainty lane.  Alternative
    # mechanisms are mapped at the canonical state above, not multiplied into
    # every sensitivity axis.
    sensitivity_rpm = 1100.0 if candidate_rpm is None else float(candidate_rpm)
    cases: list[tuple[str, dict[str, Any]]] = [("reference", {"rpm": sensitivity_rpm})]
    cases += [("phi", {"rpm": sensitivity_rpm, "equivalence_ratio": value}) for value in (0.30, 0.50)]
    cases += [("intake_pressure", {"rpm": sensitivity_rpm, "intake_pressure_bar": value}) for value in (2.3, 3.5)]
    cases += [("intake_temperature", {"rpm": sensitivity_rpm, "intake_temperature_K": value}) for value in (280.0, 350.0)]
    cases += [("wall_temperature", {"rpm": sensitivity_rpm, "wall_temperature_K": value}) for value in (520.0, 600.0)]
    for clearance in (2.0, 3.0, 5.0):
        for eccentricity in (0.0, 0.5, 1.0):
            cases.append(("annular_clearance_eccentricity", {
                "rpm": sensitivity_rpm, "annular_radial_clearance_um": clearance,
                "annular_eccentricity_ratio": eccentricity,
            }))
    for factor, patch in cases:
        result.append({
            "identity": {"case": "uncertainty", "mechanism_case": "dme_zhao_sk39", "uncertainty_factor": factor},
            "config_patch": {"fuel_profile": "dme_zhao_sk39", **patch},
        })
    return result


def _csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat = []
    for row in rows:
        out = {key: value for key, value in row.items() if key not in {"config", "zone_options", "pressure_trace_digest", "gates", "failed_gates", "classification_note", "cycle_event_times"}}
        out.update({f"gate_{key}": value for key, value in row.get("gates", {}).items()})
        out.update({f"event_{key}": value for key, value in row.get("cycle_event_times", {}).items()})
        out.update({f"trace_{key}": value for key, value in row.get("pressure_trace_digest", {}).items()})
        out["failed_gates"] = ";".join(row.get("failed_gates", []))
        flat.append(out)
    return flat


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate baseline rows across all declared mechanisms at each RPM."""
    groups: dict[float, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("status") == "ok" and row.get("rpm") is not None:
            groups.setdefault(float(row["rpm"]), []).append(row)
    result = []
    for rpm, group in sorted(groups.items()):
        result.append({
            "rpm": rpm,
            "mechanisms_observed": sorted(row.get("mechanism_case") for row in group),
            "all_declared_mechanisms_present": len({row.get("mechanism_case") for row in group}) == len(MECHANISMS),
            "all_mechanisms_robust": len(group) >= len(MECHANISMS) and all(row.get("screen_class") == "robust" for row in group),
            "screen_classes": sorted({row.get("screen_class") for row in group}),
            "limiting_mechanisms": sorted({row.get("limiting_mechanism") for row in group}),
            "minimum_gross_imep_bar": min(float(row["gross_imep_bar"]) for row in group),
            "maximum_peak_temperature_K": max(float(row["peak_temperature_K"]) for row in group),
            "maximum_pressure_rise_bar_per_deg": max(float(row["max_pressure_rise_bar_per_deg"]) for row in group),
            "minimum_mass_retained_end_fraction": min(float(row["mass_retained_end_fraction"]) for row in group),
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("baseline", "refine", "refine2", "refine3", "retry", "uncertainty"), default="baseline")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out-dir", default="results")
    args = parser.parse_args()
    if args.jobs < 1:
        raise SystemExit("--jobs must be >= 1")
    out = Path(args.out_dir)
    baseline_path = out / "op_idle_map_baseline.json"
    baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else None
    baseline_rows = baseline_payload.get("rows") if baseline_payload else None
    prior_rows = list(baseline_rows or [])
    for prior_name in ("refine", "refine2", "refine3"):
        prior_path = out / f"op_idle_map_{prior_name}.json"
        if prior_path.exists():
            prior_rows += json.loads(prior_path.read_text(encoding="utf-8")).get("rows", [])
    baseline_aggregate = aggregate(baseline_rows or [])
    prior_aggregate = aggregate(prior_rows)
    candidate_rpm = None
    if prior_aggregate:
        robust_rpms = [row["rpm"] for row in prior_aggregate if row["all_mechanisms_robust"]]
        if robust_rpms:
            first = min(robust_rpms)
            lower = [row["rpm"] for row in prior_aggregate if row["rpm"] < first]
            candidate_rpm = (max(lower) + first) / 2.0 if lower else first
    effective_scope = "refine" if args.scope in {"refine2", "refine3"} else args.scope
    work = jobs(effective_scope, baseline_rows=prior_rows if args.scope in {"refine2", "refine3"} else baseline_rows,
                candidate_rpm=candidate_rpm)
    if args.jobs == 1:
        rows = [run_job(job) for job in work]
    else:
        rows = []
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(run_job, job) for job in work]
            for future in as_completed(futures):
                rows.append(future.result())
        rows.sort(key=lambda row: (row.get("mechanism_case", ""), row.get("rpm", 0.0), row.get("uncertainty_factor", "")))
    out.mkdir(parents=True, exist_ok=True)
    stem = f"op_idle_map_{args.scope}"
    (out / f"{stem}.json").write_text(json.dumps({
        "campaign": "bounded low-idle operating map", "scope": args.scope,
        "case_count": len(rows), "rpm_grid": RPM_GRID,
        "transition_step_deg": STRICT_STEP_DEG,
        "two_zone_tolerances": {"rtol": 1.0e-9, "atol": 1.0e-15},
        "stable_idle_status": "unresolved",
        "rows": rows,
        "aggregate_by_rpm": aggregate(rows) if args.scope == "baseline" else [],
    }, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    flat = _csv_rows(rows)
    fields = sorted({key for row in flat for key in row})
    with (out / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)
    counts: dict[str, int] = {}
    for row in rows:
        key = "numerical_failure" if row.get("status") != "ok" else row.get("screen_class", "error")
        counts[key] = counts.get(key, 0) + 1
    print(json.dumps({"scope": args.scope, "case_count": len(rows), "screen_class_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
