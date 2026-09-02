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
`collect_results.py` refuses to promote a history when the fine run, Courant,
0.2% volume, closed-cylinder mass (`1e-4` relative), or tracer-boundedness gate
has failed; all failures remain explicit in
`cfd/results/cfd01_mesh_convergence.csv`. Legacy runs without a saved `rho`
field use the documented perfect-gas `p/(R T)` fallback.

`cfd_mixing_closure.py` fits
`k_mix = pi^2 D/L^2 + C_s |u_p|/B` and writes a `TwoZoneOptions`-compatible
JSON payload. It does not alter `two_zone_model.py`.

## Converged tracer solve (Issue #10)

`system/fvSolution` carries an exact-keyword `tracer`/`tracerFinal` solver
entry (`tolerance 1e-13; relTol 0`). Under the shared `"(U|e|tracer).*"`
entry the passive-scalar PBiCGStab solve stopped after one iteration per step
and leaked tracer mass (flat fine `2.4e-5`, S1 `6.8e-5`, S2 `1.67e-4`
relative); the exact entry converges it to the residual floor and removes the
drift (`~1e-11`) for a few percent more runtime. Every runner inherits the
entry. See `CFD02_S2_SCALAR_ISOLATION_REPORT.md` for the isolation and
`CFD02_REGEN_TIGHT_REPORT.md` for the regenerated flat coarse/medium/fine
histories (`cfd/results/cfd01_scalar_history_*_tight.csv`, run root
`~/OpenFOAM/cfd01-cold-flow-tracer-v9`). The legacy promoted CFD-01 files are
kept as the pre-fix record; TDC `tau_mix` changed by at most 0.1%.

Audit any case from its solver-written `rho`, `Vc`, `tracer` and `phi`:

```bash
python3 cfd/audit_scalar_inventory.py "$CFD01_RUN_ROOT/fine" \
  --labels flat_fine --output cfd/results/my_audit.json
```

## maxDeltaT answer-convergence sweep

Issue #5 step 2 uses the coarse mesh to determine whether the 0.15 CAD
`maxDeltaT` cap is unnecessarily expensive. Run:

```bash
source /opt/openfoam14/etc/bashrc
export CFD01_TIMESTEP_ROOT="$HOME/OpenFOAM/cfd01-timestep-sweep"

python3 cfd/openfoam14/cold_flow_tracer/scripts/run_timestep_sweep.py \
  --caps 0.15 0.25 0.35 0.45 --overwrite \
  --sweep-root "$CFD01_TIMESTEP_ROOT"
```

The sweep holds `maxCo=0.15` fixed by default and changes only `maxDeltaT`.
Output cadence is adjusted automatically so the maximum nominal sampling gap
stays at or below 0.5 CAD. It also accepts `--mesh {coarse,medium,fine}`,
`--max-co` (gate maximum 0.5) and `--reference-history <csv>` to judge a
candidate against an existing gate-clean history instead of rerunning the
0.15/0.15 baseline; every run must also pass the tracer-inventory gate.

Before spending Courant headroom, read `CFD01_TIMESTEP_FINE_REPORT.md`: the
step on every sector mesh is set by a spurious axis-core velocity, not by the
physical flow, and raising `maxCo` enlarges that artifact instead of the
step. The tracer function object now carries its own write control so the
field is written at the snapshot cadence rather than every step. The sweep
also accepts `--axis` and `--initial-delta-t`, passed to `run_cfd01.py`.

## Wedge axis (Issue #17, candidate)

`run_cfd01.py --axis wedge` replaces the 50 micrometre `symmetry` axis core
and three-cell sector with OpenFOAM's standard single-cell `wedge` axis
(axis collapsed to an edge, `wedge` side patches, triangular head and piston
faces). `--initial-delta-t 0.01` removes the first-step Courant spike. With
`maxCo 0.15 / maxDeltaT 0.15` unchanged this removes the F26 artifact on
every mesh, runs the fine case in 229 s instead of 1,882 s, and keeps every
fine-mesh transport observable within 1.6% of the converged sector baseline
(`CFD01_WEDGE_AXIS_REPORT.md`, F28). The default stays `sector` until the
result is reviewed; the wedge histories are
`cfd/results/cfd01_scalar_history_{coarse,medium,fine}_wedge.csv`.

```bash
python3 cfd/openfoam14/cold_flow_tracer/scripts/run_cfd01.py \
  --mesh fine --axis wedge --initial-delta-t 0.01 --overwrite \
  --run-root "$HOME/OpenFOAM/cfd01-axis/wedge_dt0p01"
```

Each run records runtime, accepted steps, maximum Courant,
volume error, closed-cylinder mass drift, tracer bounds, and `DeltaC/k_mix/tau`
at -20, 0, +20, and +45 CAD.

The 0.15 CAD run is the answer reference. A faster setting is accepted only if
all numerical gates pass and the largest relative change in both `DeltaC` and
finite `tau_mix` across those requested angles is <=5%. The summary is written
to `cfd/results/cfd01_timestep_sweep.csv`; individual transient histories stay
in the WSL-local sweep directory.
