# CFD-02 S2 scalar-inventory isolation report (Issue #10)

Scope: isolate why the S2 coarse passive tracer lost inventory on the moving
mesh, prove one treatment that is inventory-conserving and bounded on the
**existing S2 coarse geometry**, and stop there. No S3, no refinement, no
Cantera coupling, no new geometry comparison is made in this report.

Result: the loss was an **unconverged linear solve of the tracer equation**,
not a moving-mesh, flux-dimension, or boundary-flux defect. Converging that
solve reduces the S2 coarse inventory drift from `1.663e-4` to `9.9e-12`
relative with the tracer still inside `[0, 1]` and every other gate unchanged.
The physical S2 answer moves by at most 0.005%.

## 1. Equation and data path actually used (source-verified, OpenFOAM 14)

The tracer is solved by the `scalarTransport` function object
(`src/functionObjects/solvers/scalarTransport/scalarTransport.C`). Because the
solver flux `phi` has dimensions of mass flow, the compressible branch runs:

```
ddt(rho, tracer) + div(phi, tracer) - laplacian(rho*D, tracer) = 0
D = alphal*nu = 1.408*nu            (Schmidt number 0.71)
```

with `rho` and `phi` looked up by name from the solver. Findings that matter:

- **Execution order.** `foamRun` calls `solver.postSolve()`, then
  `runTime.write()`, and only then `pimple.run(runTime)`, whose `Time::run()`
  executes function objects. The tracer is therefore solved *after* the step
  is complete and written; the `writeObjects` function object rewrites
  `tracer` (and `rho`) into the time directory afterwards, so stored fields
  are self-consistent.
- **Density handed to the tracer.** `isothermalFluid::postSolve()` ends every
  transient step with `rho_ = thermo.rho()`, i.e. the thermodynamic density
  `psi*p`, replacing the continuity solution from `correctDensity()`. The
  function object's `rho` and `rho.oldTime()` are both thermodynamic
  densities; `phi` is the final pressure-equation flux made relative to the
  mesh motion by `fvc::makeRelative`.
- **Moving-mesh time term.** `EulerDdtScheme::fvmDdt(rho, vf)` uses the
  current volume `Vsc()` on the diagonal and the old volume `Vsc0()` in the
  source when the mesh is moving, so the volume change is accounted for.
- **Consequence for conservation.** Every term is a finite-volume flux or a
  cell term, so summing the discrete equation over all cells telescopes: the
  tracer mass `sum(rho*tracer*V)` can change only through boundary fluxes and
  the residual left by the linear solver. Neither the thermodynamic-density
  substitution nor the `correctPhi=no` setting can destroy tracer mass.
- **Consequence for boundedness.** The `(rho_thermo, phi)` pair does not
  satisfy discrete continuity exactly; the mismatch is the solver's own
  "time step continuity errors" line (S2: sum local up to `4.96e-5`, median
  `2.6e-10`). With upwind convection the scalar cannot become negative, and an
  overshoot above 1 is bounded by that continuity error; none occurred. The
  boundedness pass is therefore real but not structurally guaranteed by this
  function object. Section 6 records the structural alternative.

## 2. Inventory from solver-written fields and wall fluxes

`cfd/audit_scalar_inventory.py` integrates the solver's own `rho`, `Vc`,
`tracer` and `phi` (including boundary patch values) at every written time.
Record: `cfd/results/cfd02_scalar_inventory_audit.json`.

| case | tracer solve | max gas-mass drift | max tracer-inventory drift | final | largest per-output loss (at CAD) | max wall `phi` (kg/s) | tracer bounds |
|---|---|---:|---:|---:|---:|---:|---|
| S2 coarse upwind (baseline) | legacy, relTol 0.01 | `1.6e-10` | `1.663e-4` | `-1.663e-4` | `-3.41e-6` (-15.75) | piston `2.6e-23`, liner `1.5e-36` | `[6.7e-56, 0.99999]` |
| S2 coarse linearUpwind | legacy | `1.6e-10` | `2.009e-4` | `-1.905e-4` | `-4.38e-6` (-15.75) | same | `[-1.92e-2, 0.99999]` |
| **S2 coarse upwind, converged** | **tight** | `1.6e-10` | **`9.94e-12`** | `-8.3e-12` | `-2.9e-12` (-49.95) | same | `[1.1e-54, 0.99999]` |
| S1 coarse upwind (promoted) | legacy | `3.7e-10` | `6.826e-5` | `-6.826e-5` | `-7.91e-7` (-11.96) | piston `2.6e-23` | `[1.3e-53, 0.99992]` |
| flat fine v8 (promoted) | legacy | `5.4e-10` | `2.404e-5` | `+1.09e-5` | `+5.52e-7` (-11.40) | piston `6.6e-24` | `[1.1e-95, 1.0]` |

What the table isolates:

- Gas mass is constant to `1e-10` in every case from the solver's own density.
  The `6e-7` "mass drift" reported by `postprocess_history.py` is the
  perfect-gas `p/(R T)` fallback applied to the copied `-180` initial
  directory, which contains no solver `rho`; it is a reference-point artifact,
  not a solver drift, and stays far under the gate.
- Wall and symmetry fluxes are at round-off (`<= 2.6e-23` kg/s on walls
  against interior fluxes of order `1e-7`). The piston, including the S2
  bowl's vertical wall, is impermeable. There is no ALE leak.
- The tracer loss in S1 and S2 is monotonic and concentrated in late
  compression: S2 loses fastest between -30 and -13 CAD, S1 around -12 CAD,
  where squish flow and the shell gradients are strongest. Flat fine shows the
  same magnitude of per-output error but with changing sign, so its net drift
  is smaller. The loss scales with squish intensity: flat `2.4e-5`, S1
  `6.8e-5`, S2 `1.66e-4`.

## 3. Root cause: the tracer linear system was not converged

`fvSolution` supplied the tracer through the shared entry
`"(U|e|tracer).*" { tolerance 1e-8; relTol 0.01; }`. The S2 baseline log shows
every tracer solve stopping after **one** PBiCGStab iteration:

| quantity | S2 baseline | S2 converged |
|---|---:|---:|
| tracer initial residual, median / max | `3.4e-4` / `3.5e-3` | same |
| tracer final residual, median / max | `3.7e-8` / `1.2e-6` | `3.7e-15` / `1.0e-13` |
| iterations, median / max | 1 / 1 | 2 / 3 |
| OpenFOAM execution time | 224.5 s | 239.9 s |

A residual left after one iteration on an upwind-implicit transport matrix has
a spatially coherent, signed sum during strong convective transport, and that
signed sum is exactly the per-step change in `sum(rho*tracer*V)`. The bound
`|dMs| <= dt*sum|residual|` is consistent with the observed `~1e-6` per-step
loss during squish. S1's smaller loss matches its smaller final residuals
(max `3.5e-7`).

## 4. Smallest justified change and gate result on the existing S2 mesh

Change: an exact-keyword `tracer` / `tracerFinal` solver entry in the base
`cfd/openfoam14/cold_flow_tracer/system/fvSolution` (exact keys override
pattern entries), converging the linear solve:

```
tracer { solver PBiCGStab; preconditioner DILU; tolerance 1e-13; relTol 0; maxIter 500; }
tracerFinal { $tracer; }
```

Nothing else changed: same S2 coarse geometry (2,823 cells), mesh motion,
schemes (`div(phi,tracer) Gauss upwind`), `maxCo 0.15`, `maxDeltaT 0.15`,
`correctPhi no`, initial tracer field and zone definition (initial tracer mass
fraction `0.193123` in both runs). Run directory
`/home/gflip/OpenFOAM/cfd02-squish-tighttol/s2_coarse`; promoted files
`cfd/results/cfd02_s2_tighttol_*`.

| Issue #10 gate | requirement | converged S2 coarse | status |
|---|---:|---:|---|
| tracer inventory drift | `<= 1e-4` relative | `1.63e-10` (postprocessor), `9.94e-12` (solver fields) | pass |
| tracer bounded | `[0, 1]` to `1e-9` | min `0.0`, max `1.0` | pass |
| gas mass drift | `<= 1e-4` relative | `5.98e-7` (postprocessor, fallback artifact), `1.6e-10` (solver fields) | pass |
| volume closure | `<= 0.2%` | `0.1499%` | pass |
| max Courant | `<= 0.5` | `0.1908` | pass |
| same initial inventory / zone | documented | identical initialisation, `0.193123` | pass |
| checkMesh BDC / TDC / +180 | Mesh OK | OK / OK / OK | pass |

## 5. Effect on the S2 answer

Baseline versus converged S2 coarse at the requested angles:

| CAD | normalized mass-weighted RMS, baseline / converged | change | 20%-mass zone contrast, baseline / converged | change |
|---:|---:|---:|---:|---:|
| -20 | 0.534042 / 0.534048 | +0.001% | 0.381782 / 0.381781 | -0.000% |
| 0 | 0.472936 / 0.472946 | +0.002% | 0.313057 / 0.313042 | -0.005% |
| +20 | 0.436058 / 0.436061 | +0.001% | 0.325757 / 0.325741 | -0.005% |
| +45 | 0.406118 / 0.406118 | 0.000% | 0.252513 / 0.252503 | -0.004% |

The earlier S2 diagnostics (`CFD02_S2_REPORT.md`, `CFD02_ZONE_REPROCESS_REPORT.md`)
were therefore not biased by the leak; the gate was correctly refusing an
unconverged solve. Those diagnostics remain diagnostics until the geometry
comparison is redone under one set of numerics (Section 6).

## 6. What this does and does not establish

Established:

- A bounded, inventory-conserving passive-scalar treatment exists on the S2
  moving mesh: the existing function object with a converged linear solve.
- The moving-mesh machinery (`multiValveEngine` morphing, relative fluxes,
  `correctPhi no`, Euler moving-mesh time term) conserves gas and scalar mass
  to round-off. `correctPhi no` stays accepted under F11.

Not established, and deliberately not attempted here:

- **S1 and flat carry the same defect below the gate.** The promoted S1
  coarse and flat fine histories were produced with the unconverged solve
  (`6.8e-5` and `2.4e-5` drift). They remain valid under their gates, but any
  cross-geometry comparison used for a decision should regenerate flat, S1
  and S2 with the base `fvSolution` now in the repository so all three share
  numerics. This is the next bounded CFD action; it is not part of Issue #10.
- **Structural boundedness.** The function object solves against the
  thermodynamic density after `postSolve`, so its boundedness rests on the
  solver's continuity error being small (`<= 5e-5` local here). If the
  reacting/Cantera coupling later needs a scalar whose boundedness is
  guaranteed by construction, the correct route in this solver family is to
  carry the tracer as an inert species in `multicomponentFluid`: its
  `YiEqn` is solved inside the PIMPLE loop against the continuity-consistent
  density from `correctDensity()` with the same `phi`, and the laminar
  default `unityLewisFourier` gives `D = nu/Pr = 1.408*nu`, identical to the
  present diffusivity. Recipe for that future run: two species with identical
  properties (`AIR`, `TRACER`, `defaultSpecie AIR`), `div(phi,Yi_h)`
  as `multivariateSelection { TRACER upwind; e vanAlbada; }`, a converged
  `"Yi.*"` solver entry, and the tracer initialisation written to `TRACER`.
  It changes the solver module and must be validated against the converged
  function-object result before it replaces anything.
- No scheme other than upwind is promoted. The `linearUpwind` variant remains
  a failed diagnostic; with the converged solve it would still be unbounded.

## Reproduction

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig

# Converged solve (default) on the existing S2 coarse geometry
python3 cfd/openfoam14/squish/run_s2_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish-tighttol \
  --output cfd/results/cfd02_s2_tighttol_scalar_history.csv --overwrite

# Reproduce the failed baseline exactly
python3 cfd/openfoam14/squish/run_s2_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish --tracer-solver legacy --overwrite

# Solver-field inventory and wall-flux audit
python3 cfd/audit_scalar_inventory.py \
  /home/gflip/OpenFOAM/cfd02-squish/s2_coarse \
  /home/gflip/OpenFOAM/cfd02-squish-tighttol/s2_coarse \
  --labels s2_coarse_upwind_legacy s2_coarse_upwind_tight \
  --output cfd/results/cfd02_scalar_inventory_audit.json
```

## Artifacts

- `cfd/results/cfd02_s2_tighttol_scalar_history.csv`, `_mixing_time.csv`,
  `_metadata.json` (status `ok`, `tracer_solver: tight`)
- `cfd/results/cfd02_scalar_inventory_audit.json` (five stored cases)
- `cfd/audit_scalar_inventory.py`, `tests/test_s2_runner.py`
- `cfd/openfoam14/cold_flow_tracer/system/fvSolution` (exact-keyword tracer entry)
- `cfd/openfoam14/squish/run_s2_cfd.py` (`--tracer-solver tight|legacy`)
- Unchanged failed diagnostics: `cfd02_s2_coarse_*`, `cfd02_s2_linearupwind_*`
