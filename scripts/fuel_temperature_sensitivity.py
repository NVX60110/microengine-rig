#!/usr/bin/env python3
"""Bounded, reproducible fuel/temperature sensitivity campaign.

This is a constant-volume, adiabatic chemistry screen.  It tests the Fable
fuel-design hypotheses without treating an endpoint slope as feedback or
engine stability.  Ignition delay is the repository's established accepted
step maximum-dP/dt detector (``mechanism_gate.constant_volume_ignition``),
with an explicit +400 K ignition gate and +1000 K integration continuation.

The signed sensitivity is defined as the endpoint secant

    S = ln(tau(975 K) / tau(875 K)) / ln(975 K / 875 K)

for a common ignition criterion.  Ordinary ignition has S < 0.  Eleven
temperatures (10 K spacing) and adjacent local slopes are retained so that
an endpoint secant cannot hide a non-monotonic delay curve.

Run from any working directory with, for example::

    python scripts/fuel_temperature_sensitivity.py --output-dir results

Mechanism paths are resolved relative to the repository root, never cwd.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import sys
from typing import Any, Iterable

import cantera as ct

ROOT = Path(__file__).resolve().parents[1]

# Make the root importable even when invoked from outside the repository.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the repository detector as a reference and to make criterion drift
# visible to reviewers.  The campaign's runner below retains per-point state
# and errors for machine-readable provenance.
from mechanism_gate import constant_volume_ignition


STRICT_RTOL = 1.0e-9
STRICT_ATOL = 1.0e-15
TEMPERATURES_K = tuple(range(875, 976, 10))
PRESSURE_BAR = 40.0
MAX_TIME_S = 0.30
IGNITION_RISE_K = 400.0
INTEGRATION_RISE_K = 1000.0


@dataclass(frozen=True)
class Mechanism:
    name: str
    relative_path: str
    validation_status: str
    caveat: str

    @property
    def path(self) -> Path:
        return ROOT / self.relative_path


MECHANISMS: dict[str, Mechanism] = {
    "zhao_sk39": Mechanism(
        "zhao_sk39", "mechanisms/dme_zhao_sk39.yaml",
        "reduction_retention_only",
        "39-species Zhao reduction; parent retention is not experimental validation.",
    ),
    "zhao_full": Mechanism(
        "zhao_full", "mechanisms/dme_zhao_full.yaml",
        "pressure_decomposition_selection_open",
        "Distributed source activates the 1-atm DME decomposition fit; 40-bar selection is open.",
    ),
    "llnl79": Mechanism(
        "llnl79", "mechanisms/llnl_dme_2004/llnl_dme_2004.yaml",
        "independent_lineage_unvalidated_for_blend",
        "Independent LLNL DME lineage; this blend screen is not direct validation.",
    ),
    "burke": Mechanism(
        "burke", "mechanisms/burke_mech_56_54.yaml",
        "package_recovered_direct_gate_blocked",
        "Burke package loads and species are compatible, but point-level direct validation remains blocked.",
    ),
}


@dataclass(frozen=True)
class Recipe:
    hypothesis: str
    label: str
    fuel: dict[str, float]
    oxidizer: dict[str, float]
    phi: float
    egr_fraction: float | None = None


def _mix(mapping: dict[str, float]) -> str:
    return ",".join(f"{key}:{value:.12g}" for key, value in mapping.items() if value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_species(gas: ct.Solution, composition: dict[str, float]) -> dict[str, float]:
    """Resolve case-only mechanism naming differences without changing chemistry."""
    by_lower: dict[str, str] = {}
    for species in gas.species_names:
        lower = species.lower()
        if lower in by_lower and by_lower[lower] != species:
            raise ValueError(f"Ambiguous case-insensitive species in mechanism: {species}")
        by_lower[lower] = species
    resolved: dict[str, float] = {}
    missing: list[str] = []
    for species, amount in composition.items():
        actual = by_lower.get(species.lower())
        if actual is None:
            missing.append(species)
        else:
            resolved[actual] = amount
    if missing:
        raise ValueError("Missing species: " + ", ".join(missing))
    return resolved


def egr_oxidizer(fraction: float) -> dict[str, float]:
    """Synthetic exhaust recipe used only as a declared frozen-EGR screen."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("EGR fraction must be between 0 and 1.")
    e = fraction
    # Approximate Beta 2.3 exhaust vector from the existing hypothesis note.
    result = {
        "O2": (1 - e) * 0.21 + e * 0.155,
        "N2": (1 - e) * 0.79 + e * 0.75,
    }
    if e:
        result.update({"CO": e * 0.023, "CO2": e * 0.009,
                       "H2O": e * 0.05, "CH4": e * 0.011})
    return result


def recipes() -> tuple[Recipe, ...]:
    """Return the bounded hypothesis matrix; all compositions are explicit."""
    air = {"O2": 1.0, "N2": 3.76}
    pure = {"CH3OCH3": 1.0}
    result: list[Recipe] = [
        Recipe("partner", "dme25_ch4_75", {"CH3OCH3": .25, "CH4": .75}, air, .40),
        Recipe("partner", "dme25_co_75", {"CH3OCH3": .25, "CO": .75}, air, .40),
        Recipe("reference", "pure_dme", pure, air, .40),
    ]
    # Equivalent oxidizer dilution controls: each is a distinct chemistry
    # composition, not a temperature or delay post-correction.
    for label, oxidizer in (
        ("air", air),
        ("n2_plus4", {"O2": 1, "N2": 7.76}),
        ("co2_plus4", {"O2": 1, "N2": 3.76, "CO2": 4}),
        ("h2o_plus2", {"O2": 1, "N2": 3.76, "H2O": 2}),
    ):
        result.append(Recipe("dilution", f"pure_dme_{label}", pure, oxidizer, .40))
        # The central supplied hypothesis is specifically DME/CO plus dilution;
        # keep the complete N2/CO2/H2O table across every primary mechanism.
        result.append(Recipe("partner_dilution", f"dme25_co_75_{label}",
                             {"CH3OCH3": .25, "CO": .75}, oxidizer, .40))
    for phi in (.20, .30, .40):
        result.append(Recipe("lean", f"pure_dme_phi_{phi:.2f}", pure, air, phi))
    for fraction in (0.0, .20, .40):
        result.append(Recipe("egr", f"pure_dme_egr_{fraction:.0%}", pure,
                             egr_oxidizer(fraction), .40, fraction))
    # Supplied partner/fuel-fraction screen: all five partners and all four
    # DME mole fractions on Zhao sk39.  Cross-lineage checks remain limited to
    # the explicit common reference and DME/CO dilution matrix above.
    for partner in ("CH4", "H2", "CO", "C2H6", "C2H4"):
        for x in (.15, .25, .40, .60):
            if x == .25 and partner in ("CH4", "CO"):
                continue  # already represented by the named reference rows
            result.append(Recipe("partner_sweep", f"dme{x:.2f}_{partner.lower()}_{1-x:.2f}",
                                 {"CH3OCH3": x, partner: 1 - x}, air, .40))
    return tuple(result)


def _point(gas: ct.Solution, mechanism_path: Path, temperature_K: float, recipe: Recipe) -> dict[str, Any]:
    """Run one point with the repository detector and preserve failure class."""
    fuel = _resolve_species(gas, recipe.fuel)
    oxidizer = _resolve_species(gas, recipe.oxidizer)
    fuel_text = _mix(fuel)
    oxidizer_text = _mix(oxidizer)
    try:
        # This is the established repository detector.  It uses accepted-step
        # max dP/dt, strict Cantera defaults, +400 K ignition qualification,
        # and +1000 K continuation.  Keeping the call centralized prevents a
        # prototype's largest-temperature-step shortcut from entering here.
        result = constant_volume_ignition(
            str(mechanism_path), temperature_K, PRESSURE_BAR,
            fuel=fuel_text, oxidizer=oxidizer_text, equivalence_ratio=recipe.phi,
            max_time_s=MAX_TIME_S,
            ignition_temperature_rise_K=IGNITION_RISE_K,
            integration_temperature_rise_K=INTEGRATION_RISE_K,
        )
        status = "ignited" if result.ignited else "no_ignition"
        return {
            "status": status,
            "temperature_K": temperature_K,
            "delay_s": result.delay_dPdt_s,
            "peak_dPdt_Pa_s": result.peak_dPdt_Pa_s,
            "final_temperature_K": result.final_temperature_K,
            "final_pressure_bar": result.final_pressure_bar,
            "fuel_species": fuel_text,
            "oxidizer_species": oxidizer_text,
            "ignition_criterion": "accepted-step maximum dP/dt after qualifying +400 K rise",
        }
    except (ct.CanteraError, RuntimeError, ValueError, OverflowError) as exc:
        # Preserve expected chemistry/integration failures; never call them
        # extinction.  Programming defects (e.g. AttributeError) propagate.
        return {
            "status": "numerical_failure",
            "temperature_K": temperature_K,
            "delay_s": None,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "fuel_species": fuel_text,
            "oxidizer_species": oxidizer_text,
            "ignition_criterion": "accepted-step maximum dP/dt after qualifying +400 K rise",
        }


def _local_slope_records(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid = {point["temperature_K"]: point["delay_s"] for point in points
             if point.get("status") == "ignited" and point.get("delay_s")}
    temps = sorted(valid)
    return [{"temperature_low_K": a, "temperature_high_K": b,
             "S": math.log(valid[b] / valid[a]) / math.log(b / a)}
            for a, b in zip(temps, temps[1:])]


def _slopes(points: list[dict[str, Any]]) -> tuple[float | None, list[float]]:
    valid = {point["temperature_K"]: point["delay_s"] for point in points
             if point.get("status") == "ignited" and point.get("delay_s")}
    endpoint = None
    if 875 in valid and 975 in valid:
        endpoint = math.log(valid[975] / valid[875]) / math.log(975 / 875)
    local = [record["S"] for record in _local_slope_records(points)]
    return endpoint, local


def _non_monotonic(points: list[dict[str, Any]]) -> bool | None:
    delays = [point["delay_s"] for point in points
              if point.get("status") == "ignited" and point.get("delay_s")]
    if len(delays) < 3:
        return None
    differences = [b - a for a, b in zip(delays, delays[1:])]
    signs = {1 if x > 0 else -1 for x in differences if x != 0}
    return len(signs) > 1


def run_campaign(mechanism_names: Iterable[str] = ("zhao_sk39", "zhao_full", "llnl79"),
                  *, include_burke: bool = False,
                  temperatures_K: Iterable[int] = TEMPERATURES_K) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    names = list(mechanism_names)
    if include_burke and "burke" not in names:
        names.append("burke")
    unknown = [name for name in names if name not in MECHANISMS]
    if unknown:
        raise ValueError(f"Unknown mechanisms: {', '.join(unknown)}")
    temps = tuple(int(t) for t in temperatures_K)
    if len(temps) < 3 or temps[0] != 875 or temps[-1] != 975 or any(b <= a for a, b in zip(temps, temps[1:])):
        raise ValueError("Temperature grid must be increasing, include 875 K and 975 K, and have >=3 points.")
    spacings = sorted({b - a for a, b in zip(temps, temps[1:])})
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for name in names:
        mechanism = MECHANISMS[name]
        if not mechanism.path.is_file():
            raise FileNotFoundError(mechanism.path)
        gas = ct.Solution(str(mechanism.path))
        for recipe in recipes():
            # Partner breadth is intentionally confined to Zhao sk39 to keep
            # this campaign bounded; the core/dilution/lean/EGR cases run on
            # every declared mechanism.  All mechanisms still share the same
            # CH4, CO, and pure-DME reference rows.
            if recipe.hypothesis == "partner_sweep" and name != "zhao_sk39":
                continue
            try:
                _resolve_species(gas, recipe.fuel)
                _resolve_species(gas, recipe.oxidizer)
            except ValueError as exc:
                summaries.append({"mechanism": name, "case": recipe.label,
                                  "status": "incompatible", "error": str(exc)})
                continue
            points = [_point(gas, mechanism.path, temperature, recipe) for temperature in temps]
            endpoint, local = _slopes(points)
            local_records = _local_slope_records(points)
            case_id = f"{name}:{recipe.label}:phi{recipe.phi:.2f}"
            for point in points:
                rows.append({
                    "case_id": case_id, "hypothesis": recipe.hypothesis,
                    "case": recipe.label, "mechanism": name,
                    "mechanism_path": mechanism.relative_path,
                    "temperature_K": point["temperature_K"], "pressure_bar": PRESSURE_BAR,
                    "equivalence_ratio": recipe.phi,
                    "egr_fraction": recipe.egr_fraction,
                    "fuel": _mix(recipe.fuel), "oxidizer": _mix(recipe.oxidizer),
                    "status": point["status"], "delay_s": point.get("delay_s"),
                    "delay_ms": point.get("delay_s") * 1000 if point.get("delay_s") else None,
                    "peak_dPdt_Pa_s": point.get("peak_dPdt_Pa_s"),
                    "final_temperature_K": point.get("final_temperature_K"),
                    "final_pressure_bar": point.get("final_pressure_bar"),
                    "error_type": point.get("error_type"), "error": point.get("error"),
                    "ignition_criterion": point["ignition_criterion"],
                })
            summaries.append({
                "case_id": case_id, "hypothesis": recipe.hypothesis,
                "case": recipe.label, "mechanism": name,
                "mechanism_path": mechanism.relative_path,
                "equivalence_ratio": recipe.phi, "egr_fraction": recipe.egr_fraction,
                "status": "ok" if all(p["status"] != "numerical_failure" for p in points) else "numerical_failure",
                "ignited_points": sum(p["status"] == "ignited" for p in points),
                "temperature_points": len(points),
                "S_endpoint_875_975": endpoint,
                "local_S_min": min(local) if local else None,
                "local_S_max": max(local) if local else None,
                "local_S_by_interval": local_records,
                "non_monotonic_delay": _non_monotonic(points),
                "tau_925_ms": next((p["delay_s"] * 1000 for p in points if p["temperature_K"] == 925 and p.get("delay_s")), None),
                "endpoint_sign_interpretation": (
                    "ordinary_ignition_negative" if endpoint is not None and endpoint < 0
                    else "positive_NTC_like_shape_hypothesis_only" if endpoint is not None and endpoint > 0
                    else "insufficient_common_ignitions"
                ),
            })
    metadata = {
        "experiment": "fuel_temperature_sensitivity",
        "description": "Bounded constant-volume fuel partner, dilution, lean, and frozen-EGR sensitivity screen.",
        "cantera_version": ct.__version__,
        "repository_root": ".",
        "pressure_bar": PRESSURE_BAR,
        "temperature_grid_K": list(temps),
        "temperature_range_K": [875, 975],
        "temperature_spacing_K": spacings[0] if len(spacings) == 1 else spacings,
        "signed_s_definition": "S = ln(tau_975 / tau_875) / ln(975 / 875)",
        "sign_convention": "ordinary ignition has S < 0; positive S is NTC-like shape only, not self-stabilization.",
        "ignition_criterion": "repository mechanism_gate.constant_volume_ignition: accepted-step maximum dP/dt; delay qualified only after +400 K and integration continued to +1000 K",
        "integrator": {"rtol": STRICT_RTOL, "atol": STRICT_ATOL, "max_time_s": MAX_TIME_S},
        "mechanisms": [{"name": MECHANISMS[n].name, "path": MECHANISMS[n].relative_path,
                        "sha256": _sha256(MECHANISMS[n].path),
                        "validation_status": MECHANISMS[n].validation_status,
                        "caveat": MECHANISMS[n].caveat} for n in names],
        "partner_screen_scope": "CH4, H2, CO, C2H6, C2H4 at 15/85, 25/75, 40/60, and 60/40 DME/partner on Zhao sk39; core CH4, CO and pure-DME references plus full DME/CO dilution table cross-checked on every declared mechanism.",
        "egr_scope": "single-pass frozen synthetic Beta-2.3-like exhaust vector at 0, 20, 40%; no repeated-cycle feedback claim.",
        "prototype_provenance": {
            "files": [
                "external attachment 1-fuel-design.py",
                "external attachment 2-fuel-design2.py",
            ],
            "sha256": {
                "1-fuel-design.py": "633689435df702507153f2d177102095766ca07b0cf239cd5c011a5b901904a4",
                "2-fuel-design2.py": "af43afc8bd090cf14d25e0ee1737a9a38d36e965fc69d44afd3b8b3815429693",
            },
            "trust": "hypothesis_generating_untrusted; largest-temperature-step detector not used",
        },
        "summary_count": len(summaries),
        "row_count": len(rows),
    }
    metadata["summaries"] = summaries
    return rows, metadata


def write_outputs(rows: list[dict[str, Any]], metadata: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "fuel_temperature_sensitivity.csv"
    json_path = output_dir / "fuel_temperature_sensitivity.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0]) if rows else ["status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "rows": rows}, handle, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--include-burke", action="store_true",
                        help="Include compatible Burke screening rows; direct validation remains blocked.")
    parser.add_argument("--mechanisms", default="zhao_sk39,zhao_full,llnl79",
                        help="Comma-separated mechanism keys (default: three primary lineages).")
    args = parser.parse_args(argv)
    rows, metadata = run_campaign(args.mechanisms.split(","), include_burke=args.include_burke)
    write_outputs(rows, metadata, args.output_dir.resolve())
    print(json.dumps({key: metadata[key] for key in (
        "experiment", "cantera_version", "temperature_grid_K", "summary_count", "row_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
