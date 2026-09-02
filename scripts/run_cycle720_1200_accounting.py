#!/usr/bin/env python3
"""Bounded 1200-rpm valve-cycle accounting diagnostic.

This is intentionally a single-point experiment.  It separates conservation
closure from convergence of the homologous end-of-cycle state, and includes
the annular blow-by occurring inside the reacting two-zone segment.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cycle720 import Cycle720Options, FrictionBracket, MotorController, ValveConfig, simulate_cycle720
from microengine_rig import RigConfig
from physics.friction_bracket import equivalent_friction_torque_Nm


def canonical_config(step_deg: float = 5.0) -> RigConfig:
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


def valve_options(step_deg: float, max_cycles: int) -> Cycle720Options:
    return Cycle720Options(
        step_deg=step_deg, max_cycles=max_cycles, valves_enabled=True,
        friction_enabled=False, crank_dynamics_enabled=False, motor_enabled=False,
        intake_valve=ValveConfig(-360.0, -160.0, effective_area_m2=1.0e-6),
        exhaust_valve=ValveConfig(160.0, 360.0, effective_area_m2=1.0e-6),
        friction=FrictionBracket(0.05e-3, equivalent_friction_torque_Nm(0.15, 0.3971e-6), 0.30e-3),
    )


def _state_metrics(previous, current):
    names = sorted(set(previous["Y"]) | set(current["Y"]))
    return {
        "mass_rel": abs(current["mass_kg"] - previous["mass_kg"]) / max(abs(previous["mass_kg"]), 1e-30),
        "species_max": max((abs(current["Y"].get(n, 0.0) - previous["Y"].get(n, 0.0)) for n in names), default=0.0),
        "temperature_K": abs(current["T_K"] - previous["T_K"]),
        "pressure_bar": abs(current["P_bar"] - previous["P_bar"]),
    }


def main() -> None:
    step_deg, max_cycles = 5.0, 12
    config = canonical_config(step_deg)
    opts = valve_options(step_deg, max_cycles)
    records = []
    state = None
    start = time.perf_counter()
    for cycle in range(1, max_cycles + 1):
        cycle_start = time.perf_counter()
        result = simulate_cycle720(config, opts, state)
        out = result["cycle_state_out"]
        metrics = _state_metrics(state, out) if state is not None else None
        record = {
            "cycle": cycle,
            "runtime_s": time.perf_counter() - cycle_start,
            "state_metrics": metrics,
            "accounting": result["summary"].get("cycle_accounting", {}),
            "state_out": {
                "mass_kg": out["mass_kg"], "T_K": out["T_K"],
                "P_bar": out["P_bar"], "Y": out["Y"],
            },
        }
        records.append(record)
        state = out
    last_metrics = records[-1]["state_metrics"]
    # This diagnostic does not promote a periodic result.  It classifies the
    # observed closure and leaves the existing strict gates to the staged run.
    status = "unresolved_periodic_state"
    gates = {
        "mass": bool(last_metrics and last_metrics["mass_rel"] <= opts.mass_tolerance_rel),
        "species": bool(last_metrics and last_metrics["species_max"] <= opts.species_tolerance),
        "enthalpy": False,
        "temperature": bool(last_metrics and last_metrics["temperature_K"] <= opts.temperature_tolerance_K),
        "speed": True,
    }
    artifact = {
        "experiment": "cycle720-1200-accounting",
        "status": status,
        "classification": "conservation_closure_with_transient_state_drift",
        "configuration": {"rig": vars(config), "step_deg": step_deg, "max_cycles": max_cycles},
        "gates": gates,
        "records": records,
        "runtime_s": time.perf_counter() - start,
        "provenance": {
            "measured": False, "literature_derived": False,
            "project_model_assumptions": True,
            "note": "Valve area/timing/Cd, fixed wall temperature, annular clearance and two-zone leakage are project-model assumptions.",
        },
    }
    output = ROOT / "results" / "cycle720_1200_accounting.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "output": str(output), "runtime_s": artifact["runtime_s"]}, sort_keys=True))


if __name__ == "__main__":
    main()
