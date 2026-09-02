"""Analytical piston/liner thermal-clearance model.

The input clearance is *radial* while the supplied bore and piston dimensions
are diameters.  For a reference bore diameter ``Db`` and radial clearance
``c`` the reference piston diameter is ``Dp = Db - 2*c``.  Applying linear
thermal strain to both diameters gives

    c_hot = 0.5 * (Db * (1 + eps_l) - Dp * (1 + eps_p))

where ``eps`` is the integrated linear strain from the material reference
temperature to the requested hot temperature.  The factor one-half is the
only radius conversion; it is deliberately kept explicit to avoid the common
factor-of-two error.

Negative hot clearance is retained as a negative number and marked as
interference.  No contact-pressure, elastic flattening, taper, oil-film, or
temperature-gradient correction is hidden in this model.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Sequence


@dataclass(frozen=True)
class ThermalStrainProfile:
    """Piecewise-linear cumulative strain profile.

    ``points`` are ``(temperature_K, strain)`` pairs.  Endpoint slopes are
    extended linearly outside the tabulated range and the result records that
    extrapolation is the caller's responsibility.  This representation lets
    handbook mean-CTE values be converted to cumulative strain without
    pretending they are instantaneous coefficients.
    """

    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("a strain profile needs at least two points")
        previous = -math.inf
        for temperature, strain in self.points:
            if not (math.isfinite(temperature) and math.isfinite(strain)):
                raise ValueError("profile points must be finite")
            if temperature <= previous:
                raise ValueError("profile temperatures must be strictly increasing")
            previous = temperature

    def strain_at(self, temperature_K: float) -> float:
        temperature_K = float(temperature_K)
        points = self.points
        if temperature_K <= points[0][0]:
            left, right = points[0], points[1]
        elif temperature_K >= points[-1][0]:
            left, right = points[-2], points[-1]
        else:
            for left, right in zip(points, points[1:]):
                if left[0] <= temperature_K <= right[0]:
                    break
        slope = (right[1] - left[1]) / (right[0] - left[0])
        return left[1] + slope * (temperature_K - left[0])

    def effective_cte_per_K(self, reference_temperature_K: float, hot_temperature_K: float) -> float:
        delta = hot_temperature_K - reference_temperature_K
        if delta == 0:
            return 0.0
        return (self.strain_at(hot_temperature_K) - self.strain_at(reference_temperature_K)) / delta


CTE = float | ThermalStrainProfile | Sequence[tuple[float, float]]


def integrated_strain(
    reference_temperature_K: float,
    hot_temperature_K: float,
    cte_per_K: CTE,
) -> float:
    """Return dimensionless linear strain between two temperatures.

    A scalar CTE is treated as constant.  A :class:`ThermalStrainProfile` or
    sequence of points is interpreted as cumulative strain versus temperature.
    """
    if not (math.isfinite(reference_temperature_K) and math.isfinite(hot_temperature_K)):
        raise ValueError("temperatures must be finite")
    if isinstance(cte_per_K, Real):
        alpha = float(cte_per_K)
        if not math.isfinite(alpha):
            raise ValueError("CTE must be finite")
        return alpha * (hot_temperature_K - reference_temperature_K)
    profile = cte_per_K if isinstance(cte_per_K, ThermalStrainProfile) else ThermalStrainProfile(tuple(cte_per_K))
    return profile.strain_at(hot_temperature_K) - profile.strain_at(reference_temperature_K)


@dataclass(frozen=True)
class ThermalClearanceResult:
    bore_diameter_mm: float
    piston_reference_diameter_mm: float
    cold_radial_clearance_um: float
    piston_reference_temperature_K: float
    liner_reference_temperature_K: float
    hot_piston_temperature_K: float
    hot_liner_temperature_K: float
    piston_cte_per_K: float
    liner_cte_per_K: float
    piston_diameter_growth_um: float
    liner_bore_growth_um: float
    hot_piston_diameter_mm: float
    hot_liner_bore_mm: float
    hot_radial_clearance_um: float
    clearance_change_um: float
    interference: bool

    @property
    def interference_flag(self) -> bool:
        """Alias used by JSON/CSV consumers."""
        return self.interference


def calculate_clearance(
    *,
    bore_diameter_mm: float,
    cold_radial_clearance_um: float,
    piston_reference_temperature_K: float,
    liner_reference_temperature_K: float,
    hot_piston_temperature_K: float,
    hot_liner_temperature_K: float,
    piston_cte_per_K: CTE,
    liner_cte_per_K: CTE,
) -> ThermalClearanceResult:
    """Calculate hot radial clearance from separate piston and liner states."""
    values = (
        bore_diameter_mm,
        cold_radial_clearance_um,
        piston_reference_temperature_K,
        liner_reference_temperature_K,
        hot_piston_temperature_K,
        hot_liner_temperature_K,
    )
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("dimensions and temperatures must be finite")
    if bore_diameter_mm <= 0:
        raise ValueError("bore diameter must be positive")
    if cold_radial_clearance_um < 0:
        raise ValueError("cold radial clearance must be nonnegative")
    if any(value <= 0 for value in (
        piston_reference_temperature_K,
        liner_reference_temperature_K,
        hot_piston_temperature_K,
        hot_liner_temperature_K,
    )):
        raise ValueError("temperatures must be positive Kelvin values")

    piston_reference_diameter_mm = bore_diameter_mm - 2.0 * cold_radial_clearance_um * 1e-3
    if piston_reference_diameter_mm <= 0:
        raise ValueError("cold clearance is larger than the bore")

    piston_strain = integrated_strain(
        piston_reference_temperature_K, hot_piston_temperature_K, piston_cte_per_K
    )
    liner_strain = integrated_strain(
        liner_reference_temperature_K, hot_liner_temperature_K, liner_cte_per_K
    )
    piston_growth_mm = piston_reference_diameter_mm * piston_strain
    liner_growth_mm = bore_diameter_mm * liner_strain
    hot_piston_mm = piston_reference_diameter_mm + piston_growth_mm
    hot_liner_mm = bore_diameter_mm + liner_growth_mm
    hot_clearance_um = 0.5 * (hot_liner_mm - hot_piston_mm) * 1000.0
    clearance_change_um = hot_clearance_um - cold_radial_clearance_um

    piston_effective_cte = piston_strain / (hot_piston_temperature_K - piston_reference_temperature_K) if hot_piston_temperature_K != piston_reference_temperature_K else 0.0
    liner_effective_cte = liner_strain / (hot_liner_temperature_K - liner_reference_temperature_K) if hot_liner_temperature_K != liner_reference_temperature_K else 0.0
    return ThermalClearanceResult(
        bore_diameter_mm=bore_diameter_mm,
        piston_reference_diameter_mm=piston_reference_diameter_mm,
        cold_radial_clearance_um=cold_radial_clearance_um,
        piston_reference_temperature_K=piston_reference_temperature_K,
        liner_reference_temperature_K=liner_reference_temperature_K,
        hot_piston_temperature_K=hot_piston_temperature_K,
        hot_liner_temperature_K=hot_liner_temperature_K,
        piston_cte_per_K=piston_effective_cte,
        liner_cte_per_K=liner_effective_cte,
        piston_diameter_growth_um=piston_growth_mm * 1000.0,
        liner_bore_growth_um=liner_growth_mm * 1000.0,
        hot_piston_diameter_mm=hot_piston_mm,
        hot_liner_bore_mm=hot_liner_mm,
        hot_radial_clearance_um=hot_clearance_um,
        clearance_change_um=clearance_change_um,
        interference=hot_clearance_um < 0.0,
    )


def cold_clearance_for_hot_target_um(
    *,
    bore_diameter_mm: float,
    target_hot_clearance_um: float,
    piston_reference_temperature_K: float,
    liner_reference_temperature_K: float,
    hot_piston_temperature_K: float,
    hot_liner_temperature_K: float,
    piston_cte_per_K: CTE,
    liner_cte_per_K: CTE,
) -> float:
    """Solve the cold radial clearance required for a target hot clearance.

    The result is analytical for the linear-strain model and is allowed to be
    negative: a negative answer means the target hot fit would require a cold
    interference fit under the stated temperatures/materials.
    """
    piston_strain = integrated_strain(
        piston_reference_temperature_K, hot_piston_temperature_K, piston_cte_per_K
    )
    liner_strain = integrated_strain(
        liner_reference_temperature_K, hot_liner_temperature_K, liner_cte_per_K
    )
    denominator = 1.0 + piston_strain
    if denominator <= 0:
        raise ValueError("piston thermal strain makes the linear model singular")
    target_mm = target_hot_clearance_um * 1e-3
    cold_mm = (
        target_mm - 0.5 * bore_diameter_mm * (liner_strain - piston_strain)
    ) / denominator
    return cold_mm * 1000.0


def annulus_leakage_from_clearance(
    hot_radial_clearance_um: float,
    *,
    pressure_up_bar: float,
    pressure_down_bar: float = 1.0,
    temperature_K: float = 1100.0,
    viscosity_Pa_s: float = 4.0e-5,
    bore_diameter_mm: float = 8.5,
    skirt_length_mm: float = 8.0,
    eccentricity: float = 0.0,
) -> dict[str, float | str | None]:
    """Feed positive hot clearance into the existing annular leakage model.

    Interference is not clamped to zero and is not converted to a fictitious
    leak.  The returned flow/area fields are ``None`` with status
    ``"interference_invalid_annulus"`` in that case.
    """
    if hot_radial_clearance_um < 0:
        return {
            "leakage_status": "interference_invalid_annulus",
            "mass_flow_kg_s": None,
            "equivalent_cda_mm2": None,
        }
    from physics.annulus import annulus_mdot, equiv_area

    mdot = annulus_mdot(
        bore_diameter_mm,
        hot_radial_clearance_um,
        skirt_length_mm,
        pressure_up_bar,
        pressure_down_bar,
        T=temperature_K,
        mu=viscosity_Pa_s,
        eccentricity=eccentricity,
    )
    return {
        "leakage_status": "annulus_positive_clearance",
        "mass_flow_kg_s": mdot,
        "equivalent_cda_mm2": equiv_area(mdot, pressure_up_bar, temperature_K),
    }
