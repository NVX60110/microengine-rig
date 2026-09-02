#!/usr/bin/env python3
"""Audit closed-cylinder scalar inventory from solver-written OpenFOAM fields.

Issue #10 step 2 asks for the tracer inventory to be computed from the fields
the solver actually used, not only from postprocessed moments, and for the
wall fluxes to be inspected directly.  This tool reads, at every written time,
the solver density ``rho``, the cell volumes ``Vc``, the passive scalar and the
relative mass flux ``phi`` (including its boundary patch values) and reports:

* gas mass ``M = sum(rho*V)`` relative to its first written value;
* tracer mass ``Ms = sum(rho*tracer*V)`` relative to its first written value,
  which is exactly the quantity the ``scalarTransport`` function object
  conserves by finite-volume telescoping when the linear system is solved;
* the per-output increment of ``Ms`` so the crank-angle window in which any
  loss accumulates is explicit;
* the signed sum and largest magnitude of ``phi`` on each wall patch, which
  must be at round-off for an impermeable closed cylinder;
* global tracer bounds.

The initial ``-180`` directory is skipped because the runner copies it from the
static ``0`` template without ``rho`` or ``phi``; the first solver write is the
reference.  Times must contain ``rho``, ``Vc``, ``phi`` and the scalar field.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent / "openfoam14" / "cold_flow_tracer" / "scripts"))
from postprocess_history import values  # noqa: E402

WALL_PATCHES = ("piston", "liner", "cylinderHead")
ALL_PATCHES = WALL_PATCHES + ("axisCore", "symmetryMinus", "symmetryPlus")
TARGET_ANGLES = (-90.0, -45.0, -20.0, 0.0, 20.0, 45.0, 90.0, 180.0)


def patch_values(path: Path, patch: str) -> list[float] | None:
    """Return the ``value`` list of one boundary patch, or None when absent."""
    text = path.read_text()
    # Everything after the boundaryField keyword; OpenFOAM files end with a
    # footer comment after the closing brace, so do not anchor on end-of-file.
    _, separator, boundary = text.partition("boundaryField")
    if not separator:
        return None
    match = re.search(
        r"(?m)^\s*%s\s*\{(.*?)^\s*\}" % re.escape(patch), boundary, flags=re.S
    )
    if not match:
        return None
    body = match.group(1)
    nonuniform = re.search(
        r"value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(\s*(.*?)\s*\)\s*;", body, flags=re.S
    )
    if nonuniform:
        return [float(item) for item in nonuniform.group(2).split()]
    uniform = re.search(r"value\s+uniform\s+([^;]+);", body)
    if uniform:
        return [float(uniform.group(1))]
    return None


def output_times(case: Path) -> list[tuple[float, Path]]:
    result = []
    for path in case.iterdir():
        if not path.is_dir():
            continue
        try:
            angle = float(path.name)
        except ValueError:
            continue
        if all((path / name).exists() for name in ("rho", "Vc", "phi")):
            result.append((angle, path))
    return sorted(result)


def audit_case(case: Path, field: str = "tracer") -> dict[str, object]:
    times = output_times(case)
    if not times:
        raise ValueError(f"{case} has no output times with rho, Vc and phi")
    rows: list[dict[str, object]] = []
    previous_ms: float | None = None
    for angle, directory in times:
        volume = list(values(directory / "Vc"))
        count = len(volume)
        rho = list(values(directory / "rho", expected_count=count))
        scalar = list(values(directory / field, expected_count=count))
        if not (len(rho) == len(scalar) == count):
            raise ValueError(f"field lengths differ at {directory}")
        mass = sum(r * v for r, v in zip(rho, volume))
        tracer_mass = sum(r * v * s for r, v, s in zip(rho, volume, scalar))
        patches: dict[str, dict[str, float]] = {}
        for patch in ALL_PATCHES:
            flux = patch_values(directory / "phi", patch)
            if flux is None:
                continue
            patches[patch] = {
                "sum": sum(flux),
                "max_abs": max(abs(item) for item in flux),
            }
        rows.append({
            "crank_angle_deg_atdc": angle,
            "mass_kg_sector": mass,
            "tracer_mass_kg_sector": tracer_mass,
            "tracer_mass_increment": None if previous_ms is None else tracer_mass - previous_ms,
            "tracer_min": min(scalar),
            "tracer_max": max(scalar),
            "patch_phi": patches,
        })
        previous_ms = tracer_mass

    mass0 = rows[0]["mass_kg_sector"]
    tracer0 = rows[0]["tracer_mass_kg_sector"]
    if mass0 <= 0 or tracer0 <= 0:
        raise ValueError("reference mass or tracer mass is not positive")
    for row in rows:
        row["mass_drift_rel"] = row["mass_kg_sector"] / mass0 - 1.0
        row["tracer_inventory_drift_rel"] = row["tracer_mass_kg_sector"] / tracer0 - 1.0
        increment = row["tracer_mass_increment"]
        row["tracer_increment_rel"] = None if increment is None else increment / tracer0

    increments = [row for row in rows if row["tracer_increment_rel"] is not None]
    worst = max(increments, key=lambda row: abs(row["tracer_increment_rel"]))
    wall_flux = {
        patch: max(row["patch_phi"][patch]["max_abs"] for row in rows if patch in row["patch_phi"])
        for patch in ALL_PATCHES
        if any(patch in row["patch_phi"] for row in rows)
    }
    at_targets = []
    for target in TARGET_ANGLES:
        row = min(rows, key=lambda item: abs(item["crank_angle_deg_atdc"] - target))
        at_targets.append({
            "requested_crank_angle_deg_atdc": target,
            "sampled_crank_angle_deg_atdc": row["crank_angle_deg_atdc"],
            "mass_drift_rel": row["mass_drift_rel"],
            "tracer_inventory_drift_rel": row["tracer_inventory_drift_rel"],
            "tracer_min": row["tracer_min"],
            "tracer_max": row["tracer_max"],
        })
    return {
        "case": str(case),
        "field": field,
        "output_times": len(rows),
        "first_written_crank_angle_deg_atdc": rows[0]["crank_angle_deg_atdc"],
        "initial_tracer_mass_fraction": tracer0 / mass0,
        "max_abs_mass_drift_rel": max(abs(row["mass_drift_rel"]) for row in rows),
        "max_abs_tracer_inventory_drift_rel": max(
            abs(row["tracer_inventory_drift_rel"]) for row in rows
        ),
        "final_tracer_inventory_drift_rel": rows[-1]["tracer_inventory_drift_rel"],
        "largest_tracer_increment_rel": worst["tracer_increment_rel"],
        "largest_tracer_increment_crank_angle_deg_atdc": worst["crank_angle_deg_atdc"],
        "tracer_min": min(row["tracer_min"] for row in rows),
        "tracer_max": max(row["tracer_max"] for row in rows),
        "max_abs_patch_phi_kg_per_s": wall_flux,
        "at_targets": at_targets,
    }


def print_summary(result: dict[str, object]) -> None:
    print(f"case: {result['case']}")
    print(
        f"  outputs={result['output_times']} initial tracer mass fraction="
        f"{result['initial_tracer_mass_fraction']:.6f}"
    )
    print(
        f"  max|mass drift|={result['max_abs_mass_drift_rel']:.3e}  "
        f"max|tracer inventory drift|={result['max_abs_tracer_inventory_drift_rel']:.3e}  "
        f"final={result['final_tracer_inventory_drift_rel']:+.3e}"
    )
    print(
        f"  largest per-output tracer increment {result['largest_tracer_increment_rel']:+.3e} at "
        f"{result['largest_tracer_increment_crank_angle_deg_atdc']:.2f} CAD; tracer in "
        f"[{result['tracer_min']:.3e}, {result['tracer_max']:.9f}]"
    )
    flux = ", ".join(f"{k}={v:.1e}" for k, v in result["max_abs_patch_phi_kg_per_s"].items())
    print(f"  max|phi| on patches: {flux}")
    print("  CAD      mass drift   tracer drift")
    for item in result["at_targets"]:
        print(
            f"  {item['sampled_crank_angle_deg_atdc']:8.2f} {item['mass_drift_rel']:+.3e} "
            f"{item['tracer_inventory_drift_rel']:+.3e}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", nargs="+", type=Path, help="OpenFOAM case directories")
    parser.add_argument("--field", default="tracer", help="passive scalar field name")
    parser.add_argument("--labels", nargs="*", default=None, help="labels matching the case list")
    parser.add_argument("--output", type=Path, default=None, help="JSON summary path")
    args = parser.parse_args()
    labels = args.labels or [case.name for case in args.cases]
    if len(labels) != len(args.cases):
        raise SystemExit("--labels must match the number of cases")
    results = {}
    for label, case in zip(labels, args.cases):
        result = audit_case(case.resolve(), args.field)
        results[label] = result
        print_summary(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
