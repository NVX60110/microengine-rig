#!/usr/bin/env python3
"""Transparent mechanical-load screens for MicroEngine pressure histories.

These calculations replace a borrowed fixed peak-pressure limit with loads and
required dimensions. They are not a stress, fatigue, bearing-lubrication, or
fastener analysis. Gas load is reported as a lower bound because inertia,
misalignment, oil-film dynamics, stress concentrations, and thermal stress are
not solved.
"""
from __future__ import annotations

import argparse
import json
import math


def mechanical_metrics(
    *,
    peak_pressure_bar: float,
    peak_temperature_K: float,
    max_pressure_rise_bar_per_deg: float,
    peak_pressure_deg_atdc: float,
    bore_mm: float = 8.5,
    stroke_mm: float = 7.0,
    rod_stroke_ratio: float = 1.6,
    rpm: float = 1200.0,
    crankcase_pressure_bar: float = 1.0,
    crankpin_diameter_mm: float = 2.0,
    crankpin_width_mm: float = 3.0,
    cylinder_wall_thickness_mm: float = 2.0,
    wall_allowable_stress_MPa: float = 80.0,
    reference_bearing_pressure_MPa: float = 50.0,
    gamma: float = 1.30,
    gas_constant_J_kgK: float = 287.0,
    ringing_beta_us: float = 50.0,
) -> dict[str, float | str]:
    if min(bore_mm, stroke_mm, crankpin_diameter_mm, crankpin_width_mm,
           cylinder_wall_thickness_mm, wall_allowable_stress_MPa,
           reference_bearing_pressure_MPa) <= 0:
        raise ValueError("Geometry and reference allowables must be positive.")

    bore_m = bore_mm / 1000.0
    piston_area_m2 = math.pi * bore_m**2 / 4.0
    net_pressure_Pa = max(0.0, peak_pressure_bar - crankcase_pressure_bar) * 1e5
    gas_force_N = net_pressure_Pa * piston_area_m2

    crank_radius = stroke_mm / 2.0
    rod_length = rod_stroke_ratio * stroke_mm
    theta = math.radians(peak_pressure_deg_atdc)
    sin_beta = max(-0.999999, min(0.999999,
        crank_radius / rod_length * math.sin(theta)))
    rod_angle_deg = math.degrees(math.asin(sin_beta))
    rod_force_N = gas_force_N / math.sqrt(1.0 - sin_beta**2)
    projected_area_mm2 = crankpin_diameter_mm * crankpin_width_mm
    projected_bearing_pressure_MPa = rod_force_N / projected_area_mm2

    inner_radius_m = bore_m / 2.0
    outer_radius_m = inner_radius_m + cylinder_wall_thickness_mm / 1000.0
    thick_wall_factor = (
        (outer_radius_m**2 + inner_radius_m**2)
        / (outer_radius_m**2 - inner_radius_m**2)
    )
    inner_wall_hoop_stress_MPa = peak_pressure_bar * 0.1 * thick_wall_factor
    pressure_MPa = peak_pressure_bar * 0.1
    allowable_ratio = wall_allowable_stress_MPa / max(pressure_MPa, 1e-30)
    if allowable_ratio <= 1.0:
        required_wall_thickness_mm = float("inf")
    else:
        required_outer_radius_m = inner_radius_m * math.sqrt(
            (allowable_ratio + 1.0) / (allowable_ratio - 1.0)
        )
        required_wall_thickness_mm = (required_outer_radius_m - inner_radius_m) * 1000.0

    required_projected_area_mm2 = rod_force_N / reference_bearing_pressure_MPa
    required_bearing_width_mm = required_projected_area_mm2 / crankpin_diameter_mm

    crank_deg_per_second = 6.0 * rpm
    pressure_rise_bar_per_ms = (
        max_pressure_rise_bar_per_deg * crank_deg_per_second / 1000.0
    )
    pressure_rise_Pa_per_s = pressure_rise_bar_per_ms * 1e8
    sound_speed_m_s = math.sqrt(
        gamma * gas_constant_J_kgK * max(peak_temperature_K, 1.0)
    )
    ringing_beta_s = ringing_beta_us * 1e-6
    ringing_intensity_W_m2 = (
        (ringing_beta_s * pressure_rise_Pa_per_s) ** 2
        * sound_speed_m_s
        / (2.0 * gamma * max(peak_pressure_bar * 1e5, 1.0))
    )
    first_radial_frequency_Hz = 1.84118 / math.pi * sound_speed_m_s / bore_m

    return {
        "peak_net_gas_force_N": gas_force_N,
        "rod_angle_at_peak_pressure_deg": rod_angle_deg,
        "gas_only_rod_force_N": rod_force_N,
        "crankpin_projected_area_mm2": projected_area_mm2,
        "gas_only_projected_bearing_pressure_MPa": projected_bearing_pressure_MPa,
        "reference_bearing_pressure_MPa": reference_bearing_pressure_MPa,
        "required_crankpin_projected_area_mm2": required_projected_area_mm2,
        "required_bearing_width_at_reference_pressure_mm": required_bearing_width_mm,
        "thick_wall_inner_hoop_stress_MPa": inner_wall_hoop_stress_MPa,
        "wall_allowable_stress_MPa": wall_allowable_stress_MPa,
        "required_wall_thickness_at_allowable_mm": required_wall_thickness_mm,
        "pressure_rise_bar_per_ms": pressure_rise_bar_per_ms,
        "estimated_ringing_intensity_MW_m2": ringing_intensity_W_m2 / 1e6,
        "estimated_first_radial_acoustic_frequency_kHz": first_radial_frequency_Hz / 1000.0,
        "mechanical_note": (
            "Gas-only screening loads. Add inertia, fatigue, stress concentrations, "
            "thermal distortion, fasteners, piston/pin/rod FEA, and hydrodynamic or "
            "mixed-lubrication bearing analysis before setting a pressure limit."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peak-pressure-bar", type=float, required=True)
    parser.add_argument("--peak-temperature-K", type=float, required=True)
    parser.add_argument("--max-pressure-rise-bar-per-deg", type=float, required=True)
    parser.add_argument("--peak-pressure-deg-atdc", type=float, default=0.0)
    parser.add_argument("--bore-mm", type=float, default=8.5)
    parser.add_argument("--stroke-mm", type=float, default=7.0)
    parser.add_argument("--rpm", type=float, default=1200.0)
    parser.add_argument("--crankpin-diameter-mm", type=float, default=2.0)
    parser.add_argument("--crankpin-width-mm", type=float, default=3.0)
    parser.add_argument("--cylinder-wall-thickness-mm", type=float, default=2.0)
    args = parser.parse_args()
    print(json.dumps(mechanical_metrics(
        peak_pressure_bar=args.peak_pressure_bar,
        peak_temperature_K=args.peak_temperature_K,
        max_pressure_rise_bar_per_deg=args.max_pressure_rise_bar_per_deg,
        peak_pressure_deg_atdc=args.peak_pressure_deg_atdc,
        bore_mm=args.bore_mm,
        stroke_mm=args.stroke_mm,
        rpm=args.rpm,
        crankpin_diameter_mm=args.crankpin_diameter_mm,
        crankpin_width_mm=args.crankpin_width_mm,
        cylinder_wall_thickness_mm=args.cylinder_wall_thickness_mm,
    ), indent=2))


if __name__ == "__main__":
    main()
