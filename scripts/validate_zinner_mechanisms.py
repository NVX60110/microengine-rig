#!/usr/bin/env python3
"""Compare project Cantera mechanisms with the exact Zinner 2008 table.

This is a bounded chemistry-validation lane, not an engine prediction.  Each
row uses the Zinner blend, equivalence ratio, and either the thesis-adjusted
or original reflected-shock state.  The reactor is constant-volume/adiabatic
and uses the repository's strict maximum-dP/dt detector.  Zinner reports an
endwall pressure-rise ignition event; therefore the result is a declared
criterion proxy, not a claim that a 0-D reactor reproduces the shock-tube
facility in full.

Run from the repository root::

    python scripts/validate_zinner_mechanisms.py --basis adjusted

The default four-mechanism run is intentionally reproducible and writes a
compact CSV plus JSON summary.  No mechanism parameters are fitted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any

import cantera as ct

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mechanism_gate import constant_volume_ignition


MECHANISMS: dict[str, str] = {
    "zhao_sk39": "mechanisms/dme_zhao_sk39.yaml",
    "zhao_full": "mechanisms/dme_zhao_full.yaml",
    "llnl79": "mechanisms/llnl_dme_2004/llnl_dme_2004.yaml",
    "burke56_54": "mechanisms/burke_mech_56_54.yaml",
}
DATA = ROOT / "data" / "zinner2008" / "shock_tube_tabulated.csv"

STRICT_RTOL = 1.0e-9
STRICT_ATOL = 1.0e-15
MAX_TIME_S = 0.50
QUALIFICATION_RISE_K = 400.0
CONTINUATION_RISE_K = 1000.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path = DATA) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 167:
        raise ValueError(f"expected 167 Zinner rows, found {len(rows)}")
    return rows


def _species_map(gas: ct.Solution) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in gas.species_names:
        key = name.lower()
        if key in result and result[key] != name:
            raise ValueError(f"case-insensitive species collision: {result[key]}, {name}")
        result[key] = name
    return result


def _composition(row: dict[str, str], gas: ct.Solution) -> dict[str, float]:
    """Create the exact listed blend at the listed phi using an air basis."""
    names = _species_map(gas)
    ch4 = names.get("ch4")
    dme = names.get("ch3och3") or names.get("dme")
    o2 = names.get("o2")
    n2 = names.get("n2")
    missing = [label for label, value in (("CH4", ch4), ("CH3OCH3", dme),
                                           ("O2", o2), ("N2", n2)) if value is None]
    if missing:
        raise ValueError(f"mechanism missing required species: {missing}")
    fuel = f"{ch4}:{float(row['ch4_volume_fraction']):.12g},{dme}:{float(row['dme_volume_fraction']):.12g}"
    oxidizer = f"{o2}:1,{n2}:3.76"
    # Use a temporary gas only to apply Cantera's equivalence-ratio convention,
    # then return the normalized composition mapping for constant_volume_ignition.
    gas.set_equivalence_ratio(float(row["equivalence_ratio"]), fuel, oxidizer)
    return {name: float(value) for name, value in zip(gas.species_names, gas.X) if value > 0.0}


def _state(row: dict[str, str], basis: str) -> tuple[float, float]:
    if basis == "adjusted":
        return float(row["temperature_adjusted_K"]), float(row["pressure_adjusted_atm"]) * 1.01325
    if basis == "original":
        return float(row["temperature_original_K"]), float(row["pressure_original_atm"]) * 1.01325
    raise ValueError(f"unknown state basis: {basis}")


def _run_point(row: dict[str, str], mechanism_key: str, basis: str) -> dict[str, Any]:
    mechanism_path = ROOT / MECHANISMS[mechanism_key]
    gas = ct.Solution(str(mechanism_path))
    temperature, pressure_bar = _state(row, basis)
    measured_s = float(row["ignition_delay_us"]) * 1e-6
    base: dict[str, Any] = {
        "record_id": row["record_id"],
        "mixture_number": int(row["mixture_number"]),
        "mixture_label": row["mixture_label"],
        "equivalence_ratio": float(row["equivalence_ratio"]),
        "temperature_basis": basis,
        "temperature_K": temperature,
        "pressure_bar": pressure_bar,
        "measured_ignition_delay_s": measured_s,
        "ignition_target": row["ignition_target"],
        "ignition_type": row["ignition_type"],
        "facility": row["facility"],
        "provenance": row["provenance"],
        "mechanism": mechanism_key,
        "mechanism_path": MECHANISMS[mechanism_key],
        "criterion": "constant-volume adiabatic max accepted-step dP/dt after +400 K rise; +1000 K continuation",
        "comparison_note": "Zinner endwall pressure-rise delay compared with a 0-D dP/dt criterion proxy",
    }
    try:
        composition = _composition(row, gas)
        result = constant_volume_ignition(
            str(mechanism_path), temperature, pressure_bar,
            composition=composition,
            max_time_s=MAX_TIME_S,
            ignition_temperature_rise_K=QUALIFICATION_RISE_K,
            integration_temperature_rise_K=CONTINUATION_RISE_K,
        )
        simulated = result.delay_dPdt_s
        ratio = simulated / measured_s if simulated is not None and simulated > 0 else None
        base.update({
            "status": "usable" if ratio is not None else "no_ignition",
            "simulated_ignition_delay_s": simulated,
            "simulated_to_experiment_ratio": ratio,
            "final_temperature_K": result.final_temperature_K,
            "final_pressure_bar": result.final_pressure_bar,
            "peak_dPdt_Pa_s": result.peak_dPdt_Pa_s,
            "ignited": result.ignited,
        })
    except (ct.CanteraError, RuntimeError, ValueError, OverflowError) as exc:
        base.update({
            "status": "numerical_failure",
            "simulated_ignition_delay_s": None,
            "simulated_to_experiment_ratio": None,
            "ignited": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
    return base


def _summary(rows: list[dict[str, Any]], mechanisms: list[str]) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        ratio = row.get("simulated_to_experiment_ratio")
        if ratio is not None and math.isfinite(float(ratio)) and float(ratio) > 0:
            groups.setdefault(str(row["mechanism"]), []).append(float(ratio))

    def metrics(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"usable": 0, "median_ratio": None, "within_factor_2": None,
                    "within_factor_3": None, "min_ratio": None, "max_ratio": None}
        logs = [math.log10(value) for value in values]
        return {
            "usable": len(values),
            "median_ratio": 10 ** statistics.median(logs),
            "geometric_mean_ratio": 10 ** (sum(logs) / len(logs)),
            "within_factor_2": sum(0.5 <= value <= 2.0 for value in values) / len(values),
            "within_factor_3": sum(1 / 3 <= value <= 3.0 for value in values) / len(values),
            "min_ratio": min(values), "max_ratio": max(values),
        }

    def grouped(field: str) -> dict[str, dict[str, Any]]:
        labels = sorted({str(row[field]) for row in rows})
        result: dict[str, dict[str, Any]] = {}
        for label in labels:
            result[label] = {}
            for mechanism in mechanisms:
                values = [float(row["simulated_to_experiment_ratio"]) for row in rows
                          if str(row[field]) == label and row["mechanism"] == mechanism
                          and row.get("simulated_to_experiment_ratio") is not None]
                result[label][mechanism] = metrics(values)
        return result

    for row in rows:
        pressure_atm = float(row["pressure_bar"]) / 1.01325
        row["pressure_band"] = "<10_atm" if pressure_atm < 10 else ("10_to_20_atm" if pressure_atm < 20 else ">=20_atm")
        row["temperature_regime"] = "low_T_le_1175K" if float(row["temperature_K"]) <= 1175 else "high_T_gt_1175K"
        row["temperature_bin_100K"] = f"{100 * math.floor(float(row['temperature_K']) / 100):04.0f}-{100 * math.floor(float(row['temperature_K']) / 100) + 99:04.0f}K"

    return {
        "rows": len(rows),
        "mechanisms": list(mechanisms),
        "usable_rows": sum(row.get("status") == "usable" for row in rows),
        "no_ignition_rows": sum(row.get("status") == "no_ignition" for row in rows),
        "numerical_failure_rows": sum(row.get("status") == "numerical_failure" for row in rows),
        "by_mechanism": {mechanism: metrics(groups.get(mechanism, [])) for mechanism in mechanisms},
        "by_mixture": grouped("mixture_label"),
        "by_equivalence_ratio": grouped("equivalence_ratio"),
        "by_pressure_band": grouped("pressure_band"),
        "by_temperature_regime": grouped("temperature_regime"),
        "by_temperature_bin_100K": grouped("temperature_bin_100K"),
    }


def run(basis: str, mechanisms: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    unknown = sorted(set(mechanisms) - set(MECHANISMS))
    if unknown:
        raise ValueError(f"unknown mechanisms: {unknown}")
    source_rows = load_rows()
    # Preserve deterministic CSV order and do not parallelize within a point;
    # Cantera's strict integrator settings are part of the validation provenance.
    result_rows = [_run_point(row, mechanism, basis)
                   for mechanism in mechanisms for row in source_rows]
    summary = _summary(result_rows, mechanisms)
    summary.update({
        "source": "Zinner 2008 Appendix TABULATED DATA",
        "source_csv": str(DATA.relative_to(ROOT)),
        "state_basis": basis,
        "cantera_version": ct.__version__,
        "strict_rtol": STRICT_RTOL,
        "strict_atol": STRICT_ATOL,
        "max_time_s": MAX_TIME_S,
        "ignition_criterion": "project max accepted-step dP/dt; proxy for Zinner endwall pressure-rise event",
        "mechanism_sha256": {name: _sha256(ROOT / path) for name, path in MECHANISMS.items() if name in mechanisms},
        "evidence_class": "PROJECT MODEL RESULT compared with MEASURED EVIDENCE — Zinner shock-tube table",
        "caveat": "constant-volume adiabatic 0-D screening is not a shock-tube facility model; no mechanism tuning",
    })
    return summary, result_rows


def write_outputs(prefix: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with prefix.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", choices=("adjusted", "original"), default="adjusted")
    parser.add_argument("--mechanisms", default=",".join(MECHANISMS),
                        help="comma-separated mechanism keys")
    parser.add_argument("--output-prefix", type=Path,
                        default=ROOT / "results" / "zinner_mechanism_validation_adjusted")
    args = parser.parse_args()
    mechanisms = [item.strip() for item in args.mechanisms.split(",") if item.strip()]
    summary, rows = run(args.basis, mechanisms)
    write_outputs(args.output_prefix, summary, rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
