#!/usr/bin/env python3
"""Convert CFD-01 ASCII fields to volume-weighted core/wall tracer history."""
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
OMEGA = 2.0 * math.pi * RPM / 60.0
WEDGE_SCALE = 360.0 / WEDGE_DEG


def values(path: Path, vector: bool = False) -> list[float] | list[tuple[float, float, float]]:
    text = path.read_text()
    match = re.search(
        r"internalField\s+nonuniform\s+List<[^>]+>\s+\d+\s*\(\s*(.*?)\s*\)\s*;",
        text,
        flags=re.S,
    )
    if not match:
        uniform = re.search(r"internalField\s+uniform\s+([^;]+);", text)
        if not uniform:
            raise ValueError(f"Cannot parse internalField in {path}")
        raise ValueError(f"{path} has a uniform field, which is not usable for integration")
    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    if vector:
        return [tuple(float(value) for value in line.strip("()").split()) for line in lines]
    return [float(line) for line in lines]


def piston_position(theta: float) -> float:
    root = math.sqrt(ROD_M**2 - CRANK_M**2 * math.sin(theta) ** 2)
    return CRANK_M * (1.0 - math.cos(theta)) + ROD_M - root


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
        # OpenFOAM 14's writeCellVolumes function writes Vc (cell volume).
        if (path / "tracer").exists() and (path / "Vc").exists() and (path / "C").exists():
            result.append((angle, path))
    return sorted(result)


def process(case: Path, output: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for angle, directory in times(case):
        tracer = values(directory / "tracer")
        volume = values(directory / "Vc")
        centres = values(directory / "C", vector=True)
        if not (len(tracer) == len(volume) == len(centres)):
            raise ValueError(f"Field lengths differ at {directory}")
        core_v = shell_v = core_cv = shell_cv = 0.0
        for scalar, cell_volume, centre in zip(tracer, volume, centres):
            radius = math.hypot(centre[0], centre[1])
            if radius <= CORE_RADIUS_M:
                core_v += cell_volume
                core_cv += scalar * cell_volume
            else:
                shell_v += cell_volume
                shell_cv += scalar * cell_volume
        total_wedge = core_v + shell_v
        core_mean = core_cv / core_v
        wall_mean = shell_cv / shell_v
        delta = wall_mean - core_mean
        rows.append({
            "crank_angle_deg_atdc": angle,
            "time_s": (angle + 180.0) / 360.0 / (RPM / 60.0),
            "core_mean": core_mean,
            "wall_shell_mean": wall_mean,
            "delta_c": delta,
            "core_volume_mm3": core_v * WEDGE_SCALE * 1e9,
            "wall_shell_volume_mm3": shell_v * WEDGE_SCALE * 1e9,
            "total_volume_mm3": total_wedge * WEDGE_SCALE * 1e9,
            "python_volume_mm3": expected_volume(angle) * 1e9,
            "volume_error_percent": 100.0 * (
                total_wedge * WEDGE_SCALE / expected_volume(angle) - 1.0
            ),
        })
    for index, row in enumerate(rows):
        left, right = rows[max(0, index - 1)], rows[min(len(rows) - 1, index + 1)]
        if index == 0 or index == len(rows) - 1 or abs(left["delta_c"]) <= 1e-14 or abs(right["delta_c"]) <= 1e-14:
            rate = float("nan")
        else:
            rate = -(
                math.log(abs(right["delta_c"])) - math.log(abs(left["delta_c"]))
            ) / (right["time_s"] - left["time_s"])
        row["k_mix_1_s"] = rate
        row["tau_mix_ms"] = 1000.0 / rate if math.isfinite(rate) and rate > 0 else float("nan")
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
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
