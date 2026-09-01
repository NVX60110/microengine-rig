#!/usr/bin/env python3
"""MicroEngine Virtual Rig Beta 2.3.

Headless, batch-oriented closed-cycle screening model for miniature engines.
Cantera modes evolve species in a moving, heat-transferring 0-D reactor and
can include calibrated, bidirectional ring-pack leakage to a fixed crankcase.
Results are screening calculations, not a calibrated engine model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import argparse
import csv
import itertools
import json
import math

R_AIR = 287.05
REACTION_EPSILON = 1e-6
REACTION_ONSET = 1e-4
IGNITION_THRESHOLD = 1e-2


@dataclass(frozen=True)
class FuelProfile:
    name: str
    mechanism: str
    phase: str | None
    fuel: str
    oxidizer: str
    fuel_species: tuple[str, ...]
    source: str
    valid_temperature_K: tuple[float, float] | None = None
    valid_pressure_bar: tuple[float, float] | None = None
    note: str = ""
    validation_status: str = "unreviewed"
    citation_doi: str = ""
    license_note: str = "Verify the source mechanism license before redistribution."


BUILTIN_FUELS = {
    "methane": FuelProfile(
        "methane", "gri30.yaml", "gri30", "CH4:1", "O2:1, N2:3.76", ("CH4",),
        "GRI-Mech 3.0 distributed with Cantera", (300.0, 3000.0), None,
        "Regression fuel; not a gasoline surrogate.", "regression",
        "10.2172/7139075", "Distributed with Cantera; see GRI-Mech terms.",
    ),
    "ndodecane": FuelProfile(
        "ndodecane", "nDodecane_Reitz.yaml", "nDodecane_IG", "c12h26:1",
        "o2:1, n2:3.76", ("c12h26",),
        "Wang/Ra/Jia/Reitz reduced n-dodecane mechanism distributed with Cantera",
        (300.0, 3000.0), None,
        "Diesel-like comparison fuel with low-temperature chemistry.",
        "comparison", "10.4271/2014-01-2577",
        "Distributed with Cantera; verify the original mechanism terms.",
    ),
    "dme_zhao_sk39": FuelProfile(
        "dme_zhao_sk39", "mechanisms/dme_zhao_sk39.yaml", "gas", "CH3OCH3:1",
        "O2:1, N2:3.76", ("CH3OCH3",),
        "Zhao/Chaos/Kazakov/Dryer 2008 DME mechanism, 39-species skeletal reduction; "
        "verified reaction-for-reaction against the sk39 CHEMKIN source in "
        "jiweiqi/CollectionOfMechanisms",
        None, None,
        "Experimental screening profile. It reproduces the supplied Zhao parent "
        "ignition-delay shape at the checked 40-bar states, but that is a reduction "
        "retention check rather than experimental validation. Contains CH3OCH3, "
        "CH4, and H2 but not CH3OH.",
        "parent-retention-checked; engine-unvalidated", "10.1002/kin.20285",
        "Source mirrored by CollectionOfMechanisms under its repository license; "
        "verify original mechanism terms before redistribution.",
    ),
    # Backward-compatible alias for Beta 2.2-2.4 configurations. The earlier
    # Luo/Lu attribution was incorrect; both names resolve to Zhao sk39.
    "dme_luo_sk39": FuelProfile(
        "dme_luo_sk39", "mechanisms/dme_zhao_sk39.yaml", "gas", "CH3OCH3:1",
        "O2:1, N2:3.76", ("CH3OCH3",),
        "Deprecated alias of dme_zhao_sk39; Zhao/Chaos/Kazakov/Dryer 2008",
        None, None,
        "Use dme_zhao_sk39 in new configurations. This alias preserves old runs.",
        "deprecated-alias; parent-retention-checked; engine-unvalidated",
        "10.1002/kin.20285",
        "Source mirrored by CollectionOfMechanisms under its repository license; "
        "verify original mechanism terms before redistribution.",
    ),
    "dme_zhao_full": FuelProfile(
        "dme_zhao_full", "mechanisms/dme_zhao_full.yaml", "gas", "CH3OCH3:1",
        "O2:1, N2:3.76", ("CH3OCH3",),
        "Zhao/Chaos/Kazakov/Dryer 2008 full DME mechanism, 55 species and 290 reactions",
        None, None,
        "Parent-lineage diagnostic, not a production truth model. The distributed "
        "CHEMKIN source activates a 1-atm DME decomposition fit and explicitly "
        "requires choosing pressure-specific rates; audit that choice before using "
        "this profile to claim accuracy at 25-90 bar.",
        "parent-lineage-diagnostic; pressure-rate-selection-open",
        "10.1002/kin.20285",
        "Source mirrored by CollectionOfMechanisms under its repository license; "
        "verify original mechanism terms before redistribution.",
    ),
    "dme_llnl_2004": FuelProfile(
        "dme_llnl_2004", "mechanisms/llnl_dme_2004/llnl_dme_2004.yaml",
        "gas", "ch3och3:1", "o2:1, n2:3.76", ("ch3och3",),
        "LLNL DME release dme_24 (review/release May 19, 2004); Curran, "
        "Fischer, Dryer and related validation studies",
        (550.0, 1600.0), (1.0, 40.0),
        "79 species and 660 reactions converted from the LLNL CHEMKIN "
        "kinetics, thermo, and transport files. Source validation includes "
        "low-temperature/high-pressure reactors and shock tubes; this engine "
        "and its DME/CH4 blend map remain unvalidated.",
        "source-validated; engine-unvalidated", "10.1002/(SICI)1097-4601(2000)32:12<741::AID-KIN2>3.0.CO;2-9",
        "Public LLNL mechanism release; verify redistribution terms.",
    ),
}


@dataclass
class RigConfig:
    bore_mm: float = 8.5
    stroke_mm: float = 7.0
    rod_stroke_ratio: float = 1.6
    compression_ratio: float = 7.0
    rpm: float = 1200.0
    intake_pressure_bar: float = 1.5
    intake_temperature_K: float = 500.0
    equivalence_ratio: float = 1.10
    ignition_mode: str = "cantera-auto"  # cantera-auto | proxy-auto | spark | off
    fuel_profile: str = "methane"
    fuel_profile_file: str = ""
    mechanism_override: str = ""
    phase_override: str = ""
    fuel_override: str = ""
    oxidizer_override: str = ""
    fuel_blend_partner: str = ""
    fuel_primary_mole_fraction: float = 1.0
    diagnostic_species: str = "CO,CO2,H2,H2O,O2,CH2O,CH4,CH3OCH3"
    gamma: float = 1.34
    wall_mode: str = "finite"  # adiabatic | fixed | finite
    wall_temperature_K: float = 800.0
    effective_h_W_m2K: float = 600.0
    wall_mass_g: float = 2.0
    wall_cp_J_kgK: float = 850.0
    wall_ambient_temperature_K: float = 300.0
    wall_ambient_conductance_W_K: float = 0.0
    wall_heater_power_W: float = 0.0
    blowby_mode: str = "off"  # off | orifice | annular
    crankcase_pressure_bar: float = 1.0
    crankcase_temperature_K: float = 350.0
    ring_end_gap_mm: float = 0.05
    ring_axial_height_mm: float = 0.40
    ring_count: int = 2
    blowby_discharge_coefficient: float = 0.70
    blowby_effective_area_mm2: float = 0.0
    blowby_allow_reverse: bool = True
    annular_radial_clearance_um: float = 5.0
    annular_skirt_length_mm: float = 8.0
    annular_eccentricity_ratio: float = 0.0
    annular_dynamic_viscosity_Pa_s: float = 0.0  # 0 = Cantera transport value
    thermal_cycles: int = 1
    thermal_min_cycles: int = 5
    thermal_convergence_tolerance_K: float = 0.05
    cycle_revolutions: float = 2.0
    spark_deg_atdc: float = -10.0
    target_burn_fraction: float = 0.35
    burn_duration_deg: float = 35.0
    lhv_MJ_kg: float = 44.0
    stoich_afr: float = 14.7
    tau_ref_ms: float = 1.0
    T_ref_K: float = 950.0
    P_ref_bar: float = 20.0
    activation_temperature_K: float = 12000.0
    pressure_exponent: float = 1.0
    step_deg: float = 0.125


@dataclass
class Geometry:
    piston_area_m2: float
    displacement_m3: float
    clearance_volume_m3: float
    clearance_height_m: float
    crank_radius_m: float
    rod_length_m: float
    omega_rad_s: float
    volume: Any
    surface_area: Any
    piston_position: Any
    piston_velocity: Any


def _composition_names(text: str) -> tuple[str, ...]:
    return tuple(item.split(":", 1)[0].strip() for item in text.split(","))


def _profile_from_dict(data: dict[str, Any], source_file: str) -> FuelProfile:
    missing = sorted({"name", "mechanism", "fuel", "oxidizer"} - set(data))
    if missing:
        raise ValueError(f"Fuel profile {source_file} is missing: {', '.join(missing)}")
    species = tuple(data.get("fuel_species") or _composition_names(data["fuel"]))
    tr, pr = data.get("valid_temperature_K"), data.get("valid_pressure_bar")
    return FuelProfile(
        data["name"], data["mechanism"], data.get("phase"), data["fuel"],
        data["oxidizer"], species, data.get("source", f"External profile: {source_file}"),
        tuple(tr) if tr else None, tuple(pr) if pr else None, data.get("note", ""),
        data.get("validation_status", "unreviewed"), data.get("citation_doi", ""),
        data.get("license_note", "Verify the source mechanism license before redistribution."),
    )


def resolve_fuel_profile(c: RigConfig) -> FuelProfile:
    if c.fuel_profile_file:
        with open(c.fuel_profile_file, encoding="utf-8") as f:
            profile = _profile_from_dict(json.load(f), c.fuel_profile_file)
    else:
        if c.fuel_profile not in BUILTIN_FUELS:
            raise KeyError(f"Unknown fuel profile {c.fuel_profile!r}. Use --list-fuels or --fuel-profile-file.")
        profile = BUILTIN_FUELS[c.fuel_profile]
    fuel = c.fuel_override or profile.fuel
    species = tuple(profile.fuel_species if not c.fuel_override else _composition_names(fuel))
    if c.fuel_blend_partner:
        if c.fuel_override:
            raise ValueError("Use fuel_override or fuel_blend_partner, not both.")
        primary = profile.fuel_species[0]
        x = c.fuel_primary_mole_fraction
        fuel = f"{primary}:{x:.12g}, {c.fuel_blend_partner}:{1.0-x:.12g}"
        species = (primary, c.fuel_blend_partner)
    return FuelProfile(
        profile.name, c.mechanism_override or profile.mechanism,
        c.phase_override or profile.phase, fuel,
        c.oxidizer_override or profile.oxidizer,
        species,
        profile.source, profile.valid_temperature_K, profile.valid_pressure_bar, profile.note,
        profile.validation_status, profile.citation_doi, profile.license_note,
    )


def validate_config(c: RigConfig) -> None:
    if c.bore_mm <= 0 or c.stroke_mm <= 0:
        raise ValueError("Bore and stroke must be positive.")
    if c.rod_stroke_ratio <= 0.5:
        raise ValueError("rod_stroke_ratio must be > 0.5.")
    if c.compression_ratio <= 1:
        raise ValueError("compression_ratio must be > 1.")
    if c.rpm <= 0 or c.step_deg <= 0:
        raise ValueError("rpm and step_deg must be positive.")
    if c.wall_mode not in {"adiabatic", "fixed", "finite"}:
        raise ValueError("wall_mode must be adiabatic, fixed, or finite.")
    if c.wall_mode == "finite" and c.wall_mass_g * c.wall_cp_J_kgK <= 0:
        raise ValueError("Finite wall mode requires positive wall mass and heat capacity.")
    if c.blowby_mode not in {"off", "orifice", "annular"}:
        raise ValueError("blowby_mode must be off, orifice, or annular.")
    if c.crankcase_pressure_bar <= 0 or c.crankcase_temperature_K <= 0:
        raise ValueError("Crankcase pressure and temperature must be positive.")
    if c.ring_count < 0 or c.ring_end_gap_mm < 0 or c.ring_axial_height_mm < 0:
        raise ValueError("Ring count, gap, and axial height cannot be negative.")
    if not 0 <= c.blowby_discharge_coefficient <= 1.5:
        raise ValueError("blowby_discharge_coefficient must be between 0 and 1.5.")
    if not 0.0 <= c.fuel_primary_mole_fraction <= 1.0:
        raise ValueError("fuel_primary_mole_fraction must be between 0 and 1.")
    if c.blowby_mode == "annular":
        if c.annular_radial_clearance_um <= 0 or c.annular_skirt_length_mm <= 0:
            raise ValueError("Annular leakage requires positive clearance and skirt length.")
        if not 0.0 <= c.annular_eccentricity_ratio <= 1.0:
            raise ValueError("annular_eccentricity_ratio must be between 0 and 1.")
        if c.annular_dynamic_viscosity_Pa_s < 0:
            raise ValueError("annular_dynamic_viscosity_Pa_s cannot be negative.")
    if c.thermal_cycles < 1 or c.thermal_min_cycles < 1:
        raise ValueError("thermal cycle counts must be positive integers.")
    if c.thermal_convergence_tolerance_K <= 0 or c.cycle_revolutions < 1:
        raise ValueError("Thermal tolerance must be positive and cycle_revolutions >= 1.")


def build_geometry(c: RigConfig) -> Geometry:
    validate_config(c)
    bore, stroke = c.bore_mm / 1000.0, c.stroke_mm / 1000.0
    radius, rod = stroke / 2.0, c.rod_stroke_ratio * stroke
    piston_area = math.pi * bore**2 / 4.0
    displacement = piston_area * stroke
    clearance = displacement / (c.compression_ratio - 1.0)
    clearance_height = clearance / piston_area
    omega = 2.0 * math.pi * c.rpm / 60.0

    def position(theta: float) -> float:
        root = math.sqrt(max(1e-30, rod**2 - radius**2 * math.sin(theta)**2))
        return radius * (1.0 - math.cos(theta)) + rod - root

    def velocity(theta: float) -> float:
        root = math.sqrt(max(1e-30, rod**2 - radius**2 * math.sin(theta)**2))
        derivative = radius * math.sin(theta) + radius**2 * math.sin(theta) * math.cos(theta) / root
        return derivative * omega

    def volume(theta: float) -> float:
        return clearance + piston_area * position(theta)

    def surface(theta: float) -> float:
        return 2.0 * piston_area + math.pi * bore * (clearance_height + position(theta))

    return Geometry(piston_area, displacement, clearance, clearance_height, radius,
                    rod, omega, volume, surface, position, velocity)


def geometry_summary(c: RigConfig, g: Geometry) -> dict[str, float]:
    samples = [math.radians(-180.0 + i * 0.1) for i in range(3601)]
    return {
        "displacement_cc": g.displacement_m3 * 1e6,
        "clearance_volume_mm3": g.clearance_volume_m3 * 1e9,
        "clearance_height_mm": g.clearance_height_m * 1000.0,
        "rod_length_mm": g.rod_length_m * 1000.0,
        "mean_piston_speed_m_s": 2.0 * (c.stroke_mm / 1000.0) * c.rpm / 60.0,
        "max_piston_speed_m_s": max(abs(g.piston_velocity(th)) for th in samples),
        "tdc_area_volume_ratio_1_m": g.surface_area(0.0) / g.volume(0.0),
        "tdc_dwell_plus_minus_10deg_ms": math.radians(20.0) / g.omega_rad_s * 1000.0,
        "compression_time_ms": math.pi / g.omega_rad_s * 1000.0,
    }


def blowby_area_m2(c: RigConfig) -> float:
    """Return the calibrated effective ring-pack flow area.

    If ``blowby_effective_area_mm2`` is positive, it is authoritative. Otherwise
    the geometric end-gap slot is divided by sqrt(ring_count), a transparent
    screening approximation that must be calibrated against crankcase flow.
    """
    if c.blowby_mode != "orifice" or c.ring_count == 0:
        return 0.0
    if c.blowby_effective_area_mm2 > 0:
        return c.blowby_effective_area_mm2 * 1e-6
    one_ring = c.ring_end_gap_mm * c.ring_axial_height_mm * 1e-6
    return one_ring / math.sqrt(c.ring_count)


def compressible_orifice_mdot(P_up: float, T_up: float, P_down: float,
                              area_m2: float, cd: float, gamma: float,
                              gas_constant: float) -> tuple[float, bool]:
    """One-way ideal-gas orifice flow; returns (kg/s, choked)."""
    if area_m2 <= 0 or cd <= 0 or P_up <= P_down or T_up <= 0:
        return 0.0, False
    pressure_ratio = max(0.0, min(1.0, P_down / P_up))
    critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    prefactor = cd * area_m2 * P_up / math.sqrt(gas_constant * T_up)
    if pressure_ratio <= critical:
        factor = math.sqrt(gamma) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        return prefactor * factor, True
    term = 2.0 * gamma / (gamma - 1.0)
    term *= pressure_ratio ** (2.0 / gamma) - pressure_ratio ** ((gamma + 1.0) / gamma)
    return prefactor * math.sqrt(max(0.0, term)), False


def annular_eccentricity_factor(eccentricity_ratio: float) -> float:
    """Thin-annulus leakage multiplier; 1.0 concentric and 2.5 at wall contact."""
    return 1.0 + 1.5 * eccentricity_ratio**2


def compressible_annular_mdot(P_up: float, T_up: float, P_down: float,
                              bore_m: float, radial_clearance_m: float,
                              skirt_length_m: float, viscosity_Pa_s: float,
                              gas_constant: float,
                              eccentricity_ratio: float = 0.0) -> float:
    """Isothermal laminar thin-annulus mass flow.

    This is the compressible Poiseuille solution for a long, narrow annulus.
    It is a screening law for a ringless lapped piston, not a piston-rock or
    lubrication model.
    """
    if (P_up <= P_down or T_up <= 0 or bore_m <= 0 or radial_clearance_m <= 0
            or skirt_length_m <= 0 or viscosity_Pa_s <= 0 or gas_constant <= 0):
        return 0.0
    width = math.pi * bore_m
    pressure_term = P_up**2 - P_down**2
    mdot = width * radial_clearance_m**3 * pressure_term
    mdot /= 24.0 * viscosity_Pa_s * skirt_length_m * gas_constant * T_up
    return mdot * annular_eccentricity_factor(eccentricity_ratio)


def _resolved_mechanism_path(mechanism: str) -> str:
    candidate = Path(mechanism)
    if candidate.exists() or candidate.parent == Path("."):
        return str(candidate)
    local = Path(__file__).resolve().parent / candidate
    return str(local)


def profile_warnings(c: RigConfig, profile: FuelProfile) -> list[str]:
    warnings = []
    if "unvalidated" in profile.validation_status or profile.validation_status == "unreviewed":
        warnings.append(
            f"Fuel profile validation status is {profile.validation_status}; "
            "treat ignition and phasing as screening predictions."
        )
    if "pressure-rate-selection-open" in profile.validation_status:
        warnings.append(
            "The Zhao parent mechanism has not had its pressure-specific DME "
            "decomposition rate selected for this operating pressure. Use it "
            "only as a lineage diagnostic."
        )
    if "deprecated-alias" in profile.validation_status:
        warnings.append(
            "dme_luo_sk39 is a deprecated metadata alias; use dme_zhao_sk39."
        )
    if c.step_deg > 0.125:
        warnings.append(
            "Cantera crank-angle step exceeds 0.125 deg. Ignition-cliff cases "
            "must be confirmed at 0.125 deg or finer."
        )
    if profile.valid_temperature_K:
        lo, hi = profile.valid_temperature_K
        if not lo <= c.intake_temperature_K <= hi:
            warnings.append(f"Intake temperature is outside profile range {lo:g}-{hi:g} K.")
    if profile.valid_pressure_bar:
        lo, hi = profile.valid_pressure_bar
        if not lo <= c.intake_pressure_bar <= hi:
            warnings.append(f"Intake pressure is outside profile range {lo:g}-{hi:g} bar.")
    return warnings


def reaction_regime(value: float) -> str:
    if value < REACTION_EPSILON:
        return "no reaction"
    if value < 0.01:
        return "<1% reaction"
    if value < 0.10:
        return "1-10% partial reaction"
    if value < 0.50:
        return "10-50% partial reaction"
    return ">=50% runaway/full combustion"


def _cantera_reactor(c: RigConfig, g: Geometry, profile: FuelProfile):
    try:
        import cantera as ct
    except ImportError as exc:
        raise RuntimeError("Cantera mode requires `pip install cantera==3.2.0`.") from exc
    mechanism_name = _resolved_mechanism_path(profile.mechanism)
    mechanism = Path(mechanism_name)
    if mechanism.parent != Path(".") and not mechanism.exists():
        raise FileNotFoundError(f"Mechanism not found: {profile.mechanism}")
    gas = ct.Solution(mechanism_name, profile.phase) if profile.phase else ct.Solution(mechanism_name)
    gas.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    gas.set_equivalence_ratio(c.equivalence_ratio, profile.fuel, profile.oxidizer)
    initial_composition = gas.X
    missing = [name for name in profile.fuel_species if name not in gas.species_names]
    if missing:
        raise ValueError(f"Fuel species missing from mechanism: {', '.join(missing)}")
    cylinder = ct.IdealGasReactor(gas, energy="on", clone=False)
    cylinder.volume = g.volume(-math.pi)
    sink_phase = ct.Solution("air.yaml")
    # This reservoir is the gas-side thermal boundary, not the external
    # ambient. Its temperature is updated to the lumped wall temperature at
    # every crank-angle step for finite-wall runs.
    sink_phase.TP = c.wall_temperature_K, c.intake_pressure_bar * 1e5
    sink = ct.Reservoir(sink_phase, clone=False)
    piston = ct.Wall(cylinder, sink, A=g.surface_area(-math.pi))
    piston.heat_transfer_coeff = 0.0
    network = ct.ReactorNet([cylinder])
    requested_dt = math.radians(c.step_deg) / g.omega_rad_s
    network.max_time_step = requested_dt / 4.0
    network.max_err_test_fails = 20
    initial_fuel_mass = cylinder.mass * sum(cylinder.phase[name].Y[0] for name in profile.fuel_species)
    leak_area = blowby_area_m2(c)
    leak_active = (
        leak_area > 0 if c.blowby_mode == "orifice"
        else c.blowby_mode == "annular" and c.annular_radial_clearance_um > 0
    )
    blowby: dict[str, Any] = {
        "area_m2": leak_area,
        "model": c.blowby_mode,
        "crankcase": None,
        "outlet": None,
        "inlet": None,
        "thermal_sink": sink,
    }
    if leak_active:
        crank_gas = (ct.Solution(mechanism_name, profile.phase)
                     if profile.phase else ct.Solution(mechanism_name))
        crank_gas.TPX = (c.crankcase_temperature_K,
                         c.crankcase_pressure_bar * 1e5,
                         initial_composition)
        crankcase = ct.Reservoir(crank_gas, clone=False)

        def one_way_rate(upstream, downstream) -> tuple[float, bool]:
            phase = upstream.phase
            gamma = phase.cp_mass / phase.cv_mass
            gas_constant = ct.gas_constant / phase.mean_molecular_weight
            if c.blowby_mode == "orifice":
                return compressible_orifice_mdot(
                    phase.P, phase.T, downstream.phase.P, leak_area,
                    c.blowby_discharge_coefficient, gamma, gas_constant,
                )
            viscosity = c.annular_dynamic_viscosity_Pa_s
            if viscosity == 0.0:
                viscosity = phase.viscosity
            mdot = compressible_annular_mdot(
                phase.P, phase.T, downstream.phase.P,
                c.bore_mm / 1000.0,
                c.annular_radial_clearance_um * 1e-6,
                c.annular_skirt_length_mm / 1000.0,
                viscosity, gas_constant, c.annular_eccentricity_ratio,
            )
            return mdot, False

        def out_rate(_time: float = 0.0) -> float:
            return one_way_rate(cylinder, crankcase)[0]

        outlet = ct.MassFlowController(cylinder, crankcase, mdot=out_rate)
        inlet = None
        if c.blowby_allow_reverse:
            def in_rate(_time: float = 0.0) -> float:
                return one_way_rate(crankcase, cylinder)[0]

            inlet = ct.MassFlowController(crankcase, cylinder, mdot=in_rate)
        blowby.update({
            "crankcase": crankcase,
            "outlet": outlet,
            "inlet": inlet,
            "out_rate": lambda: one_way_rate(cylinder, crankcase),
            "in_rate": (lambda: one_way_rate(crankcase, cylinder))
                       if c.blowby_allow_reverse else (lambda: (0.0, False)),
        })
    else:
        blowby.update({
            "out_rate": lambda: (0.0, False),
            "in_rate": lambda: (0.0, False),
        })
    return cylinder, piston, network, initial_fuel_mass, cylinder.mass, blowby


def wall_heat_flux(c: RigConfig, gas_temperature: float, wall_temperature: float) -> float:
    return 0.0 if c.wall_mode == "adiabatic" else c.effective_h_W_m2K * (gas_temperature - wall_temperature)


def advance_wall(c: RigConfig, wall_temperature: float, q_gas_to_wall_J: float, dt: float) -> float:
    if c.wall_mode != "finite":
        return wall_temperature
    ambient_loss = c.wall_ambient_conductance_W_K * (wall_temperature - c.wall_ambient_temperature_K) * dt
    change = q_gas_to_wall_J + c.wall_heater_power_W * dt - ambient_loss
    capacity = (c.wall_mass_g / 1000.0) * c.wall_cp_J_kgK
    return max(100.0, wall_temperature + change / capacity)


def _crossing_angle(rows: list[dict[str, Any]], target: float,
                    field: str = "fuelConsumedFraction") -> float | None:
    """Linearly interpolate the first crossing of a monotone data envelope."""
    previous_deg = rows[0]["deg"]
    previous_value = rows[0][field]
    envelope = previous_value
    if envelope >= target:
        return previous_deg
    for row in rows[1:]:
        value = max(envelope, row[field])
        if value >= target:
            span = value - envelope
            fraction = 0.0 if span <= 0 else (target - envelope) / span
            return previous_deg + fraction * (row["deg"] - previous_deg)
        envelope = value
        previous_deg = row["deg"]
    return None


def _fractional_crossing_angle(rows: list[dict[str, Any]], fraction: float,
                               field: str) -> float | None:
    """Return a crank angle at a fraction of the field's maximum excursion."""
    baseline = rows[0][field]
    maximum = max(row[field] - baseline for row in rows)
    if maximum <= 0:
        return None
    shifted = [{"deg": row["deg"], "progress": row[field] - baseline} for row in rows]
    return _crossing_angle(shifted, fraction * maximum, "progress")


def _simulate_one_cycle(c: RigConfig):
    g = build_geometry(c)
    geom = geometry_summary(c, g)
    use_cantera = c.ignition_mode == "cantera-auto"
    profile = resolve_fuel_profile(c) if use_cantera else None
    warnings = profile_warnings(c, profile) if profile else []
    if use_cantera:
        cylinder, piston, network, initial_fuel_mass, initial_mass, blowby = _cantera_reactor(c, g, profile)
        available_species = {name.lower(): name for name in cylinder.phase.species_names}
        diagnostic_species = {
            requested.strip().upper(): available_species.get(requested.strip().lower())
            for requested in c.diagnostic_species.split(",") if requested.strip()
        }
        fuel_component_initial_mass = {
            name: cylinder.mass * cylinder.phase[name].Y[0]
            for name in profile.fuel_species
        }
        fuel_component_out = {name: 0.0 for name in profile.fuel_species}
        fuel_component_in = {name: 0.0 for name in profile.fuel_species}
    else:
        diagnostic_species = {}
        fuel_component_initial_mass = {}
        fuel_component_out = {}
        fuel_component_in = {}
        if c.blowby_mode != "off":
            raise RuntimeError(
                "Reactive blowby coupling requires ignition_mode=cantera-auto. "
                "Use blowby_screen.py for a standalone nonreacting estimate."
            )
        pint = c.intake_pressure_bar * 1e5
        air_mass = pint * g.volume(-math.pi) / (R_AIR * c.intake_temperature_K)
        fuel_mass = air_mass * c.equivalence_ratio / c.stoich_afr
        initial_fuel_mass = fuel_mass
        mass, temperature = air_mass + fuel_mass, c.intake_temperature_K
        initial_mass = mass
        cv = R_AIR / (c.gamma - 1.0)

    step_rad = math.radians(c.step_deg)
    dt = step_rad / g.omega_rad_s
    wall_temperature = c.wall_temperature_K
    wall_energy = work = ignition_integral = chemical_heat_cumulative = 0.0
    chemical_heat_rate = 0.0
    mass_out_cumulative = mass_in_cumulative = 0.0
    fuel_out_cumulative = fuel_in_cumulative = 0.0
    outflow_time = choked_outflow_time = 0.0
    reaction_start = ignition_angle = burn_start = None
    max_burn = last_proxy_burn = 0.0
    rows = []
    deg = -180.0
    while deg <= 180.0 + 1e-9:
        theta = math.radians(deg)
        volume, surface = g.volume(theta), g.surface_area(theta)
        if use_cantera:
            temperature, pressure, mass = cylinder.T, cylinder.phase.P, cylinder.mass
            gamma_now = cylinder.phase.cp_mass / cylinder.phase.cv_mass
            gas_constant_now = 8314.462618 / cylinder.phase.mean_molecular_weight
            fuel_now = mass * sum(cylinder.phase[name].Y[0] for name in profile.fuel_species)
            reacted_fuel = initial_fuel_mass + fuel_in_cumulative - fuel_out_cumulative - fuel_now
            burn = min(1.0, max(0.0, reacted_fuel / max(initial_fuel_mass, 1e-30)))
            out_rate, out_choked = blowby["out_rate"]()
            in_rate, _ = blowby["in_rate"]()
            chemical_heat_rate = cylinder.phase.heat_release_rate * volume
            tau = float("nan")
            component_consumption = {}
            for name in profile.fuel_species:
                component_now = mass * cylinder.phase[name].Y[0]
                component_reacted = (
                    fuel_component_initial_mass[name] + fuel_component_in[name]
                    - fuel_component_out[name] - component_now
                )
                label = name.upper()
                component_consumption[f"fuelConsumed_{label}_fraction"] = min(
                    1.0, max(0.0, component_reacted / max(fuel_component_initial_mass[name], 1e-30))
                )
        else:
            pressure = mass * R_AIR * temperature / volume
            gamma_now, gas_constant_now = c.gamma, R_AIR
            tau = (c.tau_ref_ms / 1000.0) * (pressure / (c.P_ref_bar * 1e5))**(-c.pressure_exponent)
            tau *= math.exp(c.activation_temperature_K * (1.0 / temperature - 1.0 / c.T_ref_K))
            tau *= 1.0 + 2.2 * (c.equivalence_ratio - 1.08)**2
            tau = max(1e-8, min(1000.0, tau))
            if c.ignition_mode == "proxy-auto" and burn_start is None:
                ignition_integral += dt / tau
                if ignition_integral >= 1.0:
                    burn_start = deg
            if c.ignition_mode == "spark" and burn_start is None and deg >= c.spark_deg_atdc:
                burn_start = c.spark_deg_atdc
            burn = 0.0
            if burn_start is not None and c.ignition_mode != "off":
                z = (deg - burn_start) / max(1.0, c.burn_duration_deg)
                burn = c.target_burn_fraction if z >= 1 else (c.target_burn_fraction * (3*z*z - 2*z*z*z) if z > 0 else 0.0)
            out_rate = in_rate = 0.0
            out_choked = False
            component_consumption = {}

        max_burn = max(max_burn, burn)
        if reaction_start is None and burn >= REACTION_ONSET:
            reaction_start = deg
        if ignition_angle is None and burn >= IGNITION_THRESHOLD:
            ignition_angle = deg
        qflux = wall_heat_flux(c, temperature, wall_temperature)
        species_values = {}
        if use_cantera:
            for label, actual in diagnostic_species.items():
                species_values[f"X_{label}"] = (
                    float(cylinder.phase[actual].X[0]) if actual else float("nan")
                )
        rows.append({
            "deg": deg, "P_bar": pressure / 1e5, "T_K": temperature,
            "V_mm3": volume * 1e9, "surfaceArea_mm2": surface * 1e6,
            "areaVolume_1_m": surface / volume,
            "pistonPosition_mm": g.piston_position(theta) * 1000.0,
            "pistonVelocity_m_s": g.piston_velocity(theta),
            "wallTemperature_K": wall_temperature, "wallHeat_mJ": wall_energy * 1000.0,
            "wallHeatRate_W": qflux * surface, "work_mJ": work * 1000.0,
            "ignitionIntegral": ignition_integral, "fuelConsumedFraction": burn,
            "tau_ms": tau * 1000.0,
            "cylinderMass_mg": mass * 1e6,
            "massRetentionFraction": mass / initial_mass,
            "blowbyOutRate_mg_s": out_rate * 1e6,
            "blowbyInRate_mg_s": in_rate * 1e6,
            "blowbyOutCumulative_mg": mass_out_cumulative * 1e6,
            "blowbyInCumulative_mg": mass_in_cumulative * 1e6,
            "chemicalHeatReleaseRate_W": chemical_heat_rate,
            "cumulativeChemicalHeatRelease_mJ": chemical_heat_cumulative * 1000.0,
            "gamma": gamma_now,
            "specificGasConstant_J_kgK": gas_constant_now,
            **species_values,
            **component_consumption,
        })
        if deg >= 180.0:
            break
        theta2 = math.radians(deg + c.step_deg)
        volume2, surface2 = g.volume(theta2), g.surface_area(theta2)
        area_mid = 0.5 * (surface + surface2)
        wall_temperature_step = wall_temperature
        if use_cantera:
            fuel_y_out_0 = sum(cylinder.phase[name].Y[0] for name in profile.fuel_species)
            crank_phase = blowby["crankcase"].phase if blowby["crankcase"] is not None else None
            fuel_y_in_0 = (sum(crank_phase[name].Y[0] for name in profile.fuel_species)
                           if crank_phase is not None else 0.0)
            component_y_out_0 = {
                name: cylinder.phase[name].Y[0] for name in profile.fuel_species
            }
            component_y_in_0 = {
                name: (crank_phase[name].Y[0] if crank_phase is not None else 0.0)
                for name in profile.fuel_species
            }
            piston.area = area_mid
            piston.velocity = (volume2 - volume) / dt / area_mid
            piston.heat_flux = 0.0
            piston.heat_transfer_coeff = (
                0.0 if c.wall_mode == "adiabatic" else c.effective_h_W_m2K
            )
            sink_phase = blowby["thermal_sink"].phase
            sink_phase.TP = wall_temperature_step, sink_phase.P
            network.advance(network.time + dt)
            pressure2 = cylinder.phase.P
            temperature2 = cylinder.T
            qflux2 = wall_heat_flux(c, temperature2, wall_temperature_step)
            q_gas_to_wall = 0.5 * (qflux + qflux2) * area_mid * dt
            chemical_heat_rate_2 = cylinder.phase.heat_release_rate * volume2
            out_rate_2, out_choked_2 = blowby["out_rate"]()
            in_rate_2, _ = blowby["in_rate"]()
            fuel_y_out_2 = sum(cylinder.phase[name].Y[0] for name in profile.fuel_species)
            fuel_y_in_2 = fuel_y_in_0
            mass_out_cumulative += 0.5 * (out_rate + out_rate_2) * dt
            mass_in_cumulative += 0.5 * (in_rate + in_rate_2) * dt
            fuel_out_cumulative += 0.5 * (out_rate * fuel_y_out_0 + out_rate_2 * fuel_y_out_2) * dt
            fuel_in_cumulative += 0.5 * (in_rate * fuel_y_in_0 + in_rate_2 * fuel_y_in_2) * dt
            for name in profile.fuel_species:
                component_y_out_2 = cylinder.phase[name].Y[0]
                component_y_in_2 = component_y_in_0[name]
                fuel_component_out[name] += 0.5 * (
                    out_rate * component_y_out_0[name]
                    + out_rate_2 * component_y_out_2
                ) * dt
                fuel_component_in[name] += 0.5 * (
                    in_rate * component_y_in_0[name]
                    + in_rate_2 * component_y_in_2
                ) * dt
            if out_rate > 0 or out_rate_2 > 0:
                outflow_time += dt
                if out_choked or out_choked_2:
                    choked_outflow_time += dt
            chemical_heat_cumulative += 0.5 * (chemical_heat_rate + chemical_heat_rate_2) * dt
            chemical_heat_rate = chemical_heat_rate_2
        else:
            q_gas_to_wall = qflux * area_mid * dt
            t_ad = temperature * (volume / volume2)**(c.gamma - 1.0)
            dburn = max(0.0, burn - last_proxy_burn)
            qchem = fuel_mass * c.lhv_MJ_kg * 1e6 * dburn
            temperature = max(100.0, t_ad + (-q_gas_to_wall + qchem) / (mass * cv))
            pressure2 = mass * R_AIR * temperature / volume2
            chemical_heat_cumulative += qchem
            chemical_heat_rate = qchem / dt
            last_proxy_burn = burn
        wall_temperature = advance_wall(
            c, wall_temperature_step, q_gas_to_wall, dt
        )
        wall_energy += q_gas_to_wall
        work += 0.5 * (pressure + pressure2) * (volume2 - volume)
        deg += c.step_deg

    for index, row in enumerate(rows):
        if index == 0:
            left, right = rows[0], rows[1]
        elif index == len(rows) - 1:
            left, right = rows[-2], rows[-1]
        else:
            left, right = rows[index - 1], rows[index + 1]
        row["pressureRise_bar_per_deg"] = (
            (right["P_bar"] - left["P_bar"]) / (right["deg"] - left["deg"])
        )

    peak_p = max(rows, key=lambda row: row["P_bar"])
    peak_t = max(rows, key=lambda row: row["T_K"])
    peak_pressure_rise = max(rows, key=lambda row: row["pressureRise_bar_per_deg"])
    tdc = min(rows, key=lambda row: abs(row["deg"]))
    ca10, ca50, ca90 = (
        _fractional_crossing_angle(rows, value, "cumulativeChemicalHeatRelease_mJ")
        for value in (0.10, 0.50, 0.90)
    )
    fc10, fc50, fc90 = (
        _crossing_angle(rows, value * max_burn)
        for value in (0.10, 0.50, 0.90)
    )
    peak_heat_release = max(rows, key=lambda row: row["chemicalHeatReleaseRate_W"])
    species_summary = {}
    for label in diagnostic_species:
        field = f"X_{label}"
        finite_values = [row[field] for row in rows if math.isfinite(row[field])]
        species_summary.update({
            f"end_{field}": rows[-1][field],
            f"TDC_{field}": tdc[field],
            f"peak_temperature_{field}": peak_t[field],
            f"peak_heat_release_{field}": peak_heat_release[field],
            f"max_{field}": max(finite_values) if finite_values else float("nan"),
        })
    component_summary = {}
    for name, initial_component_mass in fuel_component_initial_mass.items():
        label = name.upper()
        field = f"fuelConsumed_{label}_fraction"
        component_summary.update({
            f"initial_{label}_mass_mg": initial_component_mass * 1e6,
            f"max_{field}": max(row[field] for row in rows),
            f"final_{field}": rows[-1][field],
        })
    annular_equivalent_cdA = 0.0
    if c.blowby_mode == "annular" and tdc["blowbyOutRate_mg_s"] > 0:
        unit_flow, _ = compressible_orifice_mdot(
            tdc["P_bar"] * 1e5, tdc["T_K"], c.crankcase_pressure_bar * 1e5,
            1.0, 1.0, tdc["gamma"], tdc["specificGasConstant_J_kgK"],
        )
        if unit_flow > 0:
            annular_equivalent_cdA = tdc["blowbyOutRate_mg_s"] * 1e-6 / unit_flow * 1e6
    cycle_frequency = c.rpm / 60.0 / c.cycle_revolutions
    final_mole_fractions = {}
    if use_cantera:
        final_mole_fractions = {
            name: float(value)
            for name, value in zip(cylinder.phase.species_names, cylinder.phase.X)
            if value > 1e-12
        }
    summary = {
        **geom,
        "fuel_profile": profile.name if profile else "proxy/prescribed",
        "mechanism": profile.mechanism if profile else None,
        "mechanism_source": profile.source if profile else None,
        "mechanism_validation_status": profile.validation_status if profile else None,
        "mechanism_citation_doi": profile.citation_doi if profile else None,
        "mechanism_license_note": profile.license_note if profile else None,
        "fuel_composition": profile.fuel if profile else None,
        "diagnostic_species_resolved": diagnostic_species,
        "final_mole_fractions": final_mole_fractions,
        "trapped_mass_mg": initial_mass * 1e6,
        "initial_trapped_mass_mg": initial_mass * 1e6,
        "initial_tracked_fuel_mass_mg": initial_fuel_mass * 1e6,
        "trapped_mass_TDC_mg": tdc["cylinderMass_mg"],
        "trapped_mass_end_mg": rows[-1]["cylinderMass_mg"],
        "mass_retained_TDC_fraction": tdc["massRetentionFraction"],
        "mass_retained_end_fraction": rows[-1]["massRetentionFraction"],
        "blowby_effective_area_mm2": blowby_area_m2(c) * 1e6,
        "blowby_model": c.blowby_mode,
        "annular_radial_clearance_um": c.annular_radial_clearance_um if c.blowby_mode == "annular" else None,
        "annular_skirt_length_mm": c.annular_skirt_length_mm if c.blowby_mode == "annular" else None,
        "annular_eccentricity_factor": (
            annular_eccentricity_factor(c.annular_eccentricity_ratio)
            if c.blowby_mode == "annular" else None
        ),
        "annular_equivalent_cdA_TDC_mm2": annular_equivalent_cdA,
        "blowby_mass_out_mg": mass_out_cumulative * 1e6,
        "blowby_mass_in_mg": mass_in_cumulative * 1e6,
        "blowby_net_mass_out_mg": (mass_out_cumulative - mass_in_cumulative) * 1e6,
        "blowby_outflow_choked_time_fraction": (
            choked_outflow_time / outflow_time if outflow_time else 0.0
        ),
        "mass_balance_residual_mg": (
            initial_mass - rows[-1]["cylinderMass_mg"] * 1e-6
            - mass_out_cumulative + mass_in_cumulative
        ) * 1e6,
        "peak_pressure_bar": peak_p["P_bar"], "peak_pressure_deg_atdc": peak_p["deg"],
        "max_pressure_rise_bar_per_deg": peak_pressure_rise["pressureRise_bar_per_deg"],
        "max_pressure_rise_deg_atdc": peak_pressure_rise["deg"],
        "max_chemical_heat_release_rate_W": peak_heat_release["chemicalHeatReleaseRate_W"],
        "max_chemical_heat_release_rate_deg_atdc": peak_heat_release["deg"],
        "cumulative_chemical_heat_release_mJ": rows[-1]["cumulativeChemicalHeatRelease_mJ"],
        "peak_temperature_K": peak_t["T_K"], "peak_temperature_deg_atdc": peak_t["deg"],
        "T_at_TDC_K": tdc["T_K"], "P_at_TDC_bar": tdc["P_bar"],
        "end_temperature_K": rows[-1]["T_K"], "end_pressure_bar": rows[-1]["P_bar"],
        "wall_energy_gas_to_wall_mJ": wall_energy * 1000.0,
        "wall_final_temperature_K": wall_temperature,
        "indicated_work_mJ": work * 1000.0,
        "imep_bar": work / g.displacement_m3 / 1e5,
        "gross_indicated_work_mJ": work * 1000.0,
        "gross_imep_bar": work / g.displacement_m3 / 1e5,
        "gross_indicated_power_W_per_cylinder": work * cycle_frequency,
        "cycle_frequency_Hz": cycle_frequency,
        "reaction_started": reaction_start is not None,
        "reaction_start_deg_atdc": reaction_start,
        "ignited_1pct": ignition_angle is not None,
        "ignition_1pct_deg_atdc": ignition_angle,
        "CA10_deg_atdc": ca10,
        "CA50_deg_atdc": ca50,
        "CA90_deg_atdc": ca90,
        "fuel_consumption_10pct_of_max_deg_atdc": fc10,
        "fuel_consumption_50pct_of_max_deg_atdc": fc50,
        "fuel_consumption_90pct_of_max_deg_atdc": fc90,
        "max_fuel_consumed_fraction": max_burn,
        "final_fuel_consumed_fraction": rows[-1]["fuelConsumedFraction"],
        "reaction_regime": reaction_regime(max_burn),
        **species_summary,
        **component_summary,
        "warnings": warnings,
        "model_note": (
            "CA10/50/90 are fractions of cumulative Cantera chemical heat release. "
            "Fuel consumption is a leak-corrected reaction-extent proxy, not measured MFB. "
            "Leakage parameters require calibration. IMEP/work are gross closed-cycle "
            "values and exclude gas exchange, friction, and accessories. Species diagnostics "
            "are in-cylinder mole fractions at the named state, not exhaust-system emissions."
        ),
    }
    return rows, summary


def _advance_wall_idle(c: RigConfig, wall_temperature: float, duration_s: float) -> float:
    """Advance the lumped wall through the unmodeled part of a full engine cycle."""
    if duration_s <= 0:
        return wall_temperature
    capacity = (c.wall_mass_g / 1000.0) * c.wall_cp_J_kgK
    conductance = c.wall_ambient_conductance_W_K
    if conductance > 0:
        equilibrium = c.wall_ambient_temperature_K + c.wall_heater_power_W / conductance
        return equilibrium + (wall_temperature - equilibrium) * math.exp(-conductance * duration_s / capacity)
    return wall_temperature + c.wall_heater_power_W * duration_s / capacity


def simulate_thermal_cycles(c: RigConfig):
    """Repeat fresh-charge cycles while carrying the finite wall temperature."""
    if c.wall_mode != "finite":
        raise ValueError("thermal_cycles > 1 requires wall_mode=finite.")
    geometry = build_geometry(c)
    modeled_duration = 2.0 * math.pi / geometry.omega_rad_s
    full_cycle_duration = c.cycle_revolutions * 2.0 * math.pi / geometry.omega_rad_s
    idle_duration = max(0.0, full_cycle_duration - modeled_duration)
    wall_start = c.wall_temperature_K
    history: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    final_summary: dict[str, Any] = {}
    converged = False
    for cycle in range(1, c.thermal_cycles + 1):
        cycle_config = apply_config_patch(c, {
            "wall_temperature_K": wall_start,
            "thermal_cycles": 1,
        })
        final_rows, final_summary = _simulate_one_cycle(cycle_config)
        wall_end_closed = final_summary["wall_final_temperature_K"]
        next_wall_start = _advance_wall_idle(cycle_config, wall_end_closed, idle_duration)
        delta = next_wall_start - wall_start
        history.append({
            "cycle": cycle,
            "wall_start_K": wall_start,
            "wall_end_closed_K": wall_end_closed,
            "wall_next_cycle_K": next_wall_start,
            "wall_cycle_delta_K": delta,
            "gross_imep_bar": final_summary["gross_imep_bar"],
            "gross_work_mJ": final_summary["gross_indicated_work_mJ"],
            "wall_energy_gas_to_wall_mJ": final_summary["wall_energy_gas_to_wall_mJ"],
            "max_fuel_consumed_fraction": final_summary["max_fuel_consumed_fraction"],
            "peak_pressure_bar": final_summary["peak_pressure_bar"],
            "CA50_deg_atdc": final_summary["CA50_deg_atdc"],
        })
        wall_start = next_wall_start
        if cycle >= c.thermal_min_cycles and abs(delta) <= c.thermal_convergence_tolerance_K:
            converged = True
            break
    final_summary.update({
        "thermal_cycles_completed": len(history),
        "thermal_converged": converged,
        "thermal_final_next_cycle_wall_K": wall_start,
        "thermal_cycle_delta_K": history[-1]["wall_cycle_delta_K"],
        "thermal_cycle_history": history,
        "thermal_idle_duration_ms": idle_duration * 1000.0,
    })
    if not converged:
        final_summary["warnings"] = list(final_summary.get("warnings", [])) + [
            "Finite wall did not reach the requested repeated-cycle tolerance."
        ]
    return final_rows, final_summary


def simulate(c: RigConfig):
    validate_config(c)
    if c.thermal_cycles > 1:
        return simulate_thermal_cycles(c)
    rows, summary = _simulate_one_cycle(c)
    summary.update({
        "thermal_cycles_completed": 1,
        "thermal_converged": None,
        "thermal_final_next_cycle_wall_K": summary["wall_final_temperature_K"],
        "thermal_cycle_delta_K": summary["wall_final_temperature_K"] - c.wall_temperature_K,
        "thermal_cycle_history": [],
    })
    return rows, summary


def _coerce(value: Any, current: Any) -> Any:
    if isinstance(current, bool):
        return str(value).lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int) and not isinstance(current, bool):
        return int(value)
    if isinstance(current, float):
        return float(value)
    return value


def apply_config_patch(base: RigConfig, values: dict[str, Any]) -> RigConfig:
    data = asdict(base)
    defaults = asdict(RigConfig())
    for key, value in values.items():
        if key not in data:
            raise KeyError(f"Unknown RigConfig field: {key}")
        # Coerce against the declared field's canonical default type. A caller
        # may construct a float field with an integer literal (for example
        # wall_temperature_K=550); coercing against that runtime value would
        # silently truncate later fractional updates in repeated-cycle runs.
        data[key] = _coerce(value, defaults[key])
    return RigConfig(**data)


def _expand_grid_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and {"start", "stop", "step"} <= set(value):
        start, stop, step = float(value["start"]), float(value["stop"]), float(value["step"])
        if step == 0:
            raise ValueError("Sweep range step cannot be zero.")
        count = int(math.floor((stop - start) / step + 1e-9)) + 1
        return [start + i * step for i in range(max(0, count))]
    return [value]


def load_sweep(path: str) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, list):
        return obj
    if "runs" in obj:
        return obj["runs"]
    grid = obj.get("grid", obj)
    keys, values = list(grid), [_expand_grid_value(value) for value in grid.values()]
    return [dict(zip(keys, combination)) for combination in itertools.product(*values)]


def _flat_result(run_id: int, config: RigConfig, summary: dict[str, Any], status="ok", error=""):
    row = {"run_id": run_id, "status": status, "error": error}
    row.update({f"cfg_{key}": value for key, value in asdict(config).items()})
    row.update({f"out_{key}": value for key, value in summary.items() if not isinstance(value, (list, dict))})
    return row


def _run_case(item):
    run_id, base, values = item
    requested = apply_config_patch(base, values)
    config = requested
    last_error = None
    for retry in range(3):
        try:
            _, summary = simulate(config)
            summary["solver_retries"] = retry
            summary["requested_step_deg"] = requested.step_deg
            return _flat_result(run_id, config, summary), {"run_id": run_id, "patch": values, "config": asdict(config), "summary": summary}
        except Exception as exc:
            last_error = exc
            is_integrator_failure = type(exc).__name__ == "CanteraError" or "CVodes" in str(exc)
            if not is_integrator_failure or config.step_deg <= 0.125:
                break
            config = apply_config_patch(config, {"step_deg": config.step_deg / 2.0})
    error = f"{type(last_error).__name__}: {last_error}"
    return _flat_result(run_id, config, {}, "error", error), {"run_id": run_id, "patch": values, "config": asdict(config), "error": error}


def run_sweep(base: RigConfig, patches: list[dict[str, Any]], jobs: int = 1):
    items = [(index, base, values) for index, values in enumerate(patches, 1)]
    if jobs == 1:
        results = [_run_case(item) for item in items]
    else:
        try:
            from joblib import Parallel, delayed
        except ImportError as exc:
            raise RuntimeError("Parallel batches require `pip install joblib`.") from exc
        results = Parallel(n_jobs=jobs, backend="loky")(delayed(_run_case)(item) for item in items)
    return [item[0] for item in results], [item[1] for item in results]


def write_csv(path: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Headless MicroEngine Virtual Rig Beta 2.3")
    parser.add_argument("--config")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--csv", default="microengine_run.csv")
    parser.add_argument("--summary", default="microengine_summary.json")
    parser.add_argument("--sweep")
    parser.add_argument("--sweep-csv", default="microengine_sweep_results.csv")
    parser.add_argument("--sweep-json", default="microengine_sweep_results.json")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--list-fuels", action="store_true")
    args = parser.parse_args()
    if args.list_fuels:
        print(json.dumps({name: asdict(profile) for name, profile in BUILTIN_FUELS.items()}, indent=2))
        return
    config = RigConfig()
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            config = apply_config_patch(config, json.load(f))
    overrides = {}
    for item in args.set:
        if "=" not in item:
            parser.error(f"--set expects KEY=VALUE, received {item!r}")
        key, value = item.split("=", 1)
        overrides[key] = value
    config = apply_config_patch(config, overrides)
    if not args.sweep:
        rows, summary = simulate(config)
        write_csv(args.csv, rows)
        with open(args.summary, "w", encoding="utf-8") as f:
            json.dump({"config": asdict(config), "summary": summary}, f, indent=2)
        print(json.dumps(summary, indent=2))
        return
    flat, full = run_sweep(config, load_sweep(args.sweep), args.jobs)
    write_csv(args.sweep_csv, flat)
    with open(args.sweep_json, "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2)
    errors = sum(row["status"] != "ok" for row in flat)
    print(json.dumps({"runs": len(flat), "errors": errors, "csv": args.sweep_csv, "json": args.sweep_json}, indent=2))


if __name__ == "__main__":
    main()
