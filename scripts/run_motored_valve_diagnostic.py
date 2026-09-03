#!/usr/bin/env python3
"""Run the bounded 1,200-rpm nonreacting signed-valve diagnostic.

The output is deliberately small JSON.  This experiment diagnoses the gas
exchange/state map before chemistry, friction, crank dynamics, or motor
control are enabled.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cycle720 import (  # noqa: E402
    Cycle720Options,
    ValveConfig,
    iterate_motored_periodic_720,
)
from microengine_rig import RigConfig  # noqa: E402


def _json_safe(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def canonical_config(step_deg: float, wall_temperature: float) -> RigConfig:
    return RigConfig(
        bore_mm=8.5, stroke_mm=7.0, rod_stroke_ratio=1.6,
        compression_ratio=7.75, rpm=1200.0,
        intake_pressure_bar=3.0, intake_temperature_K=300.0,
        equivalence_ratio=0.40, wall_mode="fixed",
        wall_temperature_K=wall_temperature,
        effective_h_W_m2K=300.0, ignition_mode="cantera-auto",
        fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
        fuel_primary_mole_fraction=0.25, crankcase_pressure_bar=1.0,
        crankcase_temperature_K=350.0, step_deg=step_deg,
    )


def diagnostic_options(step_deg: float, max_cycles: int) -> Cycle720Options:
    return Cycle720Options(
        step_deg=step_deg, max_cycles=max_cycles,
        valves_enabled=True, bidirectional_valves=True,
        friction_enabled=False, crank_dynamics_enabled=False,
        motor_enabled=False,
        intake_valve=ValveConfig(-360.0, -160.0, effective_area_m2=1.0e-6),
        exhaust_valve=ValveConfig(160.0, 360.0, effective_area_m2=1.0e-6),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step-deg", type=float, default=2.0)
    parser.add_argument("--cycles", type=int, default=12)
    parser.add_argument("--wall-temperature", type=float, default=560.0)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "cycle720_1200_motored_bidirectional.json")
    args = parser.parse_args()
    config = canonical_config(args.step_deg, args.wall_temperature)
    options = diagnostic_options(args.step_deg, args.cycles)
    result = iterate_motored_periodic_720(config, options)
    artifact = {
        "experiment": "cycle720-1200-motored-bidirectional-valves",
        "status": "periodic_state_found" if result["converged"] else "unresolved_periodic_state",
        "configuration": {"rig": asdict(config), "cycle": asdict(options)},
        "convergence": result["converged"],
        "cycles": result["cycles"],
        "gates": result["gates"],
        "history": result["history"],
        "summary": result["result"]["summary"],
        "provenance": {
            "measured": False, "literature_derived": False,
            "project_model_result": True,
            "note": "Nonreacting fixed-speed ideal-gas diagnostic; valve areas, Cd, wall h and wall temperature are project-model assumptions.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(_json_safe(artifact), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": artifact["status"], "cycles": result["cycles"],
        "output": str(args.output), "gates": result["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
