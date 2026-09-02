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
- Axis-core artifact (F26): every run carries a spurious axial jet in the
  innermost axis-core ring (5.5 m/s fine, 1.5-2.3 m/s coarse at -140 CAD
  against a 0.21 m/s piston) that sets the Courant-limited step; the
  physical mean Courant number is 0.002. The tracer is exactly zero inside
  r = 1 mm at every output, so promoted transport answers are unaffected, but
  diagnostics that sample the axis or whole-field velocity statistics must
  exclude the innermost rings. Do not raise `maxCo` to buy speed: the
  artifact grows to fill the allowance (17.6 m/s at 0.45). The speed lever is
  the axis treatment itself (`CFD01_TIMESTEP_FINE_REPORT.md`).
- Fine-mesh Courant candidates (F27): `maxCo 0.30` and `0.45` with
  `maxDeltaT 0.25` take 5,228 and 5,063 steps against 5,595, no wall-time
  gain, and both fail the run gate on a start-up Courant spike (1.58 and
  2.89 in the first six steps at the cap). The reference's reported maximum
  Courant 0.373 is the same start-up spike at the 0.15 cap, not a mid-cycle
  value. Keep `maxCo 0.15 / maxDeltaT 0.15`; a small initial `deltaT`
  belongs with the axis fix.
- Wedge axis (F28, Issue #17, for review): `run_cfd01.py --axis wedge
  --initial-delta-t 0.01` removes the F26 artifact on every flat mesh
  (axis velocity 0.214 m/s at 0.215 m/s piston, global maximum at the
  piston-liner corner), keeps `maxCo 0.15 / maxDeltaT 0.15`, and passes
  every gate: volume closure 0.1269%, gas mass `<= 4.8e-7`, tracer
  inventory `<= 8e-12`, tracer in `[0, 1]`, checkMesh OK, fine-mesh
  transport observables within 1.6% of the converged sector baseline. Fine
  runtime 1,882 -> 229 s. Until adopted, `sector` remains the default and
  the `_wedge` histories are candidates, not references. The 20%-mass-zone
  contrast differs by 5-7% between formulations on coarse and medium and by
  under 1.3% on fine: treat that metric as carrying about 7% coarse-mesh
  uncertainty wherever a coarse case (S1, S2) is compared to a fine one.

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

**Issue #10 root cause and fix (2026-09-01; gate closes on merge).** The
inventory loss was an unconverged tracer linear solve, not a moving-mesh or
wall-flux defect: the shared
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
flat fine histories carried the same defect below the gate (`6.8e-5`,
`2.4e-5`). Boundedness under the function object is real but rests on the
solver's small continuity error, because it is solved against the
thermodynamic density after `postSolve`; a structurally bounded alternative
(inert species in `multicomponentFluid`) is recorded in the report and is not
part of this gate.

**Regeneration under shared numerics (2026-09-01).** Flat coarse/medium/fine
and S1 coarse were regenerated from the corrected base case
(`CFD02_REGEN_TIGHT_REPORT.md`, F24-F25): every case conserves tracer
inventory to `<= 1.5e-11` relative with tracer in `[0, 1]`; flat fine TDC
`tau_mix` moves 10.655 -> 10.665 ms; and the three-geometry comparison
reproduces the legacy ratios to `<= 0.001` with all six comparison gates `ok`
(S1/flat 20%-mass-zone contrast 1.3541 at TDC, S2/flat 1.2608, S2/S1
normalized RMS 0.9987). Status: the scalar gate is met by every history in
`cfd/results/*_tight*`; the gate closes for the project when the Issue #10
branch is merged. Under the B1 rule the regenerated result does not favour
squish; S3 and S1/S2 Cantera coupling stay blocked pending that review.

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

## Thermal-clearance and sealing gate (C1)

| Gate | Requirement | Consequence |
|---|---:|---|
| Diameter/radius convention | Report bore and piston as diameters, clearance as radial; derive the factor of two in the method | A factor-of-two ambiguity is a hard documentation failure |
| Non-positive hot clearance | Preserve the signed value; zero is contact and negative values are interference | Do not clamp to zero or evaluate non-positive clearance as a positive annulus leak |
| Independent temperatures | Sweep piston and liner temperatures independently and state their source/classification | Isothermal results are a sensitivity case, not the default |
| Material provenance | Preserve designation, temperature range, CTE treatment, conductivity, source, and uncertainty/limitation | Random/untraceable property values cannot support a promotion |
| Leakage coupling | Keep cold static leak-down and hot dynamic blow-by rows separate; pass only positive hot clearance to `physics/annulus.py` | No single calibrated leak area may be inferred from this screen |
| Tolerance study | Vary bore, piston diameter, CTE, piston temperature, and liner temperature with explicit engineering assumptions | Fractions are sensitivity outputs, never production capability or measured probability |
| Architecture language | Report a feasibility envelope and unknowns; do not promote a ringless/ring/material architecture from C1 alone | Hardware decision remains open until warm direct-flow evidence |
| Thermal-state provenance | Identify whether the p/T history is measured, CFD-derived, or a calculated proxy; keep the existing constant-`h` closure separate from any angle-dependent sensitivity | A proxy RC result cannot be presented as a measured operating temperature |
| RC inspectability | Expose node masses/cp, conductance links, gas areas, cooling, cycle/idle treatment, warm-up convergence and conductivity scaling | Hidden or unbounded thermal coefficients are a method failure |
| Warm-up envelope | Report minimum/maximum piston-skirt and liner-TDC temperatures and intersect the inverse cold-fit constraints over the whole modeled cycle | Endpoint-only fits may miss startup interference or cold leakage |
| Periodic state | For a linear RC network solve the one-cycle map `(I-A)T*=b`, or demonstrate convergence to a stated tolerance; report residual separately from finite warm-up convergence | An arbitrary cycle cutoff cannot be promoted as thermal steady state |
| Energy balance | At periodic state, report gas input, ambient/block rejection, and their cycle residual | A temperature result without energy closure is incomplete |
| Local radial pairing | Evaluate crown/upper-liner, skirt/corresponding-liner and minimum path gap from temperatures at matching axial locations | A skirt-vs-TDC pair must not be treated as a universal local clearance |
| Thermal-to-leakage coupling | Feed only positive signed hot clearance into `physics/annulus.py`; retain pressure, temperature, viscosity and eccentricity | Non-positive clearance is contact/interference, not zero-flow calibration |
| Temperature sensitivity | Include independent piston/liner temperature errors and label tolerance distributions as engineering sensitivity assumptions | Percentiles are not production probabilities or hardware capability |
| Measurement schema | Require local paired diametral dimensions, axial position/taper, independent piston/liner/gas temperatures, absolute pressures, flow reference state, lubricant condition and channel uncertainties | Incomplete rows remain invalid and cannot enter calibrated leakage evidence |
| Static/dynamic separation | Reduce static direct/differential rows to pressure-specific CdA/annulus residuals; retain dynamic blow-by without steady inversion unless pressure history is available | A cycle-averaged blow-by value is not a static leak calibration |
| Local thermal reconstruction | Pair piston and liner temperatures at the same axial station and preserve signed hot clearance | Remote temperature pairing or a zero-clamped contact state is a hard method failure |
| Clearance-exponent test | Fit a free `log(mdot)` versus `log(h_hot)` exponent only within like-for-like pressure, gas, geometry, lubricant and station groups | Do not force the exponent to three; report points and interval |
| Uncertainty provenance | Propagate supplied dimension, temperature, pressure, flow and viscosity uncertainties; label distributions as engineering assumptions | Percentiles are sensitivity outputs, not measured production probabilities |
| Calibration provenance | Record flow/pressure/temperature/dimensional zero and span checks; distinguish reference geometry from calibrated reference CdA | Geometry alone cannot create an absolute calibration |
| Synthetic isolation | Synthetic pipeline tests must use temporary files and never modify `data/leakage/records.csv` | Passing synthetic tests is not physical leakage evidence |
| Literature evidence provenance | Preserve source URL, access status, source locator, extraction method, classification and transferability for every thermal-literature value | Abstract summaries or digitized graphs cannot become model priors without explicit uncertainty and provenance |
| Literature-to-model boundary | Derive piston-minus-liner or normalized temperature quantities only from complete local paired rows | A temperature range, gradient or cooling delta without a matching liner state remains sensitivity context |
