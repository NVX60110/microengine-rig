#!/usr/bin/env python3
"""Experimental pressure-coupled two-zone model for MicroEngine Beta 2.4.

The cylinder is represented by a reactive core and a wall-adjacent zone. An
internal moving Cantera wall approximately equalizes their pressures while
conserving total volume. Only the boundary zone exchanges heat with the chamber
wall. Optional equal counterflows exchange enthalpy and species between zones.

This is a spatial-uncertainty bracket, not CFD or a calibrated quench model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any

import cantera as ct

from microengine_rig import (
    RigConfig,
    blowby_area_m2,
    build_geometry,
    compressible_annular_mdot,
    compressible_orifice_mdot,
    resolve_fuel_profile,
    validate_config,
)


@dataclass(frozen=True)
class TwoZoneOptions:
    boundary_mass_fraction: float = 0.20
    boundary_piston_area_fraction: float | None = None
    pressure_equalization_coeff_m_s_Pa: float = 5.0e-5
    interzone_heat_transfer_coeff_W_m2K: float = 100.0
    interface_area_factor: float = 1.0
    mixing_time_ms: float = 10.0  # 0 disables mass/species exchange
    mixing_model: str = "constant"  # constant | diffusion-strain
    mixing_length_mm: float = 1.0
    molecular_diffusivity_m2_s: float = 3.0e-6
    piston_strain_coefficient: float = 1.0
    mixing_min_time_ms: float = 0.10
    mixing_max_time_ms: float = 100.0
    integrator_rtol: float = 1.0e-7
    integrator_atol: float = 1.0e-14
    boundary_leak_bias: float = 0.0  # 0 proportional; 1 all leakage from boundary


def validate_two_zone(c: RigConfig, z: TwoZoneOptions) -> None:
    validate_config(c)
    if c.ignition_mode != "cantera-auto":
        raise ValueError("The two-zone model requires ignition_mode=cantera-auto.")
    if c.wall_mode not in {"fixed", "adiabatic"}:
        raise ValueError("Beta 2.4 two-zone runs support fixed or adiabatic walls.")
    if c.blowby_mode not in {"off", "orifice", "annular"}:
        raise ValueError("Two-zone runs support off, orifice, or annular blowby.")
    if not 0.02 <= z.boundary_mass_fraction <= 0.60:
        raise ValueError("boundary_mass_fraction must be between 0.02 and 0.60.")
    area_fraction = (
        z.boundary_mass_fraction if z.boundary_piston_area_fraction is None
        else z.boundary_piston_area_fraction
    )
    if not 0.02 <= area_fraction <= 0.60:
        raise ValueError("boundary_piston_area_fraction must be between 0.02 and 0.60.")
    if z.pressure_equalization_coeff_m_s_Pa <= 0:
        raise ValueError("pressure equalization coefficient must be positive.")
    if z.interzone_heat_transfer_coeff_W_m2K < 0 or z.interface_area_factor <= 0:
        raise ValueError("Inter-zone heat transfer must be nonnegative and area positive.")
    if z.mixing_time_ms < 0:
        raise ValueError("mixing_time_ms cannot be negative.")
    if z.mixing_model not in {"constant", "diffusion-strain"}:
        raise ValueError("mixing_model must be constant or diffusion-strain.")
    if z.mixing_length_mm <= 0 or z.molecular_diffusivity_m2_s < 0:
        raise ValueError("Mixing length must be positive and diffusivity nonnegative.")
    if z.piston_strain_coefficient < 0:
        raise ValueError("piston_strain_coefficient cannot be negative.")
    if not 0 < z.mixing_min_time_ms <= z.mixing_max_time_ms:
        raise ValueError("Mixing time bounds must be positive and ordered.")
    if z.integrator_rtol <= 0 or z.integrator_atol <= 0:
        raise ValueError("Integrator tolerances must be positive.")
    if not 0.0 <= z.boundary_leak_bias <= 1.0:
        raise ValueError("boundary_leak_bias must be between 0 and 1.")


def _mechanism_path(name: str) -> str:
    direct = Path(name)
    if direct.exists() or direct.parent == Path("."):
        return str(direct)
    return str(Path(__file__).resolve().parent / direct)


def _crossing(rows: list[dict[str, Any]], field: str, fraction: float) -> float | None:
    final = rows[-1][field]
    if final <= 0:
        return None
    target = fraction * final
    for left, right in zip(rows, rows[1:]):
        if left[field] <= target <= right[field]:
            span = right[field] - left[field]
            if span <= 0:
                return right["deg"]
            weight = (target - left[field]) / span
            return left["deg"] + weight * (right["deg"] - left["deg"])
    return rows[-1]["deg"]


def _branch(summary: dict[str, Any]) -> str:
    imep = summary["gross_imep_bar"]
    temperature = summary["peak_temperature_K"]
    rise = summary["max_pressure_rise_bar_per_deg"]
    conversion = summary["max_fuel_consumed_fraction"]
    ca50 = summary["CA50_deg_atdc"]
    if imep <= 0:
        return "no_positive_gross_work"
    if rise > 10.0:
        return "rapid_heat_release"
    if temperature < 1300.0 and 0.10 <= conversion < 0.90:
        if ca50 is not None and -15.0 <= ca50 <= 20.0:
            return "cool_partial_candidate"
        return "cool_partial_outside_phase_window"
    if temperature < 1600.0:
        return "intermediate_temperature"
    return "hot_combustion"


def simulate_two_zone(c: RigConfig, z: TwoZoneOptions = TwoZoneOptions()):
    """Run one closed compression-expansion cycle.

    Returns per-angle rows and a flat summary. Fuel consumption is the time
    integral of local chemical destruction of the configured fuel species; it
    therefore remains meaningful when the zones exchange mass.
    """
    validate_two_zone(c, z)
    geometry = build_geometry(c)
    profile = resolve_fuel_profile(c)
    mechanism = _mechanism_path(profile.mechanism)
    gas = ct.Solution(mechanism, profile.phase) if profile.phase else ct.Solution(mechanism)
    gas.set_equivalence_ratio(c.equivalence_ratio, profile.fuel, profile.oxidizer)
    gas.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    initial_X = gas.X

    boundary_gas = (
        ct.Solution(mechanism, profile.phase) if profile.phase
        else ct.Solution(mechanism)
    )
    boundary_gas.TPX = gas.TPX
    # Independent Solution objects preserve transport data used by the annular
    # leakage law while preventing either reactor from mutating the other.
    core = ct.IdealGasReactor(gas, energy="on", clone=False, name="core")
    boundary = ct.IdealGasReactor(
        boundary_gas, energy="on", clone=False, name="boundary"
    )
    initial_volume = geometry.volume(-math.pi)
    boundary_fraction = z.boundary_mass_fraction
    area_fraction = (
        boundary_fraction if z.boundary_piston_area_fraction is None
        else z.boundary_piston_area_fraction
    )
    core.volume = (1.0 - boundary_fraction) * initial_volume
    boundary.volume = boundary_fraction * initial_volume

    sink_gas = ct.Solution("air.yaml")
    sink_gas.TP = c.wall_temperature_K, c.intake_pressure_bar * 1e5
    sink = ct.Reservoir(sink_gas, clone=False)
    core_piston = ct.Wall(
        core, sink, A=(1.0 - area_fraction) * geometry.piston_area_m2
    )
    boundary_piston = ct.Wall(
        boundary, sink, A=area_fraction * geometry.piston_area_m2
    )
    boundary_heat = ct.Wall(
        boundary, sink, A=geometry.surface_area(-math.pi),
        U=0.0 if c.wall_mode == "adiabatic" else c.effective_h_W_m2K,
    )
    interface = ct.Wall(
        core, boundary,
        A=z.interface_area_factor * geometry.piston_area_m2,
        K=z.pressure_equalization_coeff_m_s_Pa,
        U=z.interzone_heat_transfer_coeff_W_m2K,
    )

    def instantaneous_mixing_time_s(time_s: float) -> float:
        """Return the current exchange time for the selected closure.

        The diffusion-strain closure adds a first-eigenmode radial diffusion
        rate to a piston-strain rate. It is an uncertainty model to be
        calibrated by cold-flow CFD, not a turbulence correlation.
        """
        if z.mixing_model == "constant":
            return math.inf if z.mixing_time_ms <= 0 else z.mixing_time_ms / 1000.0
        angle = -math.pi + geometry.omega_rad_s * time_s
        length_m = z.mixing_length_mm / 1000.0
        diffusion_rate = math.pi**2 * z.molecular_diffusivity_m2_s / length_m**2
        strain_rate = (
            z.piston_strain_coefficient
            * abs(geometry.piston_velocity(angle))
            / max(c.bore_mm / 1000.0, 1e-12)
        )
        raw_time = 1.0 / max(diffusion_rate + strain_rate, 1e-30)
        return min(
            z.mixing_max_time_ms / 1000.0,
            max(z.mixing_min_time_ms / 1000.0, raw_time),
        )

    mix_controllers: list[Any] = []
    mixing_enabled = z.mixing_model == "diffusion-strain" or z.mixing_time_ms > 0
    if mixing_enabled:
        def exchange_rate(time_s: float = 0.0) -> float:
            return min(core.mass, boundary.mass) / instantaneous_mixing_time_s(time_s)

        mix_controllers.extend([
            ct.MassFlowController(core, boundary, mdot=exchange_rate),
            ct.MassFlowController(boundary, core, mdot=exchange_rate),
        ])

    crankcase = None
    leak_controllers: list[Any] = []
    if c.blowby_mode in {"orifice", "annular"}:
        crank_gas = ct.Solution(mechanism, profile.phase) if profile.phase else ct.Solution(mechanism)
        crank_gas.TPX = (
            c.crankcase_temperature_K,
            c.crankcase_pressure_bar * 1e5,
            initial_X,
        )
        crankcase = ct.Reservoir(crank_gas, clone=False)

        def weights() -> tuple[float, float]:
            total = max(core.mass + boundary.mass, 1e-30)
            proportional_boundary = boundary.mass / total
            boundary_weight = (
                proportional_boundary
                + z.boundary_leak_bias * (1.0 - proportional_boundary)
            )
            return 1.0 - boundary_weight, boundary_weight

        leak_area = blowby_area_m2(c)

        def leakage_rate(upstream, downstream) -> float:
            phase = upstream.phase
            if c.blowby_mode == "orifice":
                return compressible_orifice_mdot(
                    phase.P,
                    phase.T,
                    downstream.phase.P,
                    leak_area,
                    phase.cp_mass / phase.cv_mass,
                    ct.gas_constant / phase.mean_molecular_weight,
                    c.blowby_discharge_coefficient,
                )[0]
            viscosity = c.annular_dynamic_viscosity_Pa_s or phase.viscosity
            return compressible_annular_mdot(
                phase.P, phase.T, downstream.phase.P,
                c.bore_mm / 1000.0,
                c.annular_radial_clearance_um * 1e-6,
                c.annular_skirt_length_mm / 1000.0,
                viscosity,
                ct.gas_constant / phase.mean_molecular_weight,
                c.annular_eccentricity_ratio,
            )

        def core_out(_time: float = 0.0) -> float:
            return weights()[0] * leakage_rate(core, crankcase)

        def boundary_out(_time: float = 0.0) -> float:
            return weights()[1] * leakage_rate(boundary, crankcase)

        leak_controllers.extend([
            ct.MassFlowController(core, crankcase, mdot=core_out),
            ct.MassFlowController(boundary, crankcase, mdot=boundary_out),
        ])
        if c.blowby_allow_reverse:
            def core_in(_time: float = 0.0) -> float:
                return weights()[0] * leakage_rate(crankcase, core)

            def boundary_in(_time: float = 0.0) -> float:
                return weights()[1] * leakage_rate(crankcase, boundary)

            leak_controllers.extend([
                ct.MassFlowController(crankcase, core, mdot=core_in),
                ct.MassFlowController(crankcase, boundary, mdot=boundary_in),
            ])
        else:
            core_in = lambda _time=0.0: 0.0
            boundary_in = lambda _time=0.0: 0.0
    else:
        core_out = boundary_out = core_in = boundary_in = lambda _time=0.0: 0.0

    network = ct.ReactorNet([core, boundary])
    step_rad = math.radians(c.step_deg)
    dt = step_rad / geometry.omega_rad_s
    network.max_time_step = dt / 4.0
    network.max_steps = 100000
    network.max_err_test_fails = 30
    network.rtol = z.integrator_rtol
    network.atol = z.integrator_atol

    fuel_names = list(profile.fuel_species)
    initial_component_mass = {
        name: core.mass * core.phase[name].Y[0] + boundary.mass * boundary.phase[name].Y[0]
        for name in fuel_names
    }
    initial_fuel_mass = sum(initial_component_mass.values())
    initial_mass = core.mass + boundary.mass
    component_core_reacted = {name: 0.0 for name in fuel_names}
    component_boundary_reacted = {name: 0.0 for name in fuel_names}
    component_out = {name: 0.0 for name in fuel_names}
    component_in = {name: 0.0 for name in fuel_names}
    chemical_energy = wall_energy = work = 0.0
    mass_out = mass_in = 0.0
    rows: list[dict[str, Any]] = []
    max_pressure_difference = max_volume_error = 0.0

    def component_reaction_rates(reactor) -> dict[str, float]:
        phase = reactor.phase
        return {
            name: -phase.net_production_rates[phase.species_index(name)]
            * phase.molecular_weights[phase.species_index(name)]
            * reactor.volume
            for name in fuel_names
        }

    def heat_release(reactor) -> float:
        return reactor.phase.heat_release_rate * reactor.volume

    def effective_pressure() -> float:
        return (1.0 - area_fraction) * core.phase.P + area_fraction * boundary.phase.P

    def state_rates():
        core_out_rate = core_out()
        boundary_out_rate = boundary_out()
        core_in_rate = core_in()
        boundary_in_rate = boundary_in()
        crank_phase = crankcase.phase if crankcase is not None else None
        return {
            "core_component": component_reaction_rates(core),
            "boundary_component": component_reaction_rates(boundary),
            "core_hrr": heat_release(core),
            "boundary_hrr": heat_release(boundary),
            "wall_heat": boundary_heat.heat_rate,
            "out": core_out_rate + boundary_out_rate,
            "in": core_in_rate + boundary_in_rate,
            "component_out": {
                name: (
                    core_out_rate * core.phase[name].Y[0]
                    + boundary_out_rate * boundary.phase[name].Y[0]
                ) for name in fuel_names
            },
            "component_in": {
                name: (
                    (core_in_rate + boundary_in_rate) * crank_phase[name].Y[0]
                    if crank_phase is not None else 0.0
                ) for name in fuel_names
            },
        }

    steps = int(round(360.0 / c.step_deg))
    for index in range(steps + 1):
        deg = -180.0 + index * c.step_deg
        theta = math.radians(deg)
        target_volume = geometry.volume(theta)
        total_volume = core.volume + boundary.volume
        effective_P = effective_pressure()
        # Primary conversion uses exact global inventory accounting. The
        # source-term integral below is retained only to localize reaction
        # between zones; on a stiff coarse step it can accumulate quadrature
        # error and must not be presented as physical fuel conversion.
        component_inventory_consumed = {
            name: (
                initial_component_mass[name] + component_in[name]
                - component_out[name]
                - core.mass * core.phase[name].Y[0]
                - boundary.mass * boundary.phase[name].Y[0]
            )
            for name in fuel_names
        }
        fuel_consumed = min(1.0, max(
            0.0,
            sum(component_inventory_consumed.values())
            / max(initial_fuel_mass, 1e-30),
        ))
        component_consumption = {
            f"fuelConsumed_{name.upper()}_fraction": min(
                1.0,
                max(0.0, component_inventory_consumed[name]
                    / max(initial_component_mass[name], 1e-30)),
            )
            for name in fuel_names
        }
        current_rates = state_rates()
        row = {
            "deg": deg,
            "effectivePressure_bar": effective_P / 1e5,
            "corePressure_bar": core.phase.P / 1e5,
            "boundaryPressure_bar": boundary.phase.P / 1e5,
            "pressureDifference_mbar": (core.phase.P - boundary.phase.P) / 100.0,
            "coreTemperature_K": core.T,
            "boundaryTemperature_K": boundary.T,
            "coreVolume_mm3": core.volume * 1e9,
            "boundaryVolume_mm3": boundary.volume * 1e9,
            "boundaryVolumeFraction": boundary.volume / max(total_volume, 1e-30),
            "targetVolume_mm3": target_volume * 1e9,
            "volumeClosureError_mm3": (total_volume - target_volume) * 1e9,
            "coreMass_mg": core.mass * 1e6,
            "boundaryMass_mg": boundary.mass * 1e6,
            "massRetentionFraction": (core.mass + boundary.mass) / initial_mass,
            "instantaneousMixingTime_ms": (
                instantaneous_mixing_time_s(network.time) * 1000.0
                if mixing_enabled else float("inf")
            ),
            "fuelConsumedFraction": fuel_consumed,
            "coreFuelReactionExtent_fraction_initial_total": (
                sum(component_core_reacted.values()) / max(initial_fuel_mass, 1e-30)
            ),
            "boundaryFuelReactionExtent_fraction_initial_total": (
                sum(component_boundary_reacted.values()) / max(initial_fuel_mass, 1e-30)
            ),
            "coreChemicalHeatReleaseRate_W": current_rates["core_hrr"],
            "boundaryChemicalHeatReleaseRate_W": current_rates["boundary_hrr"],
            "totalChemicalHeatReleaseRate_W": (
                current_rates["core_hrr"] + current_rates["boundary_hrr"]
            ),
            "cumulativeChemicalHeatRelease_mJ": chemical_energy * 1000.0,
            "wallHeatRate_W": current_rates["wall_heat"],
            "wallHeat_mJ": wall_energy * 1000.0,
            "work_mJ": work * 1000.0,
            "blowbyOutRate_mg_s": current_rates["out"] * 1e6,
            "blowbyInRate_mg_s": current_rates["in"] * 1e6,
            **component_consumption,
        }
        for requested in ("CO", "CO2", "CH2O", "CH4", "CH3OCH3", "O2"):
            for zone_name, reactor in (("core", core), ("boundary", boundary)):
                actual = {name.lower(): name for name in reactor.phase.species_names}.get(
                    requested.lower()
                )
                row[f"{zone_name}_X_{requested}"] = (
                    reactor.phase[actual].X[0] if actual else float("nan")
                )
        rows.append(row)
        max_pressure_difference = max(
            max_pressure_difference, abs(core.phase.P - boundary.phase.P)
        )
        max_volume_error = max(max_volume_error, abs(total_volume - target_volume))
        if index == steps:
            break

        next_theta = math.radians(deg + c.step_deg)
        next_target_volume = geometry.volume(next_theta)
        piston_velocity = (
            (next_target_volume - target_volume) / dt / geometry.piston_area_m2
        )
        core_piston.velocity = piston_velocity
        boundary_piston.velocity = piston_velocity
        boundary_heat.area = 0.5 * (
            geometry.surface_area(theta) + geometry.surface_area(next_theta)
        )
        rate0 = current_rates
        pressure0 = effective_P
        network.advance(network.time + dt)
        rate1 = state_rates()
        pressure1 = effective_pressure()

        for name in fuel_names:
            component_core_reacted[name] += 0.5 * (
                rate0["core_component"][name] + rate1["core_component"][name]
            ) * dt
            component_boundary_reacted[name] += 0.5 * (
                rate0["boundary_component"][name] + rate1["boundary_component"][name]
            ) * dt
        chemical_energy += 0.5 * (
            max(0.0, rate0["core_hrr"] + rate0["boundary_hrr"])
            + max(0.0, rate1["core_hrr"] + rate1["boundary_hrr"])
        ) * dt
        wall_energy += 0.5 * (rate0["wall_heat"] + rate1["wall_heat"]) * dt
        mass_out += 0.5 * (rate0["out"] + rate1["out"]) * dt
        mass_in += 0.5 * (rate0["in"] + rate1["in"]) * dt
        for name in fuel_names:
            component_out[name] += 0.5 * (
                rate0["component_out"][name] + rate1["component_out"][name]
            ) * dt
            component_in[name] += 0.5 * (
                rate0["component_in"][name] + rate1["component_in"][name]
            ) * dt
        work += 0.5 * (pressure0 + pressure1) * (next_target_volume - target_volume)

    for index, row in enumerate(rows):
        left = rows[max(0, index - 1)]
        right = rows[min(len(rows) - 1, index + 1)]
        angle_span = right["deg"] - left["deg"]
        row["pressureRise_bar_per_deg"] = (
            0.0 if angle_span == 0 else
            (right["effectivePressure_bar"] - left["effectivePressure_bar"]) / angle_span
        )

    peak_pressure = max(rows, key=lambda row: row["effectivePressure_bar"])
    peak_rise = max(rows, key=lambda row: row["pressureRise_bar_per_deg"])
    peak_core_temperature = max(rows, key=lambda row: row["coreTemperature_K"])
    peak_boundary_temperature = max(rows, key=lambda row: row["boundaryTemperature_K"])
    ca10, ca50, ca90 = (
        _crossing(rows, "cumulativeChemicalHeatRelease_mJ", fraction)
        for fraction in (0.10, 0.50, 0.90)
    )
    final_consumption = rows[-1]["fuelConsumedFraction"]
    cycle_frequency = c.rpm / 60.0 / c.cycle_revolutions
    summary: dict[str, Any] = {
        "model": "experimental-pressure-coupled-two-zone",
        "fuel_profile": profile.name,
        "mechanism": mechanism,
        "fuel_composition": profile.fuel,
        "boundary_mass_fraction_initial": boundary_fraction,
        "boundary_piston_area_fraction": area_fraction,
        "mixing_time_ms": z.mixing_time_ms,
        "mixing_model": z.mixing_model,
        "mixing_time_min_observed_ms": min(
            row["instantaneousMixingTime_ms"] for row in rows
        ),
        "mixing_time_max_observed_ms": max(
            row["instantaneousMixingTime_ms"] for row in rows
        ),
        "interzone_heat_transfer_coeff_W_m2K": z.interzone_heat_transfer_coeff_W_m2K,
        "pressure_equalization_coeff_m_s_Pa": z.pressure_equalization_coeff_m_s_Pa,
        "boundary_leak_bias": z.boundary_leak_bias,
        "peak_pressure_bar": peak_pressure["effectivePressure_bar"],
        "peak_pressure_deg_atdc": peak_pressure["deg"],
        "max_pressure_rise_bar_per_deg": peak_rise["pressureRise_bar_per_deg"],
        "max_pressure_rise_deg_atdc": peak_rise["deg"],
        "peak_core_temperature_K": peak_core_temperature["coreTemperature_K"],
        "peak_boundary_temperature_K": peak_boundary_temperature["boundaryTemperature_K"],
        "peak_temperature_K": max(
            peak_core_temperature["coreTemperature_K"],
            peak_boundary_temperature["boundaryTemperature_K"],
        ),
        "final_core_temperature_K": rows[-1]["coreTemperature_K"],
        "final_boundary_temperature_K": rows[-1]["boundaryTemperature_K"],
        "CA10_deg_atdc": ca10,
        "CA50_deg_atdc": ca50,
        "CA90_deg_atdc": ca90,
        "max_fuel_consumed_fraction": max(row["fuelConsumedFraction"] for row in rows),
        "final_fuel_consumed_fraction": final_consumption,
        "core_fuel_reaction_extent_fraction_initial_total": rows[-1][
            "coreFuelReactionExtent_fraction_initial_total"
        ],
        "boundary_fuel_reaction_extent_fraction_initial_total": rows[-1][
            "boundaryFuelReactionExtent_fraction_initial_total"
        ],
        "gross_indicated_work_mJ": work * 1000.0,
        "gross_imep_bar": work / geometry.displacement_m3 / 1e5,
        "gross_indicated_power_W_per_cylinder": work * cycle_frequency,
        "wall_energy_gas_to_wall_mJ": wall_energy * 1000.0,
        "cumulative_chemical_heat_release_mJ": chemical_energy * 1000.0,
        "initial_trapped_mass_mg": initial_mass * 1e6,
        "mass_retained_end_fraction": (core.mass + boundary.mass) / initial_mass,
        "blowby_mass_out_mg": mass_out * 1e6,
        "blowby_mass_in_mg": mass_in * 1e6,
        "mass_balance_residual_mg": (
            initial_mass + mass_in - mass_out - core.mass - boundary.mass
        ) * 1e6,
        "max_interzone_pressure_difference_bar": max_pressure_difference / 1e5,
        "max_volume_closure_error_mm3": max_volume_error * 1e9,
        "final_boundary_volume_fraction": rows[-1]["boundaryVolumeFraction"],
        "two_zone_note": (
            "Experimental two-reactor spatial bracket. Pressure equalization, zone mass, "
            "mixing time, interface heat transfer, and leakage allocation are model inputs, "
            "not calibrated measurements. Gross work excludes gas exchange and friction."
        ),
        "options": asdict(z),
    }
    for name in fuel_names:
        key = f"fuelConsumed_{name.upper()}_fraction"
        summary[f"max_{key}"] = max(row[key] for row in rows)
        summary[f"final_{key}"] = rows[-1][key]
        final_component_mass = (
            core.mass * core.phase[name].Y[0]
            + boundary.mass * boundary.phase[name].Y[0]
        )
        chemical_reacted = (
            component_core_reacted[name] + component_boundary_reacted[name]
        )
        component_residual = (
            initial_component_mass[name] + component_in[name]
            - component_out[name] - chemical_reacted - final_component_mass
        )
        summary[f"{name.upper()}_mass_balance_residual_mg"] = component_residual * 1e6
        summary[f"inventory_{key}"] = min(1.0, max(0.0, (
            initial_component_mass[name] + component_in[name]
            - component_out[name] - final_component_mass
        ) / max(initial_component_mass[name], 1e-30)))
    for requested in ("CO", "CO2", "CH2O", "CH4", "CH3OCH3", "O2"):
        for zone in ("core", "boundary"):
            key = f"{zone}_X_{requested}"
            summary[f"end_{key}"] = rows[-1][key]
            finite = [row[key] for row in rows if math.isfinite(row[key])]
            summary[f"max_{key}"] = max(finite) if finite else float("nan")
    summary["branch"] = _branch(summary)
    return rows, summary


__all__ = ["TwoZoneOptions", "simulate_two_zone", "validate_two_zone"]
