#!/usr/bin/env python3
"""Bounded thermal-clearance and ringless-annulus feasibility campaign.

This is an analytical screening tool, not a calibrated production tolerance
model.  It keeps cold static leak-down and hot dynamic blow-by rows separate,
uses the pressure-aware ``physics.annulus`` model, and writes provenance-rich
CSV/JSON outputs suitable for later replacement by measured material data.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from physics.thermal_clearance import (
    ThermalStrainProfile,
    annulus_leakage_from_clearance,
    calculate_clearance,
    cold_clearance_for_hot_target_um,
    integrated_strain,
)

MATERIALS_PATH = ROOT / "data" / "materials" / "thermal_properties.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "sealing"
REFERENCE_TEMPERATURE_K = 293.15
PISTON_TEMPERATURES_K = (350.0, 450.0, 550.0, 650.0)
LINER_TEMPERATURES_K = (300.0, 400.0, 500.0)
COLD_CLEARANCES_UM = tuple(i * 0.5 for i in range(41))
BORES_MM = (8.5, 12.5)
BORE_STROKES_MM = {8.5: 7.0, 12.5: 12.0}
ECCENTRICITIES = (0.0, 0.5)
PRESSURE_STATES = (
    {
        "state_id": "cold_static_leakdown",
        "mode": "cold_static",
        "pressure_up_bar": 6.5,
        "pressure_down_bar": 1.0,
        "gas_temperature_K": 300.0,
    },
    {
        "state_id": "hot_early_compression",
        "mode": "hot_dynamic",
        "pressure_up_bar": 10.0,
        "pressure_down_bar": 1.0,
        "gas_temperature_K": 450.0,
    },
    {
        "state_id": "hot_mid_compression",
        "mode": "hot_dynamic",
        "pressure_up_bar": 25.0,
        "pressure_down_bar": 1.0,
        "gas_temperature_K": 800.0,
    },
    {
        "state_id": "hot_combustion_window",
        "mode": "hot_dynamic",
        "pressure_up_bar": 45.0,
        "pressure_down_bar": 1.0,
        "gas_temperature_K": 1100.0,
    },
    {
        "state_id": "hot_peak_screen",
        "mode": "hot_dynamic",
        "pressure_up_bar": 60.0,
        "pressure_down_bar": 1.0,
        "gas_temperature_K": 1200.0,
    },
)


def load_materials(path: Path = MATERIALS_PATH) -> tuple[dict[str, Any], dict[str, ThermalStrainProfile]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    materials = {item["id"]: item for item in payload["materials"]}
    profiles = {
        item_id: ThermalStrainProfile(tuple(tuple(point) for point in item["strain_points"]))
        for item_id, item in materials.items()
    }
    return materials, profiles


def air_viscosity_sutherland(temperature_K: float) -> float:
    """Approximate air viscosity, kg/(m s), for the annulus screen."""
    if temperature_K <= 0:
        raise ValueError("temperature must be positive")
    return 1.716e-5 * (temperature_K / 273.15) ** 1.5 * (273.15 + 110.4) / (temperature_K + 110.4)


def displacement_cc(bore_mm: float, stroke_mm: float) -> float:
    return math.pi * bore_mm**2 * stroke_mm / 4000.0


def clearance_rows(
    *,
    materials: dict[str, Any],
    profiles: dict[str, ThermalStrainProfile],
    clearances_um: tuple[float, ...] = COLD_CLEARANCES_UM,
    bores_mm: tuple[float, ...] = BORES_MM,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bore_mm in bores_mm:
        stroke_mm = BORE_STROKES_MM[bore_mm]
        for piston_id, liner_id in material_pairs(materials):
            for piston_temperature_K in PISTON_TEMPERATURES_K:
                for liner_temperature_K in LINER_TEMPERATURES_K:
                    for cold_clearance_um in clearances_um:
                        thermal = calculate_clearance(
                            bore_diameter_mm=bore_mm,
                            cold_radial_clearance_um=cold_clearance_um,
                            piston_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                            liner_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                            hot_piston_temperature_K=piston_temperature_K,
                            hot_liner_temperature_K=liner_temperature_K,
                            piston_cte_per_K=profiles[piston_id],
                            liner_cte_per_K=profiles[liner_id],
                        )
                        for eccentricity in ECCENTRICITIES:
                            for state in PRESSURE_STATES:
                                effective_clearance_um = (
                                    cold_clearance_um
                                    if state["mode"] == "cold_static"
                                    else thermal.hot_radial_clearance_um
                                )
                                leakage = annulus_leakage_from_clearance(
                                    effective_clearance_um,
                                    pressure_up_bar=state["pressure_up_bar"],
                                    pressure_down_bar=state["pressure_down_bar"],
                                    temperature_K=state["gas_temperature_K"],
                                    viscosity_Pa_s=air_viscosity_sutherland(state["gas_temperature_K"]),
                                    bore_diameter_mm=bore_mm,
                                    skirt_length_mm=8.0 if bore_mm == 8.5 else 12.0,
                                    eccentricity=eccentricity,
                                )
                                mdot = leakage["mass_flow_kg_s"]
                                rows.append({
                                    "bore_mm": bore_mm,
                                    "stroke_mm": stroke_mm,
                                    "piston_material": piston_id,
                                    "liner_material": liner_id,
                                    "piston_temperature_K": piston_temperature_K,
                                    "liner_temperature_K": liner_temperature_K,
                                    "reference_temperature_K": REFERENCE_TEMPERATURE_K,
                                    "cold_radial_clearance_um": cold_clearance_um,
                                    "hot_radial_clearance_um": thermal.hot_radial_clearance_um,
                                    "clearance_change_um": thermal.clearance_change_um,
                                    "piston_diameter_growth_um": thermal.piston_diameter_growth_um,
                                    "liner_bore_growth_um": thermal.liner_bore_growth_um,
                                    "interference_flag": thermal.interference,
                                    "eccentricity_ratio": eccentricity,
                                    "state_id": state["state_id"],
                                    "mode": state["mode"],
                                    "pressure_up_bar": state["pressure_up_bar"],
                                    "pressure_down_bar": state["pressure_down_bar"],
                                    "gas_temperature_K": state["gas_temperature_K"],
                                    "air_viscosity_Pa_s": air_viscosity_sutherland(state["gas_temperature_K"]),
                                    "effective_clearance_for_leakage_um": effective_clearance_um,
                                    "leakage_status": leakage["leakage_status"],
                                    "mass_flow_kg_s": mdot,
                                    "equivalent_cda_mm2": leakage["equivalent_cda_mm2"],
                                    "mass_flow_mg_s_per_cc": (
                                        mdot * 1e6 / displacement_cc(bore_mm, stroke_mm)
                                        if isinstance(mdot, (int, float)) else None
                                    ),
                                })
    return rows


def material_pairs(materials: dict[str, Any]) -> list[tuple[str, str]]:
    pair_ids = json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))["screened_pairs"]
    for piston_id, liner_id in pair_ids:
        if piston_id not in materials or liner_id not in materials:
            raise KeyError(f"unknown material pair {piston_id}/{liner_id}")
    return [tuple(pair) for pair in pair_ids]


def uncertainty_summary(
    *,
    materials: dict[str, Any],
    profiles: dict[str, ThermalStrainProfile],
    samples: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Monte Carlo tolerance sensitivity with explicitly assumed distributions."""
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    nominal_clearances = (2.0, 3.0, 5.0, 8.0, 10.0)
    for bore_mm in BORES_MM:
        for piston_id, liner_id in material_pairs(materials):
            for nominal_um in nominal_clearances:
                for temp_error_K in (25.0, 50.0):
                    counts = {"interference": 0, "sub_1_um": 0, "1_to_3_um": 0, "3_to_5_um": 0, "ge_5_um": 0}
                    cold_interference = 0
                    for _ in range(samples):
                        # Engineering sensitivity assumptions, not production statistics:
                        # independent +/-1 um diameter metrology/manufacturing errors,
                        # +/-5% CTE, and independent uniform temperature errors.
                        bore_sample_mm = bore_mm + rng.uniform(-0.001, 0.001)
                        piston_nominal_mm = bore_mm - 2.0 * nominal_um * 1e-3
                        piston_sample_mm = piston_nominal_mm + rng.uniform(-0.001, 0.001)
                        cold_sample_um = 500.0 * (bore_sample_mm - piston_sample_mm)
                        piston_temperature_K = rng.uniform(450.0 - temp_error_K, 450.0 + temp_error_K)
                        liner_temperature_K = rng.uniform(400.0 - temp_error_K, 400.0 + temp_error_K)
                        p_factor = rng.uniform(0.95, 1.05)
                        l_factor = rng.uniform(0.95, 1.05)
                        if cold_sample_um < 0:
                            cold_interference += 1
                            # Retain the physical negative state instead of clamping it.
                            # Evaluate the thermal differential from the nominal diameter;
                            # it remains a contact warning, not a leakage value.
                            cold_for_formula = cold_sample_um
                        else:
                            cold_for_formula = cold_sample_um
                        p_alpha = profiles[piston_id].effective_cte_per_K(REFERENCE_TEMPERATURE_K, piston_temperature_K) * p_factor
                        l_alpha = profiles[liner_id].effective_cte_per_K(REFERENCE_TEMPERATURE_K, liner_temperature_K) * l_factor
                        p_strain = integrated_strain(REFERENCE_TEMPERATURE_K, piston_temperature_K, p_alpha)
                        l_strain = integrated_strain(REFERENCE_TEMPERATURE_K, liner_temperature_K, l_alpha)
                        piston_ref_mm = bore_sample_mm - 2.0 * cold_for_formula * 1e-3
                        hot_um = 500.0 * (bore_sample_mm * (1.0 + l_strain) - piston_ref_mm * (1.0 + p_strain))
                        if hot_um < 0:
                            counts["interference"] += 1
                        elif hot_um < 1:
                            counts["sub_1_um"] += 1
                        elif hot_um < 3:
                            counts["1_to_3_um"] += 1
                        elif hot_um < 5:
                            counts["3_to_5_um"] += 1
                        else:
                            counts["ge_5_um"] += 1
                    rows.append({
                        "bore_mm": bore_mm,
                        "piston_material": piston_id,
                        "liner_material": liner_id,
                        "nominal_cold_clearance_um": nominal_um,
                        "piston_temperature_center_K": 450.0,
                        "liner_temperature_center_K": 400.0,
                        "temperature_error_half_range_K": temp_error_K,
                        "samples": samples,
                        "seed": seed,
                        "bore_tolerance_diameter_um": 1.0,
                        "piston_tolerance_diameter_um": 1.0,
                        "cte_relative_half_range": 0.05,
                        "counts": counts,
                        "cold_interference_fraction": cold_interference / samples,
                        "fractions": {key: value / samples for key, value in counts.items()},
                        "assumption_label": "engineering sensitivity distribution; not measured production statistics",
                    })
    return rows


def design_summary(materials: dict[str, Any], profiles: dict[str, ThermalStrainProfile]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for bore_mm in BORES_MM:
        for piston_id, liner_id in material_pairs(materials):
            for piston_temperature_K, liner_temperature_K in ((450.0, 400.0), (500.0, 450.0), (550.0, 450.0)):
                for target_um in (2.0, 3.0, 5.0):
                    required = cold_clearance_for_hot_target_um(
                        bore_diameter_mm=bore_mm,
                        target_hot_clearance_um=target_um,
                        piston_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                        liner_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                        hot_piston_temperature_K=piston_temperature_K,
                        hot_liner_temperature_K=liner_temperature_K,
                        piston_cte_per_K=profiles[piston_id],
                        liner_cte_per_K=profiles[liner_id],
                    )
                    rows.append({
                        "bore_mm": bore_mm,
                        "piston_material": piston_id,
                        "liner_material": liner_id,
                        "piston_temperature_K": piston_temperature_K,
                        "liner_temperature_K": liner_temperature_K,
                        "target_hot_clearance_um": target_um,
                        "required_cold_radial_clearance_um": required,
                    })
    return {
        "target_rows": rows,
        "temperature_sensitivity": temperature_sensitivity(materials, profiles),
    }


def temperature_sensitivity(materials: dict[str, Any], profiles: dict[str, ThermalStrainProfile]) -> list[dict[str, Any]]:
    rows = []
    pair = ("al_4032_t6", "steel_4140")
    for bore_mm in BORES_MM:
        for cold_um in (3.0, 8.0):
            for error_K in (25.0, 50.0):
                values = []
                for p_sign in (-1.0, 1.0):
                    for l_sign in (-1.0, 1.0):
                        result = calculate_clearance(
                            bore_diameter_mm=bore_mm,
                            cold_radial_clearance_um=cold_um,
                            piston_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                            liner_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                            hot_piston_temperature_K=450.0 + p_sign * error_K,
                            hot_liner_temperature_K=400.0 + l_sign * error_K,
                            piston_cte_per_K=profiles[pair[0]],
                            liner_cte_per_K=profiles[pair[1]],
                        )
                        values.append(result.hot_radial_clearance_um)
                rows.append({
                    "bore_mm": bore_mm,
                    "pair": f"{pair[0]}/{pair[1]}",
                    "cold_clearance_um": cold_um,
                    "temperature_error_K": error_K,
                    "hot_clearance_min_um": min(values),
                    "hot_clearance_max_um": max(values),
                    "hot_clearance_span_um": max(values) - min(values),
                    "assumption_label": "independent worst-corner temperature sensitivity, not a measured distribution",
                })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def write_plots(out: Path, materials: dict[str, Any], profiles: dict[str, ThermalStrainProfile]) -> list[str]:
    """Write a few decision-oriented plots; plotting is optional at runtime."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    figure_dir = out / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # Differential expansion is easiest to audit as a hot-clearance family.
    temperatures = list(range(350, 651, 10))
    for cold_um, name in ((3.0, "3um"), (12.0, "12um")):
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        for liner_T in (300.0, 400.0, 500.0):
            values = []
            for piston_T in temperatures:
                result = calculate_clearance(
                    bore_diameter_mm=8.5,
                    cold_radial_clearance_um=cold_um,
                    piston_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                    liner_reference_temperature_K=REFERENCE_TEMPERATURE_K,
                    hot_piston_temperature_K=piston_T,
                    hot_liner_temperature_K=liner_T,
                    piston_cte_per_K=profiles["al_4032_t6"],
                    liner_cte_per_K=profiles["steel_4140"],
                )
                values.append(result.hot_radial_clearance_um)
            ax.plot(temperatures, values, label=f"liner {liner_T:.0f} K")
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.axhspan(2.0, 5.0, color="tab:green", alpha=0.12, label="2–5 µm hot window")
        ax.set(xlabel="piston temperature (K)", ylabel="hot radial clearance (µm)", title=f"Al 4032 / 4140 steel, {cold_um:g} µm cold")
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = figure_dir / f"hot_clearance_vs_piston_temperature_{name}.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path.relative_to(out).as_posix())

    # The annulus model's h^3 dependence is useful for fixture sensor sizing.
    clearances = [x * 0.1 for x in range(1, 201)]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for eccentricity in ECCENTRICITIES:
        mdot_mg_s = []
        for clearance_um in clearances:
            leakage = annulus_leakage_from_clearance(
                clearance_um,
                pressure_up_bar=45.0,
                pressure_down_bar=1.0,
                temperature_K=1100.0,
                viscosity_Pa_s=air_viscosity_sutherland(1100.0),
                bore_diameter_mm=8.5,
                skirt_length_mm=8.0,
                eccentricity=eccentricity,
            )
            mdot_mg_s.append(float(leakage["mass_flow_kg_s"]) * 1e6)
        ax.loglog(clearances, mdot_mg_s, label=f"eccentricity {eccentricity:g}")
    ax.set(xlabel="positive hot clearance (µm)", ylabel="annulus mass flow (mg/s)", title="Uncalibrated annulus screen: 8.5 mm, 45→1 bar, 1100 K")
    ax.legend()
    fig.tight_layout()
    path = figure_dir / "annulus_leakage_vs_hot_clearance.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    written.append(path.relative_to(out).as_posix())
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--samples", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--plots", action="store_true", help="also write decision plots (requires matplotlib)")
    args = parser.parse_args()
    if args.samples <= 0:
        raise SystemExit("--samples must be positive")
    materials, profiles = load_materials()
    clearance = clearance_rows(materials=materials, profiles=profiles)
    uncertainty = uncertainty_summary(materials=materials, profiles=profiles, samples=args.samples, seed=args.seed)
    summary = {
        "campaign": "C1 thermal-clearance and sealing feasibility",
        "status": "screening_only",
        "assumption_classification": {
            "measured": "none in this campaign",
            "literature_derived": "material property points and near-scale geometry citations in report",
            "calculated": "linear thermal strain, annulus mdot/equivalent CdA, tolerance fractions",
            "assumed": "temperature grids, tolerance distributions, viscosity and representative pressure states",
            "extrapolated": "profile endpoint strain outside source temperature ranges and 8.5/12.5 scale bridge",
        },
        # Keep committed metadata portable across Windows/WSL/Linux checkouts.
        "materials_file": "data/materials/thermal_properties.json",
        "pressure_states": PRESSURE_STATES,
        "temperature_grids_K": {"piston": PISTON_TEMPERATURES_K, "liner": LINER_TEMPERATURES_K},
        "cold_clearance_grid_um": COLD_CLEARANCES_UM,
        "bores_mm": BORES_MM,
        "eccentricities": ECCENTRICITIES,
        "clearance_row_count": len(clearance),
        "uncertainty_row_count": len(uncertainty),
        "design_summary": design_summary(materials, profiles),
        "uncertainty": uncertainty,
    }
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "thermal_clearance_sweep.csv", clearance)
    write_csv(out / "thermal_clearance_uncertainty.csv", uncertainty)
    plot_paths = write_plots(out, materials, profiles) if args.plots else []
    summary["plots"] = plot_paths
    (out / "thermal_clearance_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "clearance_rows": len(clearance),
        "uncertainty_rows": len(uncertainty),
        "output_dir": str(out),
        "summary": str(out / "thermal_clearance_summary.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
