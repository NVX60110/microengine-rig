# Plan

Status after Beta 2.6 and CFD-01. This file is the current project routing document.
Read `FINDINGS.md`, `BETA26_REPORT.md`, and `CFD01_REPORT.md` before using any
headline number.

Project rule: be thorough about the number the next decision depends on and
coarse about everything else.

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
- The Burke point data still needs to be obtained or digitized with facility,
  uncertainty, and ignition-criterion metadata, then passed through
  `mechanism_gate.py`.
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

CFD-01 lives on `cfd01-cold-flow-tracer` until merged to main.

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
| A1 | Obtain or digitize Burke et al. 80/20 and 60/40 CH4/DME ignition-delay points | Direct validation is now available; ReSpecTh is not the only path | Preserve facility, pressure, phi, uncertainty, and the paper's ignition criterion |
| A2 | Run `mechanism_gate.py` on the Burke set for Zhao sk39/full and LLNL | Replaces cross-fuel inference with direct DME/methane evidence | Report sim/exp distributions, nonignitions, and low-T subset; do not collapse to one engine error bar |
| A3 | Audit Zhao pressure-dependent decomposition reactions | Source header requires rate selection by pressure | Document selected channels/rates for 25-90 bar and rerun transition anchors if changed |
| A4 | Map max-dP/dt ignition-delay sensitivity around the accepted island | Quantifies how sharp the chemistry boundary is | Report local slopes and transition intervals, not universal percent uncertainty |

ReSpecTh remains useful if it supplies original machine-readable points, but it
is no longer a project blocker.

---

## Track B - CFD

### B0 - CFD-01 cleanup before new physics

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

Status update: S1 mild squish coarse is implemented and passes the mesh,
volume, mass, tracer, Courant, and output-cadence gates. The fixed-radius
core/shell diagnostic is not cross-geometry comparable because its shell
fraction collapses from ~16.7% at BDC to ~8.65% near TDC. The updated global
mass-weighted RMS gives `A_S1/A_flat = 0.835` at TDC (a lower cumulative
contrast), while the local +/-5 CAD fit gives 43.33 ms versus 39.51 ms for
flat. Treat this as a changed but non-uniform transport history, not a
uniformly faster-mixing claim. S2 remains paused until this evidence is
reviewed; if the design question requires a monotonic squish trend, one S2
coarse screen is the next bounded run.

### B2 - Bore/geometry screen

Only after B1. Bore alone is a weaker S/V lever than clearance height:
`S/V = 2/h + 4/B`. Do not spend CFD hours on bore changes until the transport
decision is closed.

---

## Track C - Sealing

### C1 - Calibrated leakage scaling study

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

---

## Immediate order

1. Close the +45 CAD mesh-convergence hole using the retained 0.15-CAD cap.
2. Run B1 squish.
3. In parallel, digitize/obtain Burke DME/CH4 data and run the direct mechanism gate.
4. Start C1 only with calibrated/convertible leakage data.
5. Audit Zhao pressure-dependent decomposition before treating a chemistry
  transition as final.
