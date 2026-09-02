"""Small compressible valve/orifice and pumping-work helper.

The helper is intentionally independent of the canonical reacting model.  It
provides a transparent boundary-condition screen for a future 720-CAD cycle:
an effective valve area, ideal-gas compressible flow, mass-through-valve
integrals, and pressure-volume pumping work.

Angle convention
----------------
Angles are crank degrees in one four-stroke cycle, ``0 <= theta < 720``.
Firing TDC is 0/720; expansion runs 0--180, exhaust 180--360, intake
360--540, and compression 540--720.  Valve timing is supplied explicitly,
so no cam timing is hidden in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ValveFlowConfig:
    """Effective-area model for one valve event [area in mm2]."""

    opening_deg: float
    closing_deg: float
    peak_area_mm2: float
    discharge_coefficient: float = 0.70
    gamma: float = 1.35
    gas_constant_J_kgK: float = 287.05

    def __post_init__(self) -> None:
        if self.closing_deg <= self.opening_deg:
            raise ValueError("closing_deg must exceed opening_deg")
        if self.peak_area_mm2 <= 0.0:
            raise ValueError("peak_area_mm2 must be positive")
        if not 0.0 < self.discharge_coefficient <= 1.0:
            raise ValueError("discharge_coefficient must be in (0, 1]")
        if self.gamma <= 1.0 or self.gas_constant_J_kgK <= 0.0:
            raise ValueError("gamma must exceed 1 and gas constant must be positive")


def effective_area_mm2(theta_deg: float, config: ValveFlowConfig) -> float:
    """Return a smooth half-sine effective area within the event [mm2]."""
    if theta_deg < config.opening_deg or theta_deg > config.closing_deg:
        return 0.0
    fraction = (theta_deg - config.opening_deg) / (config.closing_deg - config.opening_deg)
    if fraction <= 0.0 or fraction >= 1.0:
        return 0.0
    return config.peak_area_mm2 * math.sin(math.pi * fraction)


def _one_way_mdot(
    p_up_Pa: float,
    t_up_K: float,
    p_down_Pa: float,
    area_m2: float,
    discharge_coefficient: float,
    gamma: float,
    gas_constant_J_kgK: float,
) -> tuple[float, bool]:
    """Positive upstream-to-downstream mass flow and choking flag."""
    if area_m2 <= 0.0 or p_up_Pa <= p_down_Pa:
        return 0.0, False
    if min(p_up_Pa, t_up_K, discharge_coefficient) <= 0.0:
        raise ValueError("pressures, temperature, and Cd must be positive")
    ratio = max(0.0, min(1.0, p_down_Pa / p_up_Pa))
    critical = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    prefactor = discharge_coefficient * area_m2 * p_up_Pa / math.sqrt(
        gas_constant_J_kgK * t_up_K
    )
    if ratio <= critical:
        factor = math.sqrt(gamma) * (2.0 / (gamma + 1.0)) ** (
            (gamma + 1.0) / (2.0 * (gamma - 1.0))
        )
        return prefactor * factor, True
    factor = 2.0 * gamma / (gamma - 1.0)
    factor *= ratio ** (2.0 / gamma) - ratio ** ((gamma + 1.0) / gamma)
    return prefactor * math.sqrt(max(0.0, factor)), False


def signed_valve_mdot(
    p_cylinder_Pa: float,
    t_cylinder_K: float,
    p_port_Pa: float,
    t_port_K: float,
    area_mm2: float,
    discharge_coefficient: float = 0.70,
    gamma: float = 1.35,
    gas_constant_J_kgK: float = 287.05,
) -> tuple[float, bool]:
    """Return signed flow [kg/s], positive from cylinder to port.

    Temperature is taken from the upstream side, as required by the ideal-gas
    compressible-orifice expression.  The function supports reverse flow and
    returns a choking flag for the active direction.
    """
    if area_mm2 < 0.0:
        raise ValueError("area_mm2 must be non-negative")
    if min(p_cylinder_Pa, p_port_Pa, t_cylinder_K, t_port_K) <= 0.0:
        raise ValueError("pressures and temperatures must be positive")
    if p_cylinder_Pa >= p_port_Pa:
        return _one_way_mdot(
            p_cylinder_Pa, t_cylinder_K, p_port_Pa, area_mm2 * 1e-6,
            discharge_coefficient, gamma, gas_constant_J_kgK,
        )
    value, choked = _one_way_mdot(
        p_port_Pa, t_port_K, p_cylinder_Pa, area_mm2 * 1e-6,
        discharge_coefficient, gamma, gas_constant_J_kgK,
    )
    return -value, choked


def integrate_valve_history(
    theta_deg: list[float] | tuple[float, ...],
    cylinder_pressure_bar_abs: list[float] | tuple[float, ...],
    cylinder_temperature_K: list[float] | tuple[float, ...],
    port_pressure_bar_abs: float,
    port_temperature_K: float,
    valve: ValveFlowConfig,
    rpm: float,
) -> dict[str, float | list[float]]:
    """Integrate one event's valve mass flow over a crank-angle history.

    The returned ``mass_to_port_kg`` is signed.  ``flow_work_J`` is the
    enthalpy transport proxy ``integral(mdot * cp * (T_up-T_port) dt)`` and is
    not the engine pumping work.  Use :func:`pumping_work_from_pv` for the
    latter.
    """
    if rpm <= 0.0:
        raise ValueError("rpm must be positive")
    if not (len(theta_deg) == len(cylinder_pressure_bar_abs) == len(cylinder_temperature_K)):
        raise ValueError("history arrays must have equal lengths")
    if len(theta_deg) < 2:
        raise ValueError("history must contain at least two points")
    omega = rpm * 2.0 * math.pi / 60.0
    cp = valve.gamma * valve.gas_constant_J_kgK / (valve.gamma - 1.0)
    mdot_values: list[float] = []
    choked_count = 0
    mass_to_port = 0.0
    flow_work = 0.0
    for index, angle in enumerate(theta_deg):
        if index:
            dtheta = float(theta_deg[index] - theta_deg[index - 1])
            if dtheta <= 0.0:
                raise ValueError("theta_deg must be strictly increasing")
        area = effective_area_mm2(float(angle), valve)
        mdot, choked = signed_valve_mdot(
            float(cylinder_pressure_bar_abs[index]) * 1e5,
            float(cylinder_temperature_K[index]),
            port_pressure_bar_abs * 1e5,
            port_temperature_K,
            area,
            valve.discharge_coefficient,
            valve.gamma,
            valve.gas_constant_J_kgK,
        )
        mdot_values.append(mdot)
        choked_count += int(choked and area > 0.0)
        if index:
            dt = math.radians(dtheta) / omega
            mdot_mid = 0.5 * (mdot_values[index - 1] + mdot)
            t_up_mid = 0.5 * (
                float(cylinder_temperature_K[index - 1]) + float(cylinder_temperature_K[index])
            ) if mdot_mid >= 0.0 else port_temperature_K
            mass_to_port += mdot_mid * dt
            flow_work += mdot_mid * cp * (t_up_mid - port_temperature_K) * dt
    return {
        "mass_to_port_kg": mass_to_port,
        "flow_work_J": flow_work,
        "peak_abs_mdot_kg_s": max(abs(value) for value in mdot_values),
        "choked_fraction_of_active_samples": choked_count / max(1, sum(
            effective_area_mm2(float(angle), valve) > 0.0 for angle in theta_deg
        )),
        "theta_deg": list(theta_deg),
        "mdot_kg_s": mdot_values,
    }


def pumping_work_from_pv(
    volume_m3: list[float] | tuple[float, ...],
    pressure_bar_abs: list[float] | tuple[float, ...],
    displacement_m3: float,
    reference_pressure_bar_abs: float = 1.0,
) -> dict[str, float]:
    """Return closed-loop pressure-volume pumping work and PMEP.

    Work is ``integral((p - p_ref) dV)`` over the supplied 720-CAD path,
    positive when gas does work on the piston.  For a complete intake/exhaust
    loop, pumping loss is therefore usually negative.  ``pumping_mep_bar`` is
    the signed work divided by displacement; retain the sign rather than
    silently converting it into a loss magnitude.
    """
    if len(volume_m3) != len(pressure_bar_abs) or len(volume_m3) < 2:
        raise ValueError("volume and pressure histories must have equal length >= 2")
    if displacement_m3 <= 0.0:
        raise ValueError("displacement_m3 must be positive")
    work = 0.0
    for i in range(1, len(volume_m3)):
        p0 = (float(pressure_bar_abs[i - 1]) - reference_pressure_bar_abs) * 1e5
        p1 = (float(pressure_bar_abs[i]) - reference_pressure_bar_abs) * 1e5
        work += 0.5 * (p0 + p1) * (float(volume_m3[i]) - float(volume_m3[i - 1]))
    return {
        "pumping_work_J_per_cycle": work,
        "pumping_mep_bar": work / displacement_m3 / 1e5,
        "pumping_loss_magnitude_bar": max(0.0, -work / displacement_m3 / 1e5),
    }
