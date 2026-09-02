#!/usr/bin/env python3
"""Calibrated static leak-down and dynamic blow-by evidence pipeline.

This module intentionally keeps three evidence lanes separate:

1. static absolute leakage: direct flow or a calibrated differential tester can
   be converted to an effective compressible-orifice CdA;
2. static standardized-relative leakage: a documented but uncalibrated
   reference restrictor gives leak/reference CdA ratio only;
3. dynamic blow-by: direct crankcase flow is normalized and preserved, but is
   not collapsed to one steady CdA without a pressure-history inversion model.

Unspecified leak-down percentages are qualitative only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from scipy import stats

from physics.annulus import clearance_to_area

DEFAULT_R = 287.05
DEFAULT_GAMMA = 1.4


def _float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def cylinder_displacement_cc(bore_mm: float, stroke_mm: float) -> float:
    return math.pi * bore_mm**2 * stroke_mm / 4000.0


def isentropic_mass_flux_per_cda(
    upstream_bar_abs: float,
    downstream_bar_abs: float,
    temperature_K: float,
    *,
    gas_constant_J_kgK: float = DEFAULT_R,
    gamma: float = DEFAULT_GAMMA,
) -> float:
    """Return mdot/CdA [kg/(s m^2)] for an ideal-gas orifice.

    ``CdA`` is effective area, so no separate discharge coefficient appears.
    The expression handles both subcritical and choked pressure ratios.
    """
    if upstream_bar_abs <= 0 or downstream_bar_abs <= 0:
        raise ValueError("absolute pressures must be positive")
    if downstream_bar_abs >= upstream_bar_abs:
        return 0.0
    if temperature_K <= 0 or gas_constant_J_kgK <= 0 or gamma <= 1:
        raise ValueError("invalid gas state")

    pu = upstream_bar_abs * 1e5
    ratio = downstream_bar_abs / upstream_bar_abs
    critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    prefactor = pu / math.sqrt(gas_constant_J_kgK * temperature_K)
    if ratio <= critical:
        return prefactor * math.sqrt(gamma) * (
            2.0 / (gamma + 1.0)
        ) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))

    term = (2.0 * gamma / (gamma - 1.0)) * (
        ratio ** (2.0 / gamma) - ratio ** ((gamma + 1.0) / gamma)
    )
    return prefactor * math.sqrt(max(term, 0.0))


def effective_cda_mm2(
    mass_flow_kg_s: float,
    upstream_bar_abs: float,
    downstream_bar_abs: float,
    temperature_K: float,
    *,
    gas_constant_J_kgK: float = DEFAULT_R,
    gamma: float = DEFAULT_GAMMA,
) -> float:
    flux = isentropic_mass_flux_per_cda(
        upstream_bar_abs,
        downstream_bar_abs,
        temperature_K,
        gas_constant_J_kgK=gas_constant_J_kgK,
        gamma=gamma,
    )
    if flux <= 0:
        raise ValueError("pressure state cannot support positive leakage flow")
    if mass_flow_kg_s < 0:
        raise ValueError("mass flow must be nonnegative")
    return mass_flow_kg_s / flux * 1e6


def volumetric_to_mass_flow(
    volume_flow_L_min: float,
    pressure_bar_abs: float,
    temperature_K: float,
    *,
    gas_constant_J_kgK: float = DEFAULT_R,
) -> float:
    if volume_flow_L_min < 0:
        raise ValueError("volume flow must be nonnegative")
    rho = pressure_bar_abs * 1e5 / (gas_constant_J_kgK * temperature_K)
    return rho * volume_flow_L_min * 1e-3 / 60.0


def differential_leak_ratio(
    supply_bar_abs: float,
    cylinder_bar_abs: float,
    ambient_bar_abs: float,
    temperature_K: float,
    *,
    gas_constant_J_kgK: float = DEFAULT_R,
    gamma: float = DEFAULT_GAMMA,
) -> float:
    """Return leak CdA / reference CdA for a differential tester.

    At steady state, reference flow equals cylinder leakage flow. The reference
    restriction may be uncalibrated; the pressure drops still determine a
    dimensionless effective-area ratio.
    """
    g_ref = isentropic_mass_flux_per_cda(
        supply_bar_abs,
        cylinder_bar_abs,
        temperature_K,
        gas_constant_J_kgK=gas_constant_J_kgK,
        gamma=gamma,
    )
    g_leak = isentropic_mass_flux_per_cda(
        cylinder_bar_abs,
        ambient_bar_abs,
        temperature_K,
        gas_constant_J_kgK=gas_constant_J_kgK,
        gamma=gamma,
    )
    if g_leak <= 0:
        raise ValueError("cylinder pressure must exceed ambient")
    return g_ref / g_leak


def _record_mass_flow(row: dict[str, str], R: float) -> float | None:
    direct = _float(row.get("mass_flow_kg_s"))
    if direct is not None:
        return direct
    q = _float(row.get("volume_flow_L_min"))
    if q is None:
        return None
    p = _float(row.get("volume_flow_pressure_bar_abs"))
    t = _float(row.get("volume_flow_temperature_K"))
    if p is None or t is None:
        return None
    return volumetric_to_mass_flow(q, p, t, gas_constant_J_kgK=R)


def analyze_record(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(row)
    result["eligibility"] = "qualitative"
    result["reason"] = "insufficient quantitative metadata"

    mode = str(row.get("mode", "")).strip().lower()
    bore = _float(row.get("bore_mm"))
    stroke = _float(row.get("stroke_mm"))
    if bore and stroke:
        result["cylinder_displacement_cc"] = cylinder_displacement_cc(bore, stroke)

    R = _float(row.get("gas_constant_J_kgK")) or DEFAULT_R
    gamma = _float(row.get("gamma")) or DEFAULT_GAMMA
    T = _float(row.get("temperature_K"))
    ambient = _float(row.get("ambient_pressure_bar_abs")) or 1.0

    if mode == "static_direct":
        mdot = _record_mass_flow(row, R)
        pu = _float(row.get("upstream_pressure_bar_abs"))
        pd = _float(row.get("downstream_pressure_bar_abs"))
        if mdot is None or pu is None or pd is None or T is None:
            result["reason"] = "static_direct requires flow, upstream/downstream absolute pressure, and temperature"
            return result
        cda = effective_cda_mm2(mdot, pu, pd, T, gas_constant_J_kgK=R, gamma=gamma)
        result.update({
            "eligibility": "static_absolute",
            "reason": "direct flow converted to effective CdA",
            "mass_flow_kg_s_derived": mdot,
            "leak_cda_mm2": cda,
        })
        return result

    if mode == "static_differential":
        supply = _float(row.get("tester_supply_pressure_bar_abs"))
        cyl = _float(row.get("tester_cylinder_pressure_bar_abs"))
        if supply is None or cyl is None or T is None:
            result["reason"] = "static_differential requires tester supply/cylinder absolute pressure and temperature"
            return result
        ratio = differential_leak_ratio(
            supply, cyl, ambient, T,
            gas_constant_J_kgK=R, gamma=gamma,
        )
        result["leak_to_reference_cda_ratio"] = ratio
        ref_cda = _float(row.get("reference_cda_mm2"))
        if ref_cda is not None:
            result.update({
                "eligibility": "static_absolute",
                "reason": "calibrated reference CdA converts differential test to absolute leak CdA",
                "leak_cda_mm2": ratio * ref_cda,
            })
        elif _float(row.get("reference_orifice_diameter_mm")) is not None:
            result.update({
                "eligibility": "static_relative",
                "reason": "reference geometry documented but not calibrated; relative CdA ratio only",
            })
        else:
            result["reason"] = "differential tester lacks calibrated CdA or documented restrictor geometry"
        return result

    if mode == "dynamic_blowby":
        mdot = _record_mass_flow(row, R)
        if mdot is None:
            result["reason"] = "dynamic_blowby requires direct mass or referenced volumetric flow"
            return result
        result.update({
            "eligibility": "dynamic_flow",
            "reason": "direct dynamic flow retained without steady-area inversion",
            "mass_flow_kg_s_derived": mdot,
        })
        vd = result.get("cylinder_displacement_cc")
        if isinstance(vd, (int, float)) and vd > 0:
            result["mass_flow_mg_s_per_cc"] = mdot * 1e6 / vd
        return result

    result["reason"] = f"unsupported or missing mode {mode!r}"
    return result


def load_records(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def static_absolute_regression(records: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [
        row for row in records
        if row.get("eligibility") == "static_absolute"
        and isinstance(row.get("leak_cda_mm2"), (int, float))
        and isinstance(row.get("cylinder_displacement_cc"), (int, float))
        and _float(row.get("bore_mm")) is not None
    ]
    if len(accepted) < 3:
        return {
            "status": "insufficient_data",
            "accepted_count": len(accepted),
            "required_minimum": 3,
        }

    xs = [math.log(float(row["bore_mm"])) for row in accepted]
    ys = [math.log(float(row["leak_cda_mm2"]) / float(row["cylinder_displacement_cc"])) for row in accepted]
    fit = stats.linregress(xs, ys)
    dof = len(xs) - 2
    tcrit = stats.t.ppf(0.975, dof) if dof > 0 else math.nan
    slope_ci = [fit.slope - tcrit * fit.stderr, fit.slope + tcrit * fit.stderr]

    families = sorted({str(row.get("dataset_family", "")) for row in accepted})
    leave_one_family_out = []
    for family in families:
        subset = [row for row in accepted if str(row.get("dataset_family", "")) != family]
        if len(subset) < 3:
            continue
        x2 = [math.log(float(row["bore_mm"])) for row in subset]
        y2 = [math.log(float(row["leak_cda_mm2"]) / float(row["cylinder_displacement_cc"])) for row in subset]
        f2 = stats.linregress(x2, y2)
        leave_one_family_out.append({
            "omitted_family": family,
            "n": len(subset),
            "slope": f2.slope,
            "r_squared": f2.rvalue**2,
        })

    target_bore = 8.5
    predicted_log = fit.intercept + fit.slope * math.log(target_bore)
    return {
        "status": "screening",
        "accepted_count": len(accepted),
        "dataset_families": families,
        "slope_log_cda_per_vd_vs_log_bore": fit.slope,
        "slope_95pct_ci": slope_ci,
        "intercept": fit.intercept,
        "r_squared": fit.rvalue**2,
        "p_value": fit.pvalue,
        "target_bore_mm": target_bore,
        "predicted_cda_per_cc_at_8p5_mm": math.exp(predicted_log),
        "leave_one_family_out": leave_one_family_out,
        "warning": "screening extrapolation only; full-size sealing data is not direct microengine calibration",
    }


def target_annulus_brackets(
    *,
    pressure_bar_abs: float = 6.5,
    temperature_K: float = 300.0,
    mu_Pa_s: float = 1.85e-5,
) -> list[dict[str, float]]:
    rows = []
    for clearance in (2.0, 3.0, 5.0):
        for eccentricity in (0.0, 0.5):
            cda = clearance_to_area(
                clearance,
                pressure_bar_abs,
                D_mm=8.5,
                L_mm=8.0,
                T=temperature_K,
                eccentricity=eccentricity,
            )
            # physics.annulus currently fixes mu internally; retain the input in
            # metadata so a later API extension can expose it without changing
            # the evidence schema.
            rows.append({
                "clearance_um": clearance,
                "eccentricity_ratio": eccentricity,
                "comparison_pressure_bar_abs": pressure_bar_abs,
                "comparison_temperature_K": temperature_K,
                "comparison_mu_Pa_s_requested": mu_Pa_s,
                "equivalent_cda_mm2": cda,
            })
    return rows


def summarize(path: Path) -> dict[str, Any]:
    raw = load_records(path)
    records = [analyze_record(row) for row in raw]
    counts: dict[str, int] = {}
    for row in records:
        key = str(row.get("eligibility"))
        counts[key] = counts.get(key, 0) + 1
    return {
        "source_csv": str(path),
        "counts": counts,
        "static_absolute_regression": static_absolute_regression(records),
        "target_8p5mm_annulus_brackets": target_annulus_brackets(),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--output", type=Path, default=Path("leakage_scaling_results.json"))
    args = parser.parse_args()
    payload = summarize(args.data)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "counts": payload["counts"],
        "regression": payload["static_absolute_regression"],
        "output": str(args.output),
    }, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
