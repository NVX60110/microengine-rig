# Plan

Status after Beta 2.6 and CFD-01. This file is the current project routing document.
Read `FINDINGS.md`, `BETA26_REPORT.md`, and `CFD01_REPORT.md` before using any
headline number.

Project rule: be thorough about the number the next decision depends on and
coarse about everything else.

---

## Current phase — low-idle feasibility

The immediate target is a physically credible low idle, not a 25,000-rpm
redline. The completed closed-pass screen finds a nominal all-mechanism window
of approximately 1.11–2.0 krpm under the accepted Beta 2.6 state. The lower
crossing is controlled by the campaign-specific 0.87 retained-mass condition;
it is not a physical stable-idle prediction. At 1,200 rpm the nominal screen
passes, but `OP_IDLE_REPORT.md` classifies hardware idle as **possible but
fragile** because sealing is uncalibrated and the model omits the gas-exchange
revolution, pumping, residuals, friction, inertia, motor control and cycle
variability.

The next simulator change is therefore narrowly justified: add a periodic
720-CAD gas-exchange/crank layer and require mass/species/energy/speed closure.
Do not add CFD, lubrication, ring-pack or general thermal complexity to that
branch unless the repeat-cycle experiment exposes a decision-limiting need.

The parallel sealing result is an axial feasibility envelope, not a drawing:
8.5 mm Al-4032/4140 requires about 8.90–11.71 µm cold radial under constant h
or 12.76–15.40 µm under the angle sensitivity to retain 2–5 µm hot in the
neutral proxy. Preheat is not assumed monotonic and no safe-cranking
temperature is claimed.

---

## Where things stand

### Chemistry

Established:
- The Nordin n-heptane mechanism reproduces the selected shock-tube dataset with
  median sim/exp 1.527 and 84.8% of points within 2x. This validates that
  particular mechanism against that particular experiment; it is not a direct
  DME/methane error bar.
- Zhao sk39 retains the delay shape of its supplied Zhao parent closely in the
  pure-DME parent-retention test.
- A universal +/-50% engine-IMEP chemistry uncertainty is **retracted**. Use
  mechanism envelopes and transition-location intervals instead.
- Burke et al. (2015) provides direct DME/methane ignition-delay experiments at
  project-relevant compositions and pressures: pure fuels, 80/20 and 60/40
  CH4/DME, 600-1600 K, 7-41 atm, and phi 0.3-2.0.

Open:
- The Burke 2015 point table is still not machine-readable in the recovered
  Galway material. A separate Zinner (2008) thesis appendix has now been
  ingested as measured 80/20 and 60/40 blend rows; it is a related upstream
  dataset, not a substitute for the Burke 2015 supplement. The next chemistry
  step is to run the direct gate on each dataset only with its own provenance.
- Zhao parent pressure-dependent DME decomposition-rate selection remains
  unaudited for the project's 25-90 bar in-cylinder range.

### Cantera/two-zone model

- The motor-driven display-engine architecture remains the working architecture.
- Localizing wall heat into a boundary zone removes the homogeneous hot-wall
  runaway at the shared CR7 anchors and leaves bounded partial oxidation.
- Radial core/boundary transport is the dominant model-form uncertainty.
- Beta 2.6 found a conditional island at 3.0 bar, CR 7.75-8.0,
  3 micrometre/e=0.5 annular leakage, and the central provisional mixing
  closure. All three chemistry mechanisms passed the conservative screen there.
- No point is robust to every deliberately broad mixing and sealing bracket.
  This is a request for better transport and sealing data, not a hardware
  design point.

### CFD-01 flat-piston transport

CFD-01 is merged to main; the accepted flat reference uses the single-cell
`wedge` axis treatment from Issue #17.

- Geometry: 8.5 x 7.0 mm, CR 7.75, 1200 rpm, cold closed cylinder, passive
  tracer, flat piston.
- TDC mixing time on the fine mesh: **10.655 ms**.
- The TDC answer is approximately mesh-converged: coarse 10.27 ms, medium
  10.35 ms, fine 10.65 ms.
- The fitted piston-strain coefficient is zero; the measured TDC timescale also
  agrees with the first molecular-diffusion mode,
  `tau ~ L^2/(pi^2 D)`. No hidden flat-piston convective mixing was found.
- The +45 CAD value is **not** mesh-converged. Fine-mesh 39.07 ms is a lower
  bound until a finer run closes it.
- The reported +90 CAD local negative derivative is a differentiation artifact
  on a nearly flat concentration-difference history, not evidence of
  "un-mixing." The direct concentration difference should be treated as a
  plateau there.
- The provisional single scalar `tau_mix` is therefore obsolete. Use the
  measured/scheduled `tau(theta)` where available; CFD-02 squish is intended to
  test whether geometry can create a meaningful convective term.

### Sealing and mechanics

Established:
- Full-size blow-by literature constrains model architecture and uncertainty
  width; it does not directly calibrate an 8.5 mm cylinder.
- Annular clearance and eccentricity remain strong work levers.
- Mean piston speed is low (0.28 m/s at 7 mm/1200 rpm), which is favorable for
  friction, but the earlier exact FMEP range was retracted.
- Valve-flow-area screening shows large headroom at 1200 rpm, but a complete
  pumping/friction model is still absent.

Open:
- No target microengine hardware has been leak-down or blow-by tested.
- A single-orifice ring-pack proxy is only a pessimistic model class, not a
  calibrated ring pack.

---

## Track A - Chemistry

| # | Task | Why | Gate / output |
|---|---|---|---|
| A1 | Obtain or digitize Burke et al. 80/20 and 60/40 CH4/DME ignition-delay points; use Zinner rows as a separate upstream validation set | Direct validation is now available; ReSpecTh is not the only path | Preserve facility, pressure, phi, uncertainty, and the paper's ignition criterion; do not merge Zinner into Burke |
| A2 | Run `mechanism_gate.py` on the Burke and Zinner sets for Zhao sk39/full and LLNL where compatible | Replaces cross-fuel inference with direct DME/methane evidence | Report sim/exp distributions, nonignitions, and low-T subset; keep dataset provenance and ignition criteria separate |
| A3 | Audit Zhao pressure-dependent decomposition reactions | Source header requires rate selection by pressure | Document selected channels/rates for 25-90 bar and rerun transition anchors if changed |
| A4 | Map max-dP/dt ignition-delay sensitivity around the accepted island | Quantifies how sharp the chemistry boundary is | Report local slopes and transition intervals, not universal percent uncertainty |

ReSpecTh remains useful if it supplies original machine-readable points, but it
is no longer a project blocker.

---

## Track B - CFD

### B0 - CFD-01 cleanup before new physics (complete)

1. Recompute/report mesh convergence **on tau_mix at requested crank angles**.
2. Rerun +45 CAD on at least one finer mesh.
3. Add closed-domain mass-conservation accounting over the moving-mesh cycle
   (**complete for stored v8 fields**; maximum fine drift 5.986e-7 relative).
4. Keep `correctPhi=no` for the validated baseline; reopen only if a new case
   fails continuity or mass closure.
5. Sweep `maxDeltaT` on the coarse case and choose the largest value that leaves
   the measured transport answer inside the gate (**complete**: 0.25 passes
   answer gates but is not faster; retain 0.15 because 0.35/0.45 fail max Co).
6. Replace the fixed closure fit with a `tau(theta)` table/interpolant, or fit a
   geometry-aware closure only after the direct table is preserved.

### B1 - Squish geometry

This is the next physics question.

Flat-piston CFD found no useful convective contribution. Squish is therefore the
remaining intentional route to convective radial transport.

Decision:
- If squish materially reduces TDC `tau_mix` below the ~10.65 ms flat-piston
  baseline while passing mesh/mass/volume gates, feed the measured schedule back
  into the two-zone ensemble.
- If it does not, accept flat-piston molecular diffusion as the transport scale
  and stop optimizing hidden stirring.

Status update: the original fixed-radius shell diagnostic was not
cross-geometry comparable (the shell fraction collapsed from ~16.7% at BDC to
~8.65% near TDC).  The corrected solver and regenerated histories now pass
the scalar inventory/boundedness gates, and the fixed 20%-mass-zone audit gives
S1/flat 1.354x and S2/flat 1.261x zone contrast at TDC; whole-domain normalized
RMS is 0.892 and 0.891.  Neither tested squish geometry delivers the declared
transport gain, so do not run S3 or couple S1/S2 schedules into Cantera.

Issue #10 resolution (2026-09-01): the S2 inventory loss was the tracer linear
solve stopping after one PBiCGStab iteration under the shared `relTol 0.01`
solver entry, not a moving-mesh or wall-flux defect. The base `fvSolution`
now carries an exact-keyword converged `tracer` entry; on the identical S2
coarse case it gives `9.9e-12` relative inventory drift, tracer in `[0, 1]`,
all other gates unchanged, and a physical answer that moves by <= 0.005%
(`CFD02_S2_SCALAR_ISOLATION_REPORT.md`, F21-F23). The promoted S1 and flat
histories carry the same defect below the gate (`6.8e-5`, `2.4e-5`).

Regeneration status (2026-09-01, `CFD02_REGEN_TIGHT_REPORT.md`): flat
coarse/medium/fine and S1 coarse were regenerated from the corrected base
case and compared with the converged S2. Every case conserves inventory to
`<= 1.5e-11`, every answer is within 0.14% of legacy, and the three-geometry
ratios reproduce legacy to `<= 0.001` with all comparison gates `ok`
(F24). Under the B1 rule the regenerated result does not favour squish: the
fixed 20%-mass-zone contrast at TDC is 1.354x flat for S1 and 1.261x for S2
(F25).

Issue #10 is merged and closed. Issue #17 is also merged and closed: the
single-cell `wedge` axis removes the artifact on every flat mesh, runs the
fine case in 229 s instead of 1,882 s, and keeps fine-mesh transport
observables within 1.6% of the converged sector baseline (F28,
`CFD01_WEDGE_AXIS_REPORT.md`).

Next actions, in order:
1. Treat the accepted `wedge` CFD-01 case and `_wedge` histories as the flat
   references; convert any future squish generator to the same axis treatment
   before a new comparison. This is cheap performance and hygiene work, not
   an engine-design blocker; it should not displace sealing and chemistry.
2. Decide the B1 question from F25. Recommendation: accept the flat-piston
   `tau(theta)` scale from the converged CFD-01 fine history as the transport
   baseline, run no S3, and couple no S1/S2 schedule into the two-zone model.
   The only justified counter-check is a medium-mesh S1 against the 1.354x
   zone result, noting the roughly 7% coarse-mesh uncertainty of the zone
   metric quantified in F28.
3. Only if Cantera coupling needs a scalar bounded by construction, build and
   validate the `multicomponentFluid` inert-species tracer variant against
   the converged function-object result before it replaces anything.

### B2 - Bore/geometry screen

Only after B1. Bore alone is a weaker S/V lever than clearance height:
`S/V = 2/h + 4/B`. Do not spend CFD hours on bore changes until the transport
decision is closed.

---

## Track C - Sealing

### C1 - Calibrated leakage scaling study

#### C1 thermal-clearance feasibility screen (completed screening step)

The analytical thermal-fit screen is now implemented in
`physics/thermal_clearance.py` and `scripts/thermal_clearance_sweep.py`.
It covers 8.5 mm and 12.5 mm bridges, independent piston/liner temperatures,
screened material pairs, signed hot clearance, annulus leakage sensitivity,
and an explicitly assumed tolerance Monte Carlo.  Results and the limitation
statement are in `THERMAL_CLEARANCE_REPORT.md` and `data/sealing/`.

This does **not** close calibrated C1.  It establishes that the prior 2/3/5 µm
values are engineering brackets, not universal hot fits: for the representative
Al 4032/4140 pair, approximately 10.7–14.1 µm cold radial clearance is needed
for a 3–5 µm hot target at 500/450 K, and the answer remains highly sensitive
to independent temperature error.  The next C1 step is a warm, direct-flow
fixture on a 10–15 mm reference cylinder with axial fit/taper and independent
piston/liner temperature measurements.

#### C1 thermal-state RC follow-up (completed screening step)

`physics/thermal_state.py` and `scripts/thermal_state_rc.py` now provide a
seven-node, inspectable piston/liner thermal RC screen.  It consumes the only
existing heat-transfer input—a calculated `microengine_rig.py` history with
constant `h=600 W/(m² K)`—and carries the solids through repeated modeled
100 ms cycles (360° pass plus an explicit idle segment).  A separately labeled
angle-dependent pressure/temperature/speed closure is sensitivity only; there
is no crank-angle heat-flux correlation or measured wall temperature in the
repository yet.

The primary Al-4032/4140 periodic screen now assigns zero direct chamber gas
area to the conventional piston skirt; it gives 435.5 K skirt and 397.9–398.6
K liner TDC for constant h, with an 8.90–11.46 µm local paired cold-fit
intersection for a 2–5 µm hot target.  The explicitly unvalidated angle
sensitivity gives 509.7 K skirt and 446.7–447.7 K liner, moving the
intersection to 12.76–15.07 µm.  The 54-case bounded sensitivity envelope is
lower 7.65–14.15 µm and upper 10.26–16.38 µm (p05–p95; not a confidence
interval).  These are still proxy temperatures, not a hardware prediction.
The solver now includes a 0.15 W/K block-to-300 K sink and solves the linear
one-cycle map for a periodic fixed point; the 120-cycle cold-to-warm trajectory
is retained separately and is not falsely labeled converged.  The next C1
action is a warm direct-flow fixture that measures local piston/liner
temperature difference and leakage together; do not promote a ringless,
ringed or material architecture from this RC screen alone.

#### C1 warm-flow experiment readiness (completed preparation step)

`data/leakage/measurement_schema.csv`,
`scripts/reduce_leakdown_experiment.py`,
`experiments/WARM_LEAKDOWN_FIXTURE.md` and
`C1_EXPERIMENT_READINESS_REPORT.md` now define the physical validation path.
The reducer pairs piston and liner temperatures at each axial station, retains
signed hot clearance and contact, evaluates the existing annulus equation only
for positive-clearance static rows, keeps dynamic blow-by separate, fits a free
clearance exponent, and propagates explicit channel uncertainties. Synthetic
rows are test-only and never enter `data/leakage/records.csv`.

This preparation does **not** close calibrated C1 and supplies no new leakage
measurement. The next action is a pressure-rated 10–15 mm reference-cylinder
campaign with at least three repeats at 2, 4 and 6.5 bar absolute across cold
and safe warm states, with local fit/taper, paired temperatures, lubricant
condition, pressure, gas state and direct flow recorded together.

#### C1 thermal-literature ingestion (bounded evidence step)

`data/thermal/literature_sources.csv` and
`data/thermal/literature_measurements.csv` preserve the highest-value
near-scale and piston-temperature leads with access status, source locator,
classification and transferability. `scripts/analyze_thermal_literature.py`
derives local piston-minus-liner and normalized temperature quantities only from
complete paired rows. The current public set contains no paired piston/liner
temperature row and therefore supplies no empirical clearance prior. Missing
AP .09/Tian, Kruggel 710578, Furuhama and SETC point tables remain recovery
targets; graph values are not silently digitized or promoted.

The evidence lane now also records the 11.25 mm ringless Shang engine's
reported head-temperature/power context, the approximately 9 mm HCCI engine's
controlled block-temperature setpoints, and the ringed Furuhama/Tada heat-path
and leakage coefficients. Ringed values are kept out of the ringless thermal
network. A manufacturer ABC reference supports intentional cold taper
qualitatively, but no quantitative ringless skirt-to-liner conductance, oil-film
resistance or taper profile has been recovered.

#### RPM-envelope audit (hypothesis routing only)

The external RPM audit is retained as a hypothesis generator. Before any of
its regime or architecture claims can be promoted, all event-time quantities
must use `t_rev = 60/N` and the four-stroke period `t_4stroke = 120/N` seconds;
at 1200 rpm these are 50 and 100 ms, while at 25,000 rpm they are 2.4 and
4.8 ms. The audit's `mu U/W` and `tau_piston/t_cycle` labels are not accepted
as Hersey or Stanton numbers, and Reynolds/Fourier crossings are not universal
RPM boundaries.

The next bounded study is an RPM/chemistry map of self-consistent TDC pressure,
temperature and ignition delay, followed by a 1-D axial thermal-clearance
profile, a coupled fixed-point/Jacobian stability screen, and only then a
ringed-versus-ringless leakage comparison. No saddle, hard CI-to-spark switch,
“no film” lubrication claim or material architecture is promoted from the
audit.

Hypothesis: if manufactured radial clearance is roughly independent of bore,
then annular leak area scales approximately with `B*c` while displacement
scales with `B^2*S`, so leakage-per-displacement can deteriorate rapidly as
bore shrinks.

The original idea to regress miscellaneous published leak-down percentages is
too loose. Leak-down percentage is relative to the tester/reference restriction.
Pressure alone is insufficient to convert a percentage into an absolute
effective leak area.

Use evidence in this order:

1. Direct measured mass-flow / blow-by with pressure and temperature.
2. Differential leak-down data with the tester's reference-orifice geometry or
   calibration curve documented.
3. Same-instrument or standardized-tester datasets across multiple bores.
4. Uncalibrated service-manual/forum leak-down percentages only as qualitative
   context; **exclude them from the quantitative regression**.

For accepted data:
- Keep static leak-down and dynamic blow-by as separate regressions.
- Convert to an effective flow area with the correct compressible-flow model.
- Record pressure, temperature, gas, ring/seal architecture, bore, stroke,
  displacement, tester/orifice, and thermal state.
- Regress `log(A_eff / Vd)` against `log(B)` with confidence intervals and
  leave-one-family-out sensitivity.
- Compare the extrapolated 8.5 mm result against the model's 2-5 micrometre
  annular brackets, but do not call full-size ring data a direct microengine
  calibration.

### C2 - Hardware

When a suitable small engine / Toyan reference arrives:
- leak-down at several piston positions and temperatures;
- crankcase mass flow versus pressure;
- motoring torque if practical.

One calibrated small-engine dataset is more valuable than dozens of
uncalibrated leak-down percentages.

---

## Track D - Numerics and workflow

### D1 - Gates first

`GATES.md` is normative for campaign acceptance. Every new run must name its
applicable gate set before execution.

### D2 - Parallelism

For the present ~10k-cell CFD cases, use a small number of CPU ranks and measure
runtime scaling. Do not assume 12 hardware threads means 12 useful MPI ranks.
GPU work is deferred until cell count/chemistry justify launch and transfer
overhead.

### D3 - Independent review

Whoever produces a result should not be its only reviewer. Ask the reviewing
model for checkable quantities:
- mesh convergence on the answer;
- mass and volume closure;
- monotonicity where claimed;
- unit consistency;
- numerical-step sensitivity;
- whether a branch classification changes under the next-finer setting.

---

## Decision gates

| Finding | Consequence |
|---|---|
| Burke direct regression shows one mechanism badly misses the project-relevant low-T DME/CH4 data | Re-map the chemistry transition before hardware design |
| B1 squish does not improve TDC mixing enough to change branch classification | Freeze transport near the measured flat-piston schedule |
| B1 squish creates a robust faster-mixing branch | Re-run the Beta 2.6 ensemble with the CFD-derived schedule |
| C1 calibrated-flow exponent and extrapolation put 3 micrometre clearance outside demonstrated practice | Bore/seal architecture must change before packaging optimization |
| Small-engine hardware leakage is far worse than the annulus bracket | Recalibrate sealing model before any power conclusions |
| +45 CAD remains unconverged after refinement | Treat late-expansion tau only as a bound; do not tune the two-zone model to it |
| A 720-CAD repeat-cycle row does not reach periodic mass/species/energy/speed closure | Record it as numerical/transient; do not call it stable idle |
| 1,200 rpm loses positive net work or speed control after independently sourced friction/pumping are added | Move the candidate commissioning band upward; do not retune chemistry or leakage to save 1,200 rpm |
| Warm direct-flow data materially disagrees with the annulus clearance trend | Recalibrate or replace the ringless leakage architecture before promoting an idle boundary |

---

## Immediate order

The bounded preflight exposed two useful constraints before that larger model:

- the 40-bar fuel-design hypothesis produced no DME/CO+diluent recipe that met
  both the 2-5 ms delay band and a nonnegative/near-flat temperature response
  across Zhao and LLNL;
- a prescribed mass-residual map changes the nominal 1200-rpm branch
  materially. Both the 5% and 30% endpoints remain unresolved at eight
  iterations under the declared fixed-point tolerance, although deterministic
  reruns reproduce their cool-branch trends exactly and pass the independent
  numerical gates. This is a regression anchor for the future gas-exchange
  model, not a residual-fraction calibration.

1. Diagnose and close one 1,200-rpm valve-enabled 720-CAD reference cycle:
   isolate valve mass/energy mapping and timing/area assumptions, then require
   periodic mass/species/energy/temperature closure before adding friction or
   motor dynamics. The first accounting pass is classified as a
   transient/unresolved state with step-dependent residuals; it is not a stable
   idle claim.
2. After that gate passes, run 1,000/1,200/1,500/2,000 rpm at 2/3/5 µm
   hot-clearance brackets and all three mechanisms; require periodic
   mass/species/energy/speed convergence.
3. In parallel, digitize/obtain Burke DME/CH4 data and run the direct mechanism
   gate, then audit Zhao pressure-dependent decomposition. Do not optimize a
   new fuel recipe against the currently divergent constant-volume mechanisms.
4. Prepare the Issue #13 10–15 mm warm direct-flow experiment to measure the
   current low-idle limiter: paired axial temperature/clearance and flow.
5. Measure motoring torque versus crank angle/RPM when complete hardware exists.
6. Keep CFD on the accepted wedge reference; no S3 or new CFD campaign is
   justified by the low-idle result.
