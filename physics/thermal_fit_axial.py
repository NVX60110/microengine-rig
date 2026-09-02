"""Bounded axial piston/liner thermal-fit feasibility screen.

The repository RC model resolves a piston crown/skirt and liner TDC/lower
pair, not a measured one-dimensional field.  This module is deliberately a
small bridge: it interpolates those resolved temperatures at axial stations,
applies explicit *screening* taper/barrel envelopes, and evaluates the signed
hot radial clearance with :func:`physics.thermal_clearance.calculate_clearance`.

No ABC taper value, contact pressure, oil-film thickness, or ringless heat-path
coefficient is inferred here.  A zero or negative local gap is contact and is
never passed to an annulus-flow calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from physics.thermal_clearance import CTE, annulus_leakage_from_clearance, calculate_clearance, integrated_strain


@dataclass(frozen=True)
class AxialStation:
    """A corresponding piston/liner axial station, measured from crown/TDC."""

    z_mm: float
    label: str

    def __post_init__(self) -> None:
        if not (math.isfinite(self.z_mm) and self.z_mm >= 0.0):
            raise ValueError("axial station z_mm must be finite and nonnegative")
        if not self.label:
            raise ValueError("axial station label must not be empty")


DEFAULT_STATIONS = (
    AxialStation(0.0, "crown"),
    AxialStation(2.0, "upper_piston"),
    AxialStation(4.0, "ringland_or_mid_skirt"),
    AxialStation(6.0, "lower_skirt"),
    AxialStation(8.0, "skirt_end"),
)


@dataclass(frozen=True)
class AxialFitConfig:
    """Geometry and fit assumptions for the axial screen.

    ``liner_taper_um`` is a zero-mean clearance-shape amplitude: positive
    makes the top of the liner more open and the skirt end tighter.  The
    ``piston_taper_um`` term has the opposite convention (positive makes the
    piston larger toward the skirt and therefore tightens that end).  The
    barrel term is zero at both ends and largest at mid-length.  These are
    bounded hypothetical manufacturing envelopes, not ABC measurements.
    """

    bore_diameter_mm: float = 8.5
    axial_length_mm: float = 8.0
    cold_radial_clearance_um: float = 10.0
    liner_taper_um: float = 0.0
    piston_taper_um: float = 0.0
    piston_barrel_um: float = 0.0
    machining_error_um: float = 0.0
    contact_margin_um: float = 1.0

    def __post_init__(self) -> None:
        for name in ("bore_diameter_mm", "axial_length_mm", "cold_radial_clearance_um", "contact_margin_um"):
            value = float(getattr(self, name))
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.bore_diameter_mm <= 0 or self.axial_length_mm <= 0:
            raise ValueError("bore and axial length must be positive")
        if self.cold_radial_clearance_um < 0:
            raise ValueError("cold radial clearance must be nonnegative")
        if self.contact_margin_um < 0:
            raise ValueError("contact margin must be nonnegative")


def _shape_coordinate(station: AxialStation, length_mm: float) -> float:
    return min(1.0, max(0.0, station.z_mm / length_mm))


def local_cold_clearance_um(station: AxialStation, config: AxialFitConfig) -> float:
    """Return local radial cold gap after explicit taper/barrel/error terms."""
    x = _shape_coordinate(station, config.axial_length_mm)
    # Linear zero-mean liner taper: +A at crown, -A at skirt end.
    liner_term = config.liner_taper_um * (1.0 - 2.0 * x)
    # Piston taper grows toward the skirt and consumes clearance there.
    piston_taper_term = -config.piston_taper_um * (2.0 * x - 1.0)
    # A positive barrel amplitude means a larger piston at mid-length.
    barrel_term = -config.piston_barrel_um * 4.0 * x * (1.0 - x)
    return config.cold_radial_clearance_um + liner_term + piston_taper_term + barrel_term + config.machining_error_um


def _linear_temperature(z_mm: float, length_mm: float, top_K: float, bottom_K: float) -> float:
    x = min(1.0, max(0.0, z_mm / length_mm))
    return float(top_K) + x * (float(bottom_K) - float(top_K))


def _signed_hot_clearance_um(
    *,
    bore_diameter_mm: float,
    cold_radial_clearance_um: float,
    piston_reference_temperature_K: float,
    liner_reference_temperature_K: float,
    hot_piston_temperature_K: float,
    hot_liner_temperature_K: float,
    piston_cte: CTE,
    liner_cte: CTE,
) -> float:
    """Evaluate the linear-strain equation while allowing cold interference.

    ``calculate_clearance`` intentionally rejects negative *input* clearance
    for its normal hardware-fit API.  Axial envelope studies must still be
    able to represent a cold pinch, so the same closed-form equation is
    evaluated directly for that screening case.
    """
    if cold_radial_clearance_um >= 0.0:
        return calculate_clearance(
            bore_diameter_mm=bore_diameter_mm,
            cold_radial_clearance_um=cold_radial_clearance_um,
            piston_reference_temperature_K=piston_reference_temperature_K,
            liner_reference_temperature_K=liner_reference_temperature_K,
            hot_piston_temperature_K=hot_piston_temperature_K,
            hot_liner_temperature_K=hot_liner_temperature_K,
            piston_cte_per_K=piston_cte,
            liner_cte_per_K=liner_cte,
        ).hot_radial_clearance_um
    piston_strain = integrated_strain(piston_reference_temperature_K, hot_piston_temperature_K, piston_cte)
    liner_strain = integrated_strain(liner_reference_temperature_K, hot_liner_temperature_K, liner_cte)
    return (1.0 + piston_strain) * cold_radial_clearance_um + 0.5 * bore_diameter_mm * (liner_strain - piston_strain) * 1000.0


def evaluate_axial_fit(
    *,
    config: AxialFitConfig,
    piston_top_temperature_K: float,
    piston_bottom_temperature_K: float,
    liner_top_temperature_K: float,
    liner_bottom_temperature_K: float,
    piston_cte: CTE,
    liner_cte: CTE,
    stations: Sequence[AxialStation] = DEFAULT_STATIONS,
    piston_reference_temperature_K: float = 293.15,
    liner_reference_temperature_K: float = 293.15,
) -> dict[str, Any]:
    """Evaluate signed hot clearance at corresponding axial stations."""
    values = (piston_top_temperature_K, piston_bottom_temperature_K, liner_top_temperature_K, liner_bottom_temperature_K)
    if not all(math.isfinite(float(value)) and float(value) > 0 for value in values):
        raise ValueError("axial temperatures must be finite positive Kelvin values")
    rows: list[dict[str, Any]] = []
    for station in stations:
        piston_temperature = _linear_temperature(station.z_mm, config.axial_length_mm, piston_top_temperature_K, piston_bottom_temperature_K)
        liner_temperature = _linear_temperature(station.z_mm, config.axial_length_mm, liner_top_temperature_K, liner_bottom_temperature_K)
        cold = local_cold_clearance_um(station, config)
        hot = _signed_hot_clearance_um(
            bore_diameter_mm=config.bore_diameter_mm,
            cold_radial_clearance_um=cold,
            piston_reference_temperature_K=piston_reference_temperature_K,
            liner_reference_temperature_K=liner_reference_temperature_K,
            hot_piston_temperature_K=piston_temperature,
            hot_liner_temperature_K=liner_temperature,
            piston_cte=piston_cte,
            liner_cte=liner_cte,
        )
        rows.append({
            "z_mm": station.z_mm,
            "label": station.label,
            "piston_temperature_K": piston_temperature,
            "liner_temperature_K": liner_temperature,
            "cold_radial_clearance_um": cold,
            "cold_interference": cold < 0.0,
            "hot_radial_clearance_um": hot,
            "interference": hot <= 0.0,
            "below_contact_margin": hot < config.contact_margin_um,
        })
    hot_values = [row["hot_radial_clearance_um"] for row in rows]
    min_row = min(rows, key=lambda row: row["hot_radial_clearance_um"])
    return {
        "stations": rows,
        "min_hot_clearance_um": min(hot_values),
        "max_hot_clearance_um": max(hot_values),
        "min_station_label": min_row["label"],
        "contact": any(value <= 0.0 for value in hot_values),
        "contact_margin_um": config.contact_margin_um,
        "below_contact_margin": any(value < config.contact_margin_um for value in hot_values),
        "geometry_assumption": "screening taper/barrel/error envelope; no ABC dimensional measurement",
    }


def evaluate_temperature_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    config: AxialFitConfig,
    piston_cte: CTE,
    liner_cte: CTE,
    stations: Sequence[AxialStation] = DEFAULT_STATIONS,
    piston_reference_temperature_K: float = 293.15,
    liner_reference_temperature_K: float = 293.15,
) -> dict[str, Any]:
    """Evaluate a crank-angle or warm-up sequence and retain path extrema."""
    profiles = []
    for row_index, row in enumerate(rows):
        profile = evaluate_axial_fit(
            config=config,
            piston_top_temperature_K=float(row["piston_crown_temperature_K"]),
            piston_bottom_temperature_K=float(row["piston_skirt_temperature_K"]),
            liner_top_temperature_K=float(row["liner_tdc_temperature_K"]),
            liner_bottom_temperature_K=float(row["liner_lower_temperature_K"]),
            piston_cte=piston_cte,
            liner_cte=liner_cte,
            stations=stations,
            piston_reference_temperature_K=piston_reference_temperature_K,
            liner_reference_temperature_K=liner_reference_temperature_K,
        )
        # Preserve the forcing state that produced this clearance profile so
        # downstream leakage cannot accidentally pair it with BDC row zero.
        profile["source_row_index"] = row_index
        for key in ("deg", "pressure_bar", "gas_temperature_K"):
            if key in row:
                profile[f"source_{key}"] = row[key]
        profiles.append(profile)
    if not profiles:
        raise ValueError("at least one temperature row is required")
    min_profile = min(profiles, key=lambda profile: profile["min_hot_clearance_um"])
    return {
        "profiles": profiles,
        "min_hot_clearance_um": min(profile["min_hot_clearance_um"] for profile in profiles),
        "max_hot_clearance_um": max(profile["max_hot_clearance_um"] for profile in profiles),
        "contact": any(profile["contact"] for profile in profiles),
        "below_contact_margin": any(profile["below_contact_margin"] for profile in profiles),
        "worst_profile": min_profile,
    }


def required_base_fit_bounds_um(
    rows: Sequence[Mapping[str, Any]],
    *,
    config: AxialFitConfig,
    piston_cte: CTE,
    liner_cte: CTE,
    hot_target_um: tuple[float, float] = (2.0, 5.0),
    stations: Sequence[AxialStation] = DEFAULT_STATIONS,
    piston_reference_temperature_K: float = 293.15,
    liner_reference_temperature_K: float = 293.15,
) -> dict[str, Any]:
    """Intersect allowable *base* cold fits over all axial/time samples.

    The shape terms are held fixed while the scalar base clearance is solved.
    This keeps taper/barrel effects visible and preserves the radial convention
    of the existing inversion.  Bounds may be negative mathematically; that
    denotes a requested cold interference and is not promoted as a fit.
    """
    low_hot, high_hot = map(float, hot_target_um)
    if low_hot > high_hot:
        raise ValueError("hot target bounds must be ordered")
    lowers: list[float] = []
    uppers: list[float] = []
    for row in rows:
        piston_top = float(row["piston_crown_temperature_K"])
        piston_bottom = float(row["piston_skirt_temperature_K"])
        liner_top = float(row["liner_tdc_temperature_K"])
        liner_bottom = float(row["liner_lower_temperature_K"])
        for station in stations:
            x = _shape_coordinate(station, config.axial_length_mm)
            shape = (
                config.liner_taper_um * (1.0 - 2.0 * x)
                - config.piston_taper_um * (2.0 * x - 1.0)
                - config.piston_barrel_um * 4.0 * x * (1.0 - x)
                + config.machining_error_um
            )
            piston_temperature = _linear_temperature(station.z_mm, config.axial_length_mm, piston_top, piston_bottom)
            liner_temperature = _linear_temperature(station.z_mm, config.axial_length_mm, liner_top, liner_bottom)
            # Use the existing analytical inversion rather than duplicating
            # its temperature-dependent denominator here.
            from physics.thermal_clearance import cold_clearance_for_hot_target_um
            low_local = cold_clearance_for_hot_target_um(
                bore_diameter_mm=config.bore_diameter_mm,
                target_hot_clearance_um=low_hot,
                piston_reference_temperature_K=piston_reference_temperature_K,
                liner_reference_temperature_K=liner_reference_temperature_K,
                hot_piston_temperature_K=piston_temperature,
                hot_liner_temperature_K=liner_temperature,
                piston_cte_per_K=piston_cte,
                liner_cte_per_K=liner_cte,
            )
            high_local = cold_clearance_for_hot_target_um(
                bore_diameter_mm=config.bore_diameter_mm,
                target_hot_clearance_um=high_hot,
                piston_reference_temperature_K=piston_reference_temperature_K,
                liner_reference_temperature_K=liner_reference_temperature_K,
                hot_piston_temperature_K=piston_temperature,
                hot_liner_temperature_K=liner_temperature,
                piston_cte_per_K=piston_cte,
                liner_cte_per_K=liner_cte,
            )
            lowers.append(low_local - shape)
            uppers.append(high_local - shape)
    lower, upper = max(lowers), min(uppers)
    return {
        "lower_bound_um": lower,
        "upper_bound_um": upper,
        "feasible": lower <= upper,
        "nonnegative_cold_fit_feasible": max(0.0, lower) <= upper,
        "lower_bound_is_negative_interference_target": lower < 0.0,
        "hot_target_um": [low_hot, high_hot],
        "constraint_count": len(lowers),
    }


def nonuniform_annulus_leakage(
    station_rows: Sequence[Mapping[str, Any]],
    *,
    pressure_up_bar: float,
    pressure_down_bar: float = 1.0,
    temperature_K: float = 1100.0,
    viscosity_Pa_s: float = 4.0e-5,
    bore_diameter_mm: float = 8.5,
    skirt_length_mm: float = 8.0,
    eccentricity: float = 0.0,
) -> dict[str, Any]:
    """Estimate series-path leakage using the positive-clearance stations.

    For a laminar annulus bracket, conductance scales approximately as
    ``c**3``.  Equal axial segments therefore combine as
    ``1/c_eq**3 = mean(1/c_i**3)``.  This is a sensitivity closure, not a
    calibrated flow model.  Any zero/negative station is reported as contact
    and invalidates the annulus path; no fictitious zero flow is returned.
    """
    gaps = [float(row["hot_radial_clearance_um"]) for row in station_rows]
    if not gaps:
        raise ValueError("station_rows cannot be empty")
    if any(not math.isfinite(gap) for gap in gaps):
        raise ValueError("clearance values must be finite")
    if any(gap <= 0.0 for gap in gaps):
        return {
            "leakage_status": "contact_invalid_annulus",
            "mass_flow_kg_s": None,
            "equivalent_cda_mm2": None,
            "minimum_hot_clearance_um": min(gaps),
            "equivalent_clearance_um": None,
            "positive_station_count": sum(gap > 0.0 for gap in gaps),
        }
    equivalent = (sum(gap ** -3 for gap in gaps) / len(gaps)) ** (-1.0 / 3.0)
    result = annulus_leakage_from_clearance(
        equivalent,
        pressure_up_bar=pressure_up_bar,
        pressure_down_bar=pressure_down_bar,
        temperature_K=temperature_K,
        viscosity_Pa_s=viscosity_Pa_s,
        bore_diameter_mm=bore_diameter_mm,
        skirt_length_mm=skirt_length_mm,
        eccentricity=eccentricity,
    )
    return {
        **result,
        "minimum_hot_clearance_um": min(gaps),
        "equivalent_clearance_um": equivalent,
        "positive_station_count": len(gaps),
        "closure": "series axial resistance; annulus conductance proportional to clearance cubed",
    }


def minimum_preheat_temperature_K(
    *,
    config: AxialFitConfig,
    piston_offset_K: float = 0.0,
    liner_offset_K: float = 0.0,
    piston_cte: CTE,
    liner_cte: CTE,
    stations: Sequence[AxialStation] = DEFAULT_STATIONS,
    lower_bound_K: float = 293.15,
    upper_bound_K: float = 700.0,
    required_margin_um: float | None = None,
    piston_reference_temperature_K: float = 293.15,
    liner_reference_temperature_K: float = 293.15,
) -> dict[str, Any]:
    """Return a bounded conditional uniform-preheat safe interval.

    The offsets represent the unknown local piston/liner temperature split.
    With equal offsets this is only a thermal-expansion check, not a start
    permission or lubrication guarantee. A bounded grid distinguishes
    ``minimum_safe``, ``maximum_safe``, ``bounded_interval``, ``always`` and
    ``never``; common heating is not assumed to help monotonically.
    """
    margin = config.contact_margin_um if required_margin_um is None else float(required_margin_um)
    if margin < 0 or upper_bound_K < lower_bound_K:
        raise ValueError("invalid preheat bounds or required margin")

    def safe(base_K: float) -> bool:
        profile = evaluate_axial_fit(
            config=config,
            piston_top_temperature_K=base_K + piston_offset_K,
            piston_bottom_temperature_K=base_K + piston_offset_K,
            liner_top_temperature_K=base_K + liner_offset_K,
            liner_bottom_temperature_K=base_K + liner_offset_K,
            piston_cte=piston_cte,
            liner_cte=liner_cte,
            stations=stations,
            piston_reference_temperature_K=piston_reference_temperature_K,
            liner_reference_temperature_K=liner_reference_temperature_K,
        )
        return profile["min_hot_clearance_um"] >= margin

    # Without measured local heat paths there is no basis for claiming
    # monotonicity or a sharper threshold, so retain the bounded grid itself.
    samples = 161
    step = (upper_bound_K - lower_bound_K) / (samples - 1)
    temperatures = [lower_bound_K + step * i for i in range(samples)]
    safe_flags = [safe(temperature) for temperature in temperatures]
    intervals: list[list[float]] = []
    start: float | None = None
    for temperature, is_safe in zip(temperatures, safe_flags):
        if is_safe and start is None:
            start = temperature
        elif not is_safe and start is not None:
            intervals.append([start, temperature - step])
            start = None
    if start is not None:
        intervals.append([start, upper_bound_K])
    if not intervals:
        kind, threshold = "never", None
    elif len(intervals) == 1 and intervals[0][0] <= lower_bound_K and intervals[0][1] >= upper_bound_K:
        kind, threshold = "always", lower_bound_K
    elif len(intervals) == 1 and intervals[0][0] <= lower_bound_K:
        kind, threshold = "maximum_safe", intervals[0][1]
    elif len(intervals) == 1 and intervals[0][1] >= upper_bound_K:
        kind, threshold = "minimum_safe", intervals[0][0]
    else:
        kind, threshold = "bounded_interval", intervals[0][0]
    return {
        "threshold_type": kind,
        "threshold_K": threshold,
        "safe_intervals_K": intervals,
        "required_margin_um": margin,
        "temperature_bounds_K": [lower_bound_K, upper_bound_K],
        "piston_offset_K": float(piston_offset_K),
        "liner_offset_K": float(liner_offset_K),
        "interpretation": "conditional CTE-only clearance screen; not a safe-cranking permission",
    }
