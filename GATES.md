# Numerical and decision gates

This file defines acceptance gates before a campaign is launched. A run can be
useful while failing a gate, but its result must then be labeled a bound,
screening result, or numerical failure rather than promoted silently.

The gates are task-specific. Do not inherit reacting-engine defaults into a
nonreacting transport run without a reason.

## Common moving-mesh gates

| Gate | Requirement | Why |
|---|---:|---|
| Geometry/volume closure | <= 0.2% error versus analytic slider-crank volume at recorded outputs | Prevent mesh motion from changing the physical compression ratio |
| Mass conservation, closed cylinder | <= 1e-4 relative drift over the evaluated interval, with instantaneous residual reported | Scalar transport is not trustworthy if moving-mesh fluxes create or destroy gas |
| Mesh convergence on the answer | Required for any promoted scalar; target <= 5% change between the two finest practical meshes unless a looser threshold is justified in advance | Solver convergence is not answer convergence |
| Time-step convergence on the answer | Required after changing `maxDeltaT`, `maxCo`, sampling, or mesh-motion settings | A faster case is useful only if the measured observable is preserved |
| No null-as-physics | Solver stalls, NaNs, rejected CVODE/OpenFOAM states, or missing outputs are failures, not nonignition/extinction results | Avoid false physical classifications |

## Reacting Cantera / two-zone gates

| Gate | Requirement | Notes |
|---|---:|---|
| Inventory-based fuel conversion | Use global fuel inventory as the primary conversion metric | Source-term integration is localization only |
| Pressure coupling | Maximum zone pressure mismatch <= 0.10 bar for promoted two-zone cases | Existing Beta 2.4/2.6 screen |
| Crank-step convergence | Branch classification unchanged and key outputs stable on refinement | Existing accepted anchors converged from 0.25 to 0.03125 CAD |
| Numerical tolerance check | Representative stiff cases repeated at tighter CVODE tolerances | Beta 2.6 found <=0.010 bar IMEP drift and <0.5 K Tmax at the accepted tolerance |
| Conservative display-engine screen | Positive gross IMEP, 10-90% conversion, Tmax < 1600 K, MPRR <= 10 bar/deg, CA50 between -15 and +20 CAD ATDC | Screening gate, not hardware validation |
| Mechanism provenance | Mechanism source, conversion path, and validation status recorded | Parent retention is not experimental validation |

## Nonreacting CFD transport gates

| Gate | Requirement | Notes |
|---|---:|---|
| Max Courant | Default <= 1.0 for screening; tighten if answer changes | PIMPLE is implicit; accuracy, not mere stability, sets the useful limit |
| Output sampling | <= 5 CAD for broad transport screening; <= 0.5 CAD when differentiating local rates near TDC or comparing to reacting phasing | Local derivatives need denser output than integrated decay |
| Tracer boundedness | Report min/max tracer and reject material overshoot/undershoot | Passive scalar must remain physical |
| Tracer inventory conservation | Mass-weighted mean tracer drift <= 1e-4 relative for a closed no-flux case | Boundedness alone does not prove the transported scalar is conserved |
| Zone-volume stability | Boundary-zone fraction stable to <= 0.5% relative unless geometry intentionally changes it | Prevent zone definition from manufacturing apparent mixing |
| Cross-geometry mixing metric | Use whole-domain mass-weighted tracer RMS normalized by each case's own initial RMS for a global diagnostic; for a two-zone core/shell answer, also use a nominal 20% outer zone selected by cumulative mass at every output and normalize its zone contrast by its own initial contrast. Retain raw RMS and fixed-radius `DeltaC/tau_mix` as secondary diagnostics | A changed chamber alters both the seeded amplitude and the fixed-radius shell fraction; the zone-style result must hold the compared mass fraction constant rather than use a geometry-specific radial window |
| `tau_mix` promotion | Positive local derivative plus mesh/time-step convergence at the requested crank angle | Late-cycle flat/noisy derivatives must not be converted into huge finite times |
| Mass conservation | Required for every changed timestep, mesh, or geometry | `correctPhi=no` is accepted only conditionally where continuity has been demonstrated |
| Answer convergence table | At requested CAD, report direct normalized scalar amplitude plus any differentiated rate used for promotion | Do not promote a derivative while its underlying scalar metric is changing materially |
| Passive-scalar linear-solver convergence | The tracer owns an exact-keyword `tracer`/`tracerFinal` solver entry converged to the normalized-residual floor (`tolerance 1e-13; relTol 0`); never inherit the momentum/energy pattern entry. Report the tracer final residual and iteration count from the solver log, and audit inventory from solver-written `rho`/`Vc`/`phi` with `cfd/audit_scalar_inventory.py` | Under the shared `relTol 0.01` entry PBiCGStab stopped after one iteration per step and the signed residual leaked tracer mass during squish flow (S2 coarse `1.663e-4`, S1 `6.8e-5`, flat fine `2.4e-5` relative); the converged solve gives `9.9e-12` with the answer unchanged (Issue #10, `CFD02_S2_SCALAR_ISOLATION_REPORT.md`) |

### CFD-01 known status

- Volume closure: pass (~0.141%).
- TDC `tau_mix`: approximately converged, 10.27 / 10.35 / 10.65 ms.
- +45 CAD `tau_mix`: fail; 24.67 / 32.11 / 39.07 ms and still increasing.
- +90 CAD: do not report a physical negative mixing rate; direct `DeltaC`
  history is nearly flat and local differentiation is noise-sensitive.
- Mass conservation: **pass** from the stored v8 fields; maximum fine-mesh
  drift is `5.986e-7` relative (`5.986e-05%`) using the documented perfect-gas
  `p/(R T)` fallback. Tracer bounds also pass (`0` to `1`).
- `correctPhi=no`: accepted for the validated CFD-01 baseline because its
  closed-domain mass gate passes; reopen only if a new timestep, mesh, or
  geometry produces mass drift or another continuity failure.
- maxDeltaT sweep: 0.15 CAD is the recommended cap; 0.25 CAD passes the 5%
  answer gate but was not faster, while 0.35/0.45 CAD fail max Co.

### CFD-02 S1 metric warning

S1 coarse passes the mesh, Courant, volume, mass, and tracer-bounds gates, but
its inherited fixed-radius shell is not a constant ~20%-volume zone. From the
stored promoted history it is ~16.7% of chamber volume at BDC and ~8.65% near
TDC. Therefore S1's reported fixed-radius `DeltaC/tau_mix` cannot by itself be
used as an apples-to-apples two-zone transport comparison against CFD-01.

The same geometry change also changes the *initial* raw tracer amplitude:

- flat fine initial mass-weighted RMS: `0.39875866`
- S1 coarse initial mass-weighted RMS: `0.37335030`
- S1/flat initial raw-RMS ratio: `0.9363`

S1 therefore starts ~6.37% lower in raw RMS before any transport occurs. Raw
RMS remains useful as a physical amplitude, but it must not be the primary
cross-geometry mixing-efficiency metric.

### CFD-02 S1 comparison status

The stored CFD-01 fine and S1 coarse fields were reprocessed with the global
mass-weighted tracer metric. At TDC:

- raw RMS ratio `A_S1/A_flat = 0.8354`;
- **initial-normalized RMS ratio = 0.8922** (primary cumulative result);
- +/-5 CAD fitted `tau_S1 = 43.33 ms`, `R2=0.99952`;
- +/-5 CAD fitted `tau_flat = 39.51 ms`, `R2=0.99991`.

Interpretation: by TDC S1 has about 10.8% less of its own initial segregation
remaining than flat, but its local TDC decay rate is slower. The history shows
faster decay earlier in compression and weaker decay around/after TDC. This is
a changed transport history, not uniformly faster mixing.

The constant-mass-fraction reprocessing reverses the earlier S1 zone-style
interpretation: S1/flat normalized zone contrast is 1.3545 at TDC (greater
than one), with poor S1 local-fit R2. Keep the global RMS and mass-fraction
zone diagnostics separate; neither justifies S1 refinement or Cantera coupling
without a geometry-independent decision.

### CFD-02 S2 coarse status

S2 completed the bounded solve with mesh, volume, gas-mass, Courant, tracer
bounds, and output-cadence checks passing, but its mass-weighted tracer
inventory drift was `0.0167264%` (`1.67264e-4` relative), above the `0.01%`
(`1e-4` relative) gate. The S2 history is retained as an explicit
`gate_failed` diagnostic only. It does not qualify for medium/fine refinement,
Cantera coupling, or a geometry promotion. Its normalized-RMS comparison to S1
also misses the predeclared ~5% improvement threshold through -20 to TDC
(1.0468 at -20 CAD and 0.9987 at TDC).

A same-control `linearUpwind grad(tracer)` S2 rerun also fails the scalar
gates: inventory drift is `2.01883e-4` relative and the tracer minimum is
`-0.0192431`. This variant is retained as a numerical diagnostic, not as a
replacement scheme. No new squish geometry is authorized until a tracer
treatment passes both conservation and boundedness.

**Issue #10 resolution (2026-09-01).** The inventory loss was an unconverged
tracer linear solve, not a moving-mesh or wall-flux defect: the shared
`"(U|e|tracer).*" relTol 0.01` entry stopped PBiCGStab after one iteration
per step, and the signed residual removed tracer mass fastest between -30 and
-13 CAD. Solver-field audits show gas mass constant to `1e-10` and wall
`phi` at `<= 2.6e-23` kg/s in every stored case. With the exact-keyword
converged entry now in the base `fvSolution`, the same S2 coarse geometry,
mesh, schemes and controls give tracer inventory drift `9.9e-12` relative
(`1.6e-10` by the postprocessor), tracer in `[0, 1]`, unchanged volume,
Courant and mesh checks, and a physical answer that moves by at most
0.005%. Status: **one bounded, inventory-conserving passive-scalar treatment
is demonstrated on the existing S2 moving mesh** (`cfd02_s2_tighttol_*`,
`cfd/results/cfd02_scalar_inventory_audit.json`). The promoted S1 coarse and
flat fine histories carry the same defect below the gate (`6.8e-5`, `2.4e-5`);
regenerate flat, S1 and S2 with the converged solve before any cross-geometry
decision. Boundedness under the function object is real but rests on the
solver's small continuity error, because it is solved against the
thermodynamic density after `postSolve`; a structurally bounded alternative
(inert species in `multicomponentFluid`) is recorded in the report and is not
part of this gate. S3 and Cantera coupling remain blocked until the
regenerated three-geometry comparison exists.

## CFD performance gate

A performance change is accepted only if the physical answer stays inside its
numerical gate.

For `maxDeltaT` or MPI sweeps record:
- wall-clock runtime;
- accepted timesteps;
- max Courant;
- TDC mixing metric;
- +20 and +45 CAD values where resolvable;
- volume and mass closure.

Choose the fastest setting that preserves promoted observables. Do not select a
setting solely because the solver remains stable.

## Leakage-data acceptance gate

A leakage datum enters a quantitative scaling regression only if it can be
converted to physical flow/effective area without guessing the test fixture.

Accepted:
1. direct mass/volumetric flow with pressure and temperature;
2. differential leak-down with reference-orifice geometry or calibration curve;
3. repeated data from the same documented tester.

Qualitative only:
- leak-down percentages from unspecified testers;
- forum claims without test pressure/fixture;
- manufacturer adjectives such as "good compression."

Static leak-down and dynamic blow-by remain separate datasets.

## Evidence promotion language

- `CONFIRMED`: implementation cross-check or direct comparison to cited
  experiment within the stated model; never means the unbuilt engine is
  validated.
- `SCREENING`: useful model result whose controlling uncertainty is not yet
  measured/validated.
- `OPEN`: unresolved.
- `RETRACTED`: earlier claim no longer supported.

If a result fails one numerical gate but still bounds the answer, state the
direction of the bound explicitly.
