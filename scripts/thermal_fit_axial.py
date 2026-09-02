#!/usr/bin/env python3
"""Run the bounded axial thermal-fit feasibility screen.

This is intentionally a compact post-processor around the existing thermal RC
screen.  The RC topology, head/block/rod sinks, and its constant-h baseline are
unchanged; angle-dependent h remains a separate sensitivity closure.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from physics.thermal_clearance import ThermalStrainProfile
from physics.thermal_fit_axial import (
    AxialFitConfig,
    DEFAULT_STATIONS,
    evaluate_axial_fit,
    evaluate_temperature_rows,
    minimum_preheat_temperature_K,
    nonuniform_annulus_leakage,
    required_base_fit_bounds_um,
)
from physics.thermal_state import ThermalRCConfig, load_history_csv, run_thermal_rc


MATERIALS_PATH = ROOT / "data" / "materials" / "thermal_properties.json"
HISTORY_PATH = ROOT / "data" / "thermal" / "engine_history_proxy.csv"
OUT_DIR = ROOT / "data" / "thermal"


def load_materials() -> tuple[dict[str, Any], dict[str, ThermalStrainProfile]]:
    payload = json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))
    materials = {item["id"]: item for item in payload["materials"]}
    profiles = {key: ThermalStrainProfile(tuple(tuple(point) for point in item["strain_points"])) for key, item in materials.items()}
    return materials, profiles


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def candidate_shapes() -> list[dict[str, float | str]]:
    # Explicit illustrative envelopes; no value is presented as an ABC datum.
    return [
        {"candidate": "neutral", "cold_base_um": 10.0, "liner_taper_um": 0.0, "piston_taper_um": 0.0, "piston_barrel_um": 0.0},
        {"candidate": "liner_open_top", "cold_base_um": 10.0, "liner_taper_um": 2.0, "piston_taper_um": 0.0, "piston_barrel_um": 0.0},
        {"candidate": "liner_pinch_top", "cold_base_um": 10.0, "liner_taper_um": -2.0, "piston_taper_um": 0.0, "piston_barrel_um": 0.0},
        {"candidate": "piston_barrel_outward", "cold_base_um": 10.0, "liner_taper_um": 0.0, "piston_taper_um": 0.0, "piston_barrel_um": 2.0},
        {"candidate": "piston_barrel_inward", "cold_base_um": 10.0, "liner_taper_um": 0.0, "piston_taper_um": 0.0, "piston_barrel_um": -2.0},
        {"candidate": "piston_skirt_larger", "cold_base_um": 10.0, "liner_taper_um": 0.0, "piston_taper_um": 2.0, "piston_barrel_um": 0.0},
        {"candidate": "piston_crown_larger", "cold_base_um": 10.0, "liner_taper_um": 0.0, "piston_taper_um": -2.0, "piston_barrel_um": 0.0},
        # Deliberately expose the cold-pinched case requested by Issue #13.
        # This is a mathematical screening example, not a claimed ABC value.
        {"candidate": "cold_tdc_pinch_demo", "cold_base_um": 1.0, "liner_taper_um": -2.0, "piston_taper_um": 0.0, "piston_barrel_um": 0.0},
    ]


def run_case(history, profiles, bore_mm: float, h_model: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rc_config = ThermalRCConfig(bore_mm=bore_mm, h_model=h_model)
    rc_result = run_thermal_rc(history, rc_config, piston_cte=profiles["al_4032_t6"], liner_cte=profiles["steel_4140"])
    periodic_rows = rc_result["history_rows"]
    result_rows: list[dict[str, Any]] = []
    for shape in candidate_shapes():
        for error_um in (-1.0, 0.0, 1.0):
            config = AxialFitConfig(
                bore_diameter_mm=bore_mm,
                cold_radial_clearance_um=float(shape["cold_base_um"]),
                liner_taper_um=float(shape["liner_taper_um"]),
                piston_taper_um=float(shape["piston_taper_um"]),
                piston_barrel_um=float(shape["piston_barrel_um"]),
                machining_error_um=error_um,
                contact_margin_um=1.0,
            )
            bounds = required_base_fit_bounds_um(
                periodic_rows,
                config=config,
                piston_cte=profiles["al_4032_t6"],
                liner_cte=profiles["steel_4140"],
            )
            axial = evaluate_temperature_rows(
                periodic_rows,
                config=config,
                piston_cte=profiles["al_4032_t6"],
                liner_cte=profiles["steel_4140"],
            )
            # A conditional preheat check with a 30 K liner-over-piston offset
            # is included to expose how strongly the answer depends on the
            # missing local temperature split. It is not a start permission.
            preheat_config = AxialFitConfig(
                bore_diameter_mm=bore_mm,
                cold_radial_clearance_um=max(0.0, bounds["lower_bound_um"]),
                liner_taper_um=float(shape["liner_taper_um"]),
                piston_taper_um=float(shape["piston_taper_um"]),
                piston_barrel_um=float(shape["piston_barrel_um"]),
                machining_error_um=error_um,
                contact_margin_um=1.0,
            )
            try:
                preheat = minimum_preheat_temperature_K(
                    config=preheat_config,
                    piston_offset_K=0.0,
                    liner_offset_K=30.0,
                    piston_cte=profiles["al_4032_t6"],
                    liner_cte=profiles["steel_4140"],
                )
            except ValueError:
                preheat = None
            worst = axial["worst_profile"]
            leakage = nonuniform_annulus_leakage(
                worst["stations"],
                # Pair gas forcing with the same history row that supplied the
                # worst axial clearance; BDC row zero is not interchangeable.
                pressure_up_bar=float(worst["source_pressure_bar"]),
                pressure_down_bar=1.0,
                temperature_K=float(worst["source_gas_temperature_K"]),
                bore_diameter_mm=bore_mm,
                skirt_length_mm=8.0,
            )
            result_rows.append({
                "bore_mm": bore_mm,
                "h_model": h_model,
                **shape,
                "machining_error_um": error_um,
                "cold_base_um": float(shape["cold_base_um"]),
                "fit_lower_bound_um": bounds["lower_bound_um"],
                "fit_upper_bound_um": bounds["upper_bound_um"],
                "fit_feasible": bounds["feasible"],
                "nonnegative_fit_feasible": bounds["nonnegative_cold_fit_feasible"],
                "periodic_min_hot_clearance_at_base_um": axial["min_hot_clearance_um"],
                "periodic_contact_at_base": axial["contact"],
                "periodic_below_1um_margin_at_base": axial["below_contact_margin"],
                "worst_station": worst["min_station_label"],
                "worst_profile_deg": worst.get("source_deg"),
                "leakage_pressure_bar": worst.get("source_pressure_bar"),
                "leakage_gas_temperature_K": worst.get("source_gas_temperature_K"),
                "conditional_preheat_type_liner_30K_hotter": preheat["threshold_type"],
                "conditional_preheat_threshold_K_liner_30K_hotter": preheat["threshold_K"],
                "conditional_preheat_Tp_K_at_threshold": preheat["threshold_K"],
                "conditional_preheat_Tl_K_at_threshold": None if preheat["threshold_K"] is None else preheat["threshold_K"] + 30.0,
                "conditional_preheat_safe_intervals_K": json.dumps(preheat["safe_intervals_K"]),
                "nonuniform_leakage_status": leakage["leakage_status"],
                "nonuniform_equivalent_clearance_um": leakage["equivalent_clearance_um"],
                "nonuniform_mdot_mg_s": None if leakage["mass_flow_kg_s"] is None else leakage["mass_flow_kg_s"] * 1e6,
            })
    # Expose only compact axial profiles for neutral zero-error and the two
    # closures; full crank-angle histories remain in thermal_state outputs.
    profile_rows = []
    for shape in candidate_shapes()[:1]:
        config = AxialFitConfig(bore_diameter_mm=bore_mm, cold_radial_clearance_um=10.0)
        selected = evaluate_temperature_rows(
            periodic_rows,
            config=config,
            piston_cte=profiles["al_4032_t6"],
            liner_cte=profiles["steel_4140"],
        )
        for tag, profile in (("first", selected["profiles"][0]), ("worst", selected["worst_profile"])):
            for station in profile["stations"]:
                profile_rows.append({"bore_mm": bore_mm, "h_model": h_model, "candidate": shape["candidate"], "sample": tag, **station})
    summary = {
        "bore_mm": bore_mm,
        "h_model": h_model,
        "rc_periodic_min_path_hot_clearance_3um": rc_result["periodic_min_path_hot_clearance_3um"],
        "rc_warmup_min_path_hot_clearance_3um": rc_result["warmup_min_path_hot_clearance_3um"],
        "rc_periodic_info": rc_result["periodic_info"],
        "candidate_count": len(result_rows),
    }
    return summary, result_rows + [{"_profile_rows": profile_rows}]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    materials, profiles = load_materials()
    history = load_history_csv(args.history, rpm=1200.0)
    summaries: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    for bore_mm in (8.5, 12.5):
        for h_model in ("constant_h", "angle_correlation"):
            summary, rows = run_case(history, profiles, bore_mm, h_model)
            summaries.append(summary)
            candidates.extend(row for row in rows if "_profile_rows" not in row)
            profile_rows.extend(rows[-1]["_profile_rows"])
    out = args.output_dir.resolve()
    write_csv(out / "thermal_fit_axial_candidates.csv", candidates)
    write_csv(out / "thermal_fit_axial_profiles.csv", profile_rows)
    payload = {
        "campaign": "bounded axial thermally developed piston/liner-fit feasibility",
        "status": "screening_only",
        "history": str(args.history.resolve().relative_to(ROOT)).replace("\\", "/"),
        "history_classification": "calculated microengine_rig proxy; no measured wall heat flux or piston/liner temperatures",
        "materials": {"piston": "al_4032_t6", "liner": "steel_4140"},
        "stations": [{"z_mm": s.z_mm, "label": s.label} for s in DEFAULT_STATIONS],
        "screening_envelope_um": {"liner_taper_amplitude": [-2.0, 2.0], "piston_taper_amplitude": [-2.0, 2.0], "piston_barrel_amplitude": [-2.0, 2.0], "machining_error": [-1.0, 1.0]},
        "summaries": summaries,
        "model_classification": {
            "literature_derived_calculation": "material strain profiles/conductivity only; ringed literature is not injected",
            "project_model_result": "RC node temperatures, axial interpolation, signed clearance and series annulus sensitivity",
            "inference": "illustrative taper/barrel envelopes and 1 um contact margin",
            "unknowns": "local axial temperatures, ABC taper magnitude, machining error/roundness, contact pressure, oil film, ringless heat transfer and calibrated flow",
        },
        "ringless_path": "positive-clearance axial annulus sensitivity only",
        "ringed_path": "not coupled; ring Cd/heat-path literature remains ringed-only and requires ring geometry/measurement",
        "radial_convention": "all clearances are radial; bore/piston dimensions are diameters; hot gap <= 0 is contact, never flow",
        "rpm_note": "Only 1200 rpm is run; other RPM thermal effects are unsupported proxy forcing until speed-dependent history is supplied",
        "files": ["thermal_fit_axial_candidates.csv", "thermal_fit_axial_profiles.csv"],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "thermal_fit_axial_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(out), "candidate_rows": len(candidates), "profile_rows": len(profile_rows), "cases": len(summaries)}, indent=2))


if __name__ == "__main__":
    main()
