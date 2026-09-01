#!/usr/bin/env python3
"""Idealized compressor and aftercooler screen for boosted MicroEngine cases."""
from __future__ import annotations

import argparse
import json


def boost_metrics(
    *,
    initial_trapped_mass_mg_per_cylinder: float,
    intake_pressure_bar: float,
    intake_temperature_K: float,
    rpm: float,
    cylinders: int = 6,
    cycle_revolutions: float = 2.0,
    ambient_pressure_bar: float = 1.0,
    ambient_temperature_K: float = 300.0,
    compressor_isentropic_efficiency: float = 0.65,
    motor_efficiency: float = 0.85,
    gamma: float = 1.40,
    cp_J_kgK: float = 1005.0,
) -> dict[str, float | str]:
    if intake_pressure_bar < ambient_pressure_bar:
        raise ValueError("This screen expects intake pressure at or above ambient.")
    if not 0 < compressor_isentropic_efficiency <= 1 or not 0 < motor_efficiency <= 1:
        raise ValueError("Efficiencies must be in (0, 1].")
    cycle_frequency_Hz = rpm / 60.0 / cycle_revolutions
    mixture_mass_flow_kg_s = (
        initial_trapped_mass_mg_per_cylinder * 1e-6
        * cylinders * cycle_frequency_Hz
    )
    pressure_ratio = intake_pressure_bar / ambient_pressure_bar
    isentropic_outlet_K = ambient_temperature_K * pressure_ratio ** ((gamma - 1.0) / gamma)
    actual_outlet_K = ambient_temperature_K + (
        isentropic_outlet_K - ambient_temperature_K
    ) / compressor_isentropic_efficiency
    shaft_power_W = mixture_mass_flow_kg_s * cp_J_kgK * (
        actual_outlet_K - ambient_temperature_K
    )
    electrical_power_W = shaft_power_W / motor_efficiency
    aftercooler_heat_W = mixture_mass_flow_kg_s * cp_J_kgK * max(
        0.0, actual_outlet_K - intake_temperature_K
    )
    return {
        "compressor_pressure_ratio": pressure_ratio,
        "six_cylinder_mixture_mass_flow_mg_s": mixture_mass_flow_kg_s * 1e6,
        "isentropic_compressor_outlet_K": isentropic_outlet_K,
        "estimated_actual_compressor_outlet_K": actual_outlet_K,
        "estimated_compressor_shaft_power_W": shaft_power_W,
        "estimated_compressor_electrical_power_W": electrical_power_W,
        "estimated_aftercooler_heat_rejection_W": aftercooler_heat_W,
        "boost_note": (
            "Idealized steady compressor screen using trapped mixture flow. It omits "
            "volumetric-efficiency, pulsation, leakage, map, duct, and fuel-addition details."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trapped-mass-mg", type=float, required=True)
    parser.add_argument("--intake-pressure-bar", type=float, required=True)
    parser.add_argument("--intake-temperature-K", type=float, default=300.0)
    parser.add_argument("--rpm", type=float, default=1200.0)
    parser.add_argument("--cylinders", type=int, default=6)
    args = parser.parse_args()
    print(json.dumps(boost_metrics(
        initial_trapped_mass_mg_per_cylinder=args.trapped_mass_mg,
        intake_pressure_bar=args.intake_pressure_bar,
        intake_temperature_K=args.intake_temperature_K,
        rpm=args.rpm,
        cylinders=args.cylinders,
    ), indent=2))


if __name__ == "__main__":
    main()
