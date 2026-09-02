# Low-idle feasibility report

Status: integrated technical-lead decision after the Luna A operating map,
Luna B axial thermal-fit screen, Luna C independent falsification, and the
bounded 1,200-rpm 720-CAD gas-exchange preflight.

## Decision

The present simulator does **not** yet establish a physically stable idle RPM.
It establishes a reproducible conditional closed-pass boundary, but the first
valve-enabled 720-CAD case remains unresolved:

> Under the accepted Beta 2.6 closed-cycle state, all three chemistry
> mechanisms first pass the project screen at approximately **1.11 krpm**.
> The exact stored crossing, 1105.859375–1106.0546875 rpm, is the crossing of
> the campaign-specific 0.87 retained-mass gate—not a sub-rpm prediction of
> real engine behavior.

The useful design interpretation is therefore:

* **Lowest credible test target:** approximately **1,200 rpm**, classified
  **possible but fragile**.
* **More defensible nominal commissioning neighborhood:** approximately
  **1,500–2,000 rpm**, as an inference from its larger sealing and combustion
  margins; this is not yet a hardware-stable-idle claim.
* **Nominal model screen:** roughly **1.11–2.0 krpm** across the three
  mechanisms. At 3,000 rpm the mechanisms split; at 5,000 rpm and above none
  produces positive closed-pass gross work under this configuration.

The first low-speed limiter in the current model is residence-time-amplified
**annular mass loss**, not failure to ignite. Slowing from 1,200 rpm crosses
the provisional 0.87 retained-mass gate near 1.11 krpm. At 800 rpm, the still
longer chemical residence time produces a second failure mode: a hot,
rapid-pressure-rise branch. The model therefore does not support the simple
claim that “slower is always easier.”

The complete-cycle preflight does not overturn that closed-pass result. It stops
promotion earlier: the current lumped valve/state wrapper changes mass by 3.19%
and specific enthalpy by 1.14% after four cycles at 1,200 rpm, so residuals and
thermal state have not reached a periodic solution. This is an unresolved
project-model gate, not evidence that the engine fails physically.

## Provenance

* **MEASURED EVIDENCE:** none was produced by this campaign. There is no
  measured hot clearance, dynamic blow-by, motoring torque, or idle COV.
* **LITERATURE-DERIVED CALCULATION:** material expansion data used by the
  existing thermal-clearance lane and the separately recorded small-engine
  thermal evidence. No literature value was used to tune the RPM map.
* **PROJECT MODEL RESULT:** every RPM, pressure, temperature, conversion,
  work, leakage, and thermal-fit number below.
* **INFERENCE:** “possible but fragile,” the 1.5–2.0 krpm commissioning band,
  the ranked next work, and all hardware implications.

## Configuration and numerical gate

The RPM map retains the accepted conditional state rather than inventing a
new calibration: 8.5 mm bore, 7.0 mm stroke, rod/stroke 1.6, CR 7.75, 3.0 bar
and 300 K intake, phi 0.40, 560 K fixed wall, 25/75 mol% DME/CH4, central
diffusion/strain mixing, and the uncalibrated 3 µm radial/e=0.5 annulus.

All main transition rows use 0.125 CAD, `rtol=1e-9`, and `atol=1e-15`, as
justified by the Cantera preflight. Four-stroke period is `120/N`; the modeled
closed compression/expansion pass is one revolution, `60/N`. At 1,200 rpm
these are 100 ms and 50 ms respectively; the −20 to +20 CAD window is 5.56 ms
and the −40 to +40 CAD window is 11.11 ms.

One LLNL row at 1,500 rpm reached the 100,000-step CVODES ceiling at 0.125
CAD. It remains recorded as a numerical failure. The isolated 0.0625-CAD
retry completed and passed: 0.8295 bar gross IMEP, 857.0 K peak temperature,
2.376 bar/CAD maximum pressure rise, CA50 +4.21 CAD, and 0.9067 retained mass.
Luna C reproduced both decisive Zhao-full retention rows and that LLNL retry.

The lead integration also separates `screen_class=numerical_failure` from
physical `implausible` rows, uses a 720-CAD (`4*pi`) denominator for the
full-cycle average motor-torque lower-bound proxy, and describes the exported
event honestly as 1% global inventory conversion—not an independent ignition
delay.

## 1,200-rpm 720-CAD periodic-state preflight

This bounded experiment is the first complete-cycle check and is intentionally
not an RPM sweep. The disabled-regression bridge reproduces the canonical
two-zone trace exactly at the stored precision. With the assumed 1.0 mm²
half-sine intake/exhaust effective areas, 0.70 discharge coefficient, and
fixed-speed 1,200-rpm crank, four valve-enabled cycles took approximately
80.4 s and stopped at `unresolved_periodic_state`:

| gate | final cycle-to-cycle change | result |
|---|---:|---|
| mass | 3.19e-2 relative | fail |
| species | 1.11e-4 max mass fraction | fail |
| specific enthalpy | 1.14e-2 relative | fail |
| temperature | 6.65 K | fail |
| speed | 0 rpm (prescribed) | not tested dynamically |

The staged runner therefore did not enable friction, crank inertia, or motor
control. Its final open-system bookkeeping reports 1.476 mg intake,
1.293 mg exhaust, 1.995 bar signed PMEP, and 5.787 bar gas-work MEP. These are
project-model outputs under an assumed valve closure, not measurements or a
stable-idle prediction. The first justified follow-up is a nonreacting
valve/energy/state-mapping test and a bounded valve timing/area check; only a
closed 1,200-rpm reference cycle should unlock the broader RPM sweep.

## Nominal speed map

| RPM | Four-stroke period | Across-mechanism result | Controlling observation |
|---:|---:|---|---|
| 800 | 150 ms | implausible | Tmax 1,868–1,874 K; 63.5–72.2 bar/CAD; retained mass 0.808–0.812 |
| 1,000 | 120 ms | marginal | positive gross work, but retained mass only 0.856–0.863 |
| ~1,106 | 108.5 ms | nominal gate crossing | Zhao-full retained mass crosses 0.870; exact threshold is model/gate-specific |
| 1,200 | 100 ms | all-mechanism screen pass | 0.624–1.874 bar gross IMEP; retained mass 0.882–0.885 |
| 1,500 | 80 ms | pass after isolated LLNL retry | Zhao rows pass at 0.125 CAD; LLNL passes at 0.0625 CAD |
| 2,000 | 60 ms | all-mechanism screen pass | 0.913–1.421 bar gross IMEP; LLNL CA50 +15.4 CAD approaches the phasing limit |
| 3,000 | 40 ms | mechanism split | Zhao gives only 0.091–0.101 bar; LLNL is −0.350 bar |
| 5,000–10,000 | 24–12 ms | nonpositive gross work | negligible conversion at the highest speeds under the current autoignition state |

The screen labels apply positive gross IMEP, 10–90% global conversion, Tmax
below 1,600 K, pressure rise no more than 10 bar/CAD, CA50 from −15 to +20
CAD, inter-zone pressure mismatch no more than 0.10 bar, and the provisional
0.87 end-mass-retention condition. Passing them is necessary for this study,
not sufficient for stable idle.

## What 1,200 rpm actually does

| Mechanism | reacting TDC pressure | core / boundary TDC temperature | conversion | CA50 | gross IMEP | gross indicated power | retained mass |
|---|---:|---:|---:|---:|---:|---:|---:|
| LLNL 2004 | 61.33 bar | 866.9 / 729.8 K | 0.325 | −1.76 CAD | 0.624 bar | 0.248 W/cyl | 0.8850 |
| Zhao full | 65.60 bar | 909.4 / 845.3 K | 0.454 | −6.06 CAD | 1.874 bar | 0.744 W/cyl | 0.8821 |
| Zhao sk39 | 65.55 bar | 908.6 / 844.7 K | 0.447 | −6.12 CAD | 1.794 bar | 0.713 W/cyl | 0.8822 |

These are actual evolving reacting-state TDC values. The chemistry is solved
along the moving compression path; no fixed ignition delay is used. The map
exports first 1% inventory-conversion timing and CA10/CA50/CA90, but it does
not claim that the 1% event is a facility-defined ignition-delay measurement.

At 1,200 rpm, all three mechanisms pass nominally, but the retained-mass
margin above 0.87 is only about 1.2–1.5 percentage points and the absolute
annulus model is uncalibrated. That is why the correct classification is
**possible but fragile**, not robust hardware idle.

## Parameter sensitivity near the lower boundary

The one-factor screen was run at 1105.957 rpm with Zhao sk39. It is a
sensitivity map, not a probability distribution.

| Variation | Result near boundary | Interpretation |
|---|---|---|
| 2 µm radial, e=0/0.5/1.0 | all pass; retention 0.924–0.968 | tighter positive annulus greatly increases modeled margin; no contact/lubrication proof |
| 3 µm, e=0 | pass; retention 0.901 | eccentricity is a large uncalibrated lever |
| 3 µm, e=0.5 | just passes; retention 0.8701 | nominal crossing definition |
| 3 µm, e=1.0 | −0.295 bar gross IMEP | nominal clearance is not robust to full eccentricity |
| 5 µm, e=0/0.5/1.0 | all nonpositive gross work | modeled ringless path becomes implausible at this speed |
| phi 0.30 | passes, but only 0.131 bar gross IMEP | very little margin for omitted losses |
| phi 0.50 | over-conversion/hot branch | mixture is not a free torque knob |
| intake 2.3 bar | passes, 1.104 bar gross IMEP | pressure and chemistry move together |
| intake 3.5 bar | rapid-release failure | more trapped charge is not automatically safer |
| intake 280 K | marginal on retention | thermal state shifts the lower boundary |
| intake 350 K | over-conversion branch | strong temperature sensitivity |
| wall 520 K | passes, 0.321 bar gross IMEP | low gross-work margin |
| wall 600 K | over-conversion branch | wall state can change the combustion branch |

The nominal crossing is therefore not a robust multidimensional operating
region. It is a useful localization of the dominant uncertainty: hot dynamic
sealing. Equivalence ratio, intake state, and wall temperature must be
controlled rather than averaged into one “idle RPM.”

## Motor assistance

The modeled closed pass has positive gross work from the nominal ~1.11 krpm
crossing through 2,000 rpm, so the current **energy-only lower-bound** motor
proxy is zero there. That is not a prediction that no motor is needed. The
motor must still cover negative instantaneous torque, compression before heat
release, pumping on the unmodeled revolution, friction, accessories, speed
ripple, weak cycles, and combustion-mode transitions.

At 1,200 rpm the available modeled gross work is only 24.8–74.4 mJ/cycle
(0.248–0.744 W per cylinder). No defensible motor torque or power requirement
can be specified until a 720-CAD crank/inertia/friction/gas-exchange model and
motoring data exist. The electric machine remains valuable because it can
hold speed through weak cycles and any future autoignition/spark-assisted
transition without requiring positive ICE torque at every crank angle.

## Thermally developed ringless fit

The axial screen keeps the ringless concept plausible but does not validate
it. For the 8.5 mm Al-4032 piston / 4140 liner proxy, a neutral axial geometry
requires approximately:

| Thermal closure | cold radial base fit giving 2–5 µm hot |
|---|---:|
| constant `h=600 W/(m² K)` | 8.90–11.71 µm |
| angle-dependent sensitivity | 12.76–15.40 µm |

A 3 µm cold radial fit reaches periodic contact in both cases. Illustrative
±2 µm taper/barrel and ±1 µm radial machining errors can erase the common
2–5 µm path. For the neutral 10 µm constant-h case, the same-state worst-path
diagnostic occurs near +60 CAD at 18.59 bar and 721.7 K and gives 1.866 mg/s
through the current uncalibrated series-annulus model.

Preheating does not monotonically improve an Al-piston/steel-liner gap. Common
heating can close it because the piston has the higher CTE; heating the liner
relative to the piston can open a conditional interval. The model contains no
oil-film, contact-pressure, scuffing, piston-rock, or roughness calculation,
so it cannot issue a safe-cranking temperature. The conclusion is:

> A thermally developed, axially profiled ringless fit is a feasible design
> lane, but no material improvement in low-idle feasibility is demonstrated
> until local temperatures, taper, contact state, and warm dynamic flow are
> measured.

No ringless, ringed, or material architecture is promoted.

## Confidence and missing evidence

| Claim | Confidence | Reason |
|---|---|---|
| numerical reproduction of the nominal closed-pass map | high within the implemented model | strict settings, explicit failure row, targeted retry, independent reruns |
| ~1.11 krpm retained-mass screen crossing | high as a project-model calculation | narrow numerical bracket, but controlled by an uncalibrated leakage law and nonuniversal gate |
| 1,200 rpm can support useful combustion | medium-low | three mechanisms agree nominally; omitted losses and state uncertainty are large |
| 1,200 rpm is physically stable idle | unresolved | no 720-CAD gas exchange, residual carry-over, friction, inertia, controller, or cycle variability |
| 8.9–15.4 µm cold axial fit envelope | medium-low as a thermal screen | arithmetic is checked; temperature field, taper and conductances are assumed |
| ringless hardware leakage | low / uncalibrated | no direct warm-flow data or measured hot profile |

The results most limited by missing experimental data are hot dynamic leakage,
local piston/liner temperatures and taper, and motoring/friction torque. Direct
Burke DME/CH4 point data and the Zhao pressure-dependent decomposition choice
remain chemistry credibility limits.

## Fuel and prescribed-residual preflight

Two bounded follow-ups test the external Fable fuel/residual hypotheses without
rerunning the RPM campaign.

The 40-bar constant-volume fuel screen defines
`S = d ln(tau_ign) / d ln(T)` over 875-975 K and retains every 10 K point and
local slope. No tested DME/CO-plus-N2/CO2/H2O recipe simultaneously reaches the
2-5 ms delay target and preserves a nonnegative/near-flat response across the
Zhao and LLNL lineages. This rejects the supplied recipe as a current design
baseline; it does not establish system stability or prove that residual/EGR
control is useless in an evolving engine.

The separate one-revolution prescribed-residual adapter mixes fresh charge with
the preceding modeled end state on a mass basis and conserves stream enthalpy.
At the nominal 1200-rpm Zhao-sk39 anchor, `f_res=0.05` and `0.30` remain on cool
branches through eight iterations, with final gross IMEP about 3.76 and
1.95 bar respectively. Neither reaches the declared composition/temperature
fixed-point tolerances. Independent-process runs are byte-identical and all
mass, component-mass, pressure, volume, and retention gates pass, so these are
reproducible unresolved trends—not periodic 720-CAD states.

These follow-ups do not change the report's idle classification. They make
valve-derived residual carry-over and periodic convergence explicit acceptance
tests for the next simulator layer.

## Simulator gate and next experiment

The 720-CAD scaffold is now present, but it is not yet a stable-idle model.
The next justified change is specifically to diagnose the failed 1,200-rpm
valve stage: isolate nonreacting valve mass/energy mapping, inspect the assumed
timing/area closure, and then repeat until mass, species, enthalpy and
temperature close to their declared tolerances. Only after that gate passes
should friction, crank inertia/motor control, or the 1,000/1,500/2,000-rpm
campaign be enabled. No coefficient may be tuned merely to preserve 1,200 rpm.

## External software decisions

The ranked project-use order is based on immediate decision value, not a
general product rating. Full rationale and calibration cautions are in
`ENGINE_SOFTWARE_RECON.md`.

1. **ADOPT:** Cantera 3.2 and bounded CPU-process parallelism.
2. **ADOPT as evidence:** ReSpecTh records when exact experiment/criterion
   provenance matches the DME/CH4 validation lane.
3. **ADAPT/BENCHMARK:** LibICE-post for an independent p-V and heat-release
   reduction of one accepted trace.
4. **BENCHMARK/SCAVENGE:** OpenWAM for future 720-CAD ducts, valves, pumping,
   and residual trends; do not import its old full codebase.
5. **BENCHMARK:** OpenModelica/MVEMLib after a defensible torque map exists,
   for motor-flywheel-control integration rather than combustion calibration.
6. **ADAPT/BENCHMARK later:** ReynoldsFlow if measured taper/roughness requires
   a nonuniform thin-gap leakage solver.
7. **PRESERVE BOUNDED USE:** OpenFOAM 14 wedge-axis reference; no new CFD until
   a resolved heat-flux or transport quantity becomes decision-limiting.
8. **BENCHMARK later:** OpenPulse for piping acoustics after a validated valve
   boundary condition exists.
9. **REJECT now:** AmgX/OpenFOAM GPU migration; the accepted small wedge case
   is not large or linear-solver-limited enough to justify integration risk.

## Recommended first physical experiment

Use the already specified 10–15 mm warm direct-flow reference-cylinder
fixture. At corresponding axial stations measure cold bore/piston geometry,
taper and roundness, paired piston/liner temperatures, gas temperature,
upstream/downstream absolute pressure, lubricant state, and direct mass flow.
Run room/moderate/warm states at approximately 2, 4, and 6.5 bar absolute with
at least three stable repeats.

That single experiment tests the uncertain chain beneath the modeled low-idle
limiter: `temperature -> axial hot fit -> warm static annulus-flow trend`. It
can show whether the annulus model is high or low and whether an approximately
cubed clearance trend exists. It does **not** convert static leak-down into
dynamic blow-by; a pressure-history/crankcase-flow experiment is still needed
for that transfer. When a complete engine exists, the next measurements are
motoring torque versus crank angle and dynamic crankcase flow/pressure from
800–2,000 rpm.

## Reproduction

The operating-map commands and artifact inventory are in
`OP_IDLE_LUNA_A_REPORT.md`; the thermal-fit commands are in
`THERMAL_FIT_AXIAL_REPORT.md`. Independent checks and the issues found before
lead integration are preserved in `OP_IDLE_INDEPENDENT_REVIEW.md`.
