#!/usr/bin/env python3
"""Strict CSV ingestion/regression for Burke et al. CH4/DME ignition-delay data.

This module exists because the original Burke 2015 point data may arrive as a
supplementary table or a carefully digitized CSV rather than ChemKED. It keeps
facility, provenance, uncertainty, mixture label, and ignition criterion with
every point and refuses to silently compare unlike ignition definitions.

Supported simulated ignition criteria today:
- pressure / d/dt max  -> maximum dP/dt
- temperature / d/dt max -> maximum dT/dt

Other experimental criteria are preserved by the parser but reported as
unsupported by the regression until a matching diagnostic is implemented.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable

import cantera as ct

from mechanism_gate import ExperimentalPoint, constant_volume_ignition


REQUIRED_COLUMNS = {
    "temperature_K",
    "pressure_bar",
    "ignition_delay_s",
    "equivalence_ratio",
    "composition_json",
    "ignition_target",
    "ignition_type",
    "facility",
    "mixture_label",
    "provenance",
}
OPTIONAL_NUMERIC_COLUMNS = (
    "ignition_delay_uncertainty_fraction",
    "temperature_uncertainty_K",
    "pressure_uncertainty_bar",
)


def _finite_positive(value: str, field: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be finite and > 0")
    return number


def _optional_nonnegative(value: str | None, field: str) -> float | None:
    if value is None or not value.strip():
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be finite and >= 0")
    return number


def _composition(text: str) -> dict[str, float]:
    raw = json.loads(text)
    if not isinstance(raw, dict) or not raw:
        raise ValueError("composition_json must be a non-empty JSON object")
    result: dict[str, float] = {}
    total = 0.0
    for species, amount in raw.items():
        number = float(amount)
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"invalid amount for species {species!r}")
        if number > 0:
            result[str(species)] = number
            total += number
    if total <= 0:
        raise ValueError("composition_json has no positive species amounts")
    return result


def load_burke_csv(
    paths: Iterable[str | Path],
    *,
    max_pressure_bar: float | None = None,
) -> tuple[list[ExperimentalPoint], dict[str, dict[str, Any]], list[dict[str, str]]]:
    """Load strict Burke-style CSV points with explicit per-point metadata."""
    points: list[ExperimentalPoint] = []
    metadata: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []

    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            missing = sorted(REQUIRED_COLUMNS - headers)
            if missing:
                raise ValueError(f"{path} missing required columns: {missing}")
            for row_number, row in enumerate(reader, start=2):
                label = f"{path}#{row_number}"
                try:
                    temperature = _finite_positive(row["temperature_K"], "temperature_K")
                    pressure = _finite_positive(row["pressure_bar"], "pressure_bar")
                    delay = _finite_positive(row["ignition_delay_s"], "ignition_delay_s")
                    phi = _finite_positive(row["equivalence_ratio"], "equivalence_ratio")
                    composition = _composition(row["composition_json"])
                    target = row["ignition_target"].strip().lower()
                    kind = row["ignition_type"].strip().lower()
                    facility = row["facility"].strip()
                    mixture_label = row["mixture_label"].strip()
                    provenance = row["provenance"].strip()
                    if not target or not kind or not facility or not mixture_label or not provenance:
                        raise ValueError("criterion/facility/mixture_label/provenance must be non-empty")
                    uncertainties = {
                        name: _optional_nonnegative(row.get(name), name)
                        for name in OPTIONAL_NUMERIC_COLUMNS
                    }
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    rejected.append({"point": label, "reason": f"{type(exc).__name__}: {exc}"})
                    continue
                if max_pressure_bar is not None and pressure > max_pressure_bar:
                    rejected.append({"point": label, "reason": "above pressure filter"})
                    continue

                points.append(ExperimentalPoint(
                    temperature,
                    pressure,
                    delay,
                    phi,
                    composition,
                    label,
                    target,
                    kind,
                ))
                metadata[label] = {
                    "facility": facility,
                    "mixture_label": mixture_label,
                    "provenance": provenance,
                    "notes": (row.get("notes") or "").strip(),
                    **uncertainties,
                }

    if not points:
        raise RuntimeError(
            f"Zero Burke CSV points loaded; {len(rejected)} rows were rejected."
        )
    return points, metadata, rejected


def _aliases(items: Iterable[str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"alias must be SOURCE=DEST, got {item!r}")
        source, destination = (part.strip() for part in item.split("=", 1))
        if not source or not destination:
            raise ValueError(f"alias must be SOURCE=DEST, got {item!r}")
        aliases[source] = destination
    return aliases


def _map_composition(
    composition: dict[str, float], gas: ct.Solution, aliases: dict[str, str]
) -> dict[str, float]:
    def resolve(source: str) -> str:
        """Follow explicit aliases so schema synonyms can map in two steps.

        Burke CSVs use the repository schema (``CH3OCH3``) or may use the
        readable ``DME`` synonym.  A lower-case CHEMKIN phase can therefore be
        configured with ``DME=CH3OCH3`` and ``CH3OCH3=ch3och3`` without making
        the dataset's schema depend on one mechanism's spelling.
        """
        current = source
        visited: set[str] = set()
        while current in aliases:
            if current in visited:
                raise ValueError(f"cyclic species alias involving {source!r}")
            visited.add(current)
            current = aliases[current]
        return current

    mapped: dict[str, float] = {}
    missing: list[str] = []
    for source, amount in composition.items():
        destination = resolve(source)
        if destination not in gas.species_names:
            missing.append(f"{source}->{destination}")
            continue
        mapped[destination] = mapped.get(destination, 0.0) + amount
    if missing:
        raise ValueError("mechanism missing composition species: " + ", ".join(missing))
    return mapped


def _select_delay(point: ExperimentalPoint, result: Any) -> float | None:
    target = point.ignition_target.strip().lower()
    kind = point.ignition_type.strip().lower()
    if kind != "d/dt max":
        return None
    if target == "pressure":
        return result.delay_dPdt_s
    if target == "temperature":
        return result.delay_dTdt_s
    return None


def _group_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key, "")), []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for label, group in sorted(groups.items()):
        ratios = [
            float(row["simulated_to_experiment_ratio"])
            for row in group
            if row.get("simulated_to_experiment_ratio") is not None
            and float(row["simulated_to_experiment_ratio"]) > 0
        ]
        summary: dict[str, Any] = {
            "points": len(group),
            "usable_ratios": len(ratios),
            "nonignitions_or_unsupported": len(group) - len(ratios),
        }
        if ratios:
            summary.update({
                "median_sim_to_exp": 10 ** statistics.median([math.log10(v) for v in ratios]),
                "within_factor_2_fraction": sum(0.5 <= v <= 2.0 for v in ratios) / len(ratios),
            })
        result[label] = summary
    return result


def burke_regression(
    mechanism: str,
    points: list[ExperimentalPoint],
    metadata: dict[str, dict[str, Any]],
    *,
    aliases: dict[str, str] | None = None,
    max_time_s: float = 0.5,
    phase: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run Burke points without silently substituting an ignition criterion."""
    gas = ct.Solution(mechanism, phase) if phase else ct.Solution(mechanism)
    aliases = dict(aliases or {})
    # Common spelling/case aliases. Explicit CLI aliases override these.
    defaults = {
        "DME": "CH3OCH3",
        "ch3och3": "CH3OCH3",
        "o2": "O2",
        "n2": "N2",
        "ch4": "CH4",
    }
    for source, destination in defaults.items():
        aliases.setdefault(source, destination)

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    ratios: list[float] = []

    for point in points:
        meta = metadata.get(point.source_file, {})
        base = {
            "temperature_K": point.temperature_K,
            "pressure_bar": point.pressure_bar,
            "ignition_delay_s": point.ignition_delay_s,
            "equivalence_ratio": point.equivalence_ratio,
            "composition": point.composition,
            "source_file": point.source_file,
            "ignition_target": point.ignition_target,
            "ignition_type": point.ignition_type,
            **meta,
        }
        try:
            composition = _map_composition(point.composition, gas, aliases)
            supported = (
                point.ignition_type.strip().lower() == "d/dt max"
                and point.ignition_target.strip().lower() in {"pressure", "temperature"}
            )
            if not supported:
                raise ValueError(
                    f"unsupported ignition criterion {point.ignition_target!r}/"
                    f"{point.ignition_type!r}; preserve point but do not compare"
                )
            result = constant_volume_ignition(
                mechanism,
                point.temperature_K,
                point.pressure_bar,
                composition=composition,
                phase=phase,
                max_time_s=max_time_s,
            )
            simulated = _select_delay(point, result)
            ratio = simulated / point.ignition_delay_s if simulated else None
            if ratio is not None and ratio > 0:
                ratios.append(ratio)
            rows.append({
                **base,
                "simulated_delay_s": simulated,
                "simulated_to_experiment_ratio": ratio,
                "ignited": result.ignited,
                "comparison_status": "ok" if ratio is not None else "nonignition",
            })
        except (ct.CanteraError, RuntimeError, ValueError) as exc:
            failures.append({"point": point.source_file, "reason": f"{type(exc).__name__}: {exc}"})
            rows.append({
                **base,
                "simulated_delay_s": None,
                "simulated_to_experiment_ratio": None,
                "ignited": False,
                "comparison_status": "unsupported_or_failed",
                "comparison_error": f"{type(exc).__name__}: {exc}",
            })

    if not ratios:
        raise RuntimeError(f"Regression produced zero usable ratios; {len(failures)} failures.")

    logs = [math.log10(value) for value in ratios]
    low = [
        row["simulated_to_experiment_ratio"]
        for row in rows
        if row["temperature_K"] < 900 and row.get("simulated_to_experiment_ratio")
    ]
    metrics: dict[str, Any] = {
        "mechanism": mechanism,
        "experimental_points": len(points),
        "usable_ratios": len(ratios),
        "nonignitions_or_unsupported": len(points) - len(ratios),
        "median_sim_to_exp": 10 ** statistics.median(logs),
        "geometric_mean_sim_to_exp": 10 ** (sum(logs) / len(logs)),
        "within_factor_2_fraction": sum(0.5 <= r <= 2.0 for r in ratios) / len(ratios),
        "within_factor_3_fraction": sum(1 / 3 <= r <= 3.0 for r in ratios) / len(ratios),
        "minimum_ratio": min(ratios),
        "maximum_ratio": max(ratios),
        "constant_volume_adiabatic": True,
        "supported_criteria": ["pressure/d/dt max", "temperature/d/dt max"],
        "failures": failures,
        "by_facility": _group_metrics(rows, "facility"),
        "by_mixture": _group_metrics(rows, "mixture_label"),
        "by_pressure_bar": _group_metrics(rows, "pressure_bar"),
    }
    if low:
        metrics["low_temperature_below_900K_count"] = len(low)
        metrics["low_temperature_median_sim_to_exp"] = 10 ** statistics.median(
            [math.log10(float(value)) for value in low]
        )
    return metrics, rows


def _write_outputs(prefix: str, metrics: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    json_path = Path(f"{prefix}.json")
    csv_path = Path(f"{prefix}.csv")
    json_path.write_text(json.dumps({"metrics": metrics, "rows": rows}, indent=2), encoding="utf-8")
    if rows:
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanism", required=True)
    parser.add_argument("--data", action="append", required=True)
    parser.add_argument("--alias", action="append", default=[], help="species alias SOURCE=DEST")
    parser.add_argument("--phase")
    parser.add_argument("--max-pressure-bar", type=float)
    parser.add_argument("--max-time-s", type=float, default=0.5)
    parser.add_argument("--output-prefix", default="burke2015_regression")
    args = parser.parse_args()

    points, metadata, rejected = load_burke_csv(
        args.data, max_pressure_bar=args.max_pressure_bar
    )
    metrics, rows = burke_regression(
        args.mechanism,
        points,
        metadata,
        aliases=_aliases(args.alias),
        max_time_s=args.max_time_s,
        phase=args.phase,
    )
    metrics["parser_rejections"] = rejected
    _write_outputs(args.output_prefix, metrics, rows)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
