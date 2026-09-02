#!/usr/bin/env python3
"""Run one deliberately small 720-CAD scaffold case from the repository root."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from cycle720 import Cycle720Options, FrictionBracket, MotorController, ValveConfig, iterate_periodic_720
from microengine_rig import RigConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpm", type=float, default=1200.0)
    parser.add_argument("--step-deg", type=float, default=2.0)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--enable-valves", action="store_true")
    parser.add_argument("--enable-friction", action="store_true")
    parser.add_argument("--enable-motor", action="store_true")
    parser.add_argument("--output", default="cycle720_result.json")
    args = parser.parse_args()
    config = RigConfig(rpm=args.rpm, step_deg=args.step_deg)
    options = Cycle720Options(
        step_deg=args.step_deg, max_cycles=args.cycles,
        valves_enabled=args.enable_valves,
        friction_enabled=args.enable_friction,
        motor_enabled=args.enable_motor,
        intake_valve=ValveConfig(-360.0, -160.0, effective_area_m2=1e-6),
        exhaust_valve=ValveConfig(160.0, 360.0, effective_area_m2=1e-6),
        friction=FrictionBracket(1e-5, 2e-5, 4e-5),
        motor=MotorController(target_rpm=args.rpm),
    )
    result = iterate_periodic_720(config, options)
    output = {"configuration": {"rig": asdict(config), "cycle": asdict(options)},
              "convergence": result["converged"], "cycles": result["cycles"],
              "history": result["history"], "summary": result["result"]["summary"]}
    with open(args.output, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(output, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"converged": result["converged"], "cycles": result["cycles"],
                      "output": args.output}, sort_keys=True))


if __name__ == "__main__":
    main()
