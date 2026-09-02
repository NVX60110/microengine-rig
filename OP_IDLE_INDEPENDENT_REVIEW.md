# OP-IDLE Phase 1: independent Luna C review

Status: **pre-results audit only**.  This is an independent numerical and
physical falsification checklist prepared before reviewing the Luna A low-idle
map or Luna B axial thermal-fit study.  It does not promote, retract, or
modify either forthcoming result.

Baseline reviewed: `origin/main` / `78682e9`, on the `op-idle-review-luna-c`
branch.  Files reviewed include `PLAN.md`, `GATES.md`, `FINDINGS.md`,
`CANTERA_PREFLIGHT_REPORT.md`, `THERMAL_CLEARANCE_REPORT.md`,
`THERMAL_STATE_REPORT.md`, `findings/FABLE51_REVIEW.md`,
`microengine_rig.py`, `two_zone_model.py`, `uncertainty_campaign.py`,
`physics/thermal_clearance.py`, `physics/thermal_state.py`, and the test suite.

## Baseline audit

The geometry arithmetic is internally consistent at the default rig state:

| quantity | baseline value | audit note |
|---|---:|---|
| bore × stroke | 8.5 × 7.0 mm | diameter and axial length |
| displacement | 0.397215 cc | `pi B^2 S / 4` |
| BDC/TDC volume | 463.418 / 66.203 mm³ | ratio 7.000 for CR 7 |
| 1200 rpm revolution | 50 ms | `60/N` |
| 1200 rpm four-stroke period | 100 ms | `120/N` |
| modeled reacting span | 360 crank degrees | compression plus expansion only |
| mean piston speed | 0.280 m/s | useful geometry diagnostic, not FMEP |

The reacting solvers therefore provide a closed, single-pass compression/
expansion screen.  They do not model intake, exhaust, valve timing, trapped
residuals, gas-exchange pumping, friction, lubrication, contact, or brake
torque.  `gross_imep` and `gross_indicated_power` are consequently not net
engine output.  Four-stroke frequency is applied in the power summary
(`rpm / 60 / cycle_revolutions`); it does not make the missing 360 degrees of
gas exchange or the missing second crank revolution part of the solution.

`cycle_revolutions` is validated only as `>= 1`, so a four-stroke interpretation
must require and report exactly 2.0 revolutions.  Any other value must be
labeled as a per-pass or non-four-stroke diagnostic.  The thermal-state screen
has a related explicit assumption: its history is one 360-degree pass followed
by a default 0.05 s idle segment.  That equals one revolution only at 1200 rpm;
it must be derived as `60/N - modeled_pass` for an RPM map.  At low or high RPM,
leaving 0.05 s fixed changes the thermal duty cycle.

The baseline unit suite passes: `python -m unittest discover -s tests -v`
reports **80 tests, OK**.  This demonstrates implementation regressions and
bookkeeping checks, not hardware validity or model-form correctness.

## Falsification checklist for Luna A/B

### Timing, dimensions, and state definition

1. Recompute and print `t_rev=60/N`, `t_4stroke=120/N`, modeled-pass duration,
   and idle duration for every RPM.  Reject a map if an event-time ratio uses
   one revolution where a four-stroke period is required.
2. Require `cycle_revolutions=2.0` for four-stroke claims.  Check that all
   power, leakage-fraction, Damköhler-like, and thermal timescale quantities
   state their numerator and denominator units.
3. Recheck slider-crank volume closure, displacement, clearance height, piston
   velocity, and `P dV` sign under the exact map settings.  Report work as
   gross closed-cycle work and do not subtract an invented FMEP.
4. Preserve radial/diametral conventions.  Bore and piston dimensions are
   diameters; `annular_radial_clearance_um` and thermal-clearance inputs are
   radial.  The factor two must be visible in any axial-fit implementation.

### Ignition delay and chemistry

5. Separate a frozen ignition-delay surrogate from an evolving delay.  If a
   map freezes `tau` at intake/TDC, rerun with the local state-dependent
   `tau(P(theta),T(theta),phi)` and report branch changes.  For Cantera, use
   the evolving chemistry trajectory and a declared ignition criterion; do not
   infer a constant delay from one state.
6. Treat `proxy-auto` as a prescribed burn screen: its Arrhenius-like `tau`
   only triggers a user-set burn fraction and duration.  It is not an
   experimentally validated ignition model.  `spark` is likewise a prescribed
   burn profile, not spark discharge/arc chemistry.
7. Confirm the mechanism, species aliases, pressure-rate selection, and
   validity ranges for every map row.  Zhao-full remains open at 25–90 bar;
   Zhao sk39 has parent-retention evidence, not direct engine validation; LLNL
   has source-validation evidence, not this DME/CH4 map validation.  Burke
   DME/methane points and their pressure, phi, facility, uncertainty, and
   max-dP/dt criterion remain the direct validation target.
8. Record nonignitions, solver failures, and out-of-range states explicitly.
   A timeout, NaN, or retry is not extinction, nonignition, or a physical
   operating boundary.  Report the full mechanism envelope rather than a
   universal IMEP percentage error bar.

### Numerics and branch boundaries

9. For representative stiff transition rows, refine crank-angle output and
   internal-step controls (at least 0.25, 0.125, and a finer setting where
   needed), tighten CVODE tolerances, and require unchanged branch class plus
   stable peak pressure/Tmax/CA50/conversion.  The preflight demonstrates that
   a 2-degree two-zone collapse can fail while a 0.125-degree case collapses.
10. Apply the existing gates: positive global inventory conversion, pressure
    mismatch <=0.10 bar, no null-as-physics, and explicit mass/volume residuals.
    Keep source-term reaction integrals as localization only; global fuel
    inventory is the conversion metric.
11. Preserve solver retries, max internal steps, warnings, and errors in every
    Luna row.  A map point is not promotable merely because `acceptable()` is
    true: that helper does not itself encode mechanism validity, solver retry,
    thermal-fit contact, or stability.
12. Distinguish physical from numerical boundaries.  A transition that moves
    with timestep, tolerance, sampling, mechanism, mixing closure, or wall
    closure is a screening interval, not a hardware RPM limit.  Report direct
    state quantities (`P`, `T`, pressure-rise, conversion, CA50) beside any
    differentiated or threshold-derived quantity.

### Heat transfer and double-counting check

13. In the single-zone Cantera path, the Reactor wall is the gas energy sink;
    the separately accumulated `q_gas_to_wall` is an accounting/update signal,
    not a second cylinder sink.  Verify this with an energy ledger and do not
    apply the same wall flux again in the reacting integration.
14. The thermal RC pipeline is driven by a gas history that was generated with
    the existing finite-wall `h=600 W/(m² K)` proxy, then applies an independent
    gas-to-solid `h` network.  This is an explicitly assumed forcing chain, not
    a closed conjugate gas/solid solution.  Falsify any claim of physical heat
    balance by comparing: adiabatic history + RC, finite-wall history + RC,
    measured/CFD wall heat flux when available, and integrated heat against
    the gas energy change.  Do not call the resulting difference a calibrated
    wall loss.
15. Check area assignment and axial pairing.  The conventional skirt receives
    zero direct chamber-gas area in the RC model; crown/TDC liner, skirt/TDC
    liner, and skirt/lower-liner pairs must remain separate.  A minimum path
    contact result is not a zero-leak annulus result.
16. For RPM-dependent thermal work, recheck explicit RC step convergence,
    periodic-map residual, warm-up convergence separately, cycle energy
    closure, and the spectral/stability behavior of the one-cycle map.  A
    solved linear fixed point is not evidence that the physical coupled
    engine is stable.

### Sealing, clearance, and leakage

17. Keep cold static leak-down and dynamic in-cylinder blow-by as separate
    evidence lanes.  Static rows require direct flow or a calibrated/documented
    reference restriction; dynamic rows remain flow histories unless a stated
    pressure-history inversion is supplied.
18. Preserve signed hot clearance.  Zero and negative values are contact or
    interference and must not be clamped into annulus flow.  Positive annulus
    flow must retain current pressure, gas temperature/viscosity, bore, skirt
    length, and eccentricity; its cubic clearance law is an uncalibrated
    sensitivity, not a measured blow-by prediction.
19. For Luna B's axial fit, require local piston/liner temperature pairing,
    axial station, taper/roundness, thrust direction, and clearance convention.
    A crown or skirt temperature paired to a remote liner temperature cannot
    establish local clearance.  CTE profiles outside their source range are
    extrapolations and need an explicit uncertainty bracket.
20. Do not promote ringless, ringed, or material architecture from the RC
    screen.  Ring motion, multi-volume ring-pack flow, oil viscosity/film,
    piston rock, contact pressure, scuffing, wear, and manufacturability remain
    unresolved.  Likewise, an axial temperature gradient is a concept, not a
    solved lubrication model.

### Stability, operating limits, and claimed outputs

21. Require a repeated-cycle residual/EGR treatment before claiming cycle-to-
    cycle stability or an idle operating boundary.  The present reacting model
    refreshes neither charge nor residual composition and does not test a
    periodic chemistry fixed point.
22. Require a coupled thermal-clearance/leakage stability screen before using
    “runaway,” “saddle,” or “bistable” for hardware.  Include the stabilizing
    possibility that a tighter gap increases heat rejection; report Jacobian/
    eigenvalue behavior and nonlinear fixed points.
23. Motor torque, friction, pumping, accessories, brake output, lubrication,
    contact, and spark-assisted operation must remain unresolved outputs.  The
    model supports gross indicated work and conditional chemistry/thermal/
    sealing sensitivities only; it does not support net torque, brake power,
    friction power, or a spark-capable hardware operating map.
24. For every promoted-looking Luna headline, attach status and provenance:
    `CONFIRMED` implementation check, `SCREENING` model result,
    `OPEN` unresolved item, or `RETRACTED`.  Include the exact configuration,
    mechanism source/status, numerical settings, residuals, thermal closure,
    and whether the boundary is physical or numerical.

## Outputs currently supported vs unresolved

Supported as conditional calculations: slider-crank geometry and ideal-gas
closed-pass p/T/V; Cantera evolving species and global fuel-inventory change;
two-zone pressure/mixing brackets under stated closure; gross `P dV` work and
gross IMEP; pressure-rise and heat-release timing diagnostics; pressure-aware
annulus sensitivity for positive clearance; and analytical CTE/thermal-RC
screening with explicit periodic residual and energy bookkeeping.

Unresolved: net motor torque/brake power; friction and pumping; intake/exhaust
and residual/EGR chemistry; cycle-to-cycle stability; calibrated DME/CH4
ignition delay and Zhao pressure-rate selection; hardware dynamic blow-by;
ring-pack architecture; local axial thermal field and taper; oil film,
lubrication, piston rock, contact/scuffing and wear; and physical RPM or
CI-to-spark operating boundaries.  These must not be inferred from a positive
gross-IMEP screen or a numerically converged proxy.

This file intentionally stops at Phase 1.  It contains no Luna A/B result and
should be revisited only after their commits are supplied for Phase 2 review.

## Phase 2 — Luna B axial thermal-fit falsification

Reviewed read-only: Luna B commit `12f5b5281483961756ab4ffe6f7729f91b40c475`
in `microengine-rig-op-idle-thermal-fit`.  No Luna B file was modified.  The
targeted command
`python -m unittest tests.test_thermal_fit_axial tests.test_thermal_clearance tests.test_thermal_state -v`
passes **21/21 tests**.

### Checks that reproduce

* The axial station arithmetic is radial.  The hand case gives 5.01 µm hot
  radial clearance for a 5 µm cold gap with matched 100 K strains, and the
  independent inverse calculation reproduces the neutral 8.5 mm bounds
  8.8986–11.7149 µm (`constant_h`) and 12.7573–15.3984 µm (angle sensitivity).
* Signed hot gaps are preserved.  Zero/negative station gaps return
  `contact_invalid_annulus` and no flow; no contact gap is silently clamped.
  A **10 µm cold** neutral fit independently reaches 3.1047 µm minimum hot gap
  at the constant-h periodic path and −0.7698 µm under the angle sensitivity.
  For comparison, the **3 µm cold** neutral values are −3.9159 and −7.8017 µm
  respectively (contact).
* The series-annulus closure reproduces
  `c_eq = [mean(c_i^-3)]^-1/3`; for 2/4/8 µm stations the calculated value is
  2.76072 µm.  This is algebraically consistent with equal-length series
  resistances, but remains an uncalibrated flow closure and assumes one scalar
  pressure/temperature/viscosity state for the path.
* Corresponding station pairing, ±2 µm shape envelopes, ±1 µm error offsets,
  and the 1 µm contact-margin flag are exposed as assumptions.  The report
  correctly keeps ringed literature, ringless annulus flow, lubrication, and
  contact/seizure claims separate.

### Discrepancy B-C1: leakage state is not the worst-profile state

In `scripts/thermal_fit_axial.py`, each candidate first finds `worst` as the
minimum clearance over all periodic history rows, but then calls
`nonuniform_annulus_leakage` with `periodic_rows[0]["pressure_bar"]` and
`periodic_rows[0]["gas_temperature_K"]`.  Row zero is BDC (−180°), not the
row where `worst` occurred; the axial profile object does not retain its crank
angle.  This is a real state-pairing mismatch, even though the code labels the
flow as screening.

Independent rerun for the neutral 8.5 mm constant-h, 10 µm cold base case:

| state | CAD | pressure | gas T | minimum hot gap | series flow |
|---|---:|---:|---:|---:|---:|
| script BDC inputs | −180 | 3.0816 bar | 300.0 K | 3.1217 µm at BDC profile | 0.1107 mg/s (CSV) |
| actual worst profile | +60 | 18.5892 bar | 721.66 K | 3.1047 µm | 1.8663 mg/s |

The difference is about 16.9× for the same annulus law.  It does not change
the contact status of the angle-sensitivity case (both states are contact),
but any Luna B flow number must either identify the chosen state as a BDC
sensitivity or pair pressure/temperature with the worst-clearance angle.  The
same issue applies to shaped/error candidates whose worst station/time shifts.

### Timing and artifact findings

The report properly limits results to the 1200 rpm proxy.  The implementation
still hardcodes that scope in two places: `scripts/thermal_fit_axial.py` calls
`load_history_csv(..., rpm=1200.0)` with no RPM option, and the inherited RC
default uses `idle_duration_s=0.05`.  Supplying a non-1200-RPM history through
the CLI would therefore assign incorrect seconds and thermal duty cycle.  A
future speed map must pass an explicit RPM, derive the one-revolution idle
segment as `60/N - modeled_pass`, and regenerate the gas history; no RPM
boundary follows from this commit.

The report’s reproduction section says the candidate artifact has 84
shape/error rows, while the committed CSV contains 96 data rows: 8 shapes × 3
machining offsets × 4 (bore, closure) cases.  This is a documentation/count
discrepancy, not evidence of a physics error, but it should be resolved for
reproducibility.

### Luna B disposition

Luna B supports a bounded, corresponding-station **calculated** hot-gap and
series-annulus sensitivity at 1200 rpm under the stated RC/interpolation and
shape/error assumptions.  It does not establish an axial temperature field,
manufactured taper, local roundness/rock, hot contact load, oil film, ringless
lubrication, calibrated leakage, or a safe preheat/cranking interval.  The
conditional preheat scan is correctly treated as CTE-only; `minimum_safe` or
`maximum_safe` is not an engine operating permission.  The neutral and
shape/error fit intervals should remain screening envelopes, and the
state-pairing discrepancy above must be attached to any leakage headline.

Luna B review is dispositioned for now; Phase 2 remains open pending the
lead’s Luna A results.

### Correction disposition for Luna B commit `01f5fd7`

The corrected B commit pairs the leakage forcing state with the same periodic
row that supplies the worst axial clearance.  Its neutral 8.5 mm constant-h,
10 µm cold-base CSV row records approximately +60 CAD, 18.5892 bar, 721.66 K,
and **1.8663 mg/s**; the targeted regression now explicitly checks preservation
of those source fields and that paired flow exceeds the BDC-state flow.  The
previous B-C1 discrepancy is therefore **closed by the implementation change**
(the flow remains an uncalibrated sensitivity, not hardware leakage).

The corrected report now also states 96 candidate rows, matching the committed
CSV (8 shapes × 3 signed errors × 4 bore/closure cases).  The corrected
targeted suite passes **22/22 tests**.  The 1200-rpm-only scope and the
non-1200 hardcoded timing limitation remain as documented above; this
disposition does not close Phase 2 because Luna A review is still pending.

## Luna A Phase 2 falsification and disposition (`afe805b`)

### Audit method and artifact counts

I inspected Luna A commit `afe805b` without modifying its worktree, including
`scripts/op_idle_map.py`, `tests/test_op_idle_map.py`, the report, and every
compact JSON/CSV pair. The targeted Luna A suite passes **5/5**. I also reran
the two final Zhao-full boundary points and the LLNL 1500-rpm retry directly
through `run_job`; the stored headline values reproduced.

The compact artifacts contain these data-row counts (JSON `case_count` and CSV
data rows agree): baseline **27**, refine **9**, refine2 **9**, refine3 **9**,
uncertainty **18**, retry **1**. Baseline has **26 `ok` rows and one CVODES
numerical error**. Its successful rows split into **10 robust, 3 marginal,
and 13 physically implausible** rows; the numerical-error row is additionally
labelled `screen_class=implausible` with `limiting_mechanism=numerical_failure`.
Thus the report's 10/3/13 + 1 split is recoverable, but the compact class
label does not itself distinguish numerical failure from physical
implausibility.

### Checks that pass

* Four-stroke timing is dimensionally consistent: `revolution_period_s=60/N`,
  `four_stroke_period_s=120/N`, and the modeled −180 to +180 CAD segment is
  one revolution. With `cycle_revolutions=2`, the reported power uses the
  four-stroke frequency. At the exact 0.125-CAD grid, TDC selection is the
  actual 0 CAD row, not an interpolated or compression-start state.
* The `reacting_tdc_*` fields are genuinely evolving two-zone values and are
  distinct from the −180 CAD compression-start fields. An independent
  Zhao-full rerun at 1106.0546875 rpm returned 66.00752 bar reacting TDC
  pressure versus 3.00000 bar at compression start, with 0.87002044 end
  retention and 3.762295 bar gross IMEP. The lower 1105.859375-rpm rerun
  returned 0.86999505 retention and 3.763206 bar gross IMEP, matching its
  marginal/robust transition.
* The two-zone path requires `ignition_mode=cantera-auto` and advances the
  reacting network; the configured proxy `tau_ref_ms` is not used by this
  path. I found no hidden fixed ignition delay. The 1% event is correctly
  labelled as first global inventory conversion, and CA10/50/90 are based
  on cumulative heat release.
* All three declared mechanisms are represented in successful map rows. The
  1500-rpm LLNL baseline error is retained as numerical failure rather than
  silently interpreted as extinction. The 0.0625-CAD LLNL retry independently
  reproduced robust status, 0.829542 bar gross IMEP, 0.906673 retention,
  856.997 K peak temperature, 2.375536 bar/CAD peak rise, and CA50 +4.20524
  CAD.
* The final retention crossing is correctly a campaign-specific numerical
  screen: Zhao-full is marginal at 1105.859375 rpm (0.86999505 < 0.87) and
  robust at 1106.0546875 rpm (0.87002044). This is not a chemistry,
  seal-safety, or physical operability boundary. The aggregate correctly
  requires all three mechanisms and marks 1500 rpm incomplete because LLNL
  has no successful baseline row.
* The uncertainty JSON has 18 one-factor rows at 1105.95703125 rpm. The
  reported qualitative trends are present, including 3 µm/e=1.0 and 5 µm/e
  cases with negative gross work, and the 280 K intake case being marginal on
  retention. No count or unit conversion error was found in the stored
  pressure (bar), temperature (K), time (s), angle (CAD), mass (mg), work
  (mJ), power (W), and torque (N·m) fields.

### Discrepancies and unresolved interpretation

1. **Ignition wording is broader than the exported observable.** The report
   says each row stores “ignition/conversion,” but the map result contains no
   `ignition_1pct_deg_atdc` or reaction-start field. It stores only the
   explicitly labelled first 1% global inventory-conversion angle. The
   evolving Cantera path is real, but ignition delay remains unresolved and
   should not be inferred from that conversion event.

2. **Numerical/physical class ambiguity.** The one 1500-rpm baseline CVODES
   error has `screen_class=implausible`, although its limiter is
   `numerical_failure` and the report separates it from 13 physical
   implausible rows. Any consumer counting `screen_class` directly obtains
   14 implausible rows. The numerical result must remain excluded from a
   physical boundary statement.

3. **Motor-torque proxy denominator is under-specified and inconsistent with
   four-stroke power if read as engine torque.** The script computes
   `max(0,-gross_work_mJ)` and divides the converted work by **2π**, which is
   the average torque over the modeled 360-CAD segment. Reported power uses
   `work × rpm/(60×2)` for a four-stroke cycle; corresponding crankshaft
   average torque would divide by **4π**. Therefore the published proxy is a
   factor of two high if interpreted as four-stroke motor torque. It is
   acceptable only as a clearly named one-revolution lower-bound work proxy;
   it is not motor torque, brake torque, friction, or pumping work.

4. **One sensitivity prose omission.** The uncertainty table also has the
   5 µm/e=0 case at negative gross work (−95.499 mJ); the report names 5 µm/e
   =0.5 and 1.0 and 3 µm/e=1.0, but omits the 5 µm/e=0 row. This does not
   change the qualitative sensitivity conclusion.

### Final Luna A disposition

The numerical artifacts, mechanism aggregation, final narrow retention
crossing, actual reacting-TDC bookkeeping, and LLNL retry are reproducible.
The result supports only a bounded closed-cycle reacting screen and the
listed one-factor sensitivities. It does **not** support stable idle,
brake/motor torque, friction or pumping, intake/exhaust gas exchange,
residual/EGR behavior, cycle-to-cycle stability, lubrication or contact
life, or spark-assisted operation. Keep the four discrepancies above
attached to any Luna A headline; in particular, retain the numerical-vs-
physical distinction and do not promote the 1106-rpm retention crossing to a
physical operating boundary.

Luna A is therefore **conditionally reproducible with reporting caveats**;
the substantive Phase 2 falsification is complete, while the physical claims
listed above remain unresolved.

### Sol-lead integration disposition

The four Luna A reporting/bookkeeping findings were corrected after the
independent review without rerunning or retuning chemistry:

* the report now calls the exported event the evolving-path 1% global
  inventory-conversion onset and explicitly says no independent ignition-delay
  observable is exported;
* solver-error rows now use `screen_class=numerical_failure`, separate from
  physical `implausible` rows;
* the motor-torque lower-bound proxy now divides modeled negative work by
  `4*pi`, the full 720-CAD four-stroke rotation, while assigning zero load to
  the unmodeled revolution; and
* the sensitivity prose now includes the negative-work 5 µm/e=0 row.

Regression tests cover the numerical-failure class and 720-CAD torque
denominator. The underlying RPM, chemistry, pressure, temperature, work,
conversion, phasing, and retention results were not changed. All physical
scope limitations in the independent disposition remain open.
