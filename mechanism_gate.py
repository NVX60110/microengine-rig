#!/usr/bin/env python3
"""Mechanism acceptance gates for low-temperature microengine chemistry.

Two separate questions are intentionally kept separate:

1. ``parent``: did a skeletal reduction retain its parent's ignition-delay
   shape and NTC behavior? This checks reduction fidelity, not truth.
2. ``chemked``: does a mechanism reproduce measured ChemKED shock-tube delays
   using the experiment's declared ignition criterion?

Every output records conditions and parsing diagnostics. A zero-point dataset
is a hard failure. There are no bare exception handlers in the parsing path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
import argparse
import csv
import glob
import json
import math
import statistics

import cantera as ct
import yaml


@dataclass(frozen=True)
class IgnitionResult:
    delay_dPdt_s: float | None
    delay_dTdt_s: float | None
    peak_dPdt_Pa_s: float
    peak_dTdt_K_s: float
    final_temperature_K: float
    final_pressure_bar: float
    ignited: bool


@dataclass(frozen=True)
class ExperimentalPoint:
    temperature_K: float
    pressure_bar: float
    ignition_delay_s: float
    equivalence_ratio: float
    composition: dict[str, float]
    source_file: str
    ignition_target: str
    ignition_type: str


def _reactor(gas: ct.Solution) -> ct.IdealGasReactor:
    """Create a reactor without relying on Cantera's changing clone default."""
    return ct.IdealGasReactor(gas, energy="on", clone=False)


def constant_volume_ignition(
    mechanism: str,
    temperature_K: float,
    pressure_bar: float,
    *,
    composition: str | dict[str, float] | None = None,
    fuel: str | None = None,
    oxidizer: str = "O2:1,N2:3.76",
    equivalence_ratio: float = 1.0,
    phase: str | None = None,
    max_time_s: float = 2.0,
    ignition_temperature_rise_K: float = 400.0,
    integration_temperature_rise_K: float = 1000.0,
) -> IgnitionResult:
    """Adiabatic constant-volume delay using both max dP/dt and max dT/dt.

    The derivative is evaluated on CVODE's accepted internal steps. A delay is
    returned only after a substantial temperature rise; this prevents tiny
    numerical pressure drift from being labelled ignition.
    """
    gas = ct.Solution(mechanism, phase) if phase else ct.Solution(mechanism)
    if composition is not None:
        gas.TPX = temperature_K, pressure_bar * 1e5, composition
    elif fuel is not None:
        gas.set_equivalence_ratio(equivalence_ratio, fuel, oxidizer)
        gas.TP = temperature_K, pressure_bar * 1e5
    else:
        raise ValueError("Provide composition or fuel/oxidizer.")

    reactor = _reactor(gas)
    network = ct.ReactorNet([reactor])
    network.rtol = 1e-9
    network.atol = 1e-15
    initial_temperature = reactor.T
    previous_time = 0.0
    previous_temperature = reactor.T
    previous_pressure = reactor.phase.P
    peak_dPdt = (0.0, None)
    peak_dTdt = (0.0, None)

    while network.time < max_time_s:
        now = network.step()
        dt = now - previous_time
        if dt <= 0:
            raise RuntimeError("Cantera returned a non-increasing integration time.")
        dPdt = (reactor.phase.P - previous_pressure) / dt
        dTdt = (reactor.T - previous_temperature) / dt
        if dPdt > peak_dPdt[0]:
            peak_dPdt = (dPdt, now)
        if dTdt > peak_dTdt[0]:
            peak_dTdt = (dTdt, now)
        previous_time = now
        previous_temperature = reactor.T
        previous_pressure = reactor.phase.P
        # Continue well past the ignition threshold. Stopping at +400 K can
        # precede the experiment's maximum dP/dt and bias delay early.
        if reactor.T >= initial_temperature + integration_temperature_rise_K:
            break

    ignited = reactor.T >= initial_temperature + ignition_temperature_rise_K
    return IgnitionResult(
        delay_dPdt_s=peak_dPdt[1] if ignited else None,
        delay_dTdt_s=peak_dTdt[1] if ignited else None,
        peak_dPdt_Pa_s=peak_dPdt[0],
        peak_dTdt_K_s=peak_dTdt[0],
        final_temperature_K=reactor.T,
        final_pressure_bar=reactor.phase.P / 1e5,
        ignited=ignited,
    )


def _first_value(value: Any) -> Any:
    if isinstance(value, list):
        if not value:
            raise ValueError("Empty ChemKED quantity list.")
        return value[0]
    return value


def _quantity(value: Any, units: dict[str, float], field: str) -> float:
    item = _first_value(value)
    if isinstance(item, (int, float)):
        return float(item)
    parts = str(item).strip().replace("μ", "u").replace("µ", "u").split()
    if not parts:
        raise ValueError(f"Empty {field} value.")
    magnitude = float(parts[0])
    unit = parts[1].lower() if len(parts) > 1 else ""
    if unit not in units:
        raise ValueError(f"Unsupported {field} unit {unit!r}.")
    return magnitude * units[unit]


def _amount(value: Any) -> float:
    item = _first_value(value)
    if isinstance(item, dict):
        if "value" not in item:
            raise ValueError("Composition amount dictionary has no value.")
        item = item["value"]
    return float(item)


def load_chemked_points(
    patterns: Iterable[str],
    *,
    max_pressure_bar: float | None = None,
    required_target: str = "pressure",
    required_type: str = "d/dt max",
) -> tuple[list[ExperimentalPoint], list[dict[str, str]]]:
    """Load compatible ChemKED points and return explicit rejection records."""
    paths: list[str] = []
    for pattern in patterns:
        paths.extend(glob.glob(pattern))
    paths = sorted(set(paths))
    if not paths:
        raise FileNotFoundError(f"No ChemKED files matched: {list(patterns)!r}")

    points: list[ExperimentalPoint] = []
    rejected: list[dict[str, str]] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
        common = document.get("common-properties", {})
        for index, datum in enumerate(document.get("datapoints", [])):
            label = f"{path}#{index + 1}"
            try:
                ignition = datum.get("ignition-type", common.get("ignition-type", {}))
                target = str(ignition.get("target", "")).strip().lower()
                kind = str(ignition.get("type", "")).strip().lower()
                if target != required_target.lower() or kind != required_type.lower():
                    raise ValueError(f"criterion is {target!r}/{kind!r}")
                temperature = _quantity(
                    datum["temperature"], {"k": 1.0, "kelvin": 1.0}, "temperature")
                pressure = _quantity(
                    datum["pressure"],
                    {"bar": 1.0, "atm": 1.01325, "pa": 1e-5,
                     "kpa": 1e-2, "mpa": 10.0},
                    "pressure",
                )
                delay = _quantity(
                    datum["ignition-delay"],
                    {"s": 1.0, "sec": 1.0, "ms": 1e-3, "us": 1e-6,
                     "ns": 1e-9},
                    "ignition delay",
                )
                phi_raw = datum.get("equivalence-ratio", common.get("equivalence-ratio", 1.0))
                phi = float(_first_value(phi_raw))
                composition_block = datum.get("composition", common.get("composition"))
                if not composition_block:
                    raise KeyError("composition")
                composition = {
                    str(species["species-name"]): _amount(species["amount"])
                    for species in composition_block["species"]
                }
            except (KeyError, TypeError, ValueError) as exc:
                rejected.append({"point": label, "reason": f"{type(exc).__name__}: {exc}"})
                continue
            if max_pressure_bar is not None and pressure > max_pressure_bar:
                rejected.append({"point": label, "reason": "above pressure filter"})
                continue
            points.append(ExperimentalPoint(
                temperature, pressure, delay, phi, composition, str(Path(path)),
                target, kind,
            ))
    if not points:
        raise RuntimeError(
            f"Zero compatible ChemKED points loaded; {len(rejected)} were rejected."
        )
    return points, rejected


def _map_species(composition: dict[str, float], gas: ct.Solution,
                 aliases: dict[str, str]) -> dict[str, float]:
    mapped: dict[str, float] = {}
    for source, amount in composition.items():
        destination = aliases.get(source, source)
        if destination in gas.species_names:
            mapped[destination] = amount
    return mapped


def chemked_regression(
    mechanism: str,
    fuel_species: str,
    points: list[ExperimentalPoint],
    *,
    aliases: dict[str, str] | None = None,
    max_time_s: float = 0.5,
    phase: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run an experimental regression using max dP/dt ignition delay."""
    gas = ct.Solution(mechanism, phase) if phase else ct.Solution(mechanism)
    aliases = dict(aliases or {})
    aliases.setdefault("nC7H16", fuel_species)
    aliases.setdefault("NC7H16", fuel_species)
    aliases.setdefault("C7H16", fuel_species)
    aliases.setdefault("O2", "O2" if "O2" in gas.species_names else "o2")
    aliases.setdefault("N2", "N2" if "N2" in gas.species_names else "n2")

    rows: list[dict[str, Any]] = []
    ratios: list[float] = []
    failures: list[dict[str, str]] = []
    for point in points:
        composition = _map_species(point.composition, gas, aliases)
        if fuel_species not in composition:
            failures.append({"point": point.source_file, "reason": "fuel species missing"})
            continue
        try:
            result = constant_volume_ignition(
                mechanism, point.temperature_K, point.pressure_bar,
                composition=composition, phase=phase, max_time_s=max_time_s,
            )
        except (ct.CanteraError, RuntimeError, ValueError) as exc:
            failures.append({"point": point.source_file, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        simulated = result.delay_dPdt_s
        ratio = simulated / point.ignition_delay_s if simulated else None
        if ratio is not None and ratio > 0:
            ratios.append(ratio)
        rows.append({
            **asdict(point),
            "simulated_delay_s": simulated,
            "simulated_to_experiment_ratio": ratio,
            "ignited": result.ignited,
        })

    if not ratios:
        raise RuntimeError(f"Regression produced zero usable ratios; {len(failures)} failures.")
    log_ratios = [math.log10(value) for value in ratios]
    low = [row["simulated_to_experiment_ratio"] for row in rows
           if row["temperature_K"] < 900 and row["simulated_to_experiment_ratio"]]
    metrics: dict[str, Any] = {
        "mechanism": mechanism,
        "fuel_species": fuel_species,
        "experimental_points": len(points),
        "usable_ratios": len(ratios),
        "nonignitions_or_failures": len(points) - len(ratios),
        "median_sim_to_exp": 10 ** statistics.median(log_ratios),
        "geometric_mean_sim_to_exp": 10 ** (sum(log_ratios) / len(log_ratios)),
        "within_factor_2_fraction": sum(0.5 <= r <= 2.0 for r in ratios) / len(ratios),
        "within_factor_3_fraction": sum(1 / 3 <= r <= 3.0 for r in ratios) / len(ratios),
        "minimum_ratio": min(ratios),
        "maximum_ratio": max(ratios),
        "ignition_criterion": "maximum dP/dt",
        "constant_volume_adiabatic": True,
        "failures": failures,
    }
    if low:
        metrics["low_temperature_below_900K_count"] = len(low)
        metrics["low_temperature_median_sim_to_exp"] = 10 ** statistics.median(
            [math.log10(value) for value in low]
        )
    return metrics, rows


def _ntc_strength(series: list[tuple[float, float | None]]) -> float:
    """Largest delay rise after a preceding local minimum; 1 means no NTC."""
    valid = [(temperature, delay) for temperature, delay in series if delay]
    best = 1.0
    for start in range(len(valid) - 1):
        minimum = valid[start][1]
        for end in range(start + 1, len(valid)):
            best = max(best, valid[end][1] / minimum)
            minimum = min(minimum, valid[end][1])
    return best


def parent_retention(
    skeleton: str,
    parent: str,
    fuel: str,
    *,
    oxidizer: str = "O2:1,N2:3.76",
    equivalence_ratio: float = 1.0,
    pressure_bar: float = 40.0,
    temperatures_K: Iterable[float] = range(650, 1101, 50),
    max_time_s: float = 2.0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    skeleton_series: list[tuple[float, float | None]] = []
    parent_series: list[tuple[float, float | None]] = []
    ratios: list[float] = []
    for temperature in temperatures_K:
        sk = constant_volume_ignition(
            skeleton, temperature, pressure_bar, fuel=fuel, oxidizer=oxidizer,
            equivalence_ratio=equivalence_ratio, max_time_s=max_time_s,
        )
        pa = constant_volume_ignition(
            parent, temperature, pressure_bar, fuel=fuel, oxidizer=oxidizer,
            equivalence_ratio=equivalence_ratio, max_time_s=max_time_s,
        )
        skeleton_series.append((temperature, sk.delay_dPdt_s))
        parent_series.append((temperature, pa.delay_dPdt_s))
        ratio = (
            sk.delay_dPdt_s / pa.delay_dPdt_s
            if sk.delay_dPdt_s and pa.delay_dPdt_s else None
        )
        if ratio:
            ratios.append(ratio)
        rows.append({
            "temperature_K": temperature,
            "pressure_bar": pressure_bar,
            "equivalence_ratio": equivalence_ratio,
            "skeleton_delay_dPdt_s": sk.delay_dPdt_s,
            "parent_delay_dPdt_s": pa.delay_dPdt_s,
            "skeleton_to_parent_ratio": ratio,
        })
    if not ratios:
        raise RuntimeError("Parent-retention grid produced no common ignitions.")
    sk_ntc = _ntc_strength(skeleton_series)
    pa_ntc = _ntc_strength(parent_series)
    metrics = {
        "skeleton": skeleton,
        "parent": parent,
        "fuel": fuel,
        "oxidizer": oxidizer,
        "pressure_bar": pressure_bar,
        "equivalence_ratio": equivalence_ratio,
        "common_ignitions": len(ratios),
        "median_skeleton_to_parent": statistics.median(ratios),
        "minimum_skeleton_to_parent": min(ratios),
        "maximum_skeleton_to_parent": max(ratios),
        "skeleton_ntc_strength": sk_ntc,
        "parent_ntc_strength": pa_ntc,
        "ntc_strength_ratio": sk_ntc / pa_ntc if pa_ntc else None,
        "retention_pass": (
            0.8 <= statistics.median(ratios) <= 1.25
            and min(ratios) >= 2 / 3
            and max(ratios) <= 1.5
            and 0.8 <= sk_ntc / pa_ntc <= 1.25
        ),
        "scope": "reduction retention only; not experimental validation",
    }
    return metrics, rows


def _write_outputs(prefix: str, metrics: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    json_path = Path(f"{prefix}.json")
    csv_path = Path(f"{prefix}.csv")
    json_path.write_text(json.dumps({"metrics": metrics, "rows": rows}, indent=2), encoding="utf-8")
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    parent_parser = sub.add_parser("parent", help="Compare skeleton with its parent")
    parent_parser.add_argument("--skeleton", required=True)
    parent_parser.add_argument("--parent", required=True)
    parent_parser.add_argument("--fuel", required=True)
    parent_parser.add_argument("--oxidizer", default="O2:1,N2:3.76")
    parent_parser.add_argument("--phi", type=float, default=1.0)
    parent_parser.add_argument("--pressure-bar", type=float, default=40.0)
    parent_parser.add_argument("--temperatures", default="650:1100:50")
    parent_parser.add_argument("--max-time-s", type=float, default=2.0)
    parent_parser.add_argument("--output-prefix", default="parent_retention")

    chemked_parser = sub.add_parser("chemked", help="Regress against ChemKED data")
    chemked_parser.add_argument("--mechanism", required=True)
    chemked_parser.add_argument("--fuel-species", required=True)
    chemked_parser.add_argument("--data", action="append", required=True)
    chemked_parser.add_argument("--max-pressure-bar", type=float, default=60.0)
    chemked_parser.add_argument("--max-time-s", type=float, default=0.5)
    chemked_parser.add_argument("--output-prefix", default="chemked_regression")

    args = parser.parse_args()
    if args.command == "parent":
        start, stop, step = (int(value) for value in args.temperatures.split(":"))
        metrics, rows = parent_retention(
            args.skeleton, args.parent, args.fuel, oxidizer=args.oxidizer,
            equivalence_ratio=args.phi, pressure_bar=args.pressure_bar,
            temperatures_K=range(start, stop + 1, step), max_time_s=args.max_time_s,
        )
    else:
        points, rejected = load_chemked_points(
            args.data, max_pressure_bar=args.max_pressure_bar)
        metrics, rows = chemked_regression(
            args.mechanism, args.fuel_species, points, max_time_s=args.max_time_s)
        metrics["parser_rejections"] = rejected
    _write_outputs(args.output_prefix, metrics, rows)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
