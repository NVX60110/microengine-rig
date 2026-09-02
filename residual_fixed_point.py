#!/usr/bin/env python3
"""Bounded residual carry-over experiment for the one-revolution two-zone model.

This module supplies a transparent composition map around ``simulate_two_zone``.
It is deliberately not a valve, intake, exhaust, or 720-CAD model: at each map
application a fresh charge (the configured equivalence ratio) is mixed with a
mass- or mole-weighted snapshot of the preceding modeled cycle end.  Mixing is
performed at the configured intake pressure and with adiabatic enthalpy
conservation.  The resulting state is then passed to the existing solver.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

import cantera as ct

from microengine_rig import RigConfig, resolve_fuel_profile
from two_zone_model import TwoZoneOptions, simulate_two_zone


@dataclass(frozen=True)
class ResidualOptions:
    residual_fractions: tuple[float, ...] = (0.05, 0.15, 0.30)
    mixing_basis: str = "mass"  # mass or mole; f is a fraction of total charge
    max_iterations: int = 12
    composition_tolerance: float = 1.0e-8
    # The state-map temperature is evaluated after a stiff finite-step cycle;
    # 1e-3 K is tighter than the reported physical outputs and avoids mistaking
    # tiny CVODE/quadrature noise for map drift.
    temperature_tolerance_K: float = 1.0e-3


def _mechanism_path(name: str) -> str:
    direct = Path(name)
    if direct.exists() or direct.parent == Path("."):
        return str(direct)
    return str(Path(__file__).resolve().parent / direct)


def _new_gas(c: RigConfig):
    profile = resolve_fuel_profile(c)
    mechanism = _mechanism_path(profile.mechanism)
    gas = ct.Solution(mechanism, profile.phase) if profile.phase else ct.Solution(mechanism)
    gas.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    gas.set_equivalence_ratio(c.equivalence_ratio, profile.fuel, profile.oxidizer)
    gas.TP = c.intake_temperature_K, c.intake_pressure_bar * 1e5
    return profile, mechanism, gas


def _fresh_state(c: RigConfig) -> dict[str, Any]:
    """Return the configured fresh charge before residual mixing."""
    _profile, _mechanism, gas = _new_gas(c)
    return {
        "source": "fresh-charge-equivalence-ratio",
        "basis": "mass",
        "T_K": gas.T,
        "P_bar": gas.P / 1e5,
        "Y": {name: float(value) for name, value in zip(gas.species_names, gas.Y) if value > 0.0},
        "X": {name: float(value) for name, value in zip(gas.species_names, gas.X) if value > 0.0},
    }


def _normalise(values: Mapping[str, float]) -> dict[str, float]:
    total = sum(float(value) for value in values.values())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("composition must have a finite positive total")
    return {name: float(value) / total for name, value in values.items() if float(value) > 0.0}


def _mixture_metrics(gas: ct.Solution, c: RigConfig, profile) -> dict[str, float]:
    tracked_fuel_species = resolve_fuel_profile(c).fuel_species
    fuel_mass = sum(
        gas.Y[gas.species_index(name)] for name in tracked_fuel_species
        if name in gas.species_names
    )
    oxygen_mass = gas.Y[gas.species_index("O2")] if "O2" in gas.species_names else 0.0
    # The configured fresh stream supplies the reference tracked-fuel/O2
    # ratio.  This is explicitly a proxy diagnostic, not an elemental
    # equivalence ratio: products in the residual stream can contain fuel
    # fragments and oxygen-bearing species with different stoichiometry.
    _p, _m, fresh = _new_gas(c)
    fresh_fuel = sum(
        fresh.Y[fresh.species_index(name)] for name in tracked_fuel_species
        if name in fresh.species_names
    )
    fresh_oxygen = fresh.Y[fresh.species_index("O2")] if "O2" in fresh.species_names else 0.0
    fresh_ratio = fresh_fuel / max(fresh_oxygen, 1e-30)
    effective_phi = (fuel_mass / max(oxygen_mass, 1e-30)) / max(fresh_ratio, 1e-30)
    return {
        "tracked_fuel_to_O2_ratio_relative_to_fresh": effective_phi,
        "tracked_fuel_mass_fraction": fuel_mass,
        "O2_mass_fraction": oxygen_mass,
    }


def mix_fresh_and_residual(
    c: RigConfig,
    residual_state: Mapping[str, Any],
    residual_fraction: float,
    mixing_basis: str = "mass",
) -> dict[str, Any]:
    """Construct one intake state from fresh charge and prior-cycle residual.

    ``residual_fraction`` is the fraction of the *total intake charge* on the
    selected basis.  Both streams are normalized before mixing.  The residual
    stream is pressure-normalized to the configured intake pressure, while its
    composition and end temperature are retained.  The final temperature is
    obtained by setting the mixed gas enthalpy at intake pressure, so no heat
    release or guessed frozen exhaust vector is inserted by this adapter.
    """
    if not 0.0 <= residual_fraction < 1.0:
        raise ValueError("residual_fraction must satisfy 0 <= f_res < 1")
    if mixing_basis not in {"mass", "mole"}:
        raise ValueError("mixing_basis must be 'mass' or 'mole'")
    profile, mechanism, fresh = _new_gas(c)
    # Preserve Cantera's mechanism order when constructing the mixed mapping.
    # Iterating a set here made process hash randomization perturb floating
    # summation/order in the stiff map and broke reproducibility.
    species_names = tuple(fresh.species_names)
    species_set = set(species_names)
    if not isinstance(residual_state, Mapping):
        raise TypeError("residual_state must be a mapping")
    key = "Y" if mixing_basis == "mass" else "X"
    if key not in residual_state:
        raise ValueError(f"residual_state must contain {key} for {mixing_basis} mixing")
    residual_composition = residual_state[key]
    if not isinstance(residual_composition, Mapping):
        raise TypeError("residual composition must be a species mapping")
    unknown = sorted(set(residual_composition) - species_set)
    if unknown:
        raise ValueError("residual species absent from mechanism: " + ", ".join(unknown))
    residual_temperature = float(residual_state.get("T_K", c.intake_temperature_K))
    if not math.isfinite(residual_temperature) or residual_temperature <= 0.0:
        raise ValueError("residual T_K must be positive and finite")
    intake_pressure = c.intake_pressure_bar * 1e5
    residual = ct.Solution(mechanism, profile.phase) if profile.phase else ct.Solution(mechanism)
    if mixing_basis == "mass":
        fresh_values = {name: float(value) for name, value in zip(fresh.species_names, fresh.Y)}
        residual.TPY = residual_temperature, intake_pressure, dict(residual_composition)
        residual_values = {name: float(value) for name, value in zip(residual.species_names, residual.Y)}
        mixed = _normalise({
            name: (1.0 - residual_fraction) * fresh_values.get(name, 0.0)
            + residual_fraction * residual_values.get(name, 0.0)
            for name in species_names
        })
        mixed_gas = ct.Solution(mechanism, profile.phase) if profile.phase else ct.Solution(mechanism)
        mixed_gas.TPY = c.intake_temperature_K, intake_pressure, mixed
        mixed_h = ((1.0 - residual_fraction) * fresh.enthalpy_mass
                   + residual_fraction * residual.enthalpy_mass)
        mixed_gas.HP = mixed_h, intake_pressure
        output_key = "Y"
    else:
        fresh_values = {name: float(value) for name, value in zip(fresh.species_names, fresh.X)}
        residual.TPX = residual_temperature, intake_pressure, dict(residual_composition)
        residual_values = {name: float(value) for name, value in zip(residual.species_names, residual.X)}
        mixed = _normalise({
            name: (1.0 - residual_fraction) * fresh_values.get(name, 0.0)
            + residual_fraction * residual_values.get(name, 0.0)
            for name in species_names
        })
        mixed_gas = ct.Solution(mechanism, profile.phase) if profile.phase else ct.Solution(mechanism)
        mixed_gas.TPX = c.intake_temperature_K, intake_pressure, mixed
        mixed_h_mole = ((1.0 - residual_fraction) * fresh.enthalpy_mole
                        + residual_fraction * residual.enthalpy_mole)
        # HP expects mass-specific enthalpy; convert the mole-basis stream
        # mixture using the mixed state's molecular weight.
        mixed_gas.HP = mixed_h_mole / mixed_gas.mean_molecular_weight, intake_pressure
        output_key = "X"
    return {
        "source": "fresh-plus-prior-cycle-end-residual",
        "basis": mixing_basis,
        "residual_fraction": residual_fraction,
        "T_K": mixed_gas.T,
        "P_bar": mixed_gas.P / 1e5,
        output_key: {
            name: float(value)
            for name, value in zip(mixed_gas.species_names, getattr(mixed_gas, output_key))
            if value > 0.0
        },
        **_mixture_metrics(mixed_gas, c, profile),
    }


def _validate_options(options: ResidualOptions) -> None:
    if options.mixing_basis not in {"mass", "mole"}:
        raise ValueError("mixing_basis must be 'mass' or 'mole'")
    if not options.residual_fractions:
        raise ValueError("at least one residual fraction is required")
    if any(not 0.0 < value < 1.0 for value in options.residual_fractions):
        raise ValueError("residual fractions must satisfy 0 < f_res < 1")
    if not 1 <= options.max_iterations <= 100:
        raise ValueError("max_iterations must be between 1 and 100")
    if options.composition_tolerance <= 0.0 or options.temperature_tolerance_K <= 0.0:
        raise ValueError("convergence tolerances must be positive")


def run_residual_fixed_point(
    c: RigConfig,
    z: TwoZoneOptions | None = None,
    options: ResidualOptions = ResidualOptions(),
) -> dict[str, Any]:
    """Sweep residual fraction and iterate each composition map to a fixed point."""
    _validate_options(options)
    if c.step_deg > 0.125:
        raise ValueError("residual fixed-point runs require step_deg <= 0.125")
    if z is None:
        z = TwoZoneOptions(integrator_rtol=1.0e-9, integrator_atol=1.0e-15)
    fresh = _fresh_state(c)
    profile, mechanism, _ = _new_gas(c)
    mechanism_file = Path(mechanism)
    mechanism_sha256 = (
        hashlib.sha256(mechanism_file.read_bytes()).hexdigest()
        if mechanism_file.is_file() else None
    )
    rows: list[dict[str, Any]] = []
    for fraction in options.residual_fractions:
        # The loop state is the prior-cycle END state.  Only the cycle input
        # is mixed with fresh charge; otherwise feeding an already mixed input
        # back into the mixer would silently apply f_res twice.
        residual_end_state = fresh
        history: list[dict[str, Any]] = []
        converged = False
        final_summary: dict[str, Any] | None = None
        last_delta_comp = math.inf
        last_delta_t = math.inf
        for iteration in range(1, options.max_iterations + 1):
            mixed_state = mix_fresh_and_residual(
                c, residual_end_state, fraction, options.mixing_basis
            )
            _cycle_rows, summary = simulate_two_zone(
                c, z, initial_state={
                    ("Y" if options.mixing_basis == "mass" else "X"):
                        mixed_state["Y" if options.mixing_basis == "mass" else "X"],
                    "T_K": mixed_state["T_K"],
                    "P_bar": mixed_state["P_bar"],
                    "source": mixed_state["source"],
                }
            )
            end_state = summary["end_state"]
            next_state = mix_fresh_and_residual(
                c, end_state, fraction, options.mixing_basis
            )
            key = "Y" if options.mixing_basis == "mass" else "X"
            names = set(mixed_state[key]) | set(next_state[key])
            last_delta_comp = max(
                abs(mixed_state[key].get(name, 0.0) - next_state[key].get(name, 0.0))
                for name in names
            )
            last_delta_t = abs(float(mixed_state["T_K"]) - float(next_state["T_K"]))
            history.append({
                "iteration": iteration,
                "input_temperature_K": mixed_state["T_K"],
                "output_temperature_K": end_state["T_K"],
                "next_input_temperature_K": next_state["T_K"],
                "input_tracked_fuel_to_O2_ratio_relative_to_fresh": mixed_state[
                    "tracked_fuel_to_O2_ratio_relative_to_fresh"
                ],
                "input_tracked_fuel_mass_fraction": mixed_state["tracked_fuel_mass_fraction"],
                "input_O2_mass_fraction": mixed_state["O2_mass_fraction"],
                "max_composition_delta": last_delta_comp,
                "temperature_delta_K": last_delta_t,
                "branch": summary["branch"],
                "peak_temperature_K": summary["peak_temperature_K"],
                "gross_imep_bar": summary["gross_imep_bar"],
                "max_fuel_consumed_fraction": summary["max_fuel_consumed_fraction"],
                "max_pressure_rise_bar_per_deg": summary["max_pressure_rise_bar_per_deg"],
            })
            final_summary = summary
            residual_end_state = end_state
            if (last_delta_comp <= options.composition_tolerance
                    and last_delta_t <= options.temperature_tolerance_K):
                converged = True
                break
        if final_summary is None:
            raise RuntimeError("residual fixed-point loop produced no cycle")
        component_residuals = [
            abs(value) for key, value in final_summary.items()
            if key.endswith("_mass_balance_residual_mg")
        ]
        max_component_residual = max(component_residuals, default=0.0)
        gate_pass = (
            final_summary["max_interzone_pressure_difference_bar"] <= 0.10
            and final_summary["max_volume_closure_error_mm3"] <= 0.20
            and abs(final_summary["mass_balance_residual_mg"]) <= 1.0e-3
            and max_component_residual <= 1.0e-3
        )
        rows.append({
            "residual_fraction": fraction,
            "mixing_basis": options.mixing_basis,
            "converged": converged,
            "iterations": len(history),
            "final_max_composition_delta": last_delta_comp,
            "final_temperature_delta_K": last_delta_t,
            "branch": final_summary["branch"],
            "peak_temperature_K": final_summary["peak_temperature_K"],
            "gross_imep_bar": final_summary["gross_imep_bar"],
            "max_fuel_consumed_fraction": final_summary["max_fuel_consumed_fraction"],
            "max_pressure_rise_bar_per_deg": final_summary["max_pressure_rise_bar_per_deg"],
            "numerical_gate_status": "pass" if gate_pass else "fail",
            "mass_balance_residual_mg": final_summary["mass_balance_residual_mg"],
            "max_component_mass_balance_residual_mg": max_component_residual,
            "max_interzone_pressure_difference_bar": final_summary[
                "max_interzone_pressure_difference_bar"
            ],
            "max_volume_closure_error_mm3": final_summary["max_volume_closure_error_mm3"],
            "mass_retained_end_fraction": final_summary["mass_retained_end_fraction"],
            "final_input_tracked_fuel_to_O2_ratio_relative_to_fresh": history[-1][
                "input_tracked_fuel_to_O2_ratio_relative_to_fresh"
            ],
            "final_input_tracked_fuel_mass_fraction": history[-1]["input_tracked_fuel_mass_fraction"],
            "final_input_O2_mass_fraction": history[-1]["input_O2_mass_fraction"],
            "cycle_interval_deg": "-180 to +180 (one revolution)",
            "history": history,
        })
    return {
        "model": "residual-carry-over-fixed-point-adapter",
        "conditions": {
            "cantera_version": ct.__version__,
            "mechanism_repo_relative_path": profile.mechanism,
            "mechanism_sha256": mechanism_sha256,
            "fresh_charge_equivalence_ratio": c.equivalence_ratio,
            "fuel_conversion_denominator": (
                "total tracked fuel mass in each mixed initial charge (not fresh-only)"
            ),
            "intake_pressure_bar": c.intake_pressure_bar,
            "intake_temperature_K": c.intake_temperature_K,
            "mixing_basis": options.mixing_basis,
            "mixing_definition": (
                "f_res is the mass/mole fraction of total intake charge allocated "
                "to a prior-cycle-end stream; streams are normalized before mixing"
            ),
            "pressure_treatment": "both streams pressure-normalized to intake pressure before mixing",
            "enthalpy_treatment": "adiabatic stream mixing; mixed h at fixed intake pressure determines T",
            "cycle_interval_deg": "-180 to +180 (one revolution only)",
            "two_zone_options": asdict(z),
            "residual_options": asdict(options),
        },
        "rows": rows,
        "warning": (
            "This is a synthetic composition-map experiment around a closed one-revolution "
            "two-zone solver. It does not model valves, gas exchange, pumping, exhaust, "
            "friction, crank inertia, or a periodic 720-CAD engine. Convergence is only "
            "convergence of the stated intake residual operator."
        ),
    }


__all__ = ["ResidualOptions", "mix_fresh_and_residual", "run_residual_fixed_point"]


def main() -> None:
    """Run the bounded OP_IDLE nominal endpoint bracket."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fractions", default="0.05,0.30")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--output", default="results/residual_fixed_point_anchor.json")
    args = parser.parse_args()
    config = RigConfig(
        bore_mm=8.5, stroke_mm=7.0, compression_ratio=7.75, rpm=1200.0,
        fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
        fuel_primary_mole_fraction=0.25, equivalence_ratio=0.40,
        intake_pressure_bar=3.0, intake_temperature_K=300.0,
        wall_mode="fixed", wall_temperature_K=560.0,
        effective_h_W_m2K=300.0, blowby_mode="annular",
        annular_radial_clearance_um=3.0, annular_skirt_length_mm=8.0,
        annular_eccentricity_ratio=0.5, step_deg=0.125,
    )
    zone = TwoZoneOptions(
        boundary_mass_fraction=0.20, mixing_model="diffusion-strain",
        mixing_time_ms=10.0, interzone_heat_transfer_coeff_W_m2K=100.0,
        pressure_equalization_coeff_m_s_Pa=7.0e-5,
        integrator_rtol=1.0e-9, integrator_atol=1.0e-15,
    )
    options = ResidualOptions(
        residual_fractions=tuple(float(value) for value in args.fractions.split(",")),
        max_iterations=args.max_iterations,
    )
    report = run_residual_fixed_point(config, zone, options)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": args.output,
        "rows": [
            {key: value for key, value in row.items() if key != "history"}
            for row in report["rows"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
