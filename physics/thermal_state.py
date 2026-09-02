"""Small lumped piston/liner thermal state model.

This module is intentionally an inspectable RC network rather than pseudo-FEA.
It consumes a crank-angle history from :mod:`microengine_rig` (or a compatible
CSV), advances seven physical solid nodes through one modeled 360-degree pass,
and carries the solid temperatures through repeated warm-up cycles.  The
repository's existing model has no angle-resolved heat-flux correlation, so the
``constant_h`` closure is the baseline and ``angle_correlation`` is explicitly
an engineering sensitivity closure, not a validated Woschni implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from microengine_rig import RigConfig, build_geometry
from physics.thermal_clearance import CTE, calculate_clearance, cold_clearance_for_hot_target_um


@dataclass(frozen=True)
class HistoryPoint:
    """One gas-state sample in a 360-degree crank-angle history."""

    deg: float
    pressure_bar: float
    gas_temperature_K: float
    piston_velocity_m_s: float
    dt_s: float


@dataclass(frozen=True)
class ThermalNode:
    """Lumped solid node with heat capacity and optional external sink."""

    name: str
    mass_kg: float
    cp_J_kgK: float
    initial_temperature_K: float = 300.0
    external_temperature_K: float = 300.0
    external_conductance_W_K: float = 0.0

    @property
    def capacity_J_K(self) -> float:
        return self.mass_kg * self.cp_J_kgK


@dataclass(frozen=True)
class ConductiveLink:
    """Bidirectional solid-to-solid thermal conductance."""

    node_a: str
    node_b: str
    conductance_W_K: float


@dataclass(frozen=True)
class ThermalRCConfig:
    bore_mm: float = 8.5
    stroke_mm: float = 7.0
    compression_ratio: float = 7.75
    rod_stroke_ratio: float = 1.6
    rpm: float = 1200.0
    piston_material: str = "al_4032_t6"
    liner_material: str = "steel_4140"
    piston_reference_temperature_K: float = 293.15
    liner_reference_temperature_K: float = 293.15
    h_ref_W_m2K: float = 600.0
    h_model: str = "constant_h"
    # Reference conductivities let the material screen affect conduction as
    # well as CTE.  The link geometry is still a bracket; these values are
    # not a finite-element extraction.
    piston_conductivity_W_mK: float | None = None
    liner_conductivity_W_mK: float | None = None
    reference_piston_conductivity_W_mK: float = 154.0
    reference_liner_conductivity_W_mK: float = 42.6
    pressure_ref_bar: float = 10.0
    gas_temperature_ref_K: float = 700.0
    velocity_ref_m_s: float = 0.28
    h_min_multiplier: float = 0.25
    h_max_multiplier: float = 4.0
    # The conventional skirt is not a combustion-chamber surface.  Keep this
    # field only as an explicit compatibility knob; the default is zero and
    # gas-sidewall area is assigned to liner bands instead.
    piston_skirt_area_fraction: float = 0.0
    liner_tdc_area_fraction: float = 0.425
    ambient_temperature_K: float = 300.0
    block_ambient_conductance_W_K: float = 0.15
    idle_duration_s: float = 0.05
    max_warmup_cycles: int = 120
    min_warmup_cycles: int = 10
    convergence_tolerance_K: float = 0.01
    solve_periodic_fixed_point: bool = True


_SCREENING_CONDUCTIVITY_W_MK = {
    "al_4032_t6": 154.0,
    "al_2618_t61": 147.0,
    "al_6061_t6": 167.0,
    "steel_4140": 42.6,
    "gray_iron_gjl250": 48.5,
    "si3n4_sn201b": 25.0,
}


def _selected_conductivity(material: str, explicit: float | None, reference: float) -> float:
    value = _SCREENING_CONDUCTIVITY_W_MK.get(material, reference) if explicit is None else explicit
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("material conductivity must be finite and positive")
    return value


def default_nodes(config: ThermalRCConfig) -> tuple[ThermalNode, ...]:
    """Return seven physical nodes with explicit engineering capacities.

    Masses and heat capacities are screening assumptions, not a CAD mass
    extraction.  They are deliberately exposed here so a later weighed part
    or material data sheet can replace them without changing the solver.
    """
    if config.piston_material.startswith("al_"):
        piston_cp = 900.0
    elif config.piston_material.startswith("si3n4"):
        piston_cp = 700.0
    else:
        piston_cp = 500.0
    if config.liner_material.startswith("al_"):
        liner_cp = 900.0
    elif config.liner_material.startswith("si3n4"):
        liner_cp = 700.0
    elif config.liner_material.startswith("gray_iron"):
        liner_cp = 460.0
    else:
        liner_cp = 500.0
    if config.block_ambient_conductance_W_K < 0:
        raise ValueError("block ambient conductance must be nonnegative")
    return (
        ThermalNode("piston_crown", 0.00045, piston_cp),
        ThermalNode("piston_skirt", 0.00080, piston_cp),
        ThermalNode("rod_crank", 0.00070, 500.0),
        ThermalNode("liner_tdc", 0.00040, liner_cp),
        ThermalNode("liner_lower", 0.00080, liner_cp),
        ThermalNode("head_deck", 0.00100, 500.0),
        ThermalNode(
            "block", 0.00200, 850.0,
            external_temperature_K=config.ambient_temperature_K,
            external_conductance_W_K=config.block_ambient_conductance_W_K,
        ),
    )


def default_links(config: ThermalRCConfig | None = None) -> tuple[ConductiveLink, ...]:
    """Return transparent solid conduction brackets in W/K.

    The base conductances are engineering geometry brackets.  When a config
    is supplied, piston and liner links scale linearly with the selected
    material conductivity relative to the Al-4032/4140 reference pair.  This
    is a screening representation of ``k A/L``; it is not a CAD/FEM result.
    """
    config = config or ThermalRCConfig()
    piston_k = _selected_conductivity(config.piston_material, config.piston_conductivity_W_mK, config.reference_piston_conductivity_W_mK)
    liner_k = _selected_conductivity(config.liner_material, config.liner_conductivity_W_mK, config.reference_liner_conductivity_W_mK)
    piston_scale = piston_k / config.reference_piston_conductivity_W_mK
    liner_scale = liner_k / config.reference_liner_conductivity_W_mK
    return (
        ConductiveLink("piston_crown", "piston_skirt", 0.75 * piston_scale),
        ConductiveLink("piston_skirt", "rod_crank", 0.25 * piston_scale),
        ConductiveLink("rod_crank", "block", 0.10),
        ConductiveLink("liner_tdc", "liner_lower", 0.60 * liner_scale),
        ConductiveLink("liner_lower", "block", 1.20 * liner_scale),
        ConductiveLink("head_deck", "block", 1.00),
    )


def _finite(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def load_history_csv(path: Path, rpm: float = 1200.0) -> list[HistoryPoint]:
    """Read `microengine_rig` rows or a compatible portable CSV.

    Required columns are `deg`, `P_bar`, and `T_K`.  `pistonVelocity_m_s` is
    optional and defaults to zero.  Sampling is converted to seconds using
    the supplied rpm; this keeps history files portable across OSes.
    """
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    if len(rows) < 2:
        raise ValueError("thermal history needs at least two rows")
    parsed = []
    omega = 2.0 * math.pi * float(rpm) / 60.0
    for row in rows:
        deg = float(row.get("deg", row.get("crank_angle_deg", "nan")))
        pressure = float(row.get("P_bar", row.get("pressure_bar", "nan")))
        temperature = float(row.get("T_K", row.get("gas_temperature_K", "nan")))
        velocity = float(row.get("pistonVelocity_m_s", row.get("piston_velocity_m_s", 0.0)))
        parsed.append((deg, pressure, temperature, velocity))
    parsed.sort(key=lambda item: item[0])
    result: list[HistoryPoint] = []
    for index, (deg, pressure, temperature, velocity) in enumerate(parsed):
        if index == 0:
            next_deg = parsed[1][0]
        elif index == len(parsed) - 1:
            next_deg = parsed[index][0]
        else:
            next_deg = parsed[index + 1][0]
        dt_s = max(0.0, math.radians(next_deg - deg) / omega)
        result.append(HistoryPoint(deg, pressure, temperature, velocity, dt_s))
    result[-1] = HistoryPoint(result[-1].deg, result[-1].pressure_bar, result[-1].gas_temperature_K, result[-1].piston_velocity_m_s, 0.0)
    if result[-1].deg - result[0].deg < 300.0:
        raise ValueError("thermal history must span approximately one crank revolution")
    return result


def history_from_rows(rows: Sequence[Mapping[str, Any]], rpm: float = 1200.0) -> list[HistoryPoint]:
    """Convert in-memory engine-model rows using the same rules as CSV input."""
    omega = 2.0 * math.pi * float(rpm) / 60.0
    ordered = sorted(rows, key=lambda row: float(row["deg"]))
    result = []
    for index, row in enumerate(ordered):
        deg = float(row["deg"])
        next_deg = float(ordered[index + 1]["deg"]) if index + 1 < len(ordered) else deg
        result.append(HistoryPoint(
            deg=deg,
            pressure_bar=float(row["P_bar"]),
            gas_temperature_K=float(row["T_K"]),
            piston_velocity_m_s=float(row.get("pistonVelocity_m_s", 0.0)),
            dt_s=max(0.0, math.radians(next_deg - deg) / omega),
        ))
    if len(result) < 2:
        raise ValueError("thermal history needs at least two rows")
    return result


def gas_areas_m2(config: ThermalRCConfig, deg: float) -> dict[str, float]:
    """Partition gas-facing area without heating the conventional skirt.

    Combustion gas directly sees the crown, head/deck and cylinder wall.  The
    skirt temperature therefore comes from crown/body conduction, rod paths and
    any explicitly supplied external sink.  The sidewall split is between the
    TDC liner band and lower liner only; no area is silently assigned to the
    piston skirt.
    """
    rig = RigConfig(
        bore_mm=config.bore_mm,
        stroke_mm=config.stroke_mm,
        compression_ratio=config.compression_ratio,
        rod_stroke_ratio=config.rod_stroke_ratio,
        rpm=config.rpm,
        ignition_mode="off",
    )
    geometry = build_geometry(rig)
    theta = math.radians(deg)
    piston_area = geometry.piston_area_m2
    side_area = math.pi * (config.bore_mm / 1000.0) * (
        geometry.clearance_height_m + geometry.piston_position(theta)
    )
    liner_tdc = config.liner_tdc_area_fraction * side_area
    liner_lower = max(0.0, side_area - liner_tdc)
    return {
        "piston_crown": piston_area,
        "piston_skirt": 0.0,
        "liner_tdc": liner_tdc,
        "liner_lower": liner_lower,
        "head_deck": piston_area,
    }


def heat_transfer_coeff_W_m2K(point: HistoryPoint, config: ThermalRCConfig) -> float:
    """Return baseline or labeled angle-dependent gas-side coefficient."""
    if config.h_model == "constant_h":
        return config.h_ref_W_m2K
    if config.h_model != "angle_correlation":
        raise ValueError("h_model must be constant_h or angle_correlation")
    # Woschni-shaped sensitivity only: pressure, inverse temperature, and a
    # piston-speed proxy.  No claim is made that this is a validated miniature
    # engine correlation; the clip prevents an unbounded proxy from dominating.
    pressure_factor = max(0.05, point.pressure_bar / config.pressure_ref_bar) ** 0.8
    temperature_factor = max(0.1, config.gas_temperature_ref_K / max(point.gas_temperature_K, 1.0)) ** 0.53
    velocity_factor = max(0.10, abs(point.piston_velocity_m_s)) / max(config.velocity_ref_m_s, 1e-9)
    velocity_factor = velocity_factor ** 0.8
    multiplier = pressure_factor * temperature_factor * velocity_factor
    multiplier = min(config.h_max_multiplier, max(config.h_min_multiplier, multiplier))
    return config.h_ref_W_m2K * multiplier


def _advance_network(
    temperatures: list[float],
    dt_s: float,
    point: HistoryPoint | None,
    config: ThermalRCConfig,
    nodes: Sequence[ThermalNode],
    links: Sequence[ConductiveLink],
    area_lookup: Mapping[float, Mapping[str, float]] | None = None,
) -> tuple[list[float], dict[str, float], dict[str, float]]:
    if dt_s <= 0:
        zeros = {node.name: 0.0 for node in nodes}
        return list(temperatures), zeros, dict(zeros)
    names = {node.name: index for index, node in enumerate(nodes)}
    rates = [0.0] * len(nodes)
    gas_rates = {node.name: 0.0 for node in nodes}
    external_rates = {node.name: 0.0 for node in nodes}
    if point is not None:
        areas = area_lookup[point.deg] if area_lookup is not None else gas_areas_m2(config, point.deg)
        h = heat_transfer_coeff_W_m2K(point, config)
        for node_name, area in areas.items():
            index = names[node_name]
            q = h * area * (point.gas_temperature_K - temperatures[index])
            rates[index] += q
            gas_rates[node_name] += q
    for index, node in enumerate(nodes):
        if node.external_conductance_W_K > 0:
            q = node.external_conductance_W_K * (node.external_temperature_K - temperatures[index])
            rates[index] += q
            external_rates[node.name] += q
    for link in links:
        ia, ib = names[link.node_a], names[link.node_b]
        q = link.conductance_W_K * (temperatures[ib] - temperatures[ia])
        rates[ia] += q
        rates[ib] -= q
    updated = [temperature + dt_s * rate / node.capacity_J_K for temperature, rate, node in zip(temperatures, rates, nodes)]
    if any(not math.isfinite(value) or value < 0.0 for value in updated):
        raise ValueError("thermal RC produced a negative temperature")
    return updated, gas_rates, external_rates


def _advance_idle(
    temperatures: list[float],
    duration_s: float,
    config: ThermalRCConfig,
    nodes: Sequence[ThermalNode],
    links: Sequence[ConductiveLink],
    area_lookup: Mapping[float, Mapping[str, float]] | None = None,
) -> list[float]:
    if duration_s <= 0:
        return list(temperatures)
    # Subdivide the idle interval so the explicit RC update remains well below
    # the smallest plausible solid time constant.
    steps = max(1, math.ceil(duration_s / 0.001))
    dt = duration_s / steps
    result = list(temperatures)
    for _ in range(steps):
        result, _, _ = _advance_network(result, dt, None, config, nodes, links, area_lookup)
    return result


def _advance_cycle(
    temperatures: Sequence[float],
    history: Sequence[HistoryPoint],
    config: ThermalRCConfig,
    nodes: Sequence[ThermalNode],
    links: Sequence[ConductiveLink],
    area_lookup: Mapping[float, Mapping[str, float]],
) -> tuple[list[float], float, float]:
    """Advance one modeled pass plus idle segment and collect energy terms."""
    result = list(temperatures)
    gas_energy_J = 0.0
    external_energy_J = 0.0
    for point in history:
        result, gas_rates, external_rates = _advance_network(result, point.dt_s, point, config, nodes, links, area_lookup)
        gas_energy_J += sum(gas_rates.values()) * point.dt_s
        external_energy_J += sum(external_rates.values()) * point.dt_s
    if config.idle_duration_s > 0:
        steps = max(1, math.ceil(config.idle_duration_s / 0.001))
        dt = config.idle_duration_s / steps
        for _ in range(steps):
            result, gas_rates, external_rates = _advance_network(result, dt, None, config, nodes, links, area_lookup)
            gas_energy_J += sum(gas_rates.values()) * dt
            external_energy_J += sum(external_rates.values()) * dt
    return result, gas_energy_J, external_energy_J


def _solve_linear_system(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    """Solve a small dense system with pivoted Gaussian elimination."""
    n = len(vector)
    augmented = [list(map(float, row)) + [float(vector[i])] for i, row in enumerate(matrix)]
    for pivot in range(n):
        row = max(range(pivot, n), key=lambda index: abs(augmented[index][pivot]))
        if abs(augmented[row][pivot]) < 1e-14:
            raise ValueError("periodic RC map is singular")
        augmented[pivot], augmented[row] = augmented[row], augmented[pivot]
        scale = augmented[pivot][pivot]
        augmented[pivot] = [value / scale for value in augmented[pivot]]
        for index in range(n):
            if index == pivot:
                continue
            factor = augmented[index][pivot]
            if factor:
                augmented[index] = [left - factor * right for left, right in zip(augmented[index], augmented[pivot])]
    return [augmented[index][-1] for index in range(n)]


def _periodic_fixed_point(
    history: Sequence[HistoryPoint],
    config: ThermalRCConfig,
    nodes: Sequence[ThermalNode],
    links: Sequence[ConductiveLink],
    area_lookup: Mapping[float, Mapping[str, float]],
) -> tuple[list[float], dict[str, float]]:
    """Solve T_end=A*T_start+b for the periodic starting state."""
    n = len(nodes)
    zero_end, _, _ = _advance_cycle([0.0] * n, history, config, nodes, links, area_lookup)
    columns: list[list[float]] = []
    for column in range(n):
        basis = [0.0] * n
        basis[column] = 1.0
        end, _, _ = _advance_cycle(basis, history, config, nodes, links, area_lookup)
        columns.append([end[row] - zero_end[row] for row in range(n)])
    # Columns above are A's columns.  Solve (I-A)T*=b.
    matrix = [[(1.0 if row == col else 0.0) - columns[col][row] for col in range(n)] for row in range(n)]
    start = _solve_linear_system(matrix, zero_end)
    end, gas_energy_J, external_energy_J = _advance_cycle(start, history, config, nodes, links, area_lookup)
    residual = max(abs(after - before) for after, before in zip(end, start))
    scale = max(1.0, abs(gas_energy_J))
    return start, {
        "periodic_residual_K": residual,
        "cycle_gas_energy_J": gas_energy_J,
        "cycle_external_energy_J": external_energy_J,
        "cycle_energy_balance_residual_J": gas_energy_J + external_energy_J,
        "cycle_energy_balance_relative": abs(gas_energy_J + external_energy_J) / scale,
    }


def _clearance_snapshot(
    config: ThermalRCConfig,
    pair_temperatures: Mapping[str, tuple[float, float]],
    piston_cte: CTE,
    liner_cte: CTE,
    cold_clearances_um: Iterable[float],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for cold_um in cold_clearances_um:
        label = str(float(cold_um)).replace(".", "p")
        clearances: dict[str, float] = {}
        for pair_name, (piston_temperature_K, liner_temperature_K) in pair_temperatures.items():
            clearance = calculate_clearance(
                bore_diameter_mm=config.bore_mm,
                cold_radial_clearance_um=float(cold_um),
                piston_reference_temperature_K=config.piston_reference_temperature_K,
                liner_reference_temperature_K=config.liner_reference_temperature_K,
                hot_piston_temperature_K=piston_temperature_K,
                hot_liner_temperature_K=liner_temperature_K,
                piston_cte_per_K=piston_cte,
                liner_cte_per_K=liner_cte,
            )
            clearances[pair_name] = clearance.hot_radial_clearance_um
            result[f"hot_clearance_{pair_name}_{label}_um"] = clearance.hot_radial_clearance_um
            result[f"interference_{pair_name}_{label}"] = clearance.interference
        # Preserve the historical skirt/TDC key while making the local pairs
        # and the minimum path gap explicit for cross-geometry consumers.
        legacy = clearances["skirt_liner_tdc"]
        result[f"hot_clearance_{label}_um"] = legacy
        result[f"interference_{label}"] = legacy < 0.0
        result[f"hot_clearance_min_path_{label}_um"] = min(clearances.values())
        result[f"interference_min_path_{label}"] = min(clearances.values()) < 0.0
    return result


def run_thermal_rc(
    history: Sequence[HistoryPoint],
    config: ThermalRCConfig,
    *,
    piston_cte: CTE,
    liner_cte: CTE,
    nodes: Sequence[ThermalNode] | None = None,
    links: Sequence[ConductiveLink] | None = None,
    cold_clearances_um: Sequence[float] = (3.0, 8.0, 12.0, 16.0),
) -> dict[str, Any]:
    """Run warm-up, solve the periodic fixed point, and return fit bounds."""
    if len(history) < 2:
        raise ValueError("history needs at least two points")
    nodes = tuple(nodes or default_nodes(config))
    links = tuple(links or default_links(config))
    area_lookup = {point.deg: gas_areas_m2(config, point.deg) for point in history}
    if len({node.name for node in nodes}) != len(nodes):
        raise ValueError("thermal node names must be unique")
    if any(node.capacity_J_K <= 0 for node in nodes):
        raise ValueError("thermal node capacities must be positive")
    temperatures = [node.initial_temperature_K for node in nodes]
    cycle_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    node_index = {node.name: index for index, node in enumerate(nodes)}
    required_nodes = {"piston_crown", "piston_skirt", "rod_crank", "liner_tdc", "liner_lower", "head_deck", "block"}
    missing = required_nodes - set(node_index)
    if missing:
        raise ValueError(f"thermal nodes missing required names: {sorted(missing)}")
    piston_index = node_index["piston_skirt"]
    liner_index = node_index["liner_tdc"]
    periodic_start: list[float] | None = None
    periodic_info: dict[str, Any] = {
        "periodic_fixed_point_requested": bool(config.solve_periodic_fixed_point),
        "periodic_fixed_point_solved": False,
    }
    if config.solve_periodic_fixed_point:
        try:
            periodic_start, fixed_info = _periodic_fixed_point(history, config, nodes, links, area_lookup)
            periodic_info.update(fixed_info)
            periodic_info["periodic_fixed_point_solved"] = True
        except ValueError as error:
            # A network with no external sink and no forcing has no unique
            # periodic solution.  Keep the warm-up result and expose why the
            # analytic solve was unavailable instead of hiding the failure.
            periodic_info["periodic_solver_error"] = str(error)

    warmup_converged = False
    for cycle in range(1, config.max_warmup_cycles + 1):
        cycle_start = list(temperatures)
        temperatures, gas_energy_J, external_energy_J = _advance_cycle(temperatures, history, config, nodes, links, area_lookup)
        delta_K = max(abs(after - before) for after, before in zip(temperatures, cycle_start))
        warmup_pair_temperatures = {
            "crown_liner_tdc": (temperatures[node_index["piston_crown"]], temperatures[node_index["liner_tdc"]]),
            "skirt_liner_tdc": (temperatures[node_index["piston_skirt"]], temperatures[node_index["liner_tdc"]]),
            "skirt_liner_lower": (temperatures[node_index["piston_skirt"]], temperatures[node_index["liner_lower"]]),
        }
        warmup_fit = _clearance_snapshot(config, warmup_pair_temperatures, piston_cte, liner_cte, (3.0,))
        cycle_rows.append({
            "cycle": cycle,
            "max_temperature_K": max(temperatures),
            "min_temperature_K": min(temperatures),
            "piston_skirt_end_K": temperatures[piston_index],
            "liner_tdc_end_K": temperatures[liner_index],
            "cycle_max_delta_K": delta_K,
            "gas_energy_J": gas_energy_J,
            "external_energy_J": external_energy_J,
            "cycle_energy_balance_residual_J": gas_energy_J + external_energy_J,
            "min_path_hot_clearance_3um": warmup_fit["hot_clearance_min_path_3p0_um"],
            "skirt_liner_tdc_hot_clearance_3um": warmup_fit["hot_clearance_skirt_liner_tdc_3p0_um"],
        })
        if cycle >= config.min_warmup_cycles and delta_K <= config.convergence_tolerance_K:
            warmup_converged = True
            break
    if not cycle_rows:
        raise RuntimeError("thermal RC produced no final-cycle rows")

    # Use the solved periodic start for the reported operating cycle.  The
    # warm-up trajectory remains in cycle_rows so startup and periodic states
    # cannot be conflated.
    final_cycle_start = periodic_start if periodic_start is not None else list(temperatures)
    final_cycle_end, final_gas_energy_J, final_external_energy_J = _advance_cycle(
        final_cycle_start, history, config, nodes, links, area_lookup
    )
    periodic_info.setdefault("periodic_residual_K", max(abs(after - before) for after, before in zip(final_cycle_end, final_cycle_start)))
    periodic_info.setdefault("cycle_gas_energy_J", final_gas_energy_J)
    periodic_info.setdefault("cycle_external_energy_J", final_external_energy_J)
    periodic_info.setdefault("cycle_energy_balance_residual_J", final_gas_energy_J + final_external_energy_J)
    periodic_info.setdefault("cycle_energy_balance_relative", abs(final_gas_energy_J + final_external_energy_J) / max(1.0, abs(final_gas_energy_J)))
    periodic_converged = bool(
        periodic_info.get("periodic_fixed_point_solved")
        and periodic_info.get("periodic_residual_K", math.inf) <= config.convergence_tolerance_K
        and periodic_info.get("cycle_energy_balance_relative", math.inf) <= 1e-8
    ) if periodic_info.get("periodic_fixed_point_solved") else warmup_converged

    # Capture the final periodic pass, pairing temperatures at corresponding
    # axial locations rather than silently using skirt-vs-TDC for every gap.
    capture_temperatures = list(final_cycle_start)
    for point in history:
        pair_temperatures = {
            "crown_liner_tdc": (capture_temperatures[node_index["piston_crown"]], capture_temperatures[node_index["liner_tdc"]]),
            "skirt_liner_tdc": (capture_temperatures[node_index["piston_skirt"]], capture_temperatures[node_index["liner_tdc"]]),
            "skirt_liner_lower": (capture_temperatures[node_index["piston_skirt"]], capture_temperatures[node_index["liner_lower"]]),
        }
        snapshot = {
            "cycle": "periodic_fixed_point" if periodic_start is not None else cycle_rows[-1]["cycle"],
            "deg": point.deg,
            "pressure_bar": point.pressure_bar,
            "gas_temperature_K": point.gas_temperature_K,
            "h_W_m2K": heat_transfer_coeff_W_m2K(point, config),
            "piston_crown_temperature_K": capture_temperatures[node_index["piston_crown"]],
            "piston_skirt_temperature_K": capture_temperatures[node_index["piston_skirt"]],
            "rod_crank_temperature_K": capture_temperatures[node_index["rod_crank"]],
            "liner_tdc_temperature_K": capture_temperatures[node_index["liner_tdc"]],
            "liner_lower_temperature_K": capture_temperatures[node_index["liner_lower"]],
            "head_deck_temperature_K": capture_temperatures[node_index["head_deck"]],
            "block_temperature_K": capture_temperatures[node_index["block"]],
        }
        snapshot.update(_clearance_snapshot(
            config,
            pair_temperatures,
            piston_cte,
            liner_cte,
            cold_clearances_um,
        ))
        final_rows.append(snapshot)
        capture_temperatures, _, _ = _advance_network(capture_temperatures, point.dt_s, point, config, nodes, links, area_lookup)

    # The required cold fit interval is the intersection of all instantaneous
    # inverse constraints: c_hot >= 2 µm and c_hot <= 5 µm.
    lower_bounds = []
    upper_bounds = []
    pair_keys = {
        "crown_liner_tdc": ("piston_crown_temperature_K", "liner_tdc_temperature_K"),
        "skirt_liner_tdc": ("piston_skirt_temperature_K", "liner_tdc_temperature_K"),
        "skirt_liner_lower": ("piston_skirt_temperature_K", "liner_lower_temperature_K"),
    }
    for row in final_rows:
        for piston_key, liner_key in pair_keys.values():
            lower_bounds.append(cold_clearance_for_hot_target_um(
                bore_diameter_mm=config.bore_mm,
                target_hot_clearance_um=2.0,
                piston_reference_temperature_K=config.piston_reference_temperature_K,
                liner_reference_temperature_K=config.liner_reference_temperature_K,
                hot_piston_temperature_K=row[piston_key],
                hot_liner_temperature_K=row[liner_key],
                piston_cte_per_K=piston_cte,
                liner_cte_per_K=liner_cte,
            ))
            upper_bounds.append(cold_clearance_for_hot_target_um(
                bore_diameter_mm=config.bore_mm,
                target_hot_clearance_um=5.0,
                piston_reference_temperature_K=config.piston_reference_temperature_K,
                liner_reference_temperature_K=config.liner_reference_temperature_K,
                hot_piston_temperature_K=row[piston_key],
                hot_liner_temperature_K=row[liner_key],
                piston_cte_per_K=piston_cte,
                liner_cte_per_K=liner_cte,
            ))
    inverse_lower = max(lower_bounds)
    inverse_upper = min(upper_bounds)
    fit_bounds = {
        "lower_bound_um": inverse_lower,
        "upper_bound_um": inverse_upper,
        "feasible": inverse_lower <= inverse_upper,
        "nonnegative_cold_fit_feasible": max(0.0, inverse_lower) <= inverse_upper,
        "lower_bound_is_negative_interference_target": inverse_lower < 0.0,
    }
    startup_pair_temperatures = {
        "crown_liner_tdc": (nodes[node_index["piston_crown"]].initial_temperature_K, nodes[node_index["liner_tdc"]].initial_temperature_K),
        "skirt_liner_tdc": (nodes[node_index["piston_skirt"]].initial_temperature_K, nodes[node_index["liner_tdc"]].initial_temperature_K),
        "skirt_liner_lower": (nodes[node_index["piston_skirt"]].initial_temperature_K, nodes[node_index["liner_lower"]].initial_temperature_K),
    }
    startup_fit = _clearance_snapshot(config, startup_pair_temperatures, piston_cte, liner_cte, (3.0,))
    return {
        "config": config,
        "nodes": nodes,
        "links": links,
        "history_rows": final_rows,
        "cycle_rows": cycle_rows,
        "converged": periodic_converged,
        "periodic_converged": periodic_converged,
        "warmup_converged": warmup_converged,
        "periodic_info": periodic_info,
        "cycles_completed": len(cycle_rows),
        "final_node_temperatures_K": {node.name: value for node, value in zip(nodes, final_cycle_end)},
        "periodic_start_node_temperatures_K": {node.name: value for node, value in zip(nodes, final_cycle_start)},
        "piston_crown_min_K": min(row["piston_crown_temperature_K"] for row in final_rows),
        "piston_crown_max_K": max(row["piston_crown_temperature_K"] for row in final_rows),
        "piston_skirt_min_K": min(row["piston_skirt_temperature_K"] for row in final_rows),
        "piston_skirt_max_K": max(row["piston_skirt_temperature_K"] for row in final_rows),
        "liner_tdc_min_K": min(row["liner_tdc_temperature_K"] for row in final_rows),
        "liner_tdc_max_K": max(row["liner_tdc_temperature_K"] for row in final_rows),
        "liner_lower_min_K": min(row["liner_lower_temperature_K"] for row in final_rows),
        "liner_lower_max_K": max(row["liner_lower_temperature_K"] for row in final_rows),
        "required_cold_clearance_for_hot_2_to_5_um": fit_bounds,
        "startup_clearance_3um": startup_fit,
        "warmup_min_path_hot_clearance_3um": min(row["min_path_hot_clearance_3um"] for row in cycle_rows),
        "warmup_max_path_hot_clearance_3um": max(row["min_path_hot_clearance_3um"] for row in cycle_rows),
        "periodic_min_path_hot_clearance_3um": min(row["hot_clearance_min_path_3p0_um"] for row in final_rows),
        "periodic_max_path_hot_clearance_3um": max(row["hot_clearance_min_path_3p0_um"] for row in final_rows),
        "model_classification": {
            "measured": "none",
            "literature_derived": "material CTE/conductivity inputs only",
            "calculated": "RC temperatures and thermal-clearance inversion",
            "assumed": "node masses/cp, conductances, gas-area partition, h closures and history use",
            "extrapolated": "warm-up trajectory and periodic state from repeated modeled closed-cycle history",
        },
    }
