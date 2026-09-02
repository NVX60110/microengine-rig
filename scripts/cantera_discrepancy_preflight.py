#!/usr/bin/env python3
"""Bounded attribution study for the adiabatic two-zone regression check.

This reproduces ``tests.test_rig.RigTests.test_two_zone_collapses_to_single_zone_when_adiabatic``
under the locally installed Cantera version.  It varies only controls that the
canonical code already exposes: ``RigConfig.step_deg`` and
``TwoZoneOptions.integrator_{rtol,atol}``.  The single-zone and two-zone
calculations use the same crank-angle increment for each row.

The two-zone options, chemistry, geometry, and thermodynamic state are held at
the regression-test values.  This is an attribution/preflight diagnostic, not
a chemistry tuning or a new production campaign.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import platform
import sys
from typing import Any

import cantera as ct

# Make direct ``python scripts/...py`` invocation resolve the repository modules
# in the same way as the existing command-line scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from microengine_rig import RigConfig, simulate
from two_zone_model import TwoZoneOptions, simulate_two_zone


TOLERANCE_CASES: dict[str, tuple[float, float]] = {
    "loose": (1.0e-5, 1.0e-12),
    "moderate": (1.0e-6, 1.0e-13),
    "production": (1.0e-7, 1.0e-14),
    "strict": (1.0e-8, 1.0e-15),
    # Cantera 3.2 ReactorNet defaults used by the canonical single-zone
    # solver (the two-zone code currently overrides them).
    "cantera_default": (1.0e-9, 1.0e-15),
    "very_strict": (1.0e-9, 1.0e-16),
}
STEP_DEG_VALUES = (4.0, 2.0, 1.0, 0.5, 0.25, 0.125)


def regression_config(step_deg: float) -> RigConfig:
    return RigConfig(
        fuel_profile="methane",
        intake_temperature_K=300.0,
        intake_pressure_bar=1.2,
        equivalence_ratio=0.4,
        wall_mode="adiabatic",
        blowby_mode="off",
        step_deg=step_deg,
        bore_mm=8.5,
        stroke_mm=7.0,
        compression_ratio=7.0,
        rpm=1200.0,
    )


def scalar(value: Any) -> Any:
    """Convert NumPy/Cantera scalar-like values for stable JSON output."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return float(value)


def run_one(step_deg: float, tolerance_case: str) -> dict[str, Any]:
    rtol, atol = TOLERANCE_CASES[tolerance_case]
    config = regression_config(step_deg)
    options = replace(
        TwoZoneOptions(), integrator_rtol=rtol, integrator_atol=atol
    )
    _, single = simulate(config)
    _, two = simulate_two_zone(config, options)

    single_pressure = float(single["peak_pressure_bar"])
    two_pressure = float(two["peak_pressure_bar"])
    single_temperature = float(single["peak_temperature_K"])
    two_temperature = float(two["peak_temperature_K"])
    single_conversion = float(single["max_fuel_consumed_fraction"])
    two_conversion = float(two["max_fuel_consumed_fraction"])
    return {
        "step_deg": step_deg,
        "tolerance_case": tolerance_case,
        "integrator_rtol": rtol,
        "integrator_atol": atol,
        "network_max_time_step_fraction_of_output_dt": 0.25,
        "single_peak_pressure_bar": single_pressure,
        "two_zone_peak_pressure_bar": two_pressure,
        "peak_pressure_difference_bar": two_pressure - single_pressure,
        "peak_pressure_relative_difference": (two_pressure - single_pressure) / single_pressure,
        "single_peak_temperature_K": single_temperature,
        "two_zone_peak_temperature_K": two_temperature,
        "peak_temperature_difference_K": two_temperature - single_temperature,
        "single_max_fuel_consumed_fraction": single_conversion,
        "two_zone_max_fuel_consumed_fraction": two_conversion,
        "fuel_conversion_difference": two_conversion - single_conversion,
        "two_zone_max_interzone_pressure_difference_bar": float(
            two["max_interzone_pressure_difference_bar"]
        ),
        "single_gross_imep_bar": float(single["gross_imep_bar"]),
        "two_zone_gross_imep_bar": float(two["gross_imep_bar"]),
        "gross_imep_difference_bar": float(two["gross_imep_bar"] - single["gross_imep_bar"]),
        "single_CA50_deg_atdc": scalar(single.get("CA50_deg_atdc")),
        "two_zone_CA50_deg_atdc": scalar(two.get("CA50_deg_atdc")),
    }


def main() -> None:
    rows: list[dict[str, Any]] = []
    for step_deg in STEP_DEG_VALUES:
        for tolerance_case in TOLERANCE_CASES:
            print(f"step={step_deg:g} deg, tolerance={tolerance_case}", flush=True)
            rows.append(run_one(step_deg, tolerance_case))

    payload = {
        "study": "adiabatic two-zone collapse discrepancy preflight",
        "status": "diagnostic; no chemistry tuning",
        "python": sys.version,
        "platform": platform.platform(),
        "cantera_version": ct.__version__,
        "canonical_config": asdict(regression_config(2.0)),
        "two_zone_options": asdict(TwoZoneOptions()),
        "tolerance_cases": {
            name: {"integrator_rtol": rtol, "integrator_atol": atol}
            for name, (rtol, atol) in TOLERANCE_CASES.items()
        },
        "step_deg_values": list(STEP_DEG_VALUES),
        "notes": [
            "Single-zone and two-zone runs use the same step_deg in each row.",
            "The two-zone default has a finite 10 ms reciprocal exchange closure; it is not replaced by a new mixing value.",
            "network.max_time_step is the existing model rule: one quarter of the crank-angle output interval.",
            "Conversion is reported for completeness; this lean methane case is effectively nonreacting.",
        ],
        "rows": rows,
    }
    output = Path("results/cantera_discrepancy_preflight.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
