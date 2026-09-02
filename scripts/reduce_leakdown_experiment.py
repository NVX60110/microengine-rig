#!/usr/bin/env python3
"""Reduce warm leak-down/blow-by measurements without inventing calibration.

The input is a strict row-oriented CSV described by
``data/leakage/measurement_schema.csv``.  Each diameter/temperature pair is
local to one axial station.  Static direct-flow rows are compared with the
existing annulus equation; dynamic blow-by rows remain a separate lane and are
never inverted to a steady CdA without a pressure history.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from physics.annulus import R_AIR, GAMMA, annulus_mdot, equiv_area
from physics.thermal_clearance import ThermalStrainProfile, calculate_clearance

MATERIALS_PATH = ROOT / "data" / "materials" / "thermal_properties.json"
MODES = {"static_direct", "static_differential", "dynamic_blowby"}
# These fields are marked required in measurement_schema.csv and are metadata,
# not numeric channels that can be validated by _positive().
REQUIRED_VALUE_FIELDS = (
    "record_id", "run_id", "reference_cylinder_id", "timestamp_utc", "mode",
    "repeat_number", "stabilization_criterion", "piston_material", "liner_material",
    "lubricant", "lubricant_condition", "gas", "notes",
)
H3_PRESSURE_DECIMALS = 2
H3_TEMPERATURE_DECIMALS = 1


def _float(row: dict[str, str], key: str, *, required: bool = False) -> float | None:
    value = row.get(key, "")
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError(f"missing {key}")
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{key} is not numeric: {value!r}") from error
    if not math.isfinite(number):
        raise ValueError(f"{key} must be finite")
    return number


def _positive(row: dict[str, str], key: str, *, required: bool = False) -> float | None:
    value = _float(row, key, required=required)
    if value is not None and value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


def load_profiles() -> dict[str, ThermalStrainProfile]:
    payload = json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))
    return {
        item["id"]: ThermalStrainProfile(tuple(tuple(point) for point in item["strain_points"]))
        for item in payload["materials"]
    }


def required_schema_fields() -> set[str]:
    """Return fields marked required in the versioned measurement schema."""
    with (ROOT / "data" / "leakage" / "measurement_schema.csv").open(newline="", encoding="utf-8") as handle:
        return {row["field"] for row in csv.DictReader(handle) if row.get("required", "").strip().lower() == "yes"}


def validate_input_header(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise ValueError("input CSV has no header")
    missing = sorted(required_schema_fields() - set(fieldnames))
    if missing:
        raise ValueError("input CSV is missing required schema fields: " + ", ".join(missing))


def gas_properties(row: dict[str, str]) -> tuple[float, float]:
    gas = row["gas"].strip().lower()
    if gas in {"air", "dry_air"}:
        default_r, default_gamma = R_AIR, GAMMA
    elif gas in {"nitrogen", "n2"}:
        default_r, default_gamma = 296.8, 1.40
    else:
        raise ValueError("gas must be air/dry_air or nitrogen/n2")
    r = _float(row, "gas_constant_J_kgK") or default_r
    gamma = _float(row, "gamma") or default_gamma
    if r <= 0 or gamma <= 1:
        raise ValueError("gas constant must be positive and gamma must exceed one")
    return r, gamma


def viscosity(row: dict[str, str]) -> float:
    supplied = _positive(row, "viscosity_Pa_s")
    if supplied is not None:
        return supplied
    gas = row["gas"].strip().lower()
    temperature = float(_positive(row, "chamber_gas_temperature_K", required=True))
    if gas in {"air", "dry_air"}:
        return 1.716e-5 * (temperature / 273.15) ** 1.5 * (273.15 + 110.4) / (temperature + 110.4)
    if gas in {"nitrogen", "n2"}:
        return 1.663e-5 * (temperature / 273.15) ** 1.5 * (273.15 + 107.0) / (temperature + 107.0)
    raise ValueError("unsupported gas")


def _cte(row: dict[str, str], key: str, profiles: dict[str, ThermalStrainProfile]) -> ThermalStrainProfile | float:
    material_key = "piston_material" if key == "piston" else "liner_material"
    override_key = "piston_cte_per_K" if key == "piston" else "liner_cte_per_K"
    override = _float(row, override_key)
    if override is not None:
        if override <= 0:
            raise ValueError(f"{override_key} must be positive")
        return override
    material = row[material_key].strip()
    if material not in profiles:
        raise ValueError(f"{material_key} {material!r} is not in thermal_properties.json; supply {override_key}")
    return profiles[material]


def measured_mass_flow(row: dict[str, str], gas_r: float) -> tuple[float | None, str]:
    mass = _float(row, "mass_flow_kg_s")
    volume = _float(row, "volume_flow_L_min")
    if mass is not None and mass < 0:
        raise ValueError("mass_flow_kg_s must be nonnegative")
    if volume is not None and volume < 0:
        raise ValueError("volume_flow_L_min must be nonnegative")
    if mass is not None:
        return mass, "direct_mass_flow"
    if volume is None:
        return None, "not_reported"
    p_ref = _positive(row, "flow_meter_reference_pressure_bar_abs", required=True)
    t_ref = _positive(row, "flow_meter_reference_temperature_K", required=True)
    q_m3_s = volume * 1e-3 / 60.0
    rho = p_ref * 1e5 / (gas_r * t_ref)
    return rho * q_m3_s, "volume_to_mass_at_meter_reference"


def displacement_mm3(row: dict[str, str]) -> float | None:
    stroke = _positive(row, "stroke_mm")
    bore = _positive(row, "bore_diameter_cold_mm")
    return None if stroke is None or bore is None else math.pi / 4.0 * bore * bore * stroke


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = fraction * (len(values) - 1)
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def _normal(rng: random.Random, value: float, sigma: float | None) -> float:
    return value if not sigma else rng.gauss(value, sigma)


def _condition_bucket(value: str, decimals: int) -> str:
    """Canonicalize sensor jitter while retaining a readable grouping key."""
    return f"{float(value):.{decimals}f}"


def reduce_row(raw: dict[str, str], profiles: dict[str, ThermalStrainProfile], *, index: int, mc_samples: int, seed: int) -> dict[str, Any]:
    out: dict[str, Any] = dict(raw)
    errors: list[str] = []
    try:
        mode = raw.get("mode", "").strip()
        for key in REQUIRED_VALUE_FIELDS:
            if raw.get(key) is None or str(raw.get(key)).strip() == "":
                raise ValueError(f"missing required value {key}")
        if mode not in MODES:
            raise ValueError(f"mode must be one of {sorted(MODES)}")
        repeat = _float(raw, "repeat_number", required=True)
        if repeat is None or repeat < 1 or repeat != math.floor(repeat):
            raise ValueError("repeat_number must be a positive integer")
        for key in ("bore_diameter_cold_mm", "piston_diameter_cold_mm", "measurement_axial_position_mm", "piston_temperature_K", "liner_temperature_K", "chamber_gas_temperature_K", "upstream_pressure_bar_abs", "downstream_pressure_bar_abs", "ambient_pressure_bar_abs", "axial_flow_length_mm", "eccentricity"):
            _float(raw, key, required=True)
        bore = _positive(raw, "bore_diameter_cold_mm", required=True)
        piston_diameter = _positive(raw, "piston_diameter_cold_mm", required=True)
        for key in (
            "ambient_pressure_bar_abs", "upstream_pressure_bar_abs", "downstream_pressure_bar_abs",
            "piston_temperature_K", "liner_temperature_K", "chamber_gas_temperature_K",
            "axial_flow_length_mm",
        ):
            value = _positive(raw, key, required=True)
            if value is None:
                raise ValueError(f"{key} must be positive")
        for key in (
            "piston_temperature_uncertainty_K", "liner_temperature_uncertainty_K",
            "bore_diameter_uncertainty_mm", "piston_diameter_uncertainty_mm",
            "upstream_pressure_uncertainty_bar", "downstream_pressure_uncertainty_bar",
            "mass_flow_uncertainty_kg_s", "volume_flow_uncertainty_L_min",
            "viscosity_uncertainty_fraction",
        ):
            value = _float(raw, key)
            if value is not None and value < 0:
                raise ValueError(f"{key} must be nonnegative")
        if piston_diameter >= bore:
            raise ValueError("piston diameter must be smaller than bore")
        cold_from_dimensions = (bore - piston_diameter) * 1000.0 / 2.0
        supplied_cold = _float(raw, "cold_radial_clearance_um")
        out["cold_radial_clearance_from_dimensions_um"] = cold_from_dimensions
        out["cold_clearance_consistency_error_um"] = None if supplied_cold is None else supplied_cold - cold_from_dimensions
        if supplied_cold is not None and abs(supplied_cold - cold_from_dimensions) > max(0.25, 0.10 * max(abs(cold_from_dimensions), 1.0)):
            raise ValueError("reported cold_radial_clearance_um disagrees with measured diameters")
        cold = cold_from_dimensions
        p_cte, l_cte = _cte(raw, "piston", profiles), _cte(raw, "liner", profiles)
        piston_reference_temperature = _positive(raw, "piston_reference_temperature_K") or 293.15
        liner_reference_temperature = _positive(raw, "liner_reference_temperature_K") or 293.15
        clearance = calculate_clearance(
            bore_diameter_mm=bore,
            cold_radial_clearance_um=cold,
            piston_reference_temperature_K=piston_reference_temperature,
            liner_reference_temperature_K=liner_reference_temperature,
            hot_piston_temperature_K=float(raw["piston_temperature_K"]),
            hot_liner_temperature_K=float(raw["liner_temperature_K"]),
            piston_cte_per_K=p_cte,
            liner_cte_per_K=l_cte,
        )
        out.update({
            "status": "valid",
            "cold_radial_clearance_um": cold,
            "piston_diameter_growth_um": clearance.piston_diameter_growth_um,
            "liner_bore_growth_um": clearance.liner_bore_growth_um,
            "hot_radial_clearance_um": clearance.hot_radial_clearance_um,
            "clearance_change_um": clearance.clearance_change_um,
            "interference": clearance.interference,
            "contact_flag": clearance.hot_radial_clearance_um <= 0.0,
        })
        gas_r, gamma = gas_properties(raw)
        measured_mdot, flow_source = measured_mass_flow(raw, gas_r)
        out["measured_mass_flow_kg_s"] = measured_mdot
        out["flow_source"] = flow_source
        if mode != "dynamic_blowby" and measured_mdot is not None and measured_mdot > 0:
            out["measured_effective_cda_mm2"] = equiv_area(measured_mdot, float(raw["upstream_pressure_bar_abs"]), float(raw["chamber_gas_temperature_K"]), gamma=gamma, gas_constant=gas_r)
        else:
            out["measured_effective_cda_mm2"] = None
        if mode == "dynamic_blowby":
            out["model_status"] = "dynamic_not_inverted"
            out["annulus_model_mass_flow_kg_s"] = None
            out["measured_to_annulus_flow_ratio"] = None
            out["annulus_model_effective_cda_mm2"] = None
        elif clearance.hot_radial_clearance_um <= 0:
            out["model_status"] = "contact_invalid_annulus"
            out["annulus_model_mass_flow_kg_s"] = None
            out["measured_to_annulus_flow_ratio"] = None
            out["annulus_model_effective_cda_mm2"] = None
        elif float(raw["upstream_pressure_bar_abs"]) <= float(raw["downstream_pressure_bar_abs"]):
            out["model_status"] = "nonpositive_pressure_delta"
            out["annulus_model_mass_flow_kg_s"] = None
            out["measured_to_annulus_flow_ratio"] = None
            out["annulus_model_effective_cda_mm2"] = None
        else:
            model_mdot = annulus_mdot(
                float(raw["bore_diameter_cold_mm"]), clearance.hot_radial_clearance_um,
                float(raw["axial_flow_length_mm"]), float(raw["upstream_pressure_bar_abs"]),
                float(raw["downstream_pressure_bar_abs"]), T=float(raw["chamber_gas_temperature_K"]),
                mu=viscosity(raw), eccentricity=float(raw["eccentricity"]), gas_constant=gas_r,
            )
            out["model_status"] = "annulus_positive_clearance"
            out["annulus_model_mass_flow_kg_s"] = model_mdot
            out["annulus_model_effective_cda_mm2"] = equiv_area(model_mdot, float(raw["upstream_pressure_bar_abs"]), float(raw["chamber_gas_temperature_K"]), gamma=gamma, gas_constant=gas_r)
            out["measured_to_annulus_flow_ratio"] = None if measured_mdot is None or model_mdot <= 0 else measured_mdot / model_mdot
        displacement = displacement_mm3(raw)
        out["displacement_mm3"] = displacement
        out["measured_cda_per_displacement_mm_minus1"] = None if displacement is None or out["measured_effective_cda_mm2"] is None else out["measured_effective_cda_mm2"] / displacement
        out["uncertainty"] = propagate_uncertainty(raw, profiles, out, mc_samples=mc_samples, seed=seed + index)
        for key, value in out["uncertainty"].items():
            if key != "sensitivity_ranking" and isinstance(value, (int, float, str)):
                out[f"uncertainty_{key}"] = value
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))
        out.update({"status": "invalid", "errors": errors, "model_status": "not_evaluated"})
    return out


def _perturbed_row(raw: dict[str, str], channel: str, delta: float) -> dict[str, str]:
    row = dict(raw)
    key_map = {
        "piston_temperature": "piston_temperature_K", "liner_temperature": "liner_temperature_K",
        "bore_diameter": "bore_diameter_cold_mm", "piston_diameter": "piston_diameter_cold_mm",
        "upstream_pressure": "upstream_pressure_bar_abs", "downstream_pressure": "downstream_pressure_bar_abs",
        "mass_flow": "mass_flow_kg_s", "volume_flow": "volume_flow_L_min",
        "viscosity": "viscosity_Pa_s",
    }
    key = key_map[channel]
    baseline = viscosity(raw) if channel == "viscosity" and str(row.get(key, "")).strip() == "" else float(row[key])
    row[key] = str(baseline + delta)
    if channel in {"bore_diameter", "piston_diameter"}:
        # The independently reported clearance is derived from the nominal
        # dimensions; discard it when sampling those dimensions so a valid
        # perturbation is not rejected by the consistency cross-check.
        row["cold_radial_clearance_um"] = ""
    return row


def propagate_uncertainty(raw: dict[str, str], profiles: dict[str, ThermalStrainProfile], reduced: dict[str, Any], *, mc_samples: int, seed: int) -> dict[str, Any]:
    if mc_samples <= 0 or reduced.get("status") != "valid":
        return {"samples": 0}
    rng = random.Random(seed)
    channels = {
        "piston_temperature": _float(raw, "piston_temperature_uncertainty_K") or 0.0,
        "liner_temperature": _float(raw, "liner_temperature_uncertainty_K") or 0.0,
        "bore_diameter": _float(raw, "bore_diameter_uncertainty_mm") or 0.0,
        "piston_diameter": _float(raw, "piston_diameter_uncertainty_mm") or 0.0,
        "upstream_pressure": _float(raw, "upstream_pressure_uncertainty_bar") or 0.0,
        "downstream_pressure": _float(raw, "downstream_pressure_uncertainty_bar") or 0.0,
        "mass_flow": _float(raw, "mass_flow_uncertainty_kg_s") or 0.0,
        "volume_flow": _float(raw, "volume_flow_uncertainty_L_min") or 0.0,
        "viscosity": (_float(raw, "viscosity_uncertainty_fraction") or 0.0) * (float(raw["viscosity_Pa_s"]) if _float(raw, "viscosity_Pa_s") is not None else viscosity(raw)),
    }
    if _float(raw, "mass_flow_kg_s") is None:
        channels["mass_flow"] = 0.0
    if _float(raw, "volume_flow_L_min") is None:
        channels["volume_flow"] = 0.0
    hot_values: list[float] = []
    predicted_values: list[float] = []
    measured_cda_values: list[float] = []
    ratios: list[float] = []
    for _ in range(mc_samples):
        row = dict(raw)
        for channel, sigma in channels.items():
            if sigma <= 0:
                continue
            key = {
                "piston_temperature": "piston_temperature_K", "liner_temperature": "liner_temperature_K",
                "bore_diameter": "bore_diameter_cold_mm", "piston_diameter": "piston_diameter_cold_mm",
                "upstream_pressure": "upstream_pressure_bar_abs", "downstream_pressure": "downstream_pressure_bar_abs",
                "mass_flow": "mass_flow_kg_s", "volume_flow": "volume_flow_L_min", "viscosity": "viscosity_Pa_s",
            }[channel]
            baseline = viscosity(row) if channel == "viscosity" and str(row.get(key, "")).strip() == "" else float(row[key])
            row[key] = str(_normal(rng, baseline, sigma))
            if channel in {"bore_diameter", "piston_diameter"}:
                row["cold_radial_clearance_um"] = ""
        try:
            sample = reduce_row(row, profiles, index=0, mc_samples=0, seed=seed)
            if sample.get("status") != "valid":
                continue
            hot_values.append(float(sample["hot_radial_clearance_um"]))
            if sample.get("annulus_model_mass_flow_kg_s") is not None:
                predicted_values.append(float(sample["annulus_model_mass_flow_kg_s"]))
            if sample.get("measured_effective_cda_mm2") is not None:
                measured_cda_values.append(float(sample["measured_effective_cda_mm2"]))
            if sample.get("measured_to_annulus_flow_ratio") is not None:
                ratios.append(float(sample["measured_to_annulus_flow_ratio"]))
        except (ValueError, KeyError):
            continue
    sensitivity = []
    for channel, sigma in channels.items():
        if sigma <= 0:
            continue
        try:
            plus = reduce_row(_perturbed_row(raw, channel, sigma), profiles, index=0, mc_samples=0, seed=seed)
            minus = reduce_row(_perturbed_row(raw, channel, -sigma), profiles, index=0, mc_samples=0, seed=seed)
            item: dict[str, Any] = {"channel": channel, "one_sigma_input": sigma, "hot_clearance_half_range_um": abs(float(plus["hot_radial_clearance_um"]) - float(minus["hot_radial_clearance_um"])) / 2.0}
            if plus.get("measured_effective_cda_mm2") and minus.get("measured_effective_cda_mm2"):
                item["measured_cda_log_half_range"] = abs(math.log(float(plus["measured_effective_cda_mm2"])) - math.log(float(minus["measured_effective_cda_mm2"]))) / 2.0
            if plus.get("annulus_model_mass_flow_kg_s") is not None and minus.get("annulus_model_mass_flow_kg_s") is not None and reduced.get("annulus_model_mass_flow_kg_s"):
                item["predicted_flow_log_half_range"] = abs(math.log(float(plus["annulus_model_mass_flow_kg_s"])) - math.log(float(minus["annulus_model_mass_flow_kg_s"]))) / 2.0
            sensitivity.append(item)
        except (ValueError, KeyError):
            continue
    sensitivity.sort(key=lambda item: item.get("hot_clearance_half_range_um", 0.0), reverse=True)
    return {
        "samples": mc_samples,
        "successful_samples": len(hot_values),
        "hot_clearance_p05_um": quantile(hot_values, 0.05),
        "hot_clearance_p50_um": quantile(hot_values, 0.50),
        "hot_clearance_p95_um": quantile(hot_values, 0.95),
        "predicted_flow_p05_kg_s": quantile(predicted_values, 0.05),
        "predicted_flow_p50_kg_s": quantile(predicted_values, 0.50),
        "predicted_flow_p95_kg_s": quantile(predicted_values, 0.95),
        "measured_cda_p05_mm2": quantile(measured_cda_values, 0.05),
        "measured_cda_p50_mm2": quantile(measured_cda_values, 0.50),
        "measured_cda_p95_mm2": quantile(measured_cda_values, 0.95),
        "measured_to_model_ratio_p05": quantile(ratios, 0.05),
        "measured_to_model_ratio_p50": quantile(ratios, 0.50),
        "measured_to_model_ratio_p95": quantile(ratios, 0.95),
        "sensitivity_ranking": sensitivity,
        "assumption_label": "independent Gaussian channel errors supplied by the experimenter; not production statistics",
    }


def fit_h3(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("status") != "valid" or row.get("mode") != "static_direct":
            continue
        if row.get("measured_mass_flow_kg_s") is None or float(row["measured_mass_flow_kg_s"]) <= 0 or float(row["hot_radial_clearance_um"]) <= 0:
            continue
        # Only compare like with like: pressure, gas temperature, geometry,
        # eccentricity and lubricant state are held fixed within a fit.
        key = (
            str(row.get("reference_cylinder_id", "")),
            str(row.get("measurement_axial_position_mm", "")),
            str(row.get("lubricant_condition", "")),
            _condition_bucket(str(row.get("upstream_pressure_bar_abs", "")), H3_PRESSURE_DECIMALS),
            _condition_bucket(str(row.get("downstream_pressure_bar_abs", "")), H3_PRESSURE_DECIMALS),
            _condition_bucket(str(row.get("chamber_gas_temperature_K", "")), H3_TEMPERATURE_DECIMALS),
            str(row.get("axial_flow_length_mm", "")),
            str(row.get("eccentricity", "")),
        )
        groups.setdefault(key, []).append(row)
    fits = []
    for key, group in groups.items():
        x = [math.log(float(row["hot_radial_clearance_um"])) for row in group]
        y = [math.log(float(row["measured_mass_flow_kg_s"])) for row in group]
        if len(group) < 3 or len(set(x)) < 3:
            continue
        xbar, ybar = sum(x) / len(x), sum(y) / len(y)
        sxx = sum((value - xbar) ** 2 for value in x)
        slope = sum((a - xbar) * (b - ybar) for a, b in zip(x, y)) / sxx
        intercept = ybar - slope * xbar
        residual = sum((b - (intercept + slope * a)) ** 2 for a, b in zip(x, y))
        se = math.sqrt(residual / max(1, len(x) - 2) / sxx)
        fits.append({
            "reference_cylinder_id": key[0], "measurement_axial_position_mm": key[1], "lubricant_condition": key[2],
            "upstream_pressure_bar_abs": key[3], "downstream_pressure_bar_abs": key[4], "chamber_gas_temperature_K": key[5],
            "axial_flow_length_mm": key[6], "eccentricity": key[7],
            "points": len(group), "clearance_exponent": slope, "ci95_low": slope - 1.96 * se, "ci95_high": slope + 1.96 * se,
            "ideal_annulus_exponent": 3.0, "log_intercept": intercept,
            "classification": "calculated from measured rows; normal-theory interval",
        })
    return fits


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row if key != "uncertainty" and key != "errors"})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: value for key, value in row.items() if key in fields})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-csv", type=Path, default=ROOT / "data" / "leakage" / "reduced_experiment_results.csv")
    parser.add_argument("--output-json", type=Path, default=ROOT / "data" / "leakage" / "reduced_experiment_results.json")
    parser.add_argument("--mc-samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260902)
    args = parser.parse_args()
    profiles = load_profiles()
    with args.input_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        validate_input_header(reader.fieldnames)
        rows = [reduce_row(row, profiles, index=index, mc_samples=args.mc_samples, seed=args.seed) for index, row in enumerate(reader)]
    output = {
        "input_file": args.input_csv.name,
        "input_sha256": hashlib.sha256(args.input_csv.read_bytes()).hexdigest(),
        "schema_file": "data/leakage/measurement_schema.csv",
        "classification": {"measured": "input channels only", "calculated": "hot clearance, annulus comparison, uncertainty propagation and h^3 fits", "assumed": "material profiles, gas properties where not supplied, independent channel errors", "extrapolated": "none"},
        "row_count": len(rows),
        "valid_row_count": sum(row.get("status") == "valid" for row in rows),
        "invalid_row_count": sum(row.get("status") == "invalid" for row in rows),
        "dynamic_rows_not_inverted": sum(row.get("mode") == "dynamic_blowby" for row in rows),
        "h3_scaling_fits": fit_h3(rows),
        "rows": rows,
    }
    write_csv(args.output_csv, rows)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "valid": output["valid_row_count"], "invalid": output["invalid_row_count"], "h3_fits": len(output["h3_scaling_fits"]), "output_csv": str(args.output_csv), "output_json": str(args.output_json)}, indent=2))


if __name__ == "__main__":
    main()
