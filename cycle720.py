#!/usr/bin/env python3
"""Minimum viable four-stroke (720 CAD) cycle scaffold.

This module is deliberately a *wrapper and bookkeeping layer* around the
accepted one-revolution two-zone solver.  It adds explicit intake, compression,
combustion/expansion, and exhaust phases, a configurable quasi-1D valve/orifice
screen, residual-state carry-over, and crank/motor accounting.  It is not a
valve-train model or a calibrated engine-cycle solver.

The ``regression`` path calls :func:`two_zone_model.simulate_two_zone` directly
when all new physics are disabled.  This is intentional: the canonical closed
pass remains the reference and cannot silently acquire a second implementation.
All valve areas, discharge coefficients, friction and controller constants are
project-model assumptions and are exposed in dataclasses.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import json
import math
from pathlib import Path
from typing import Any, Mapping

import cantera as ct

from microengine_rig import RigConfig, build_geometry, compressible_orifice_mdot, resolve_fuel_profile
from physics.valve_flow import signed_valve_mdot
from two_zone_model import TwoZoneOptions, simulate_two_zone


PHASES = ("intake", "compression", "combustion-expansion", "exhaust")


@dataclass(frozen=True)
class ValveConfig:
    """Simple valve timing/area representation; angles are -360..+360 CAD."""

    open_start_deg: float
    open_end_deg: float
    effective_area_m2: float = 1.0e-6
    discharge_coefficient: float = 0.70
    gamma: float = 1.34
    gas_constant_J_kgK: float = 287.05

    def validate(self) -> None:
        if self.open_end_deg < self.open_start_deg:
            raise ValueError("valve open_end_deg must be >= open_start_deg")
        if self.effective_area_m2 < 0 or not 0 <= self.discharge_coefficient <= 1.5:
            raise ValueError("valve area and discharge coefficient are invalid")
        if self.gamma <= 1 or self.gas_constant_J_kgK <= 0:
            raise ValueError("valve gamma must exceed one and gas constant be positive")

    def area_at(self, deg: float) -> float:
        self.validate()
        if self.open_start_deg <= deg <= self.open_end_deg:
            return self.effective_area_m2
        return 0.0


@dataclass(frozen=True)
class FrictionBracket:
    """Constant torque bracket, kept separate from gas work (assumed)."""

    low_torque_Nm: float = 0.0
    central_torque_Nm: float = 0.0
    high_torque_Nm: float = 0.0
    selected: str = "central"

    def torque(self) -> float:
        values = {"low": self.low_torque_Nm, "central": self.central_torque_Nm,
                  "high": self.high_torque_Nm}
        if self.selected not in values or values[self.selected] < 0:
            raise ValueError("friction selected must be low, central, or high")
        return values[self.selected]


@dataclass(frozen=True)
class MotorController:
    """Proportional speed-hold controller used only for bookkeeping dynamics."""

    target_rpm: float = 1200.0
    gain_Nm_per_rad_s: float = 1.0e-5
    max_torque_Nm: float = 0.01
    inertia_kg_m2: float = 1.0e-7

    def validate(self) -> None:
        if self.target_rpm <= 0 or self.gain_Nm_per_rad_s < 0 or self.max_torque_Nm < 0:
            raise ValueError("motor controller values are invalid")
        if self.inertia_kg_m2 <= 0:
            raise ValueError("motor inertia must be positive")


@dataclass(frozen=True)
class Cycle720Options:
    """Controls for one complete 720-CAD cycle and repeated-cycle iteration."""

    step_deg: float = 1.0
    valves_enabled: bool = False
    # The original staged wrapper intentionally used one-way flow.  The
    # diagnostic path can opt into a signed orifice calculation without
    # changing the canonical regression result.
    bidirectional_valves: bool = False
    friction_enabled: bool = False
    crank_dynamics_enabled: bool = False
    motor_enabled: bool = False
    # The accepted closed-pass model settings.  Keeping this as an explicit
    # option prevents the 720 wrapper from silently substituting a new mixing
    # closure during the regression bridge.
    two_zone_options: TwoZoneOptions = field(default_factory=lambda: TwoZoneOptions(
        mixing_model="diffusion-strain", mixing_length_mm=1.0,
        molecular_diffusivity_m2_s=3.0e-6, piston_strain_coefficient=1.0,
        integrator_rtol=1.0e-9, integrator_atol=1.0e-15))
    # The full cycle is -360..+360 CAD: intake TDC=-360, firing TDC=0.
    intake_valve: ValveConfig = ValveConfig(-360.0, -160.0)
    exhaust_valve: ValveConfig = ValveConfig(160.0, 360.0)
    friction: FrictionBracket = FrictionBracket()
    motor: MotorController = MotorController()
    max_cycles: int = 12
    mass_tolerance_rel: float = 1.0e-6
    species_tolerance: float = 1.0e-7
    enthalpy_tolerance_rel: float = 1.0e-6
    temperature_tolerance_K: float = 1.0e-3
    speed_tolerance_rpm: float = 1.0e-3
    exhaust_pressure_bar: float | None = None

    def validate(self, c: RigConfig) -> None:
        if self.step_deg <= 0 or 720.0 / self.step_deg < 2:
            raise ValueError("step_deg must produce at least two 720-CAD steps")
        if self.max_cycles < 1:
            raise ValueError("max_cycles must be positive")
        if any(x <= 0 for x in (self.mass_tolerance_rel, self.species_tolerance,
                                 self.enthalpy_tolerance_rel, self.temperature_tolerance_K,
                                 self.speed_tolerance_rpm)):
            raise ValueError("periodic tolerances must be positive")
        self.intake_valve.validate(); self.exhaust_valve.validate()
        self.friction.torque(); self.motor.validate()
        if self.exhaust_pressure_bar is not None and self.exhaust_pressure_bar <= 0:
            raise ValueError("exhaust pressure must be positive")
        if self.motor_enabled and abs(self.motor.target_rpm - c.rpm) > 1e-9:
            raise ValueError("motor target_rpm must match RigConfig.rpm")
        if self.motor_enabled and not self.crank_dynamics_enabled:
            raise ValueError("motor control requires crank_dynamics_enabled")


def phase_at(deg: float) -> str:
    """Return phase on the explicit -360..+360 cycle convention.

    Intake TDC is -360 CAD, intake BDC is -180 CAD, firing TDC is 0 CAD,
    expansion BDC is +180 CAD, and exhaust ends at +360 CAD.  The canonical
    two-zone -180..+180 BDC-to-BDC trace therefore maps without rotation.
    """
    # +360 is retained as the end-of-exhaust boundary. Other exact 720-CAD
    # multiples are the same firing-TDC phase as 0 CAD.
    if math.isclose(deg, 360.0, abs_tol=1e-12):
        return "exhaust"
    if math.isclose(deg % 720.0, 0.0, abs_tol=1e-12):
        deg = 0.0
    x = ((deg + 360.0) % 720.0) - 360.0
    if x < -180.0:
        return "intake"
    if x < 0.0:
        return "compression"
    if x < 180.0:
        return "combustion-expansion"
    return "exhaust"


def _mechanism(c: RigConfig) -> tuple[str, str | None]:
    profile = resolve_fuel_profile(c)
    path = profile.mechanism
    # Keep Cantera's built-in names (gri30.yaml, air.yaml, ...) bare.  Only
    # repository-relative mechanism paths need resolving against this module.
    if not Path(path).exists() and Path(path).parent != Path("."):
        path = str(Path(__file__).resolve().parent / path)
    return path, profile.phase


def _fresh_state(c: RigConfig, volume_m3: float) -> dict[str, Any]:
    path, phase = _mechanism(c)
    gas = ct.Solution(path, phase) if phase else ct.Solution(path)
    profile = resolve_fuel_profile(c)
    gas.set_equivalence_ratio(c.equivalence_ratio, profile.fuel, profile.oxidizer)
    gas.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    return {"mass_kg": gas.density * volume_m3, "T_K": gas.T,
            "P_bar": gas.P / 1e5, "Y": {n: float(y) for n, y in zip(gas.species_names, gas.Y)},
            "speed_rpm": c.rpm, "h_J_kg": gas.enthalpy_mass}


def serialize_cycle_state(state: Mapping[str, Any]) -> str:
    """Stable JSON serialization used for reproducibility and cycle hashing."""
    clean = {"mass_kg": float(state["mass_kg"]), "T_K": float(state["T_K"]),
             "P_bar": float(state["P_bar"]), "speed_rpm": float(state.get("speed_rpm", 0.0)),
             "h_J_kg": float(state.get("h_J_kg", 0.0)),
             "Y": {str(k): float(v) for k, v in sorted(state["Y"].items())}}
    if "u_J_kg" in state:
        clean["u_J_kg"] = float(state["u_J_kg"])
    if "volume_m3" in state:
        clean["volume_m3"] = float(state["volume_m3"])
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _state_phase(c: RigConfig, state: Mapping[str, Any],
                 gas: ct.Solution | None = None) -> ct.Solution:
    path, phase = _mechanism(c)
    if gas is None:
        gas = ct.Solution(path, phase) if phase else ct.Solution(path)
    gas.TPY = float(state["T_K"]), float(state["P_bar"]) * 1e5, dict(state["Y"])
    # A two-zone end state can preserve its directly aggregated internal
    # energy.  Reconstructing only from mass-weighted h at an effective
    # pressure can otherwise create an artificial energy jump at the exhaust
    # valve.  ``volume_m3`` is deliberately explicit so this path cannot be
    # mistaken for a generic hidden state variable.
    if "u_J_kg" in state and "volume_m3" in state:
        gas.UV = float(state["u_J_kg"]), float(state["volume_m3"]) / max(float(state["mass_kg"]), 1e-30)
    return gas


def _state_enthalpy(c: RigConfig, state: Mapping[str, Any]) -> float:
    """Recover specific enthalpy with the configured mechanism/composition."""
    return _state_phase(c, state).enthalpy_mass


def _advance_lumped(c: RigConfig, state: Mapping[str, Any], volume_old: float,
                    volume_new: float, dt: float, valve: ValveConfig | None,
                    reservoir: ct.Solution | None, direction: str,
                    return_details: bool = False,
                    bidirectional: bool = False,
                    wall_heat_J: float = 0.0,
                    working_gas: ct.Solution | None = None,
                    _substep_level: int = 0):
    """Advance an ideal-gas lump with explicit valve mass and energy balance."""
    gas = _state_phase(c, state, working_gas)
    m0, u0, p0, t0 = float(state["mass_kg"]), gas.int_energy_mass, gas.P, gas.T
    # The valve relation is explicit in this lumped diagnostic.  If a coarse
    # external CAD step would transfer an appreciable fraction of the lump,
    # resolve that same signed flow over internal substeps instead of clipping
    # it at an arbitrary fraction of the mass.  This is a numerical stability
    # measure only; each substep re-evaluates pressure, direction, and choking.
    if (bidirectional and _substep_level == 0 and valve is not None
            and reservoir is not None and valve.area_at(float(state.get("deg", 0.0))) > 0.0):
        sub_state = dict(state)
        total: dict[str, Any] | None = None
        directions: list[str] = []
        raw_integral = 0.0
        choked_any = False
        remaining = dt
        elapsed = 0.0
        substeps = 0
        # Limit each explicit substep to 2% of the current lump.  The local
        # time step is chosen from the instantaneous signed flow and therefore
        # adapts again after a pressure reversal; no arbitrary mass fraction
        # is clipped from the physical transfer.
        while remaining > dt * 1.0e-12:
            sub_state["deg"] = float(state.get("deg", 0.0))
            sub_gas = _state_phase(c, sub_state, working_gas)
            sub_raw, _ = signed_valve_mdot(
                sub_gas.P, sub_gas.T, reservoir.P, reservoir.T,
                valve.area_at(float(state.get("deg", 0.0))) * 1.0e6,
                valve.discharge_coefficient, valve.gamma,
                valve.gas_constant_J_kgK)
            local_dt = remaining
            if abs(sub_raw) > 0.0:
                local_dt = min(local_dt, 0.02 * float(sub_state["mass_kg"]) / abs(sub_raw))
            if local_dt <= dt * 1.0e-14:
                # The state has become too small for a meaningful explicit
                # transfer step.  Stop with a diagnostic failure rather than
                # passing a near-zero mass to Cantera's UV root solver.
                raise RuntimeError(
                    "bidirectional valve substep underflow: "
                    f"mass={sub_state['mass_kg']:.6e} kg, mdot={sub_raw:.6e} kg/s"
                )
            sub_old = volume_old + (volume_new - volume_old) * elapsed / dt
            sub_new = volume_old + (volume_new - volume_old) * (elapsed + local_dt) / dt
            sub_state, _, details = _advance_lumped(
                c, sub_state, sub_old, sub_new, local_dt,
                valve, reservoir, direction, return_details=True,
                bidirectional=True, wall_heat_J=wall_heat_J * local_dt / dt,
                working_gas=working_gas, _substep_level=1)
            raw_integral += details["raw_signed_mdot_cylinder_to_port_kg_s"] * local_dt
            directions.append(details["flow_direction"])
            choked_any = choked_any or bool(details["choked"])
            if total is None:
                total = dict(details)
                total["species_mass_in_kg"] = list(details["species_mass_in_kg"])
                total["species_mass_out_kg"] = list(details["species_mass_out_kg"])
            else:
                for key in ("mass_in_kg", "mass_out_kg", "enthalpy_in_J",
                            "enthalpy_out_J", "work_by_gas_J",
                            "wall_heat_to_gas_J"):
                    total[key] += details[key]
                total["species_mass_in_kg"] = [
                    a + b for a, b in zip(total["species_mass_in_kg"], details["species_mass_in_kg"])
                ]
                total["species_mass_out_kg"] = [
                    a + b for a, b in zip(total["species_mass_out_kg"], details["species_mass_out_kg"])
                ]
                total["internal_energy_out_J"] = details["internal_energy_out_J"]
            elapsed += local_dt
            remaining -= local_dt
            substeps += 1
            if substeps > 10000:
                raise RuntimeError("bidirectional valve substep limit exceeded")
        assert total is not None
        total["internal_energy_in_J"] = total["internal_energy_in_J"]
        total["raw_signed_mdot_cylinder_to_port_kg_s"] = raw_integral / dt
        total["signed_mdot_cylinder_to_port_kg_s"] = (
            total["mass_out_kg"] - total["mass_in_kg"]
        ) / dt
        unique_directions = set(directions) - {"zero"}
        if len(unique_directions) > 1:
            total["flow_direction"] = "mixed"
        elif unique_directions:
            total["flow_direction"] = next(iter(unique_directions))
        else:
            total["flow_direction"] = "zero"
        total["choked"] = choked_any
        total["substeps"] = substeps
        total["transfer_limiter_fraction"] = 0.0
        return sub_state, (
            total["mass_in_kg"] - total["mass_out_kg"]
        ) / dt, total
    # Capture the outlet enthalpy before mutating the lumped state.  The
    # control-volume balance removes mass carrying the pre-step gas state;
    # using post-step enthalpy here would manufacture an energy residual.
    h0 = gas.enthalpy_mass
    dm_in = dm_out = 0.0
    raw_mdot_cylinder_to_port = 0.0
    choked = False
    flow_direction = "closed"
    if valve is not None and reservoir is not None:
        area = valve.area_at(float(state.get("deg", 0.0)))
        if bidirectional:
            # ``signed_valve_mdot`` is positive from cylinder to port.  This
            # convention remains the same for intake and exhaust valves, so a
            # pressure reversal naturally exchanges cylinder composition and
            # upstream enthalpy in the reverse direction.
            raw_mdot_cylinder_to_port, choked = signed_valve_mdot(
                p0, t0, reservoir.P, reservoir.T, area * 1.0e6,
                valve.discharge_coefficient, valve.gamma,
                valve.gas_constant_J_kgK)
            transfer = raw_mdot_cylinder_to_port * dt
            # Only enforce positivity if a step would mathematically empty
            # the lump.  Unlike the former 10/50% transfer cap, this does not
            # clip a valid reverse-flow transfer in normal operation.
            cap = max(0.0, m0 * (1.0 - 1.0e-12))
            if transfer >= 0.0:
                dm_out = min(transfer, cap)
            else:
                dm_in = min(-transfer, cap)
            if dm_out > 0.0:
                flow_direction = "cylinder_to_port"
            elif dm_in > 0.0:
                flow_direction = "port_to_cylinder"
            else:
                flow_direction = "zero"
        else:
            if direction == "in":
                mdot = compressible_orifice_mdot(reservoir.P, reservoir.T, p0, area,
                                                  valve.discharge_coefficient, valve.gamma,
                                                  valve.gas_constant_J_kgK)[0]
                dm_in = min(mdot * dt, max(0.0, m0 * 0.5))
                if dm_in > 0.0:
                    flow_direction = "port_to_cylinder"
            else:
                mdot = compressible_orifice_mdot(p0, t0, reservoir.P, area,
                                                  valve.discharge_coefficient, valve.gamma,
                                                  valve.gas_constant_J_kgK)[0]
                dm_out = min(mdot * dt, max(0.0, m0 * 0.5))
                if dm_out > 0.0:
                    flow_direction = "cylinder_to_port"
    m1 = max(1e-30, m0 + dm_in - dm_out)
    y0 = gas.Y.copy()
    y1 = (m0 * y0 + dm_in * reservoir.Y - dm_out * y0) / m1 if reservoir is not None else y0
    # First-order p*dV work and enthalpy transport. The method is intentionally
    # inspectable; it is not a substitute for a valve-volume CFD calculation.
    u1 = (m0 * u0 - p0 * (volume_new - volume_old) + wall_heat_J
          + dm_in * (reservoir.enthalpy_mass if reservoir is not None else 0.0)
          - dm_out * gas.enthalpy_mass) / m1
    gas.TPY = max(150.0, min(5000.0, t0)), max(1.0, p0), y1
    gas.UV = u1, volume_new / m1
    next_state = {"mass_kg": m1, "T_K": gas.T, "P_bar": gas.P / 1e5,
            "Y": {n: float(y) for n, y in zip(gas.species_names, gas.Y)},
            "speed_rpm": float(state.get("speed_rpm", c.rpm)),
            "h_J_kg": gas.enthalpy_mass, "u_J_kg": gas.int_energy_mass,
            "volume_m3": volume_new}
    net = (dm_in - dm_out) / dt
    if not return_details:
        return next_state, net
    return next_state, net, {
        "mass_in_kg": dm_in,
        "mass_out_kg": dm_out,
        "enthalpy_in_J": dm_in * (reservoir.enthalpy_mass if reservoir is not None else 0.0),
        "enthalpy_out_J": dm_out * h0,
        "work_by_gas_J": p0 * (volume_new - volume_old),
        "wall_heat_to_gas_J": float(wall_heat_J),
        "wall_heat_rate_W": float(wall_heat_J) / dt if dt > 0.0 else 0.0,
        "raw_signed_mdot_cylinder_to_port_kg_s": raw_mdot_cylinder_to_port,
        "signed_mdot_cylinder_to_port_kg_s": (dm_out - dm_in) / dt if dt > 0.0 else 0.0,
        "flow_direction": flow_direction,
        "choked": bool(choked),
        "transfer_limiter_fraction": 0.0 if bidirectional else 0.50,
        "substeps": 1,
        "internal_energy_in_J": m0 * u0,
        "internal_energy_out_J": m1 * gas.int_energy_mass,
        "species_mass_in_kg": (dm_in * reservoir.Y).tolist() if reservoir is not None else [],
        "species_mass_out_kg": (dm_out * y0).tolist(),
    }


def _gas_torque(c: RigConfig, pressure_bar: float, theta_deg: float) -> float:
    g = build_geometry(c)
    th = math.radians(theta_deg)
    eps = 1e-3
    dV_dtheta = (g.volume(th + eps) - g.volume(th - eps)) / (2.0 * eps)
    return pressure_bar * 1e5 * dV_dtheta


def _speed_step(c: RigConfig, options: Cycle720Options, speed_rpm: float,
                torque_gas: float, dt: float) -> tuple[float, float]:
    # The canonical regression and gas-exchange-only stages hold crank speed
    # at the prescribed RigConfig value.  Do not integrate gas torque against
    # a placeholder inertia unless the caller explicitly enables crank
    # dynamics; doing so can create meaningless six-figure RPM excursions.
    if not options.crank_dynamics_enabled:
        return speed_rpm, 0.0
    friction = options.friction.torque() if options.friction_enabled else 0.0
    motor = 0.0
    if options.motor_enabled:
        error = (options.motor.target_rpm - speed_rpm) * 2.0 * math.pi / 60.0
        motor = max(-options.motor.max_torque_Nm,
                    min(options.motor.max_torque_Nm, options.motor.gain_Nm_per_rad_s * error))
    alpha = (torque_gas + motor - friction) / (options.motor.inertia_kg_m2 if options.motor_enabled else 1.0e-7)
    return max(1.0, speed_rpm + alpha * dt * 60.0 / (2.0 * math.pi)), motor


def simulate_cycle720(c: RigConfig, options: Cycle720Options = Cycle720Options(),
                      initial_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run one 720-CAD cycle, returning rows, state and staged bookkeeping.

    With all new features disabled, this returns the canonical two-zone rows
    and summary directly under ``closed_pass``; that path is the regression
    contract. Enabled gas exchange uses an ideal-gas lump around the same
    reacting compression/combustion/expansion kernel.
    """
    options.validate(c)
    if not options.valves_enabled and not options.friction_enabled and not options.motor_enabled:
        closed_rows, closed_summary = simulate_two_zone(
            c, options.two_zone_options, initial_state=initial_state)
        rows = [dict(row, phase="compression" if row["deg"] < 0 else
                     "combustion-expansion", cycle_deg=row["deg"])
                for row in closed_rows]
        end = closed_summary["end_state"]
        end_state = {"mass_kg": closed_summary["initial_trapped_mass_mg"] * 1e-6 * closed_summary["mass_retained_end_fraction"],
                     "T_K": end["T_K"], "P_bar": end["P_bar"], "Y": end["Y"],
                     "speed_rpm": c.rpm}
        end_state["h_J_kg"] = _state_enthalpy(c, end_state)
        regression = {
            "reference": "two_zone_model.simulate_two_zone",
            "canonical_row_count": len(closed_rows),
            "mapped_firing_tdc_pressure_bar": next(
                row["effectivePressure_bar"] for row in closed_rows if abs(row["deg"]) < 1e-12),
            "canonical_gross_work_mJ": closed_summary["gross_indicated_work_mJ"],
            "canonical_mass_balance_residual_mg": closed_summary.get("mass_balance_residual_mg"),
            "canonical_max_volume_closure_error_mm3": closed_summary.get("max_volume_closure_error_mm3"),
            "gate": True,
            "note": "No 720-CAD gas exchange, pumping, friction or motor work is invented on this path.",
        }
        summary = dict(closed_summary)
        summary.update({
            "model": "minimum-viable-720-CAD-wrapper-regression",
            "phase_names": PHASES,
            "cycle_start_convention": "-360 CAD intake TDC; 0 CAD firing TDC; +360 CAD exhaust end",
            "one_revolution_period_s": 60.0 / c.rpm,
            "four_stroke_period_s": 120.0 / c.rpm,
        })
        return {"rows": rows, "summary": summary, "closed_pass": True,
                "regression": regression,
                "cycle_state_in": initial_state, "cycle_state_out": end_state,
                "periodic_metrics": {"mass_rel": 0.0, "species_max": 0.0,
                                      "enthalpy_rel": 0.0, "temperature_K": 0.0,
                                      "speed_rpm": 0.0},
                "options": asdict(options)}

    g = build_geometry(c)
    path, phase = _mechanism(c)
    profile = resolve_fuel_profile(c)
    fresh = ct.Solution(path, phase) if phase else ct.Solution(path)
    fresh.set_equivalence_ratio(c.equivalence_ratio, profile.fuel, profile.oxidizer)
    fresh.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    exhaust = ct.Solution(path, phase) if phase else ct.Solution(path)
    # Do not leave a mechanism-dependent default composition in the exhaust
    # reservoir.  This is immaterial for the legacy one-way path, but becomes
    # physically important as soon as reverse valve flow is enabled.
    exhaust.TPX = c.crankcase_temperature_K, (
        options.exhaust_pressure_bar or c.crankcase_pressure_bar
    ) * 1e5, fresh.X
    state = dict(initial_state) if initial_state and "mass_kg" in initial_state else _fresh_state(c, g.volume(0.0))
    state.setdefault("speed_rpm", c.rpm)
    cycle_initial_state = dict(state)
    rows: list[dict[str, Any]] = []
    total_in = total_out = 0.0
    valve_enthalpy_in = valve_enthalpy_out = 0.0
    valve_work = 0.0
    intake_enthalpy_in = intake_enthalpy_out = intake_work = 0.0
    exhaust_enthalpy_in = exhaust_enthalpy_out = exhaust_work = 0.0
    valve_species_in: list[float] | None = None
    valve_species_out: list[float] | None = None
    work_by_phase = {p: 0.0 for p in PHASES}
    motor_torque = []
    n = int(round(720.0 / options.step_deg))
    dt = math.radians(options.step_deg) / (2.0 * math.pi * c.rpm / 60.0)

    # Intake: TDC (-360) to BDC (-180).  The first state is deliberately a
    # residual/clearance-volume state, then the moving lump draws from fresh
    # charge through the configured effective valve area.
    intake_rows = []
    for i in range(n // 4 + 1):
        deg = -360.0 + i * options.step_deg
        if i:
            previous = intake_rows[-1]
            state["deg"] = previous["cycle_deg"]
            state, net, details = _advance_lumped(
                c, state, g.volume(math.radians(previous["cycle_deg"])),
                g.volume(math.radians(deg)), dt,
                options.intake_valve if options.valves_enabled else None, fresh, "in",
                return_details=True, bidirectional=options.bidirectional_valves)
            valve_enthalpy_in += details["enthalpy_in_J"]
            valve_enthalpy_out += details["enthalpy_out_J"]
            valve_work += details["work_by_gas_J"]
            intake_enthalpy_in += details["enthalpy_in_J"]
            intake_enthalpy_out += details["enthalpy_out_J"]
            intake_work += details["work_by_gas_J"]
            if details["species_mass_in_kg"]:
                if valve_species_in is None:
                    valve_species_in = [0.0] * len(details["species_mass_in_kg"])
                valve_species_in = [a + b for a, b in zip(valve_species_in, details["species_mass_in_kg"])]
            if valve_species_out is None:
                valve_species_out = [0.0] * len(details["species_mass_out_kg"])
            valve_species_out = [a + b for a, b in zip(valve_species_out, details["species_mass_out_kg"])]
            total_in += max(0.0, net * dt); total_out += max(0.0, -net * dt)
        intake_rows.append({"cycle_deg": deg, "phase": "intake", "pressure_bar": state["P_bar"],
                            "temperature_K": state["T_K"], "mass_kg": state["mass_kg"],
                            "valve_mass_flow_kg_s": net if i else 0.0,
                            "speed_rpm": state.get("speed_rpm", c.rpm), "motor_torque_Nm": 0.0})
    rows.extend(intake_rows)
    intake_close_state = dict(state)

    # Compression through expansion is always the accepted one-revolution
    # model.  Its -180..+180 angles map to 180..540 in the four-stroke cycle.
    closed_c = replace(c, intake_temperature_K=state["T_K"], intake_pressure_bar=state["P_bar"],
                       step_deg=options.step_deg)
    closed_rows, closed_summary = simulate_two_zone(
        closed_c, options.two_zone_options,
        initial_state={"Y": state["Y"], "T_K": state["T_K"], "P_bar": state["P_bar"],
                       "source": "720-intake-close"})
    for cr in closed_rows:
        angle = cr["deg"]
        rows.append(dict(cr, phase=phase_at(angle), cycle_deg=angle,
                         pressure_bar=cr["effectivePressure_bar"],
                         temperature_K=cr["coreTemperature_K"], mass_kg=(cr["coreMass_mg"] + cr["boundaryMass_mg"]) * 1e-6,
                         valve_mass_flow_kg_s=0.0, speed_rpm=state.get("speed_rpm", c.rpm), motor_torque_Nm=0.0))
    end = closed_summary["end_state"]
    closed_initial_mass_kg = closed_summary["initial_trapped_mass_mg"] * 1e-6
    closed_final_mass_kg = closed_initial_mass_kg * closed_summary["mass_retained_end_fraction"]
    state = {"mass_kg": closed_final_mass_kg,
             "T_K": end["T_K"], "P_bar": end["P_bar"], "Y": end["Y"],
             "speed_rpm": state.get("speed_rpm", c.rpm),
             "h_J_kg": _state_enthalpy(c, end),
             "u_J_kg": closed_summary.get("final_internal_energy_J", 0.0) / max(closed_final_mass_kg, 1e-30),
             "volume_m3": g.volume(math.pi)}
    post_closed_state = dict(state)

    # Exhaust: BDC (+180) to intake TDC (+360), using post-combustion state.
    exhaust_rows = []
    for j in range(1, n // 4 + 1):
        deg = 180.0 + j * options.step_deg
        previous = exhaust_rows[-1] if exhaust_rows else rows[-1]
        state["deg"] = previous["cycle_deg"]
        state, net, details = _advance_lumped(
            c, state, g.volume(math.radians(previous["cycle_deg"])),
            g.volume(math.radians(deg)), dt,
            options.exhaust_valve if options.valves_enabled else None, exhaust, "out",
            return_details=True, bidirectional=options.bidirectional_valves)
        valve_enthalpy_in += details["enthalpy_in_J"]
        valve_enthalpy_out += details["enthalpy_out_J"]
        valve_work += details["work_by_gas_J"]
        exhaust_enthalpy_in += details["enthalpy_in_J"]
        exhaust_enthalpy_out += details["enthalpy_out_J"]
        exhaust_work += details["work_by_gas_J"]
        if valve_species_in is None:
            valve_species_in = [0.0] * len(details["species_mass_in_kg"])
        valve_species_in = [a + b for a, b in zip(valve_species_in, details["species_mass_in_kg"])]
        if valve_species_out is None:
            valve_species_out = [0.0] * len(details["species_mass_out_kg"])
        valve_species_out = [a + b for a, b in zip(valve_species_out, details["species_mass_out_kg"])]
        total_in += max(0.0, net * dt); total_out += max(0.0, -net * dt)
        exhaust_rows.append({"cycle_deg": deg, "phase": "exhaust", "pressure_bar": state["P_bar"],
                             "temperature_K": state["T_K"], "mass_kg": state["mass_kg"],
                             "valve_mass_flow_kg_s": net, "speed_rpm": state.get("speed_rpm", c.rpm),
                             "motor_torque_Nm": 0.0})
    rows.extend(exhaust_rows)
    # Complete output uses gas pressure for torque/inertia diagnostics.  The
    # pressure trace in the closed rows remains the canonical reacting trace.
    speed = float(state.get("speed_rpm", c.rpm))
    for idx, row in enumerate(rows):
        previous = rows[max(0, idx - 1)]
        theta = row["cycle_deg"]
        tg = _gas_torque(c, row["pressure_bar"], theta)
        speed, tm = _speed_step(c, options, speed, tg, dt)
        row["gas_torque_Nm"] = tg
        row["friction_torque_Nm"] = options.friction.torque() if options.friction_enabled else 0.0
        row["motor_torque_Nm"] = tm
        row["speed_rpm"] = speed
        if idx:
            work_by_phase[row["phase"]] += 0.5 * (row["pressure_bar"] + previous["pressure_bar"]) * 1e5 * (
                g.volume(math.radians(theta)) - g.volume(math.radians(previous["cycle_deg"]))) * 1e3
        motor_torque.append(tm)
    out = {"mass_kg": state["mass_kg"], "T_K": state["T_K"], "P_bar": state["P_bar"],
           "Y": state["Y"], "speed_rpm": speed, "h_J_kg": state.get("h_J_kg", _specific_enthalpy(state))}
    def total_internal_energy(snapshot: Mapping[str, Any]) -> float:
        gas = _state_phase(c, snapshot)
        return float(snapshot["mass_kg"]) * gas.int_energy_mass

    closed_in_kg = closed_summary.get("blowby_mass_in_mg", 0.0) * 1e-6
    closed_out_kg = closed_summary.get("blowby_mass_out_mg", 0.0) * 1e-6
    closed_h_in = closed_summary.get("blowby_enthalpy_in_J", 0.0)
    closed_h_out = closed_summary.get("blowby_enthalpy_out_J", 0.0)
    closed_work = closed_summary.get("gross_indicated_work_mJ", 0.0) * 1e-3
    closed_wall_heat = closed_summary.get("wall_energy_gas_to_wall_mJ", 0.0) * 1e-3
    closed_u0 = closed_summary.get("initial_internal_energy_J", total_internal_energy(intake_close_state))
    closed_u1 = closed_summary.get("final_internal_energy_J", total_internal_energy(state))
    # ``wall_energy_gas_to_wall`` is positive for heat leaving the gas.  It is
    # therefore subtracted from the gas internal-energy balance.
    closed_energy_residual = closed_u1 - (closed_u0 + closed_h_in - closed_h_out
                                          - closed_work - closed_wall_heat)
    cycle_initial_mass = float(cycle_initial_state["mass_kg"])
    cycle_final_mass = float(out["mass_kg"])
    cycle_mass_residual = (cycle_initial_mass + total_in + closed_in_kg
                           - total_out - closed_out_kg - cycle_final_mass)
    cycle_u0 = total_internal_energy(cycle_initial_state)
    cycle_u1 = total_internal_energy(out)
    cycle_energy_residual = cycle_u1 - (
        cycle_u0 + valve_enthalpy_in - valve_enthalpy_out + closed_h_in - closed_h_out
        - valve_work - closed_work - closed_wall_heat
    )
    intake_energy_residual = (
        total_internal_energy(intake_close_state) - total_internal_energy(cycle_initial_state)
        - (intake_enthalpy_in - intake_enthalpy_out - intake_work)
    )
    exhaust_energy_residual = (
        total_internal_energy(out) - total_internal_energy(post_closed_state)
        - (exhaust_enthalpy_in - exhaust_enthalpy_out - exhaust_work)
    )
    summary = {"model": "minimum-viable-720-CAD-wrapper", "phase_names": PHASES,
               "cycle_start_convention": "-360 CAD intake TDC; 0 CAD firing TDC; +360 CAD exhaust end",
               "one_revolution_period_s": 60.0 / c.rpm,
               "four_stroke_period_s": 120.0 / c.rpm,
               "gross_work_mJ": sum(work_by_phase.values()),
               "phase_work_mJ": work_by_phase, "intake_mass_mg": total_in * 1e6,
               "exhaust_mass_mg": total_out * 1e6,
               "pumping_work_mJ": work_by_phase["intake"] + work_by_phase["exhaust"],
               "friction_work_mJ": -sum(row["friction_torque_Nm"] * (2.0 * math.pi * options.step_deg / 360.0)
                                         for row in rows) * 1e3,
               "motor_torque_peak_Nm": max((abs(x) for x in motor_torque), default=0.0),
               "motor_torque_rms_Nm": math.sqrt(sum(x*x for x in motor_torque) / max(1, len(motor_torque))),
               "cycle_accounting": {
                   "initial_mass_mg": cycle_initial_mass * 1e6,
                   "final_mass_mg": cycle_final_mass * 1e6,
                   "initial_pressure_bar": float(cycle_initial_state["P_bar"]),
                   "final_pressure_bar": float(out["P_bar"]),
                   "initial_temperature_K": float(cycle_initial_state["T_K"]),
                   "final_temperature_K": float(out["T_K"]),
                   "integrated_intake_mass_in_mg": total_in * 1e6,
                   "integrated_exhaust_mass_out_mg": total_out * 1e6,
                   "closed_kernel_initial_mass_mg": closed_initial_mass_kg * 1e6,
                   "closed_kernel_final_mass_mg": closed_final_mass_kg * 1e6,
                   "closed_kernel_blowby_in_mg": closed_in_kg * 1e6,
                   "closed_kernel_blowby_out_mg": closed_out_kg * 1e6,
                   "mass_balance_residual_mg": cycle_mass_residual * 1e6,
                   "mass_balance_residual_rel_cycle_start": cycle_mass_residual / max(cycle_initial_mass, 1e-30),
                   "mass_balance_residual_rel_closed_kernel": cycle_mass_residual / max(closed_initial_mass_kg, 1e-30),
                   "closed_kernel_mass_balance_residual_mg": closed_summary.get("mass_balance_residual_mg"),
                   "closed_kernel_mass_balance_residual_rel": (
                       closed_summary.get("mass_balance_residual_mg", 0.0) * 1e-6
                       / max(closed_initial_mass_kg, 1e-30)
                   ),
                   "valve_enthalpy_in_J": valve_enthalpy_in,
                   "valve_enthalpy_out_J": valve_enthalpy_out,
                   "closed_blowby_enthalpy_in_J": closed_h_in,
                   "closed_blowby_enthalpy_out_J": closed_h_out,
                   "initial_total_enthalpy_J": cycle_initial_mass * _state_phase(c, cycle_initial_state).enthalpy_mass,
                   "final_total_enthalpy_J": cycle_final_mass * _state_phase(c, out).enthalpy_mass,
                   "closed_energy_balance_residual_J": closed_energy_residual,
                   "energy_balance_residual_J": cycle_energy_residual,
                   "intake_and_exhaust_combined_energy_residual_J": (
                       cycle_energy_residual - closed_energy_residual
                   ),
                   "intake_energy_balance_residual_J": intake_energy_residual,
                   "exhaust_energy_balance_residual_J": exhaust_energy_residual,
                   "energy_terms_are_screening_accounting": True,
                   "species_basis": "Cantera species order; valve vectors include both directions",
                   "valve_species_in_kg": valve_species_in or [],
                   "valve_species_out_kg": valve_species_out or [],
               },
               "cycle_state_out": out, "cycle_state_in": initial_state,
               "note": "Valve flow, friction and motor values are project-model assumptions; gas exchange is lumped.",
               "options": asdict(options)}
    return {"rows": rows, "summary": summary, "closed_pass": False,
            "cycle_state_in": initial_state, "cycle_state_out": out,
            "periodic_metrics": {}, "options": asdict(options)}


def simulate_motored_cycle720(
    c: RigConfig, options: Cycle720Options = Cycle720Options(
        valves_enabled=True, bidirectional_valves=True,
    ), initial_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one nonreacting, fixed-speed 720-CAD gas-exchange cycle.

    This is a diagnostic for valve/state semantics, not an engine operating
    point.  It advances one ideal-gas lump through the same geometry, valve
    timings, manifold states, and wall-temperature boundary used by the
    staged wrapper, but deliberately excludes chemistry, blow-by, friction,
    crank dynamics, and motor control.  ``bidirectional_valves`` must be true:
    reverse flow uses cylinder composition and enthalpy for the outgoing side
    and the reservoir state for the incoming side.

    ``mass_kg`` and ``u_J_kg`` are carried explicitly in the returned state so
    that the end state is a valid Poincare-map input rather than a pressure /
    temperature-only reconstruction.  Wall heat is a first-order explicit
    term using ``effective_h_W_m2K`` and ``wall_temperature_K``; it is an
    inspectable diagnostic closure, not a resolved heat-transfer model.
    """
    options.validate(c)
    if not options.valves_enabled or not options.bidirectional_valves:
        raise ValueError("motored diagnostic requires bidirectional valves_enabled")
    if options.friction_enabled or options.crank_dynamics_enabled or options.motor_enabled:
        raise ValueError("motored diagnostic excludes friction and crank/motor dynamics")
    if c.wall_mode not in {"adiabatic", "fixed"}:
        raise ValueError("motored diagnostic requires adiabatic or fixed wall mode")

    g = build_geometry(c)
    path, phase = _mechanism(c)
    profile = resolve_fuel_profile(c)
    fresh = ct.Solution(path, phase) if phase else ct.Solution(path)
    fresh.set_equivalence_ratio(c.equivalence_ratio, profile.fuel, profile.oxidizer)
    fresh.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    exhaust = ct.Solution(path, phase) if phase else ct.Solution(path)
    # A bare Solution carries the mechanism's arbitrary default composition
    # (for GRI this is not air).  A motored/no-chemistry exhaust manifold
    # must not inject that composition during reverse flow; use the same
    # inert/fresh mixture as the intake reservoir unless a future manifold
    # model supplies a measured residual composition.
    exhaust.TPX = c.crankcase_temperature_K, (
        options.exhaust_pressure_bar or c.crankcase_pressure_bar
    ) * 1e5, fresh.X
    working_gas = ct.Solution(path, phase) if phase else ct.Solution(path)
    state = dict(initial_state) if initial_state is not None else _fresh_state(c, g.volume(0.0))
    state.setdefault("speed_rpm", c.rpm)
    state.setdefault("volume_m3", g.volume(0.0))
    cycle_initial_state = dict(state)
    n = int(round(720.0 / options.step_deg))
    if abs(n * options.step_deg - 720.0) > 1.0e-9:
        raise ValueError("step_deg must divide 720 exactly for motored diagnostics")
    dt = math.radians(options.step_deg) / g.omega_rad_s
    angles = [-360.0 + i * options.step_deg for i in range(n + 1)]
    rows: list[dict[str, Any]] = []
    accounting = {
        "mass_in_kg": 0.0, "mass_out_kg": 0.0,
        "enthalpy_in_J": 0.0, "enthalpy_out_J": 0.0,
        "work_by_gas_J": 0.0, "wall_heat_to_gas_J": 0.0,
        "species_in_kg": [0.0] * len(fresh.species_names),
        "species_out_kg": [0.0] * len(fresh.species_names),
        "events": {
            "intake": {"steps": 0, "reverse_steps": 0, "mass_in_kg": 0.0,
                        "mass_out_kg": 0.0, "choked_steps": 0},
            "exhaust": {"steps": 0, "reverse_steps": 0, "mass_in_kg": 0.0,
                         "mass_out_kg": 0.0, "choked_steps": 0},
        },
    }

    def state_row(deg: float, phase_name: str, valve_name: str | None,
                  net: float, details: Mapping[str, Any] | None,
                  wall_heat_rate: float, piston_work_rate: float) -> dict[str, Any]:
        detail = details or {}
        return {
            "cycle_deg": deg, "phase": phase_name,
            "pressure_bar": float(state["P_bar"]),
            "temperature_K": float(state["T_K"]),
            "mass_kg": float(state["mass_kg"]),
            "valve_name": valve_name or "closed",
            "valve_open": valve_name is not None,
            "valve_mass_flow_kg_s": float(net),
            "signed_mdot_cylinder_to_port_kg_s": float(
                detail.get("signed_mdot_cylinder_to_port_kg_s", 0.0)
            ),
            "raw_signed_mdot_cylinder_to_port_kg_s": float(
                detail.get("raw_signed_mdot_cylinder_to_port_kg_s", 0.0)
            ),
            "valve_flow_direction": detail.get("flow_direction", "closed"),
            "valve_choked": bool(detail.get("choked", False)),
            "wall_heat_rate_W": float(wall_heat_rate),
            "piston_work_rate_W": float(piston_work_rate),
            "speed_rpm": float(state.get("speed_rpm", c.rpm)),
        }

    # The first point is a homologous intake-TDC snapshot.  Subsequent points
    # use the previous angle to select the active valve and evaluate dV.
    rows.append(state_row(angles[0], phase_at(angles[0]), "intake", 0.0, None, 0.0, 0.0))
    for index in range(1, len(angles)):
        previous_deg = angles[index - 1]
        deg = angles[index]
        phase_name = phase_at(previous_deg)
        if options.intake_valve.area_at(previous_deg) > 0.0:
            valve_name, valve, reservoir = "intake", options.intake_valve, fresh
        elif options.exhaust_valve.area_at(previous_deg) > 0.0:
            valve_name, valve, reservoir = "exhaust", options.exhaust_valve, exhaust
        else:
            valve_name, valve, reservoir = None, None, None
        state["deg"] = previous_deg
        gas_before = _state_phase(c, state)
        wall_heat_rate = 0.0
        if c.wall_mode == "fixed":
            wall_heat_rate = c.effective_h_W_m2K * g.surface_area(
                math.radians(0.5 * (previous_deg + deg))
            ) * (c.wall_temperature_K - gas_before.T)
        next_state, net, details = _advance_lumped(
            c, state,
            g.volume(math.radians(previous_deg)),
            g.volume(math.radians(deg)), dt,
            valve, reservoir, "in" if valve_name == "intake" else "out",
            return_details=True, bidirectional=True,
            wall_heat_J=wall_heat_rate * dt,
            working_gas=working_gas,
        )
        state = next_state
        accounting["mass_in_kg"] += details["mass_in_kg"]
        accounting["mass_out_kg"] += details["mass_out_kg"]
        accounting["enthalpy_in_J"] += details["enthalpy_in_J"]
        accounting["enthalpy_out_J"] += details["enthalpy_out_J"]
        accounting["work_by_gas_J"] += details["work_by_gas_J"]
        accounting["wall_heat_to_gas_J"] += details["wall_heat_to_gas_J"]
        accounting["species_in_kg"] = [
            a + b for a, b in zip(accounting["species_in_kg"], details["species_mass_in_kg"])
        ]
        accounting["species_out_kg"] = [
            a + b for a, b in zip(accounting["species_out_kg"], details["species_mass_out_kg"])
        ]
        if valve_name is not None:
            event = accounting["events"][valve_name]
            event["steps"] += 1
            event["reverse_steps"] += int(details["flow_direction"] == "port_to_cylinder")
            event["mass_in_kg"] += details["mass_in_kg"]
            event["mass_out_kg"] += details["mass_out_kg"]
            event["choked_steps"] += int(details["choked"])
        rows.append(state_row(
            deg, phase_name, valve_name, net, details,
            wall_heat_rate, details["work_by_gas_J"] / dt,
        ))

    def total_internal_energy(snapshot: Mapping[str, Any]) -> float:
        gas = _state_phase(c, snapshot, working_gas)
        return float(snapshot["mass_kg"]) * gas.int_energy_mass

    initial_mass = float(cycle_initial_state["mass_kg"])
    final_mass = float(state["mass_kg"])
    mass_residual = initial_mass + accounting["mass_in_kg"] - accounting["mass_out_kg"] - final_mass
    initial_gas = _state_phase(c, cycle_initial_state, working_gas)
    final_gas = _state_phase(c, state, working_gas)
    initial_species = initial_mass * initial_gas.Y
    final_species = final_mass * final_gas.Y
    species_residual = [
        float(a + b - c_) for a, b, c_ in zip(
            initial_species, accounting["species_in_kg"],
            [x + y for x, y in zip(accounting["species_out_kg"], final_species)],
        )
    ]
    initial_u = total_internal_energy(cycle_initial_state)
    final_u = total_internal_energy(state)
    energy_residual = final_u - (
        initial_u + accounting["enthalpy_in_J"] - accounting["enthalpy_out_J"]
        - accounting["work_by_gas_J"] + accounting["wall_heat_to_gas_J"]
    )
    minimum = min(rows, key=lambda row: row["temperature_K"])
    maximum = max(rows, key=lambda row: row["temperature_K"])
    diagnostics = {
        "minimum_temperature": dict(minimum),
        "maximum_temperature": dict(maximum),
        "temperature_excursion_K": maximum["temperature_K"] - minimum["temperature_K"],
        "state_map_norm_definition": (
            "sqrt(mass_rel^2 + (delta_T/300 K)^2 + (delta_P/max(P,1 bar))^2 "
            "+ species_max^2); diagnostic only"
        ),
    }
    accounting.update({
        "initial_mass_kg": initial_mass, "final_mass_kg": final_mass,
        "mass_balance_residual_kg": mass_residual,
        "mass_balance_residual_rel_initial": mass_residual / max(initial_mass, 1e-30),
        "initial_total_internal_energy_J": initial_u,
        "final_total_internal_energy_J": final_u,
        "energy_balance_residual_J": energy_residual,
        "species_balance_residual_kg": species_residual,
        "species_balance_residual_max_kg": max((abs(x) for x in species_residual), default=0.0),
    })
    state["deg"] = 360.0
    return {
        "rows": rows,
        "summary": {
            "model": "nonreacting-motored-720-CAD-signed-valve-diagnostic",
            "four_stroke_period_s": 120.0 / c.rpm,
            "accounting": accounting,
            "diagnostics": diagnostics,
            "state_in": cycle_initial_state,
            "state_out": state,
            "provenance": {
                "measured": False, "literature_derived": False,
                "project_model_assumptions": True,
                "note": "Fixed-speed ideal-gas motored diagnostic; valve areas, Cd, wall h and wall temperature are assumptions.",
            },
        },
        "cycle_state_in": cycle_initial_state,
        "cycle_state_out": state,
        "closed_pass": False,
    }


def _state_metrics(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, float]:
    y_names = sorted(set(previous["Y"]) | set(current["Y"]))
    species = max((abs(float(current["Y"].get(k, 0.0)) - float(previous["Y"].get(k, 0.0))) for k in y_names), default=0.0)
    m0 = max(abs(float(previous["mass_kg"])), 1e-30)
    h0 = _specific_enthalpy(previous); h1 = _specific_enthalpy(current)
    return {"mass_rel": abs(float(current["mass_kg"]) - float(previous["mass_kg"])) / m0,
            "species_max": species, "enthalpy_rel": abs(h1-h0) / max(abs(h0), 1.0),
            "temperature_K": abs(float(current["T_K"]) - float(previous["T_K"])),
            "speed_rpm": abs(float(current.get("speed_rpm", 0.0)) - float(previous.get("speed_rpm", 0.0)))}


def _specific_enthalpy(state: Mapping[str, Any]) -> float:
    if "h_J_kg" in state:
        return float(state["h_J_kg"])
    # A standard-air fallback is enough for convergence bookkeeping when a
    # mechanism cannot be reconstructed from an intentionally partial state.
    try:
        gas = ct.Solution("air.yaml")
        gas.TPY = float(state["T_K"]), float(state["P_bar"]) * 1e5, {"O2": 0.21, "N2": 0.79}
        return gas.enthalpy_mass
    except Exception:
        return 1005.0 * float(state["T_K"])


def iterate_motored_periodic_720(
    c: RigConfig, options: Cycle720Options = Cycle720Options(
        valves_enabled=True, bidirectional_valves=True,
    ), initial_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Directly iterate the fixed-speed motored Poincare map.

    No acceleration is applied here.  The cycle map is intentionally exposed
    as ordinary direct cycling so any future fixed-point accelerator can be
    checked against this reference.  The returned ``map_norm`` is a scaled
    diagnostic, while the component metrics remain the actual gate quantities.
    """
    options.validate(c)
    state = dict(initial_state) if initial_state is not None else None
    history: list[dict[str, Any]] = []
    result = None
    for cycle in range(1, options.max_cycles + 1):
        result = simulate_motored_cycle720(c, options, state)
        out = result["cycle_state_out"]
        if state is not None:
            metrics = _state_metrics(state, out)
            pressure_rel = abs(float(out["P_bar"]) - float(state["P_bar"])) / max(
                abs(float(state["P_bar"])), 1.0
            )
            map_norm = math.sqrt(
                metrics["mass_rel"] ** 2
                + (metrics["temperature_K"] / 300.0) ** 2
                + pressure_rel ** 2
                + metrics["species_max"] ** 2
            )
        else:
            metrics = {"mass_rel": math.inf, "species_max": math.inf,
                       "enthalpy_rel": math.inf, "temperature_K": math.inf,
                       "speed_rpm": math.inf}
            map_norm = math.inf
        accounting = result["summary"]["accounting"]
        history.append({
            "cycle": cycle, **metrics, "pressure_rel": pressure_rel if state is not None else math.inf,
            "map_norm": map_norm,
            "accounting": accounting,
            "diagnostics": result["summary"]["diagnostics"],
            "homologous_end_state": {
                "mass_kg": float(out["mass_kg"]), "T_K": float(out["T_K"]),
                "P_bar": float(out["P_bar"]),
                "Y": {str(k): float(v) for k, v in out["Y"].items()},
            },
            "state_hash": serialize_cycle_state(out),
        })
        state = out
        if cycle > 1 and all((
            metrics["mass_rel"] <= options.mass_tolerance_rel,
            metrics["species_max"] <= options.species_tolerance,
            metrics["enthalpy_rel"] <= options.enthalpy_tolerance_rel,
            metrics["temperature_K"] <= options.temperature_tolerance_K,
            metrics["speed_rpm"] <= options.speed_tolerance_rpm,
        )):
            return {"converged": True, "cycles": cycle, "history": history,
                    "result": result, "state": state,
                    "gates": {"mass": True, "species": True, "enthalpy": True,
                               "temperature": True, "speed": True}}
    last = history[-1]
    return {
        "converged": False, "cycles": options.max_cycles,
        "history": history, "result": result, "state": state,
        "gates": {
            "mass": last["mass_rel"] <= options.mass_tolerance_rel,
            "species": last["species_max"] <= options.species_tolerance,
            "enthalpy": last["enthalpy_rel"] <= options.enthalpy_tolerance_rel,
            "temperature": last["temperature_K"] <= options.temperature_tolerance_K,
            "speed": last["speed_rpm"] <= options.speed_tolerance_rpm,
        },
    }


def iterate_periodic_720(c: RigConfig, options: Cycle720Options = Cycle720Options(),
                         initial_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Iterate complete cycles until strict mass/species/energy/T/speed closure."""
    options.validate(c)
    state = dict(initial_state) if initial_state is not None else None
    history: list[dict[str, Any]] = []
    result = None
    for cycle in range(1, options.max_cycles + 1):
        result = simulate_cycle720(c, options, state)
        out = result["cycle_state_out"]
        metrics = _state_metrics(state, out) if state is not None and "mass_kg" in state else {
            "mass_rel": math.inf, "species_max": math.inf, "enthalpy_rel": math.inf,
            "temperature_K": math.inf, "speed_rpm": math.inf}
        summary = result.get("summary", {})
        accounting = summary.get("cycle_accounting", {})
        homologous_state = {
            "mass_kg": float(out["mass_kg"]),
            "T_K": float(out["T_K"]),
            "P_bar": float(out["P_bar"]),
            "Y": {str(name): float(value) for name, value in out["Y"].items()},
        }
        history.append({"cycle": cycle, **metrics,
                        "state_hash": serialize_cycle_state(out),
                        "homologous_end_state": homologous_state,
                        "accounting": accounting,
                        "intake_mass_mg": summary.get("intake_mass_mg"),
                        "exhaust_mass_mg": summary.get("exhaust_mass_mg"),
                        "pumping_work_mJ": summary.get("pumping_work_mJ"),
                        "friction_work_mJ": summary.get("friction_work_mJ"),
                        "gas_work_mJ": summary.get("gross_work_mJ", summary.get("gross_indicated_work_mJ")),
                        "motor_torque_peak_Nm": summary.get("motor_torque_peak_Nm"),
                        "motor_torque_rms_Nm": summary.get("motor_torque_rms_Nm")})
        state = out
        if all((metrics["mass_rel"] <= options.mass_tolerance_rel,
                metrics["species_max"] <= options.species_tolerance,
                metrics["enthalpy_rel"] <= options.enthalpy_tolerance_rel,
                metrics["temperature_K"] <= options.temperature_tolerance_K,
                metrics["speed_rpm"] <= options.speed_tolerance_rpm)):
            return {"converged": True, "cycles": cycle, "history": history, "result": result,
                    "state": state, "gates": {"mass": True, "species": True, "enthalpy": True,
                                                "temperature": True, "speed": True}}
    last = history[-1]
    return {"converged": False, "cycles": options.max_cycles, "history": history, "result": result,
            "state": state, "gates": {"mass": last["mass_rel"] <= options.mass_tolerance_rel,
                                       "species": last["species_max"] <= options.species_tolerance,
                                       "enthalpy": last["enthalpy_rel"] <= options.enthalpy_tolerance_rel,
                                       "temperature": last["temperature_K"] <= options.temperature_tolerance_K,
                                       "speed": last["speed_rpm"] <= options.speed_tolerance_rpm}}


__all__ = ["ValveConfig", "FrictionBracket", "MotorController", "Cycle720Options",
           "phase_at", "serialize_cycle_state", "simulate_cycle720",
           "simulate_motored_cycle720", "iterate_periodic_720",
           "iterate_motored_periodic_720"]
