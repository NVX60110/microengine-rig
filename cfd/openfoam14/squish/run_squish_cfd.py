#!/usr/bin/env python3
"""Build and run the first constant-CR squish geometry (S1, coarse mesh).

The S1 crown is a stepped bowl: a 0.50 mm squish land outside a 3.25 mm
bowl radius and a 0.918 mm recessed bowl floor.  The recess is chosen so the
analytic TDC clearance volume equals the flat-piston CR=7.75 volume.  The
native v14 multiValveEngine mover translates the complete piston patch,
including the bowl wall, by the same slider-crank displacement.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import sys
import time

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]
FLAT_SCRIPTS = PROJECT_ROOT / "cfd" / "openfoam14" / "cold_flow_tracer" / "scripts"
sys.path.insert(0, str(FLAT_SCRIPTS))

from postprocess_history import process  # noqa: E402
from collect_results import (  # noqa: E402
    MAX_MASS_DRIFT_REL,
    TRACER_TOL,
    check_cells,
    max_courant,
)
from run_cfd01 import (  # noqa: E402
    BORE_M,
    CR,
    ROOT as FLAT_ROOT,
    STROKE_M,
    initialise_tracer,
    run,
)


RADIUS_M = BORE_M / 2.0
INNER_RADIUS_M = 0.00005
BOWL_RADIUS_M = 0.00325
SQUISH_WIDTH_M = 0.00100
SQUISH_GAP_M = 0.00050
BOWL_RECESS_M = 0.000918
WEDGE_DEG = 5.0
AZIMUTHAL_CELLS = 3
BOWL_RADIAL_CELLS = 17
LAND_RADIAL_CELLS = 5
BOWL_LOWER_AXIAL_CELLS = 5
UPPER_AXIAL_CELLS = 38
MAX_COURANT_GATE = 0.5
MAX_VOLUME_ERROR_PERCENT = 0.2
MAX_OUTPUT_GAP_CAD = 0.5


def clearance_height() -> float:
    return STROKE_M / (CR - 1.0)


def geometry_summary() -> dict[str, float]:
    area = math.pi * RADIUS_M**2
    bowl_area = math.pi * BOWL_RADIUS_M**2
    land_area = area - bowl_area
    head_z = clearance_height() + STROKE_M
    land_tdc = head_z - SQUISH_GAP_M
    land_bdc = land_tdc - STROKE_M
    bowl_bdc = land_bdc - BOWL_RECESS_M
    flat_tdc = area * clearance_height()
    squish_tdc = land_area * SQUISH_GAP_M + bowl_area * (SQUISH_GAP_M + BOWL_RECESS_M)
    return {
        "bore_mm": BORE_M * 1000.0,
        "stroke_mm": STROKE_M * 1000.0,
        "compression_ratio": CR,
        "bowl_radius_mm": BOWL_RADIUS_M * 1000.0,
        "squish_width_mm": SQUISH_WIDTH_M * 1000.0,
        "squish_gap_tdc_mm": SQUISH_GAP_M * 1000.0,
        "bowl_recess_mm": BOWL_RECESS_M * 1000.0,
        "squish_area_fraction": land_area / area,
        "flat_tdc_volume_mm3": flat_tdc * 1e9,
        "squish_tdc_volume_mm3": squish_tdc * 1e9,
        "analytic_tdc_volume_error_percent": 100.0 * (squish_tdc / flat_tdc - 1.0),
        "head_z_bdc_mm": head_z * 1000.0,
        "land_piston_z_bdc_mm": land_bdc * 1000.0,
        "bowl_piston_z_bdc_mm": bowl_bdc * 1000.0,
    }


def block_mesh_dict() -> str:
    """Generate three conformal radial blocks with a stepped bowl crown."""
    half = math.radians(WEDGE_DEG / 2.0)
    head_z = clearance_height() + STROKE_M
    land_tdc = head_z - SQUISH_GAP_M
    land_bdc = land_tdc - STROKE_M
    bowl_bdc = land_bdc - BOWL_RECESS_M
    radii = (INNER_RADIUS_M, BOWL_RADIUS_M, RADIUS_M)
    zlevels = (bowl_bdc, land_bdc, head_z)
    vertices: list[str] = []
    index: dict[tuple[int, int, int], int] = {}

    def vertex(ring: int, side: int, zlevel: int) -> int:
        key = (ring, side, zlevel)
        if key not in index:
            angle = -half if side == 0 else half
            r = radii[ring]
            index[key] = len(vertices)
            vertices.append(
                f"({r * math.cos(angle):.12g} {r * math.sin(angle):.12g} {zlevels[zlevel]:.12g})"
            )
        return index[key]

    def block(r0: int, r1: int, z0: int, z1: int, nr: int, nz: int) -> str:
        # Right-handed ordering: radial, azimuthal, axial.
        ids = [
            vertex(r0, 0, z0), vertex(r1, 0, z0),
            vertex(r1, 1, z0), vertex(r0, 1, z0),
            vertex(r0, 0, z1), vertex(r1, 0, z1),
            vertex(r1, 1, z1), vertex(r0, 1, z1),
        ]
        return f"    hex ({' '.join(str(item) for item in ids)}) ({nr} {AZIMUTHAL_CELLS} {nz}) simpleGrading (1 1 1)"

    blocks = [
        block(0, 1, 0, 1, BOWL_RADIAL_CELLS, BOWL_LOWER_AXIAL_CELLS),
        block(0, 1, 1, 2, BOWL_RADIAL_CELLS, UPPER_AXIAL_CELLS),
        block(1, 2, 1, 2, LAND_RADIAL_CELLS, UPPER_AXIAL_CELLS),
    ]

    def face(ids: list[int]) -> str:
        return "(" + " ".join(str(item) for item in ids) + ")"

    # Convenience handles for boundary faces.
    b0m, b1m, b1p, b0p = (vertex(0, 0, 0), vertex(1, 0, 0), vertex(1, 1, 0), vertex(0, 1, 0))
    l0m, l1m, l1p, l0p = (vertex(0, 0, 1), vertex(1, 0, 1), vertex(1, 1, 1), vertex(0, 1, 1))
    h0m, h1m, h1p, h0p = (vertex(0, 0, 2), vertex(1, 0, 2), vertex(1, 1, 2), vertex(0, 1, 2))
    l2m, l2p, h2m, h2p = (vertex(2, 0, 1), vertex(2, 1, 1), vertex(2, 0, 2), vertex(2, 1, 2))

    wedge_minus = [
        face([h0m, h1m, l1m, l0m]),
        face([h1m, h2m, l2m, l1m]),
        face([l0m, l1m, b1m, b0m]),
    ]
    wedge_plus = [
        face([h0p, l0p, l1p, h1p]),
        face([h1p, l1p, l2p, h2p]),
        face([b0p, b1p, l1p, l0p]),
    ]

    return f'''/* Generated by run_squish_cfd.py; S1 coarse constant-CR crown. */
FoamFile
{{
    format ascii;
    class dictionary;
    location "system";
    object blockMeshDict;
}}

convertToMeters 1;

vertices
(
    {' '.join(vertices)}
);

blocks
(
{chr(10).join(blocks)}
);

boundary
(
    piston
    {{
        type wall;
        // Bottom bowl floor, squish land, and vertical bowl wall all move.
        faces
        (
            {face([b0m, b1m, b1p, b0p])}
            {face([l1m, l2m, l2p, l1p])}
            {face([b1m, b1p, l1p, l1m])}
        );
    }}
    liner
    {{
        type wall;
        faces ({face([h2m, h2p, l2p, l2m])});
    }}
    cylinderHead
    {{
        type wall;
        faces
        (
            {face([h0m, h0p, h1p, h1m])}
            {face([h1m, h1p, h2p, h2m])}
        );
    }}
    axisCore
    {{
        type symmetry;
        faces
        (
            {face([h0m, l0m, l0p, h0p])}
            {face([l0m, b0m, b0p, l0p])}
        );
    }}
    symmetryMinus
    {{
        type symmetryPlane;
        faces ({' '.join(wedge_minus)});
    }}
    symmetryPlus
    {{
        type symmetryPlane;
        faces ({' '.join(wedge_plus)});
    }}
);
'''


def prepare(case: Path, overwrite: bool) -> None:
    if case.exists():
        if not overwrite:
            raise FileExistsError(f"{case} exists; use --overwrite")
        shutil.rmtree(case)
    case.mkdir(parents=True)
    shutil.copytree(FLAT_ROOT / "0", case / "-180")
    for item in ("constant", "system"):
        shutil.copytree(FLAT_ROOT / item, case / item)
    (case / "system" / "blockMeshDict").write_text(block_mesh_dict())


def validate_case(case: Path, output: Path) -> tuple[list[dict[str, float]], dict[str, object], list[str]]:
    """Reprocess the case and apply the CFD-01 numerical gates to S1."""
    history = process(case, output)
    max_volume = max(abs(item["volume_error_percent"]) for item in history)
    max_mass = max(abs(item["mass_error_percent"]) for item in history)
    tracer_min = min(item["tracer_min"] for item in history)
    tracer_max = max(item["tracer_max"] for item in history)
    angles = [item["crank_angle_deg_atdc"] for item in history]
    max_gap = max(b - a for a, b in zip(angles, angles[1:])) if len(angles) > 1 else math.inf
    cells = check_cells(case / "log.checkMesh_bdc")
    solver_log = (case / "log.foamRun").read_text(errors="replace")
    courant = max_courant(case / "log.foamRun")
    execution_matches = re.findall(
        r"ExecutionTime\s*=\s*([0-9.eE+-]+)\s+s\s+ClockTime\s*=\s*([0-9.eE+-]+)\s+s",
        solver_log,
    )
    openfoam_execution_s = float(execution_matches[-1][0]) if execution_matches else None
    openfoam_clock_s = float(execution_matches[-1][1]) if execution_matches else None
    checks = {
        "mesh_ok_bdc": "Mesh OK" in (case / "log.checkMesh_bdc").read_text(errors="replace"),
        "mesh_ok_tdc": "Mesh OK" in (case / "log.checkMesh_tdc").read_text(errors="replace"),
        "mesh_ok_after_motion": "Mesh OK" in (case / "log.checkMesh_after_motion").read_text(errors="replace"),
    }
    failures: list[str] = []
    if not all(checks.values()):
        failures.append("checkMesh failed at one or more required times")
    if cells is None:
        failures.append("cell count missing")
    if courant is None or courant > MAX_COURANT_GATE:
        failures.append(f"max Courant > {MAX_COURANT_GATE}")
    if max_volume > MAX_VOLUME_ERROR_PERCENT:
        failures.append(f"volume error > {MAX_VOLUME_ERROR_PERCENT}%")
    if max_mass > 100.0 * MAX_MASS_DRIFT_REL:
        failures.append(f"mass drift > {100.0 * MAX_MASS_DRIFT_REL:g}%")
    if tracer_min < -TRACER_TOL or tracer_max > 1.0 + TRACER_TOL:
        failures.append("tracer outside [0,1]")
    if max_gap > MAX_OUTPUT_GAP_CAD + 1e-9:
        failures.append(f"output gap > {MAX_OUTPUT_GAP_CAD} CAD")
    metrics = {
        "cell_count": cells,
        "accepted_steps": len(re.findall(r"(?m)^Time\s*=", solver_log)),
        "openfoam_execution_time_s": openfoam_execution_s,
        "openfoam_clock_time_s": openfoam_clock_s,
        "max_courant": courant,
        "max_volume_error_percent": max_volume,
        "max_mass_error_percent": max_mass,
        "tracer_min": tracer_min,
        "tracer_max": tracer_max,
        "max_observed_output_gap_cad": max_gap,
        **checks,
    }
    return history, metrics, failures


def write_target_summary(history: list[dict[str, float]], path: Path) -> None:
    """Write the requested S1 transport points without requiring pandas."""
    targets = (-90.0, -45.0, -20.0, 0.0, 20.0, 45.0, 90.0)
    fields = [
        "requested_crank_angle_deg_atdc", "sampled_crank_angle_deg_atdc",
        "delta_c", "k_mix_1_s", "tau_mix_ms", "mass_error_percent",
        "tracer_min", "tracer_max",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for target in targets:
            row = min(history, key=lambda item: abs(item["crank_angle_deg_atdc"] - target))
            writer.writerow({
                "requested_crank_angle_deg_atdc": target,
                "sampled_crank_angle_deg_atdc": row["crank_angle_deg_atdc"],
                "delta_c": row["delta_c"],
                "k_mix_1_s": row["k_mix_1_s"],
                "tau_mix_ms": row["tau_mix_ms"],
                "mass_error_percent": row["mass_error_percent"],
                "tracer_min": row["tracer_min"],
                "tracer_max": row["tracer_max"],
            })


def sibling_output(path: Path, suffix: str) -> Path:
    """Derive a companion output from --output so variants never clobber the promoted S1 files."""
    name = path.name
    marker = "_scalar_history.csv"
    if name.endswith(marker):
        return path.with_name(name[: -len(marker)] + suffix)
    return path.with_name(path.stem + suffix)


def tracer_solver_settings(case: Path) -> dict[str, str] | None:
    """Record the exact-keyword tracer solver entry the case actually used (Issue #10)."""
    text = (case / "system" / "fvSolution").read_text()
    match = re.search(r"\n[ \t]*tracer[ \t]*\n[ \t]*\{\n(.*?)\n[ \t]*\}\n", text, flags=re.S)
    if match is None:
        return None
    settings = {}
    for key in ("solver", "preconditioner", "tolerance", "relTol", "maxIter"):
        value = re.search(rf"(?m)^[ \t]*{key}[ \t]+([^;]+);", match.group(1))
        if value:
            settings[key] = value.group(1).strip()
    return settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=Path("/home/gflip/OpenFOAM/cfd02-squish"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-only", action="store_true", help="validate an existing s1_coarse run without rerunning OpenFOAM")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "cfd/results/cfd02_s1_coarse_scalar_history.csv")
    args = parser.parse_args()
    if shutil.which("foamRun") is None:
        raise SystemExit("foamRun is not on PATH; source /opt/openfoam14/etc/bashrc first.")
    run_root = args.run_root.expanduser().resolve()
    if " " in str(run_root):
        raise SystemExit("--run-root must not contain spaces")
    case = run_root / "s1_coarse"
    if args.validate_only:
        if not case.exists():
            raise SystemExit(f"existing case not found: {case}")
    else:
        prepare(case, args.overwrite)
    started = time.monotonic()
    # Validation is intentionally allowed to re-run without destroying the
    # original solver timing.  Keep the timing recorded by the full run and
    # report the separate post-processing cost when --validate-only is used.
    previous_metadata: dict[str, object] = {}
    metadata_path = case / "cfd02_s1_metadata.json"
    if args.validate_only and metadata_path.exists():
        try:
            previous_metadata = json.loads(metadata_path.read_text())
        except (OSError, json.JSONDecodeError):
            previous_metadata = {}
    status = "failed"
    error = ""
    try:
        if not args.validate_only:
            run(["blockMesh"], case, "log.blockMesh")
            initialise_tracer(case)
            run(["checkMesh", "-time", "-180"], case, "log.checkMesh_bdc")
            run(["foamRun"], case, "log.foamRun")
            run(["checkMesh", "-time", "0"], case, "log.checkMesh_tdc")
            run(["checkMesh", "-time", "180"], case, "log.checkMesh_after_motion")
        history, metrics, failures = validate_case(case, args.output.resolve())
        write_target_summary(
            history,
            sibling_output(args.output.resolve(), "_mixing_time.csv"),
        )
        status = "ok" if not failures else "gate_failed"
        error = "; ".join(failures)
    except Exception as exc:
        history = []
        error = f"{type(exc).__name__}: {exc}"
        metrics = {}
    validation_runtime = time.monotonic() - started
    solver_runtime = (
        previous_metadata.get("runtime_s", validation_runtime)
        if args.validate_only
        else validation_runtime
    )
    metadata = {
        "case": "CFD-02 S1 mild squish coarse",
        "tracer_solver_settings": tracer_solver_settings(case) if case.exists() else None,
        "geometry": geometry_summary(),
        "radial_cells": BOWL_RADIAL_CELLS + LAND_RADIAL_CELLS,
        "azimuthal_cells": AZIMUTHAL_CELLS,
        "axial_cells_bowl_lower": BOWL_LOWER_AXIAL_CELLS,
        "axial_cells_upper": UPPER_AXIAL_CELLS,
        "processor_count": 1,
        "status": status,
        "error": error,
        "runtime_s": solver_runtime,
        "validation_runtime_s": validation_runtime if args.validate_only else None,
        "output": str(args.output.resolve()),
        **metrics,
    }
    (case / "cfd02_s1_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    sibling_output(args.output.resolve(), "_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    if status != "ok":
        raise SystemExit(error)
    print(json.dumps({**metadata, "output_times": len(history)}, indent=2))


if __name__ == "__main__":
    main()
