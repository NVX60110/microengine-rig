#!/usr/bin/env python3
"""Validate and derive transferable quantities from the thermal-literature CSVs.

The input files deliberately separate source leads from point observations.
This script never fills missing temperatures, never converts a reported delta
into an absolute temperature, and never promotes a non-transferable result into
the engine model.  It derives local piston-minus-liner and normalized
temperature quantities only when the same row (or explicitly grouped profile
rows) contains all required values.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "data" / "thermal" / "literature_sources.csv"
DEFAULT_MEASUREMENTS = ROOT / "data" / "thermal" / "literature_measurements.csv"


def _number(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric value: {value!r}")
    return number


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no header")
        return list(reader)


def derive(sources: list[dict[str, str]], measurements: list[dict[str, str]]) -> dict[str, Any]:
    source_ids = {row.get("source_id", "") for row in sources}
    if "" in source_ids:
        raise ValueError("literature_sources.csv contains a blank source_id")
    derived: list[dict[str, Any]] = []
    unpaired_temperature_rows = 0
    for row in measurements:
        source_id = row.get("source_id", "")
        if source_id not in source_ids:
            raise ValueError(f"measurement {row.get('measurement_id', '')} references unknown source {source_id!r}")
        value = _number(row.get("value"))
        if value is not None:
            derived.append({
                "derived_id": row.get("measurement_id", "") + ":reported",
                "source_id": source_id,
                "engine_id": row.get("engine_id", ""),
                "metric": row.get("quantity", ""),
                "value": value,
                "unit": row.get("unit", ""),
                "uncertainty": row.get("uncertainty", ""),
                "classification": row.get("classification", ""),
                "transferability": row.get("transferability", ""),
                "derivation": "reported value copied from literature_measurements.csv; no transformation",
                "source_locator": row.get("source_locator", ""),
                "notes": row.get("notes", ""),
            })
        piston = _number(row.get("piston_temperature_K"))
        liner = _number(row.get("liner_temperature_K"))
        ambient = _number(row.get("ambient_temperature_K"))
        if piston is None or liner is None:
            if row.get("piston_temperature_K", "").strip() or row.get("liner_temperature_K", "").strip():
                unpaired_temperature_rows += 1
            continue
        derived.append({
            "derived_id": row.get("measurement_id", "") + ":piston_minus_liner",
            "source_id": source_id,
            "engine_id": row.get("engine_id", ""),
            "metric": "piston_minus_liner_temperature",
            "value": piston - liner,
            "unit": "K",
            "uncertainty": "",
            "classification": "calculated",
            "transferability": row.get("transferability", ""),
            "derivation": "piston_temperature_K - liner_temperature_K from one local paired row",
            "source_locator": row.get("source_locator", ""),
            "notes": row.get("notes", ""),
        })
        if ambient is not None and piston > ambient and liner > ambient:
            denominator = piston - ambient
            if denominator != 0:
                derived.append({
                    "derived_id": row.get("measurement_id", "") + ":normalized_liner",
                    "source_id": source_id,
                    "engine_id": row.get("engine_id", ""),
                    "metric": "(liner_minus_ambient)/(piston_minus_ambient)",
                    "value": (liner - ambient) / denominator,
                    "unit": "1",
                    "uncertainty": "",
                    "classification": "calculated",
                    "transferability": row.get("transferability", ""),
                    "derivation": "(liner_temperature_K - ambient_temperature_K) / (piston_temperature_K - ambient_temperature_K)",
                    "source_locator": row.get("source_locator", ""),
                    "notes": row.get("notes", ""),
                })
    return {
        "classification": {
            "literature_reported": "values copied from an identified source row",
            "calculated": "only arithmetic from complete local paired fields",
            "assumed": "none",
            "extrapolated": "none",
        },
        "source_count": len(sources),
        "measurement_count": len(measurements),
        "reported_value_count": sum(_number(row.get("value")) is not None for row in measurements),
        "paired_temperature_count": sum(_number(row.get("piston_temperature_K")) is not None and _number(row.get("liner_temperature_K")) is not None for row in measurements),
        "unpaired_temperature_rows": unpaired_temperature_rows,
        "derived_count": len(derived),
        "derived": derived,
    }


def write_derived_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["derived_id", "source_id", "engine_id", "metric", "value", "unit", "uncertainty", "classification", "transferability", "derivation", "source_locator", "notes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--measurements", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument("--output-json", type=Path, default=ROOT / "data" / "thermal" / "literature_transferables.json")
    parser.add_argument("--output-csv", type=Path, default=ROOT / "data" / "thermal" / "literature_transferables.csv")
    args = parser.parse_args()
    result = derive(_read(args.sources), _read(args.measurements))
    result["sources_file"] = str(args.sources.relative_to(ROOT)) if args.sources.is_relative_to(ROOT) else args.sources.name
    result["measurements_file"] = str(args.measurements.relative_to(ROOT)) if args.measurements.is_relative_to(ROOT) else args.measurements.name
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    write_derived_csv(args.output_csv, result["derived"])
    print(json.dumps({key: result[key] for key in ("source_count", "measurement_count", "reported_value_count", "paired_temperature_count", "derived_count", "output_json" ) if key in result} | {"output_json": str(args.output_json), "output_csv": str(args.output_csv)}, indent=2))


if __name__ == "__main__":
    main()
