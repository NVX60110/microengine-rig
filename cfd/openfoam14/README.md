# OpenFOAM 14 CFD-01: cold-flow radial tracer

CFD-01 is a closed-cylinder, nonreacting moving-piston baseline for calibrating
the two-zone radial exchange closure. It does **not** modify or invoke the
canonical Cantera model.

## Model

- 8.5 mm bore, 7.0 mm stroke, CR 7.75, rod/stroke 1.6, 1200 rpm.
- Engine user time spans -180 to +180 CAD ATDC; the mesh is created at BDC.
- Initial air state: 3.0 bar and 300 K. All walls are no-slip, adiabatic, and
  scalar-impermeable. Momentum transport is laminar.
- The v14 `multiValveEngine` / `crankConnectingRodMotion` mover is adapted
  from `tutorials/XiFluid/kivaTest`, with no valves or topology changes.
- A 5-degree symmetry sector is used. A 50 micrometre slip/symmetry axis-core
  regularisation prevents a singular axis cell; planar sector chords and the
  core omission together remain inside the 0.2% slider-crank volume gate.
- `tracer=1` in the outer 20%-volume shell (`r > R sqrt(0.8)`, nominal shell
  thickness 0.447 mm) and `tracer=0` in the core. The runner writes this
  nonuniform field from mesh cell centres so the initialization is explicit.

OpenFOAM cannot use a case directory whose path contains spaces. Source stays
in this repository, while transient runs are placed in a WSL-local path.

## Run in WSL2

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig
export CFD01_RUN_ROOT="$HOME/OpenFOAM/cfd01-cold-flow-tracer"

python3 cfd/openfoam14/cold_flow_tracer/scripts/run_cfd01.py \
  --mesh all --overwrite --run-root "$CFD01_RUN_ROOT"

python3 cfd/openfoam14/cold_flow_tracer/scripts/collect_results.py \
  --run-root "$CFD01_RUN_ROOT"

python3 scripts/fits/cfd_mixing_closure.py \
  cfd/results/cfd01_scalar_history.csv \
  --output cfd/results/cfd01_two_zone_options.json

pvpython cfd/openfoam14/cold_flow_tracer/scripts/render_paraview.py \
  "$CFD01_RUN_ROOT/fine" --time=-90 \
  --output cfd/results/cfd01_piston_tracer.png
```

The runner writes `checkMesh` logs at BDC (`-180` CAD), TDC (`0` CAD), and
post-motion (`+180` CAD). It uses one processor with a configured `maxCo`
target of 0.15; the collector requires every measured maximum to remain at or
below the 0.5 validation limit.
`collect_results.py` refuses to promote a history when the fine run, Courant
limit, or 0.2% volume agreement gate has failed; all failures remain explicit
in `cfd/results/cfd01_mesh_convergence.csv`.

`cfd_mixing_closure.py` fits
`k_mix = pi^2 D/L^2 + C_s |u_p|/B` and writes a `TwoZoneOptions`-compatible
JSON payload. It does not alter `two_zone_model.py`.
