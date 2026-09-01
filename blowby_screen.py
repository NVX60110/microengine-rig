#!/usr/bin/env python3
"""Beta 2.1 nonreacting blowby screen (Python standard library only).

Motored ideal-gas compression/expansion with bidirectional compressible-orifice
ring leakage. Open-system energy uses flow enthalpy (cp*T), not internal energy.
Use this to bound leakage before running the Cantera chemistry model.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math

R_AIR = 287.05


def geometry(bore_mm: float, stroke_mm: float, compression_ratio: float,
             rod_stroke_ratio: float = 1.6):
    bore, stroke = bore_mm / 1000.0, stroke_mm / 1000.0
    radius, rod = stroke / 2.0, rod_stroke_ratio * stroke
    area = math.pi * bore**2 / 4.0
    displacement = area * stroke
    clearance = displacement / (compression_ratio - 1.0)
    clearance_height = clearance / area

    def position(theta: float) -> float:
        root = math.sqrt(max(1e-30, rod**2 - radius**2 * math.sin(theta)**2))
        return radius * (1.0 - math.cos(theta)) + rod - root

    def volume(theta: float) -> float:
        return clearance + area * position(theta)

    def surface(theta: float) -> float:
        return 2.0 * area + math.pi * bore * (clearance_height + position(theta))

    return displacement, clearance, volume, surface


def orifice_mdot(p_up: float, t_up: float, p_down: float, area_m2: float,
                 discharge_coefficient: float, gamma: float, gas_constant: float):
    if area_m2 <= 0 or discharge_coefficient <= 0 or p_up <= p_down:
        return 0.0, False
    ratio = max(0.0, min(1.0, p_down / p_up))
    critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    prefactor = discharge_coefficient * area_m2 * p_up / math.sqrt(gas_constant * t_up)
    if ratio <= critical:
        factor = math.sqrt(gamma) * (2.0 / (gamma + 1.0)) ** (
            (gamma + 1.0) / (2.0 * (gamma - 1.0)))
        return prefactor * factor, True
    factor = 2.0 * gamma / (gamma - 1.0)
    factor *= ratio ** (2.0 / gamma) - ratio ** ((gamma + 1.0) / gamma)
    return prefactor * math.sqrt(max(0.0, factor)), False


def run(bore_mm=8.5, stroke_mm=7.0, compression_ratio=7.0,
        rod_stroke_ratio=1.6, rpm=1200.0, intake_pressure_bar=1.5,
        intake_temperature_K=500.0, crankcase_pressure_bar=1.0,
        crankcase_temperature_K=350.0, wall_temperature_K=800.0,
        effective_h_W_m2K=300.0, ring_end_gap_mm=0.05,
        ring_axial_height_mm=0.40, ring_count=2,
        discharge_coefficient=0.70, effective_area_mm2=0.0,
        allow_reverse=True, gamma=1.35, step_deg=0.05):
    displacement, clearance, volume_at, surface_at = geometry(
        bore_mm, stroke_mm, compression_ratio, rod_stroke_ratio)
    omega = rpm * 2.0 * math.pi / 60.0
    dtheta, dt = math.radians(step_deg), math.radians(step_deg) / omega
    cv, cp = R_AIR / (gamma - 1.0), gamma * R_AIR / (gamma - 1.0)
    if effective_area_mm2 > 0:
        leak_area = effective_area_mm2 * 1e-6
    elif ring_count > 0:
        leak_area = ring_end_gap_mm * ring_axial_height_mm * 1e-6 / math.sqrt(ring_count)
    else:
        leak_area = 0.0

    theta = -math.pi
    volume = volume_at(theta)
    mass = intake_pressure_bar * 1e5 * volume / (R_AIR * intake_temperature_K)
    initial_mass, temperature = mass, intake_temperature_K
    pressure = mass * R_AIR * temperature / volume
    mass_out = mass_in = work = wall_energy = 0.0
    peak_pressure, peak_temperature = pressure, temperature
    tdc_mass = tdc_pressure = tdc_temperature = None
    outflow_steps = choked_steps = 0
    steps = int(round(360.0 / step_deg))

    for index in range(steps):
        theta2 = theta + dtheta
        volume2 = volume_at(theta2)
        area_mid = 0.5 * (surface_at(theta) + surface_at(theta2))
        out_rate, choked = orifice_mdot(
            pressure, temperature, crankcase_pressure_bar * 1e5, leak_area,
            discharge_coefficient, gamma, R_AIR)
        in_rate = 0.0
        if allow_reverse:
            in_rate, _ = orifice_mdot(
                crankcase_pressure_bar * 1e5, crankcase_temperature_K, pressure,
                leak_area, discharge_coefficient, gamma, R_AIR)
        dm_out, dm_in = out_rate * dt, in_rate * dt
        dm_out = min(dm_out, 0.25 * mass)
        q_gas_to_wall = effective_h_W_m2K * area_mid * (temperature - wall_temperature_K) * dt
        piston_work = pressure * (volume2 - volume)
        energy2 = (mass * cv * temperature - piston_work - q_gas_to_wall
                   - dm_out * cp * temperature
                   + dm_in * cp * crankcase_temperature_K)
        mass2 = mass - dm_out + dm_in
        if mass2 <= 1e-15:
            raise RuntimeError("Cylinder mass collapsed; reduce the step or leak area.")
        temperature2 = max(100.0, energy2 / (mass2 * cv))
        pressure2 = mass2 * R_AIR * temperature2 / volume2
        work += 0.5 * (pressure + pressure2) * (volume2 - volume)
        wall_energy += q_gas_to_wall
        mass_out += dm_out
        mass_in += dm_in
        if out_rate > 0:
            outflow_steps += 1
            choked_steps += int(choked)
        theta, volume, mass = theta2, volume2, mass2
        temperature, pressure = temperature2, pressure2
        peak_pressure, peak_temperature = max(peak_pressure, pressure), max(peak_temperature, temperature)
        if tdc_mass is None and theta >= 0:
            tdc_mass, tdc_pressure, tdc_temperature = mass, pressure, temperature

    return {
        "bore_mm": bore_mm,
        "stroke_mm": stroke_mm,
        "compression_ratio": compression_ratio,
        "rpm": rpm,
        "ring_end_gap_mm": ring_end_gap_mm,
        "effective_leak_area_mm2": leak_area * 1e6,
        "displacement_cc": displacement * 1e6,
        "clearance_volume_mm3": clearance * 1e9,
        "initial_mass_mg": initial_mass * 1e6,
        "tdc_mass_mg": tdc_mass * 1e6,
        "tdc_mass_retained_fraction": tdc_mass / initial_mass,
        "end_mass_retained_fraction": mass / initial_mass,
        "mass_out_mg": mass_out * 1e6,
        "mass_in_mg": mass_in * 1e6,
        "mass_balance_residual_mg": (initial_mass - mass - mass_out + mass_in) * 1e6,
        "tdc_pressure_bar": tdc_pressure / 1e5,
        "tdc_temperature_K": tdc_temperature,
        "peak_pressure_bar": peak_pressure / 1e5,
        "peak_temperature_K": peak_temperature,
        "wall_energy_gas_to_wall_mJ": wall_energy * 1000.0,
        "indicated_work_mJ": work * 1000.0,
        "imep_bar": work / displacement / 1e5,
        "outflow_choked_step_fraction": choked_steps / outflow_steps if outflow_steps else 0.0,
        "model_note": "Screening model; calibrate effective leak area and Cd against crankcase flow.",
    }


def main():
    parser = argparse.ArgumentParser(description="Standard-library microengine blowby screen")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--sweep", help="JSON object mapping parameter names to value lists")
    parser.add_argument("--json", default="blowby_screen_results.json")
    parser.add_argument("--csv", default="blowby_screen_results.csv")
    args = parser.parse_args()
    base = {}
    for item in args.set:
        key, value = item.split("=", 1)
        base[key] = value.lower() == "true" if value.lower() in {"true", "false"} else float(value)
    patches = [{}]
    if args.sweep:
        with open(args.sweep, encoding="utf-8") as handle:
            sweep_data = json.load(handle)
        grid = sweep_data.get("grid", sweep_data)
        keys = list(grid)
        patches = [dict(zip(keys, values)) for values in itertools.product(*(grid[key] for key in keys))]
    results = [run(**{**base, **patch}) for patch in patches]
    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    with open(args.csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps({"runs": len(results), "json": args.json, "csv": args.csv}, indent=2))


if __name__ == "__main__":
    main()
