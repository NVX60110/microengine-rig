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
| Cross-geometry mixing metric | If the core/shell volume fraction changes materially between geometries or through the cycle, use global mass-weighted tracer RMS/variance decay as the primary comparison; fixed-radius `DeltaC/tau_mix` becomes a geometry-specific diagnostic | A squish land can change the Eulerian shell volume even when the CFD is correct, making the original CFD-01 two-zone metric non-equivalent |
| `tau_mix` promotion | Positive local derivative plus mesh/time-step convergence at the requested crank angle | Late-cycle flat/noisy derivatives must not be converted into huge finite times |
| Mass conservation | Required for every changed timestep, mesh, or geometry | `correctPhi=no` is accepted only conditionally where continuity has been demonstrated |
| Answer convergence table | At requested CAD, report direct scalar amplitude plus any differentiated rate used for promotion | Do not promote a derivative while its underlying scalar metric is changing materially |

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
Reprocess CFD-01 and S1 with the global mass-weighted tracer RMS/variance
metric before running S2.

### CFD-02 S1 comparison status

The stored CFD-01 v8 fine and S1 coarse fields have now been reprocessed with
the global metric. At TDC, `A_S1/A_flat=0.8354` (raw mass-weighted RMS), while
the +/-5 CAD fit gives `tau_S1=43.33 ms` versus `tau_flat=39.51 ms`, with
`R2=0.99952` and `0.99991`. Keep both values: the amplitude indicates a lower
cumulative contrast, but the local rate does not establish uniformly faster
mixing. The comparison JSON is the current cross-geometry decision artifact.

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
