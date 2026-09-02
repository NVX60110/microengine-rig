#!/usr/bin/env python3
"""Bounded staged 1200-rpm 720-CAD gas-exchange experiment.

This script intentionally runs one operating point only.  It stops promotion
at the first stage whose periodic gates do not close; later stages are not
silently run to rescue the result.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cycle720 import Cycle720Options, FrictionBracket, MotorController, ValveConfig, iterate_periodic_720, simulate_cycle720
from microengine_rig import RigConfig
from two_zone_model import simulate_two_zone
from physics.friction_bracket import equivalent_friction_torque_Nm


def json_safe(value):
    """Encode first-cycle non-finite deltas as JSON null, not fake zeros."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value


def canonical_config(step_deg: float = 2.0) -> RigConfig:
    """Accepted Beta 2.6 fixed-wall anchor; no new tuning is applied."""
    return RigConfig(
        bore_mm=8.5, stroke_mm=7.0, rod_stroke_ratio=1.6,
        compression_ratio=7.75, rpm=1200.0,
        intake_pressure_bar=3.0, intake_temperature_K=300.0,
        equivalence_ratio=0.40, wall_mode="fixed", wall_temperature_K=560.0,
        effective_h_W_m2K=300.0, ignition_mode="cantera-auto",
        fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
        fuel_primary_mole_fraction=0.25, crankcase_pressure_bar=1.0,
        crankcase_temperature_K=350.0, blowby_mode="annular",
        annular_radial_clearance_um=3.0, annular_skirt_length_mm=8.0,
        annular_eccentricity_ratio=0.5, step_deg=step_deg,
    )


def options(stage: str, step_deg: float, cycles: int) -> Cycle720Options:
    central_friction = equivalent_friction_torque_Nm(0.15, 0.3971e-6)
    return Cycle720Options(
        step_deg=step_deg, max_cycles=cycles,
        valves_enabled=stage in {"valves", "friction", "dynamics"},
        friction_enabled=stage in {"friction", "dynamics"},
        crank_dynamics_enabled=stage == "dynamics", motor_enabled=False,
        intake_valve=ValveConfig(-360.0, -160.0, effective_area_m2=1.0e-6),
        exhaust_valve=ValveConfig(160.0, 360.0, effective_area_m2=1.0e-6),
        friction=FrictionBracket(0.05e-3, central_friction, 0.30e-3),
        motor=MotorController(target_rpm=1200.0, gain_Nm_per_rad_s=1.0e-5,
                              max_torque_Nm=0.01, inertia_kg_m2=1.0e-7),
    )


def main() -> None:
    output = Path("results/cycle720_1200_staged.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    step_deg, cycles = 2.0, 4
    config = canonical_config(step_deg)
    started = time.perf_counter()
    records = []

    # Stage 0: direct canonical bridge.  It is an explicit gate before any
    # open-system result is interpreted.
    regression_options = options("regression", step_deg, cycles)
    regression = simulate_cycle720(config, regression_options)
    # Independent same-process baseline: a regression result is only valid if
    # both calls agree on the canonical trace, not merely because the wrapper
    # returned its own ``gate=True`` marker.
    baseline_rows, baseline_summary = simulate_two_zone(
        config, regression_options.two_zone_options)
    reg = regression["regression"]
    pressure_error = max(abs(a["effectivePressure_bar"] - b["effectivePressure_bar"])
                         for a, b in zip(regression["rows"], baseline_rows))
    temperature_error = max(abs(a["coreTemperature_K"] - b["coreTemperature_K"])
                            for a, b in zip(regression["rows"], baseline_rows))
    work_error = abs(reg["canonical_gross_work_mJ"] - baseline_summary["gross_indicated_work_mJ"])
    reg.update({"independent_baseline": "two_zone_model.simulate_two_zone",
                "pressure_max_abs_error_bar": pressure_error,
                "core_temperature_max_abs_error_K": temperature_error,
                "gross_work_abs_error_mJ": work_error,
                "gate": (len(regression["rows"]) == len(baseline_rows)
                          and pressure_error <= 0.0 and temperature_error <= 0.0
                          and work_error <= 0.0)})
    records.append({"stage": "disabled-regression", "status": "pass" if reg["gate"] else "failed",
                    "runtime_s": time.perf_counter() - started, "summary": regression["summary"],
                    "regression": reg})

    prior = None
    for stage in ("valves", "friction", "dynamics"):
        stage_start = time.perf_counter()
        try:
            result = iterate_periodic_720(config, options(stage, step_deg, cycles), prior)
            prior = result["state"]
            status = "pass" if result["converged"] else "unresolved_periodic_state"
            error = None
            failed_gates = [name for name, passed in result["gates"].items() if not passed]
            summary = result["result"]["summary"]
            displacement = config.bore_mm / 1000.0
            displacement = 3.141592653589793 * displacement**2 / 4.0 * config.stroke_mm / 1000.0
            summary = dict(summary)
            summary["pumping_mep_bar"] = (summary.get("pumping_work_mJ", 0.0) * 1e-3
                                           / displacement / 1e5)
            summary["friction_mep_bar"] = (summary.get("friction_work_mJ", 0.0) * 1e-3
                                            / displacement / 1e5)
            summary["gas_work_mep_bar"] = (summary.get("gross_work_mJ", 0.0) * 1e-3
                                            / displacement / 1e5)
            record = {
                "stage": stage, "status": status,
                "runtime_s": time.perf_counter() - stage_start,
                "cycles": result["cycles"], "converged": result["converged"],
                "failed_gates": failed_gates,
                "gates": result["gates"], "history": result["history"],
                "summary": summary,
            }
        except Exception as exc:  # preserve explicit numerical failure row
            record = {"stage": stage, "status": "numerical_failure",
                      "runtime_s": time.perf_counter() - stage_start,
                      "cycles": 0, "converged": False,
                      "error_type": type(exc).__name__, "error": str(exc)}
        records.append(record)
        if record["status"] != "pass":
            break

    artifact = {"experiment": "cycle720-1200-staged", "status": records[-1]["status"],
                "configuration": {"rig": asdict(config), "step_deg": step_deg,
                                   "four_stroke_period_s": 120.0 / config.rpm,
                                   "one_revolution_period_s": 60.0 / config.rpm},
                "records": records, "total_runtime_s": time.perf_counter() - started,
                "provenance": {"measured": False, "literature_derived": False,
                               "project_model_assumptions": True,
                               "note": "Valve areas, timing, Cd and friction bracket are explicit assumptions."}}
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(json_safe(artifact), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": artifact["status"], "output": str(output),
                      "total_runtime_s": artifact["total_runtime_s"]}, sort_keys=True))


if __name__ == "__main__":
    main()
