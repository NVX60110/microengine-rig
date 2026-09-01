#!/usr/bin/env python3
"""Run the CFD-01 coarse-mesh maxDeltaT answer-convergence sweep."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[4]
RESULTS = PROJECT_ROOT / "cfd" / "results"
sys.path.insert(0, str(HERE.parent))

from collect_results import (  # noqa: E402
    MAX_MASS_DRIFT_REL,
    TRACER_TOL,
    check_cells,
    max_courant,
    nearest,
)
from postprocess_history import process  # noqa: E402
from run_cfd01 import initialise_tracer, prepare, run  # noqa: E402

DEFAULT_CAPS = (0.15, 0.25, 0.35, 0.45)
TARGETS = (-20.0, 0.0, 20.0, 45.0)
MAX_CO_TARGET = 0.15
MAX_COURANT_GATE = 0.5
MAX_VOLUME_ERROR_PERCENT = 0.2
ANSWER_REL_TOL = 0.05
MAX_OUTPUT_GAP_CAD = 0.5


def case_tag(cap: float) -> str:
    return f"dt_{cap:.3f}".replace(".", "p")


def configure_control_dict(case: Path, max_delta_t: float) -> int:
    """Patch only timestep/output controls in the copied case."""
    if max_delta_t <= 0:
        raise ValueError("maxDeltaT must be positive")

    interval = max(1, math.floor(MAX_OUTPUT_GAP_CAD / max_delta_t + 1e-12))
    path = case / "system" / "controlDict"
    text = path.read_text()

    def replace_one(pattern: str, replacement: str, label: str) -> None:
        nonlocal text
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
        if count != 1:
            raise ValueError(f"could not patch {label} in {path}")

    replace_one(
        r"^maxCo\s+[-+0-9.eE]+;",
        f"maxCo {MAX_CO_TARGET:.12g};",
        "maxCo",
    )
    replace_one(
        r"^maxDeltaT\s+[-+0-9.eE]+;",
        f"maxDeltaT {max_delta_t:.12g};",
        "maxDeltaT",
    )

    # Keep field and function-object writes synchronized. With timeStep output,
    # interval*maxDeltaT remains at or below the local-derivative sampling gate.
    text = re.sub(
        r"^(\s*writeInterval)\s+\d+;",
        lambda match: f"{match.group(1)} {interval};",
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^(\s*executeInterval)\s+\d+;",
        lambda match: f"{match.group(1)} {interval};",
        text,
        flags=re.M,
    )
    path.write_text(text)
    return interval


def accepted_steps(log: Path) -> int:
    if not log.exists():
        return 0
    return len(re.findall(r"(?m)^Time\s*=", log.read_text(errors="replace")))


def rel_error(value: float, reference: float) -> float:
    if not (math.isfinite(value) and math.isfinite(reference)):
        return math.inf
    scale = abs(reference)
    return abs(value - reference) / scale if scale > 1e-14 else abs(value - reference)


def suffix(target: float) -> str:
    return f"{target:+.0f}".replace("+", "p").replace("-", "m")


def run_case(cap: float, sweep_root: Path, overwrite: bool) -> dict[str, object]:
    tag = case_tag(cap)
    run_root = sweep_root / tag
    case = prepare("coarse", run_root, overwrite)
    write_interval = configure_control_dict(case, cap)
    started = time.monotonic()

    row: dict[str, object] = {
        "tag": tag,
        "mesh_level": "coarse",
        "max_delta_t_cad": cap,
        "max_co_target": MAX_CO_TARGET,
        "write_interval_steps": write_interval,
        "max_nominal_output_gap_cad": write_interval * cap,
        "status": "failed",
        "error": "",
    }

    try:
        run(["blockMesh"], case, "log.blockMesh")
        initialise_tracer(case)
        run(["checkMesh", "-time", "-180"], case, "log.checkMesh_bdc")
        run(["foamRun"], case, "log.foamRun")
        run(["checkMesh", "-latestTime"], case, "log.checkMesh_after_motion")

        history = process(case, run_root / "cfd01_timestep_history.csv")
        row["cell_count"] = check_cells(case / "log.checkMesh_bdc")
        row["accepted_steps"] = accepted_steps(case / "log.foamRun")
        row["max_courant"] = max_courant(case / "log.foamRun")
        row["max_volume_error_percent"] = max(
            abs(item["volume_error_percent"]) for item in history
        )
        row["max_mass_error_percent"] = max(
            abs(item["mass_error_percent"]) for item in history
        )
        row["tracer_min"] = min(item["tracer_min"] for item in history)
        row["tracer_max"] = max(item["tracer_max"] for item in history)
        row["max_observed_output_gap_cad"] = max(
            b["crank_angle_deg_atdc"] - a["crank_angle_deg_atdc"]
            for a, b in zip(history, history[1:])
        )

        for target in TARGETS:
            point = nearest(history, target)
            key = suffix(target)
            row[f"sampled_cad_{key}"] = point["crank_angle_deg_atdc"]
            row[f"delta_c_{key}"] = point["delta_c"]
            row[f"k_mix_1_s_{key}"] = point["k_mix_1_s"]
            row[f"tau_mix_ms_{key}"] = point["tau_mix_ms"]

        failures: list[str] = []
        if row["cell_count"] is None:
            failures.append("cell count missing")
        if row["max_courant"] is None or float(row["max_courant"]) > MAX_COURANT_GATE:
            failures.append(f"max Courant > {MAX_COURANT_GATE}")
        if float(row["max_volume_error_percent"]) > MAX_VOLUME_ERROR_PERCENT:
            failures.append(f"volume error > {MAX_VOLUME_ERROR_PERCENT}%")
        if float(row["max_mass_error_percent"]) > 100.0 * MAX_MASS_DRIFT_REL:
            failures.append(f"mass drift > {100.0 * MAX_MASS_DRIFT_REL:g}%")
        if float(row["tracer_min"]) < -TRACER_TOL or float(row["tracer_max"]) > 1.0 + TRACER_TOL:
            failures.append("tracer outside [0,1]")
        if float(row["max_observed_output_gap_cad"]) > MAX_OUTPUT_GAP_CAD + 1e-9:
            failures.append(f"output gap > {MAX_OUTPUT_GAP_CAD} CAD")

        row["status"] = "ok" if not failures else "gate_failed"
        row["error"] = "; ".join(failures)
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"

    row["runtime_s"] = time.monotonic() - started
    (run_root / "cfd01_timestep_metadata.json").write_text(
        json.dumps(row, indent=2, allow_nan=True) + "\n"
    )
    return row


def apply_answer_gate(rows: list[dict[str, object]]) -> None:
    baseline = next(
        (row for row in rows if math.isclose(float(row["max_delta_t_cad"]), 0.15)),
        None,
    )
    if baseline is None or baseline["status"] != "ok":
        for row in rows:
            row["answer_gate"] = "unavailable"
            row["max_answer_rel_error"] = math.inf
        return

    for row in rows:
        if row["status"] != "ok":
            row["answer_gate"] = "failed_run_gate"
            row["max_answer_rel_error"] = math.inf
            continue

        errors: list[float] = []
        for target in TARGETS:
            key = suffix(target)
            errors.extend(
                [
                    rel_error(
                        float(row[f"delta_c_{key}"]),
                        float(baseline[f"delta_c_{key}"]),
                    ),
                    rel_error(
                        float(row[f"tau_mix_ms_{key}"]),
                        float(baseline[f"tau_mix_ms_{key}"]),
                    ),
                ]
            )
        row["max_answer_rel_error"] = max(errors)
        row["answer_gate"] = (
            "pass" if float(row["max_answer_rel_error"]) <= ANSWER_REL_TOL else "fail"
        )


def write_summary(rows: list[dict[str, object]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--caps", type=float, nargs="+", default=list(DEFAULT_CAPS))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--sweep-root",
        type=Path,
        default=Path(
            os.environ.get(
                "CFD01_TIMESTEP_ROOT",
                str(Path.home() / "OpenFOAM/cfd01-timestep-sweep"),
            )
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS / "cfd01_timestep_sweep.csv",
    )
    args = parser.parse_args()

    if shutil.which("foamRun") is None:
        raise SystemExit("foamRun is not on PATH; source /opt/openfoam14/etc/bashrc first.")

    caps = sorted(set(args.caps))
    if not any(math.isclose(cap, 0.15) for cap in caps):
        raise SystemExit("The sweep must include the 0.15 CAD baseline.")
    if any(cap <= 0 or cap > MAX_OUTPUT_GAP_CAD for cap in caps):
        raise SystemExit("Caps must be >0 and <=0.5 CAD.")

    sweep_root = args.sweep_root.expanduser().resolve()
    if " " in str(sweep_root):
        raise SystemExit("--sweep-root must not contain spaces (OpenFOAM requirement).")
    sweep_root.mkdir(parents=True, exist_ok=True)

    rows = [run_case(cap, sweep_root, args.overwrite) for cap in caps]
    apply_answer_gate(rows)
    write_summary(rows, args.output.resolve())

    accepted = [
        row
        for row in rows
        if row.get("status") == "ok" and row.get("answer_gate") == "pass"
    ]
    fastest = min(accepted, key=lambda row: float(row["runtime_s"])) if accepted else None
    print(
        json.dumps(
            {
                "answer_relative_tolerance": ANSWER_REL_TOL,
                "rows": rows,
                "recommended": fastest,
                "output": str(args.output.resolve()),
            },
            indent=2,
            allow_nan=True,
        )
    )
    if not accepted:
        raise SystemExit("No timestep setting passed both numerical and answer gates.")


if __name__ == "__main__":
    main()
