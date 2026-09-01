#!/usr/bin/env python3
"""Validate CFD-01 runs and write the project-level result CSV files."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import re
import shutil
import sys

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[4]
RESULTS = PROJECT_ROOT / "cfd" / "results"
sys.path.insert(0, str(HERE.parent))
from postprocess_history import process  # noqa: E402


LEVELS = ("coarse", "medium", "fine")
REQUESTED_ANGLES = (-90.0, -45.0, -20.0, 0.0, 20.0, 45.0, 90.0)
MAX_MASS_DRIFT_REL = 1e-4
TRACER_TOL = 1e-9


def check_cells(log: Path) -> int | None:
    if not log.exists():
        return None
    match = re.search(r"\bcells:\s+(\d+)", log.read_text(errors="replace"))
    return int(match.group(1)) if match else None


def max_courant(log: Path) -> float | None:
    if not log.exists():
        return None
    values = re.findall(r"Courant Number mean:\s*[-+0-9.eE]+\s+max:\s*([-+0-9.eE]+)", log.read_text(errors="replace"))
    return max((float(value) for value in values), default=None)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def nearest(rows: list[dict[str, float]], angle: float) -> dict[str, float]:
    return min(rows, key=lambda row: abs(row["crank_angle_deg_atdc"] - angle))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-root", type=Path,
        default=Path(os.environ.get("CFD01_RUN_ROOT", str(Path.home() / "OpenFOAM/cfd01-cold-flow-tracer"))),
    )
    args = parser.parse_args()
    run_root = args.run_root.expanduser().resolve()
    RESULTS.mkdir(parents=True, exist_ok=True)
    convergence: list[dict[str, object]] = []
    successful: dict[str, list[dict[str, float]]] = {}

    for level in LEVELS:
        case = run_root / level
        row: dict[str, object] = {"mesh_level": level, "status": "failed", "error": ""}
        metadata_path = case / "cfd01_run_metadata.json"
        if not metadata_path.exists():
            row["error"] = "run metadata missing"
            convergence.append(row)
            continue
        metadata = json.loads(metadata_path.read_text())
        row.update(metadata)
        row["cell_count"] = check_cells(case / "log.checkMesh_bdc")
        row["max_courant"] = max_courant(case / "log.foamRun")
        if metadata["status"] != "ok":
            convergence.append(row)
            continue
        try:
            history = process(case, RESULTS / f"cfd01_scalar_history_{level}.csv")
            row["max_volume_error_percent"] = max(abs(item["volume_error_percent"]) for item in history)
            row["max_mass_error_percent"] = max(abs(item["mass_error_percent"]) for item in history)
            row["tracer_min"] = min(item["tracer_min"] for item in history)
            row["tracer_max"] = max(item["tracer_max"] for item in history)
            if row["cell_count"] is None:
                raise ValueError("cell count could not be parsed from checkMesh")
            if row["max_courant"] is None or float(row["max_courant"]) > 0.5 + 1e-12:
                raise ValueError("Courant control missing or exceeded 0.5")
            if float(row["max_volume_error_percent"]) > 0.2:
                raise ValueError("slider-crank volume error exceeded 0.2%")
            if float(row["max_mass_error_percent"]) > 100.0 * MAX_MASS_DRIFT_REL:
                raise ValueError(
                    f"closed-cylinder mass drift exceeded {100.0 * MAX_MASS_DRIFT_REL:.6g}%"
                )
            if float(row["tracer_min"]) < -TRACER_TOL or float(row["tracer_max"]) > 1.0 + TRACER_TOL:
                raise ValueError("passive tracer left physical [0,1] bounds")
            row["status"] = "ok"
            row["error"] = ""
            successful[level] = history
        except Exception as exc:
            row["status"] = "failed"
            row["error"] = f"{type(exc).__name__}: {exc}"
        convergence.append(row)

    write_csv(RESULTS / "cfd01_mesh_convergence.csv", convergence)

    # The finest successful mesh is the result of record. If fine fails, no
    # CFD result is promoted; a failed mesh row is still retained above.
    if "fine" not in successful:
        raise SystemExit("Fine CFD-01 case is not validated; no result promoted.")
    history = successful["fine"]
    shutil.copyfile(RESULTS / "cfd01_scalar_history_fine.csv", RESULTS / "cfd01_scalar_history.csv")
    mixing_rows = []
    for requested in REQUESTED_ANGLES:
        item = nearest(history, requested)
        mixing_rows.append({
            "requested_crank_angle_deg_atdc": requested,
            "sampled_crank_angle_deg_atdc": item["crank_angle_deg_atdc"],
            "k_mix_1_s": item["k_mix_1_s"],
            "tau_mix_ms": item["tau_mix_ms"],
            "delta_c": item["delta_c"],
            "mass_error_percent": item["mass_error_percent"],
            "tracer_min": item["tracer_min"],
            "tracer_max": item["tracer_max"],
        })
    write_csv(RESULTS / "cfd01_mixing_time.csv", mixing_rows)
    max_mass = max(abs(item["mass_error_percent"]) for item in history)
    print(
        f"validated fine history ({len(history)} output times); "
        f"max mass drift={max_mass:.6g}%"
    )


if __name__ == "__main__":
    main()
