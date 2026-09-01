#!/usr/bin/env python3
"""Map ignition-delay temperature sensitivity as an operability diagnostic.

The objective is not shortest delay. It is the smallest magnitude of
``d(ln tau) / d(ln T)``: a flatter ignition-delay curve is less sensitive to
small temperature errors. Results are constant-volume, adiabatic chemistry
screens and must not be mistaken for engine-cycle stability margins.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import json
import math

from mechanism_gate import constant_volume_ignition


@dataclass(frozen=True)
class MechanismCase:
    name: str
    path: str
    fuel: str
    oxidizer: str
    caveat: str


DEFAULT_CASES = (
    MechanismCase(
        "zhao_sk39", "mechanisms/dme_zhao_sk39.yaml",
        "CH3OCH3:0.25,CH4:0.75", "O2:1,N2:3.76",
        "Reduction retention checked; no direct blend validation.",
    ),
    MechanismCase(
        "zhao_full55", "mechanisms/dme_zhao_full.yaml",
        "CH3OCH3:0.25,CH4:0.75", "O2:1,N2:3.76",
        "Active DME decomposition fit is 1 atm; pressure-rate selection remains open.",
    ),
    MechanismCase(
        "llnl79", "mechanisms/llnl_dme_2004/llnl_dme_2004.yaml",
        "ch3och3:0.25,ch4:0.75", "o2:1,n2:3.76",
        "Independent lineage; engine blend remains unvalidated.",
    ),
)


def temperature_grid(text: str) -> list[int]:
    start, stop, step = (int(value) for value in text.split(":"))
    if step <= 0 or stop < start:
        raise ValueError("Temperature grid must be START:STOP:positive_STEP.")
    return list(range(start, stop + 1, step))


def pressure_grid(text: str) -> list[float]:
    values = [float(value) for value in text.split(",")]
    if not values or any(value <= 0 for value in values):
        raise ValueError("Pressures must be positive comma-separated bar values.")
    return values


def run_map(
    cases: tuple[MechanismCase, ...] = DEFAULT_CASES,
    *,
    temperatures_K: list[int],
    pressures_bar: list[float],
    equivalence_ratio: float = 0.40,
    max_time_s: float = 2.0,
) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    minima: list[dict] = []
    for case in cases:
        if not Path(case.path).is_file():
            raise FileNotFoundError(case.path)
        for pressure in pressures_bar:
            delays: list[float | None] = []
            for temperature in temperatures_K:
                result = constant_volume_ignition(
                    case.path, temperature, pressure, fuel=case.fuel,
                    oxidizer=case.oxidizer, equivalence_ratio=equivalence_ratio,
                    max_time_s=max_time_s,
                )
                delays.append(result.delay_dPdt_s)
            local_rows: list[dict] = []
            for index, (temperature, delay) in enumerate(zip(temperatures_K, delays)):
                slope = None
                if (0 < index < len(temperatures_K) - 1
                        and delays[index - 1] and delays[index + 1]):
                    slope = math.log(delays[index + 1] / delays[index - 1]) / math.log(
                        temperatures_K[index + 1] / temperatures_K[index - 1]
                    )
                row = {
                    "mechanism": case.name,
                    "mechanism_path": case.path,
                    "pressure_bar": pressure,
                    "temperature_K": temperature,
                    "equivalence_ratio": equivalence_ratio,
                    "fuel": case.fuel,
                    "delay_dPdt_ms": delay * 1000 if delay else None,
                    "dln_tau_dln_T": slope,
                    "abs_dln_tau_dln_T": abs(slope) if slope is not None else None,
                    "flat_sensitivity_abs_le_1": abs(slope) <= 1.0 if slope is not None else False,
                    "caveat": case.caveat,
                }
                rows.append(row)
                local_rows.append(row)
            eligible = [row for row in local_rows
                        if row["abs_dln_tau_dln_T"] is not None
                        and 800 <= row["temperature_K"] <= 1100]
            if eligible:
                best = min(eligible, key=lambda row: row["abs_dln_tau_dln_T"])
                minima.append({
                    "mechanism": case.name,
                    "pressure_bar": pressure,
                    "best_temperature_K": best["temperature_K"],
                    "best_slope": best["dln_tau_dln_T"],
                    "best_delay_ms": best["delay_dPdt_ms"],
                })
    metadata = {
        "objective": "minimize absolute d(ln ignition delay)/d(ln temperature)",
        "model": "adiabatic constant-volume; max dP/dt delay",
        "equivalence_ratio": equivalence_ratio,
        "temperatures_K": temperatures_K,
        "pressures_bar": pressures_bar,
        "minima_800_to_1100K": minima,
        "warning": (
            "Flat constant-volume sensitivity is an operability indicator, not proof "
            "of stable engine combustion. Spatial transport and wall coupling remain open."
        ),
    }
    return rows, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temperatures", default="750:1250:25")
    parser.add_argument("--pressures-bar", default="25,35,45,60")
    parser.add_argument("--phi", type=float, default=0.40)
    parser.add_argument("--max-time-s", type=float, default=2.0)
    parser.add_argument("--csv", default="operability_sensitivity.csv")
    parser.add_argument("--json", default="operability_sensitivity.json")
    args = parser.parse_args()
    rows, metadata = run_map(
        temperatures_K=temperature_grid(args.temperatures),
        pressures_bar=pressure_grid(args.pressures_bar),
        equivalence_ratio=args.phi,
        max_time_s=args.max_time_s,
    )
    with open(args.csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "rows": rows}, handle, indent=2)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
