#!/usr/bin/env python3
"""Reproduce the Beta 2.6 CVODE tolerance check at one central anchor."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path

from microengine_rig import apply_config_patch
from uncertainty_campaign import base_config, mixing_cases
from two_zone_model import simulate_two_zone


MECHANISMS = ("dme_zhao_sk39", "dme_llnl_2004")
TOLERANCES = {
    "production": (1.0e-7, 1.0e-14),
    "strict": (1.0e-9, 1.0e-15),
}


def main() -> None:
    config = apply_config_patch(base_config(), {
        "compression_ratio": 7.75,
        "intake_pressure_bar": 3.0,
        "blowby_mode": "annular",
        "annular_radial_clearance_um": 3.0,
        "annular_eccentricity_ratio": 0.5,
        "annular_skirt_length_mm": 8.0,
    })
    central = mixing_cases()["central"]
    rows = []
    for mechanism in MECHANISMS:
        mechanism_config = apply_config_patch(config, {"fuel_profile": mechanism})
        for label, (rtol, atol) in TOLERANCES.items():
            options = replace(central, integrator_rtol=rtol, integrator_atol=atol)
            _, summary = simulate_two_zone(mechanism_config, options)
            rows.append({
                "mechanism": mechanism,
                "tolerance_case": label,
                "integrator_rtol": rtol,
                "integrator_atol": atol,
                "gross_imep_bar": summary["gross_imep_bar"],
                "peak_temperature_K": summary["peak_temperature_K"],
                "max_fuel_consumed_fraction": summary["max_fuel_consumed_fraction"],
                "max_pressure_rise_bar_per_deg": summary["max_pressure_rise_bar_per_deg"],
            })

    deltas = []
    for mechanism in MECHANISMS:
        pair = {row["tolerance_case"]: row for row in rows if row["mechanism"] == mechanism}
        deltas.append({
            "mechanism": mechanism,
            "absolute_imep_shift_bar": abs(
                pair["production"]["gross_imep_bar"] - pair["strict"]["gross_imep_bar"]
            ),
            "absolute_peak_temperature_shift_K": abs(
                pair["production"]["peak_temperature_K"] - pair["strict"]["peak_temperature_K"]
            ),
            "absolute_conversion_shift": abs(
                pair["production"]["max_fuel_consumed_fraction"]
                - pair["strict"]["max_fuel_consumed_fraction"]
            ),
        })

    payload = {
        "conditions": {
            "config": asdict(config),
            "zone_options_without_tolerances": {
                key: value for key, value in asdict(central).items()
                if key not in {"integrator_rtol", "integrator_atol"}
            },
        },
        "rows": rows,
        "deltas": deltas,
    }
    Path("beta26_tolerance_check.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(deltas, indent=2))


if __name__ == "__main__":
    main()
