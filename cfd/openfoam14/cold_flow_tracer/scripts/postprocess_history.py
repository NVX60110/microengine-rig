#!/usr/bin/env python3
"""Convert CFD scalar fields to transport histories.

The original CFD-01 core/shell diagnostic is preserved for flat-piston
regression.  Cross-geometry comparisons additionally use global tracer moments
so a changing squish-land volume cannot masquerade as a change in mixing.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import re


BORE_M = 0.0085
STROKE_M = 0.007
CR = 7.75
ROD_STROKE_RATIO = 1.6
RPM = 1200.0
WEDGE_DEG = 5.0
CORE_RADIUS_M = (BORE_M / 2.0) * math.sqrt(0.8)
AREA_M2 = math.pi * BORE_M**2 / 4.0
CLEARANCE_M3 = AREA_M2 * STROKE_M / (CR - 1.0)
ROD_M = ROD_STROKE_RATIO * STROKE_M
CRANK_M = STROKE_M / 2.0
WEDGE_SCALE = 360.0 / WEDGE_DEG
AIR_MOL_WEIGHT_KG_PER_KMOL = 28.965
R_UNIVERSAL_J_PER_KMOL_K = 8314.46261815324
R_AIR = R_UNIVERSAL_J_PER_KMOL_K / AIR_MOL_WEIGHT_KG_PER_KMOL
# CFD-01 was initialized as a nominal 20%-volume outer shell.  Use the same
# fraction as a mass-defined zone for cross-geometry comparisons; the flat
# finite-volume mesh realizes 0.1984 because of cell-centre/axis regularisation.
TARGET_SHELL_MASS_FRACTION = 0.20


def values(
    path: Path,
    vector: bool = False,
    expected_count: int | None = None,
) -> list[float] | list[tuple[float, float, float]]:
    """Read an OpenFOAM internal field, including uniform legacy fields."""
    text = path.read_text()
    match = re.search(
        r"internalField\s+nonuniform\s+List<[^>]+>\s+\d+\s*\(\s*(.*?)\s*\)\s*;",
        text,
        flags=re.S,
    )
    if match:
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        if vector:
            return [tuple(float(value) for value in line.strip("()").split()) for line in lines]
        return [float(line) for line in lines]

    uniform = re.search(r"internalField\s+uniform\s+([^;]+);", text)
    if not uniform:
        raise ValueError(f"Cannot parse internalField in {path}")
    if expected_count is None:
        raise ValueError(f"{path} is uniform but expected_count was not supplied")
    token = uniform.group(1).strip()
    if vector:
        item = tuple(float(value) for value in token.strip("()").split())
        if len(item) != 3:
            raise ValueError(f"Cannot parse uniform vector in {path}")
        return [item] * expected_count
    return [float(token)] * expected_count


def piston_position(theta: float) -> float:
    root = math.sqrt(ROD_M**2 - (STROKE_M / 2.0) ** 2 * math.sin(theta) ** 2)
    return (STROKE_M / 2.0) * (1.0 - math.cos(theta)) + ROD_M - root


def expected_volume(angle_deg: float) -> float:
    return CLEARANCE_M3 + AREA_M2 * piston_position(math.radians(angle_deg))


def times(case: Path) -> list[tuple[float, Path]]:
    result = []
    for path in case.iterdir():
        if not path.is_dir():
            continue
        try:
            angle = float(path.name)
        except ValueError:
            continue
        if (path / "tracer").exists() and (path / "Vc").exists() and (path / "C").exists():
            result.append((angle, path))
    return sorted(result)


def density(directory: Path, count: int) -> list[float]:
    """Use solver rho when available; otherwise derive perfect-gas rho from p,T."""
    rho_path = directory / "rho"
    if rho_path.exists():
        return list(values(rho_path, expected_count=count))
    p_path, t_path = directory / "p", directory / "T"
    if not p_path.exists() or not t_path.exists():
        raise ValueError(
            f"{directory} has neither rho nor both p/T; mass conservation cannot be evaluated"
        )
    pressure = list(values(p_path, expected_count=count))
    temperature = list(values(t_path, expected_count=count))
    result = []
    for p_value, t_value in zip(pressure, temperature):
        if t_value <= 0:
            raise ValueError(f"nonpositive temperature in {directory}")
        result.append(p_value / (R_AIR * t_value))
    return result


def _log_decay_rate(rows: list[dict[str, float]], index: int, key: str) -> float:
    """Centered local decay rate -d ln(quantity)/dt for a positive amplitude."""
    if index == 0 or index == len(rows) - 1:
        return float("nan")
    left, right = rows[index - 1], rows[index + 1]
    a, b = left[key], right[key]
    if not (math.isfinite(a) and math.isfinite(b)) or a <= 1e-14 or b <= 1e-14:
        return float("nan")
    return -(math.log(b) - math.log(a)) / (right["time_s"] - left["time_s"])


def _mass_fraction_zone(
    cells: list[tuple[float, float, float, float]],
    total_volume: float,
    total_mass: float,
) -> dict[str, float]:
    """Measure a fixed-mass outer zone without using a geometry-specific radius.

    Cells are ranked from the liner inward.  The last cell is fractionally
    weighted when necessary so the shell contains exactly the target mass
    fraction.  This is a two-zone diagnostic, not a replacement for the global
    RMS metric; the legacy fixed-radius fields remain in every history.
    """
    target_mass = TARGET_SHELL_MASS_FRACTION * total_mass
    shell_mass = shell_volume = shell_tracer_mass = 0.0
    remaining = target_mass
    for radius, cell_volume, cell_mass, scalar in sorted(cells, key=lambda item: item[0], reverse=True):
        if remaining <= 0.0:
            break
        if cell_mass <= 0.0:
            continue
        weight = min(1.0, remaining / cell_mass)
        shell_mass += weight * cell_mass
        shell_volume += weight * cell_volume
        shell_tracer_mass += weight * scalar * cell_mass
        remaining -= weight * cell_mass
    core_mass = total_mass - shell_mass
    core_volume = total_volume - shell_volume
    core_tracer_mass = 0.0
    # The total scalar inventory is reconstructed from the cell list so the
    # complementary core has exactly the same discretized mass balance.
    total_tracer_mass = sum(cell_mass * scalar for _, _, cell_mass, scalar in cells)
    core_tracer_mass = total_tracer_mass - shell_tracer_mass
    shell_mean = shell_tracer_mass / shell_mass
    core_mean = core_tracer_mass / core_mass
    return {
        "mf_zone_core_mean": core_mean,
        "mf_zone_shell_mean": shell_mean,
        "mf_zone_delta_c": shell_mean - core_mean,
        "mf_zone_shell_mass_fraction": shell_mass / total_mass,
        "mf_zone_shell_volume_fraction": shell_volume / total_volume,
        "mf_zone_core_volume_mm3": core_volume * WEDGE_SCALE * 1e9,
        "mf_zone_shell_volume_mm3": shell_volume * WEDGE_SCALE * 1e9,
    }


def process(case: Path, output: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for angle, directory in times(case):
        volume = list(values(directory / "Vc"))
        count = len(volume)
        tracer = list(values(directory / "tracer", expected_count=count))
        centres = list(values(directory / "C", vector=True, expected_count=count))
        rho = density(directory, count)
        if not (len(tracer) == len(volume) == len(centres) == len(rho)):
            raise ValueError(f"Field lengths differ at {directory}")

        core_v = shell_v = core_cv = shell_cv = 0.0
        core_mass = shell_mass = 0.0
        wedge_mass = 0.0
        tracer_mass_1 = tracer_mass_2 = 0.0
        tracer_vol_1 = tracer_vol_2 = 0.0
        cells: list[tuple[float, float, float, float]] = []

        for scalar, cell_volume, centre, density_value in zip(tracer, volume, centres, rho):
            radius = math.hypot(centre[0], centre[1])
            cell_mass = density_value * cell_volume
            cells.append((radius, cell_volume, cell_mass, scalar))
            if radius <= CORE_RADIUS_M:
                core_v += cell_volume
                core_cv += scalar * cell_volume
                core_mass += cell_mass
            else:
                shell_v += cell_volume
                shell_cv += scalar * cell_volume
                shell_mass += cell_mass

            wedge_mass += cell_mass
            tracer_mass_1 += scalar * cell_mass
            tracer_mass_2 += scalar * scalar * cell_mass
            tracer_vol_1 += scalar * cell_volume
            tracer_vol_2 += scalar * scalar * cell_volume

        total_wedge = core_v + shell_v
        core_mean = core_cv / core_v
        wall_mean = shell_cv / shell_v
        delta = wall_mean - core_mean

        mass_mean = tracer_mass_1 / wedge_mass
        mass_variance = max(0.0, tracer_mass_2 / wedge_mass - mass_mean**2)
        volume_mean = tracer_vol_1 / total_wedge
        volume_variance = max(0.0, tracer_vol_2 / total_wedge - volume_mean**2)
        mf_zone = _mass_fraction_zone(cells, total_wedge, wedge_mass)

        rows.append({
            "crank_angle_deg_atdc": angle,
            "time_s": (angle + 180.0) / 360.0 / (RPM / 60.0),
            "core_mean": core_mean,
            "wall_shell_mean": wall_mean,
            "delta_c": delta,
            "tracer_min": min(tracer),
            "tracer_max": max(tracer),
            "core_volume_mm3": core_v * WEDGE_SCALE * 1e9,
            "wall_shell_volume_mm3": shell_v * WEDGE_SCALE * 1e9,
            "wall_shell_volume_fraction": shell_v / total_wedge,
            "wall_shell_mass_fraction": shell_mass / wedge_mass,
            "total_volume_mm3": total_wedge * WEDGE_SCALE * 1e9,
            "python_volume_mm3": expected_volume(angle) * 1e9,
            "volume_error_percent": 100.0 * (
                total_wedge * WEDGE_SCALE / expected_volume(angle) - 1.0
            ),
            "mass_mg": wedge_mass * WEDGE_SCALE * 1e6,
            "tracer_mass_mean": mass_mean,
            "tracer_mass_variance": mass_variance,
            "tracer_mass_rms": math.sqrt(mass_variance),
            "tracer_volume_mean": volume_mean,
            "tracer_volume_variance": volume_variance,
            "tracer_volume_rms": math.sqrt(volume_variance),
            **mf_zone,
        })

    if not rows:
        raise ValueError(f"No usable CFD output times found in {case}")

    initial_mass = rows[0]["mass_mg"]
    initial_tracer_mass_mean = rows[0]["tracer_mass_mean"]
    initial_mass_rms = rows[0]["tracer_mass_rms"]
    initial_volume_rms = rows[0]["tracer_volume_rms"]
    initial_mf_delta = rows[0]["mf_zone_delta_c"]
    if initial_mass <= 0:
        raise ValueError("Initial integrated mass is not positive")
    if initial_mass_rms <= 0 or initial_volume_rms <= 0:
        raise ValueError("Initial tracer variance is not positive")
    if initial_mf_delta <= 0:
        raise ValueError("Initial mass-fraction zone contrast is not positive")

    for row in rows:
        row["mass_error_percent"] = 100.0 * (row["mass_mg"] / initial_mass - 1.0)
        row["tracer_inventory_error_percent"] = 100.0 * (
            row["tracer_mass_mean"] / initial_tracer_mass_mean - 1.0
        )
        row["tracer_mass_rms_normalized"] = row["tracer_mass_rms"] / initial_mass_rms
        row["tracer_volume_rms_normalized"] = row["tracer_volume_rms"] / initial_volume_rms
        row["mf_zone_delta_c_normalized"] = abs(row["mf_zone_delta_c"]) / abs(initial_mf_delta)

    for index, row in enumerate(rows):
        # Legacy fixed-radius core/shell decay. Keep for CFD-01 regression, but
        # do not use it alone for cross-geometry squish comparisons when the
        # shell volume fraction changes strongly through the cycle.
        if index == 0 or index == len(rows) - 1:
            zone_rate = float("nan")
        else:
            left, right = rows[index - 1], rows[index + 1]
            if abs(left["delta_c"]) <= 1e-14 or abs(right["delta_c"]) <= 1e-14:
                zone_rate = float("nan")
            else:
                zone_rate = -(
                    math.log(abs(right["delta_c"])) - math.log(abs(left["delta_c"]))
                ) / (right["time_s"] - left["time_s"])
        row["k_mix_1_s"] = zone_rate
        row["tau_mix_ms"] = (
            1000.0 / zone_rate if math.isfinite(zone_rate) and zone_rate > 0 else float("nan")
        )

        global_rate = _log_decay_rate(rows, index, "tracer_mass_rms")
        row["k_global_mix_1_s"] = global_rate
        row["tau_global_mix_ms"] = (
            1000.0 / global_rate
            if math.isfinite(global_rate) and global_rate > 0
            else float("nan")
        )

        mf_rate = _log_decay_rate(rows, index, "mf_zone_delta_c_normalized")
        row["k_mf_zone_mix_1_s"] = mf_rate
        row["tau_mf_zone_mix_ms"] = (
            1000.0 / mf_rate
            if math.isfinite(mf_rate) and mf_rate > 0
            else float("nan")
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = process(args.case.resolve(), args.output.resolve())
    max_mass = max(abs(row["mass_error_percent"]) for row in rows)
    max_inventory = max(abs(row["tracer_inventory_error_percent"]) for row in rows)
    tracer_min = min(row["tracer_min"] for row in rows)
    tracer_max = max(row["tracer_max"] for row in rows)
    shell_min = min(row["wall_shell_volume_fraction"] for row in rows)
    shell_max = max(row["wall_shell_volume_fraction"] for row in rows)
    print(
        f"wrote {len(rows)} rows to {args.output}; "
        f"max mass drift={max_mass:.6g}%, tracer=[{tracer_min:.6g}, {tracer_max:.6g}], "
        f"tracer inventory drift={max_inventory:.6g}%, shell volume fraction=[{shell_min:.6g}, {shell_max:.6g}]"
    )


if __name__ == "__main__":
    main()
