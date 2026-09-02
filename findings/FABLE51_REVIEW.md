# Review of Fable 5.1 hypotheses

This note records a review of the external Fable 5.1 handoff. It is not a findings promotion. Claims below remain hypotheses unless tied to repository evidence or cited literature.

## 1. CFD state after Issue #10 resolution

The fixed-20%-mass-zone audit supersedes the earlier global-RMS squish interpretation for the two-zone design question:

- S1/flat normalized core/shell contrast at TDC: **1.3541**.
- S2/flat normalized core/shell contrast at TDC: **1.2608**.
- The original S2 loss was an under-converged tracer linear solve. The
  exact-key `tracer` solver entry (`tolerance 1e-13`, `relTol 0`) reduces
  inventory drift to approximately `1e-11`; regenerated flat/S1/S2 results
  reproduce the mixing answers within the accepted gates.
- `linearUpwind grad(tracer)` remains a rejected scheme experiment because it
  both lost inventory and produced a negative scalar. It is not the accepted
  repair.

Therefore no S1/S2 squish transport schedule is eligible for Cantera coupling,
but the reason is now the negative geometry decision: neither tested squish
case improves the fixed-20%-mass-zone TDC contrast. Issue #10 is resolved and
closed. S3 remains blocked because the present evidence does not justify the
geometry campaign, not because scalar conservation is unresolved.

## 2. Swirl-decay claim: arithmetic rejected

Fable proposed first-mode viscous spin-down

`tau = R^2 / (14.7 nu)`

and quoted `0.14 ms` at intake and `0.54 ms` near TDC for the 8.5 mm bore.

The form is consistent with the first `J1` azimuthal mode (`j_1,1 ~= 3.8317`, so `j_1,1^2 ~= 14.68`), but the quoted evaluations are not consistent with gas kinematic viscosity at the project scale.

For `R = 4.25 mm`, order-of-magnitude ideal-gas/air-property estimates give:

- around `500 K, 1.5-3 bar`: `nu ~ 1.3e-5 to 2.6e-5 m^2/s`, hence `tau ~ 0.05-0.10 s`;
- around `900-925 K, 40 bar`: `nu ~ 2-3e-6 m^2/s`, hence `tau ~ 0.4-0.6 s`.

Thus "swirl dies in 0.14-0.54 ms" is rejected by roughly two to three orders
of magnitude. A more explicit state audit gives about `0.23 s` at 3 bar/300 K,
`0.05-0.10 s` at 1.5-3 bar/500 K, `0.49 s` at 40 bar/900 K, and
`0.79-1.05 s` at the modeled OP-IDLE TDC states. At 1200 rpm those are about
`0.5-2.3` four-stroke-cycle e-folding times in intake-like states and
`4.9-10.5` at the instantaneous compressed states.

This rescues swirl as a hypothesis, not as a result. A cycle needs the
time-varying integral `exp(-integral(dt/tau(theta)))`, and real end walls,
geometry, turbulence, intake and exhaust can add loss. The current closed
cylinder has no intake valve, tangential inlet, or swirl velocity field, so it
cannot show that intake-generated swirl persists for 5-10 complete cycles.
Low Reynolds number implies laminar flow, not automatically sub-millisecond
loss of angular momentum.

Sources for the review: Acheson, *Elementary Fluid Dynamics*, spin-down of azimuthal flow in a cylinder using `J1` modes; standard air viscosity data/Sutherland-level estimates. Exact project-mixture viscosity should be computed if swirl becomes decision-critical.

## 3. Squish-as-displacement: plausible but not demonstrated beneficial

The qualitative idea that a squish land displaces outer gas toward the bowl without requiring turbulence is physically reasonable. However, the fixed-20%-mass audit shows the tested S1 geometry retains **more**, not less, core/shell contrast at TDC. Therefore "make the squish band coincide with the wall layer" is a hypothesis for a future geometry, not a result of S1/S2.

No S3 should be run under the current decision gate. Issue #10 has already
isolated and repaired the scalar solve; the remaining blocker is that S1/S2 did
not provide the required two-zone transport gain.

## 4. Residual-gas / repeated-cycle chemistry: valid missing model, no 8% default

The canonical reacting model is effectively single-cycle. Residual hot products and partially reacted species can alter the next cycle, especially near a chemistry transition. This is a legitimate missing model.

Do **not** adopt `8% residual` as a universal default. Residual fraction depends on valve timing, pressure ratio, gas exchange, speed, and geometry and is not yet calibrated for this engine. A later repeated-cycle model should sweep or compute residual fraction and solve for a periodic fixed point.

## 5. DME crankcase/lubrication concern: direction accepted, magnitude open

Published DME tribology work confirms very low viscosity/lubricity and fuel-system material/lubrication challenges. Blow-by containing DME/fuel-air mixture is therefore a real lubrication, compatibility, and flammability concern.

The exact statement "37% blow-by" must remain tied to whichever uncalibrated sealing bracket produced it; it is not a measured property of the target engine. Do not size crankcase ventilation from that number until sealing is experimentally calibrated.

## 6. 12 mm bench mule: useful prototype strategy, not a theorem

A larger single-cylinder mule is attractive for instrumentation, sealing, machining, pressure sensing and mechanism validation. However, "if it fails at 12 mm, it could never work at 8.5 mm" is too strong: combustion, heat transfer, surface ignition, sealing architecture and geometry may change with scale. Treat 12 mm as a risk-reduction platform, not a proof-by-scaling.

## 7. Sound/acoustics: legitimate project question, presently input-limited

The rig can eventually map an accepted cylinder/exhaust pressure history into an exhaust/acoustic model. This is relevant to the project's founding display/sound objective. Current reacting pressure traces are still mechanism/closure-dependent, so an acoustics result today would be exploratory rather than a design gate.

## 8. Fuel-cut detector: architecture implication accepted, timing corrected

At `1200 rpm`:

- one revolution = `50 ms`;
- one four-stroke 720-degree cycle = **100 ms**.

Therefore Fable's `50 ms per cycle` statement is incorrect. The motor-driven architecture nevertheless makes fuel inhibition a strong fail-safe because the crank can continue motoring without combustion.

A future controller should define measurable hard limits before hardware work. Candidate fast signals are crank-angle-resolved cylinder pressure (primary, if packaging permits), crank angular acceleration/encoder residual, and motor torque/current residual. A detected hot/rapid-pressure event cannot be undone after the current injection has reacted; the primary action is to inhibit the **next** fuel event and let the motor carry the crank.

## 9. Pure-DME + EGR hypothesis: test, do not promote

EGR is a credible DME/HCCI phasing lever. The Fable table has now been replaced
by a reproducible repository campaign using the signed definition
`S = d ln(tau_ign) / d ln(T)` and a common max-dP/dt criterion. Ordinary
ignition has `S < 0`; positive `S` is only an NTC-like shape diagnostic.

The proposed 25/75 DME/CO blend is nearly flat in both Zhao lineages but is too
fast near 925 K (~1.3 ms), while LLNL gives a strongly negative endpoint slope.
Adding N2, CO2, or H2O can move the delay toward 2-5 ms, but none of the tested
recipes retains a nonnegative/near-flat response across Zhao and LLNL. No fuel
or EGR architecture is promoted.

Published high-pressure DME work shows that H2O/CO2/N2 dilution have different thermal and chemical effects. In particular, steam can chemically accelerate DME ignition relative to equivalent N2 dilution in some temperature ranges. Therefore statements such as "H2O is the best retarder" or "CO-rich exhaust provides negative feedback" are mechanism-, state-, and composition-dependent.

Before any future promotion:

1. retain the versioned 40-bar curve and signed/local-slope definition already
   implemented in `scripts/fuel_temperature_sensitivity.py`;
2. resolve the Zhao pressure-rate choice and direct Burke validation before
   treating cross-mechanism disagreement as a fuel-optimization surface;
3. replace the completed prescribed residual-composition adapter with a
   valve-derived 720-CAD periodic state rather than injecting one frozen Beta
   2.3 exhaust vector;
4. perturb wall temperature, residual fraction and EGR fraction and require the feedback sign to remain stabilizing;
5. only then test the concept in the two-zone/repeated-cycle model.

## 10. RPM-envelope audit: hypothesis status and corrected quantities

The attached full-envelope audit is useful as a hypothesis generator, not as a
new design baseline. Several headline quantities require correction before
they can enter a result table:

- At speed `N` rpm, one revolution is `60/N` seconds and one four-stroke
  720-degree cycle is `120/N` seconds. Thus the four-stroke period is 100 ms at
  1200 rpm and 4.8 ms at 25,000 rpm (the one-revolution values are 50 ms and
  2.4 ms). Any `Lambda`, leakage-fraction or Damkohler map must use the stated
  event duration consistently.
- `mu*U/W` with `W` as force is not dimensionless Hersey number; lubrication
  regime needs a defined pressure/geometry load parameter and, ideally, a
  film-thickness-to-roughness ratio. `tau_piston/t_cycle` is a thermal
  timescale ratio, not Stanton number.
- Reynolds number, Fourier number and a Woschni-shaped heat-transfer closure do
  not establish a universal laminar/turbulent or combustion-mode boundary at a
  particular rpm. The transition must be evaluated from the self-consistent
  pressure, temperature, viscosity and flow state.
- Positive thermal/leakage feedback suggests a stability question, not a
  proven saddle or bistability. A coupled fixed-point/Jacobian calculation must
  include the stabilizing possibility that a tighter gap increases piston-to-
  liner heat rejection. Ringed-vs-ringless remains a testable hypothesis, not a
  promoted architecture.
- At low speed, mixed/boundary lubrication is more likely to occupy more of the
  cycle; “no oil or gas film exists” is not established. Likewise,
  compression-ignition failure and a hard CI-to-spark switch are hypotheses
  until RPM-dependent TDC states and ignition delays are computed.
- For an 8.5 mm bore with `R=4.25 mm`, a steel-piston temperature-only
  sensitivity is approximately `-R*alpha_steel = -52 nm/K`; near-cancellation
  occurs only when piston and liner temperatures co-vary with matched CTE, not
  when piston temperature changes alone.

The revised queue is therefore: (1) an RPM/chemistry regime map using actual
TDC `P,T` and Cantera ignition delays, (2) a 1-D axial piston/liner thermal
profile and `c_hot(z)`, (3) coupled stability-envelope analysis, and (4) a
first-order ringed/ringless leakage screen. No numerical RPM boundary,
clearance architecture or mode-switch rpm is promoted by this audit.

## Routing

Current routing is:

1. Keep Issue #10 closed and keep S3 blocked under the geometry-value gate.
2. Treat the merged OP-IDLE RPM map and axial thermal-fit screen as the current
   conditional baselines; do not rerun them merely to reproduce this handoff.
3. Reproduce the supplied fuel-temperature tables with the repository ignition
   criterion and compare mechanisms before evaluating a fuel/EGR architecture.
4. Add only a bounded residual-composition fixed-point adapter before a full
   720-CAD gas-exchange/crank model. A prescribed residual fraction is not a
   valve-model result.
5. Issue #4 direct Burke validation remains open pending original or explicitly
   digitized experiment points. The direct-flow fixture already includes a
   room-temperature first matrix, so no second fixture model is needed.
