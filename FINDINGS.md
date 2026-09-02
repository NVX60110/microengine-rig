# Findings ledger

Every numerical claim must include conditions, status, and the script/result
that produced it. `CONFIRMED` means implementation cross-check or comparison
to cited experiment—not hardware validation of the engine.

Status: `CONFIRMED` · `SCREENING` · `RETRACTED` · `OPEN`

Baseline unless stated: 8.5 x 7.0 mm, CR 7, 1200 rpm, 25/75 mol% DME/methane,
phi 0.40, 560 K fixed wall, 3 micrometre concentric annulus, 20% boundary-zone
mass, 10 ms mixing.

## Chemistry and mechanisms

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| C1 | Nordin-41 reproduces the selected n-heptane shock-tube set with median sim/exp 1.527; 84.8% within 2x; low-T median 1.351 | 99 Ciezki 1993 + Fieweger 1997 ChemKED points, <=60 bar, constant-volume adiabatic, ignition=max dP/dt, 0.5 s ceiling | CONFIRMED vs experiment | `mechanism_gate.py`, `nordin_chemked.json` |
| C2 | Peters-21 fails LTC severely; an exact single error factor is timeout-dependent | Same data; at 0.5 s, 34 nonignitions and low-T median 100x among 8 ignited points; at 2 s, 27 nonignitions and low-T median 164x among 14 | CONFIRMED negative control | `peters_chemked.json`, `peters_chemked_2s.json` |
| C3 | Zhao sk39 retained its supplied parent's delay shape | Pure DME/air, phi 1.0, 40 bar, 650-1100 K; median sk/full 1.062, range 1.007-1.163; NTC 1.522 vs 1.465 | CONFIRMED as reduction retention only | `zhao_parent_retention.json` |
| C4 | The 39-species mechanism previously called Luo/Lu is Zhao 2008 sk39 | Fresh CHEMKIN conversion: identical 39 species, 175 equations, and forward rate constants at 900 K/40 bar | CONFIRMED metadata correction | `mechanisms/README.md` |
| C5 | Zhao-full is not ground truth at engine pressure until its decomposition-rate selection is audited | Distributed source activates 1-atm DME decomposition rate and instructs selection by pressure; rig operates 25-90 bar in-cylinder | OPEN | mechanism header, `mechanisms/README.md` |
| C6 | A universal +/-50% IMEP error bar is justified by the n-heptane regression | Cross-fuel inference only | RETRACTED | Report mechanism envelope and boundary intervals instead |
| C7 | Direct experimental DME/methane validation data exists at project-relevant composition and pressure | Burke et al. measured pure fuels plus 80/20 and 60/40 CH4/DME, 600-1600 K, 7-41 atm, phi .3-2.0 using shock tubes and an RCM | CONFIRMED source identified; point data not yet ingested | DOI `10.1016/j.combustflame.2014.08.014`; `BETA26_REPORT.md` |

## Operability and two-zone behavior

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| O1 | The claimed -0.06 to -0.27 flat sensitivity window was a solver-step artifact | Handoff script maximized raw `T_now-T_previous`, not dT/dt | RETRACTED | `operability_sensitivity.py`, `BETA25_REPORT.md` |
| O2 | Correct max-dP/dt slopes at 45 bar are not flat | 25/75 DME/CH4, phi .40; Zhao slope -2.30 at 850 K, -2.89 at 900 K, -2.68 at 950 K; LLNL -2.84, -4.05, -7.09 | SCREENING chemistry diagnostic | `operability_sensitivity.csv` |
| O3 | Bounded partial oxidation can persist above 1000 K | At 2.3 bar: Zhao sk39 CR8.25 reaches 1219 K/75.3%/5.9 bar-per-deg; full CR8 reaches 1169 K; at 3 bar all lineages remain bounded at CR7.75, 1026-1200 K | SCREENING, one prescribed spatial closure | `two_zone_transition_*.json` |
| O4 | A nearby hot transition remains and is mechanism-dependent | 2.3 bar: first hotter samples sk39 CR8.5, full CR8.25, LLNL CR8.25; 3.0 bar: all hot at CR8.0 | SCREENING | `two_zone_transition_*.csv` |
| O5 | Localizing wall heat suppresses the Beta2.3 homogeneous runaway at the shared CR7 anchor | 2.3 bar, baseline closure: sk39 1.04 bar/36.6%/901 K; LLNL .66 bar/29.1%/867 K | CONFIRMED across two lineages within model | `two_zone_campaign.csv`, `BETA24_REPORT.md` |
| O6 | Radial mixing closure is the dominant model-form uncertainty | Boundary mass 10-30%, mixing 0-20 ms; branches span no reaction to runaway | SCREENING | `two_zone_campaign.csv` |
| O7 | A bounded mixing window appears between extinction and rapid heat release | 72-case pilot, 3 bar, CR 7.75/8.0, three mechanisms; slow=100 ms, central=12-34 ms, fast=2.4-3.2 ms | SCREENING closure ensemble | Fast mixing: 0/24 acceptable; central: 10/24; slow: 10/24, `beta26_uncertainty.json` |
| O8 | CR 7.75 and 8.0 are mechanism-robust under the 3 micrometre/e=.5 annulus plus central mixing closure | 3 bar, 25/75 DME/CH4, phi .40, 560 K wall; all three mechanisms pass the conservative display-engine screen | SCREENING, conditional on uncalibrated sealing/mixing | `beta26_uncertainty.csv`, `beta26_uncertainty_audit.png` |
| O9 | Retention is necessary but not sufficient | Every acceptable pilot case retained at least .874 of end-cycle cylinder mass; sealed fast-mixing cases still ran away | SCREENING | `beta26_uncertainty.json` |

## Sealing and mechanics

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| M1 | Annular leakage must be evaluated at current pressure; fixed equivalent CdA is not transferable | Isothermal compressible Poiseuille annulus has mdot proportional to Pu^2-Pd^2; choked orifice mdot proportional to Pu | CONFIRMED model law | `microengine_rig.py`, `physics/annulus.py` |
| M2 | Clearance and eccentricity remain strong work levers | Shared two-zone anchor; 2/3/5 micrometre and e=0/.5 | SCREENING | `two_zone_campaign.csv` |
| M3 | Valve-seat leakage should use annular/contact flow, not a knife-edge orifice | 3.5 mm valve, 0.3 mm seat width, 45 bar/1100 K screen | CONFIRMED model correction; hot effective gap OPEN | `physics/annulus.py` |
| M4 | Oil-lubricated FMEP is exactly .018-.044 bar | Supplied screen undercounted journal energy/cycle and covered 360 rather than 720 degrees | RETRACTED exact range | Correct 720-degree model + motoring torque needed |
| M5 | Low piston speed is favorable for friction | Mean piston speed .28 m/s at 7 mm/1200 rpm | SCREENING, not a complete FMEP result | geometry |
| M6 | Mach index .0149 indicates large valve-flow-area headroom at 1200 rpm | 3.5 mm valve, .8 mm lift, Ci=.35 | SCREENING | Do not extrapolate linearly to a 48,000 rpm valve-train limit |
| M7 | Axial thermal zoning solves lubrication | Hot head/top liner with cooler lower liner | RETRACTED as solved; retain as concept | Requires conjugate thermal/oil-film model and hardware |
| M8 | Public full-size blow-by data constrains model structure, not the target's absolute leakage | 84 x 90 mm three-ring engine model matched measured flow within 15%; wear raised flow 56-60%. Ring-pack literature reports side passages can exceed end-gap area by >10x | CONFIRMED source interpretation | `sealing_prior.py`, Koszalka 2004/2022 |
| M9 | A single-orifice ring-pack proxy is a pessimistic upper-flow bracket, not a calibrated ring pack | 0.006 mm2 single-stage area retained only .19-.21 in the pilot and never made positive work | SCREENING model-class warning | Multi-stage inter-ring volumes and ring motion are absent; `beta26_uncertainty.json` |
| M10 | Uncalibrated leak-down percentages cannot be converted to absolute leak area from test pressure alone | Differential leak-down percentage depends on the tester/reference restriction | CONFIRMED measurement-method constraint | `PLAN.md`, `GATES.md`; use documented reference-orifice/calibration or direct flow |
| M11 | Static leak-down and dynamic blow-by must remain separate scaling datasets | Different flow histories and measurement definitions | CONFIRMED method constraint | `PLAN.md`, `GATES.md` |

## Numerics and method

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| N1 | Zero-point dataset loads must fail loudly | ChemKED parsing | CONFIRMED safeguard | `mechanism_gate.py`, test suite |
| N2 | Primary two-zone conversion must use global fuel inventory | Initial + inflow - outflow - remaining | CONFIRMED bookkeeping correction | `two_zone_model.py` |
| N3 | Source-term integration is retained only for reaction localization | Stiff hot branches can accumulate outer-step quadrature error | CONFIRMED safeguard | component residuals + inventory metric |
| N4 | Accepted Beta2.4 shared-anchor results are crank-step converged | .25 to .03125 degree: sk39 IMEP 1.0446 to 1.0418; LLNL .6580 to .6537 | CONFIRMED numerical convergence | `two_zone_convergence.csv` |
| N5 | Relaxed two-zone CVODE tolerances remove LLNL trace-radical stalls without material solution drift | rtol/atol 1e-7/1e-14 vs 1e-9/1e-15 at CR7.75, 3 bar, annular 3um/e=.5, central mixing: IMEP shifts .004 bar Zhao and .010 bar LLNL; Tmax <.5 K | CONFIRMED two-point numerical check | `BETA26_REPORT.md` |

## CFD-01 / CFD-02 in-cylinder transport

Flat-piston CFD-01 conditions: 8.5 x 7.0 mm, CR 7.75, 1200 rpm, cold closed
cylinder, passive tracer, OpenFOAM 14, three meshes (2706 / 5289 / 10455 cells).
CFD-02 changes only the piston/head clearance shape unless stated.

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| F1 | Flat-piston TDC transport is consistent with molecular diffusion; fitted piston-strain coefficient is 0.0 | Fine mesh closure fit | CONFIRMED within CFD-01 model | `CFD01_REPORT.md`, `cfd/results/cfd01_two_zone_options.json` |
| F2 | Fine-mesh `tau_mix` at TDC is 10.655 ms | sampled +0.042 CAD | CONFIRMED numerical result | `cfd/results/cfd01_mixing_time.csv` |
| F3 | TDC `tau_mix` is approximately mesh-converged: coarse 10.27 / medium 10.35 / fine 10.65 ms | requested 0 CAD | CONFIRMED numerical convergence | per-mesh scalar histories; `findings/CFD01_ADDENDUM.md` |
| F4 | Beta 2.4's 10 ms prescribed mixing time was close to the measured flat-piston value near the combustion window | roughly +/-20 CAD | SCREENING model implication | `cfd/results/cfd01_mixing_time.csv` |
| F5 | A single scalar mixing time is not an adequate full-cycle closure | fine history spans ~10.65 ms near TDC to >=39 ms by +45 CAD | CONFIRMED within CFD-01 | scalar history + addendum |
| F6 | The +90 CAD negative local derivative is not evidence of physical un-mixing; the direct concentration difference remains positive and late-cycle differentiation is noise-sensitive | +90 CAD onward | CORRECTED interpretation | per-mesh scalar histories; `findings/CFD01_ADDENDUM.md` |
| F7 | +45 CAD pointwise `tau_mix` is not mesh-converged: coarse 24.67 / medium 32.11 / fine 39.07 ms | requested +45 CAD | OPEN bound; not a blocker for the near-TDC squish decision | per-mesh scalar histories, Issue #5 |
| F8 | Flat-piston outer-shell zone definition is stable at approximately 0.1984 of cylinder volume | moving flat-piston cycle | CONFIRMED numerical check | scalar histories |
| F9 | Slider-crank volume closure is approximately 0.1407% across flat meshes | all meshes | CONFIRMED | `cfd/results/cfd01_mesh_convergence.csv` |
| F10 | Closed-domain mass drift is 5.986e-7 relative on the flat fine stored run; legacy fields were evaluated with perfect-gas `rho=p/(RT)` fallback | moving mesh, v8 stored fields | CONFIRMED numerical gate | `cfd/results/cfd01_mesh_convergence.csv`, `CFD01_REPORT.md` |
| F11 | `correctPhi=no` is acceptable for the validated CFD-01 baseline; reopen only if a new timestep, mesh, or geometry fails continuity/mass gates | moving mesh, stored v8 fields | CONFIRMED baseline decision; conditional reopen | `GATES.md`, `CFD01_REPORT.md` |
| F12 | Preserve/interpolate measured transport histories before fitting a lower-order closure | full cycle | METHOD NOTE | `findings/CFD01_ADDENDUM.md`, `GATES.md` |
| F13 | maxDeltaT=0.25 CAD passes the 5% answer gate but is not faster in the measured coarse run; 0.35/0.45 CAD fail max Co (0.740/0.854) | coarse mesh, maxCo target 0.15 | CONFIRMED numerical sweep; retain 0.15 CAD recommendation | `cfd/results/cfd01_timestep_sweep.csv`, `CFD01_REPORT.md` |
| F14 | S1 mild constant-CR squish coarse passes its numerical gates; its inherited fixed-radius `DeltaC/tau_mix` is geometry-specific because shell volume falls from 16.74% at BDC to 8.65% near TDC | 3.25 mm bowl radius, 1.00 mm squish width, 0.50 mm TDC gap, 0.918 mm recess; 2,763 cells; 1200 rpm | CONFIRMED method warning; S1 remains SCREENING physics | `CFD02_S1_REPORT.md`, `cfd/results/cfd02_s1_coarse_metadata.json` |
| F15 | Cross-geometry cumulative mixing must use each case's mass-weighted tracer RMS normalized by its own initial RMS when initial tracer amplitude differs. At TDC S1/flat normalized RMS is 0.8922, while the +/-5 CAD fitted tau is 43.33/39.51 ms | Flat initial raw RMS 0.39875866; S1 initial 0.37335030 (ratio 0.9363); tracer inventory drift <=6.83e-5 relative | SCREENING; S1 has ~10.8% less initial-normalized segregation remaining at TDC but no uniform local-rate improvement | `cfd/compare_tracer_mixing.py`, `cfd/results/cfd01_vs_cfd02_s1_tracer_mixing.json`, `CFD02_S1_REPORT.md` |
| F16 | S1 changes the timing of mixing: its +/-5 CAD fitted tau is faster than flat through much of compression (e.g. -20 CAD: 35.15 vs 50.85 ms) but slower at TDC (43.33 vs 39.51 ms) and after | S1 coarse vs flat fine global normalized RMS fit | SCREENING history-shape result | `cfd/results/cfd01_vs_cfd02_s1_tracer_mixing.json` |

| F17 | S2 medium squish coarse fails the closed-cylinder tracer-inventory gate despite passing mesh, gas-mass, volume, Courant, and tracer-bounds gates | 3.00 mm bowl, 1.25 mm squish, 0.35 mm gap, 2,823 cells; max tracer-inventory drift 0.0167264% = 1.67264e-4 relative | NUMERICAL FAILURE; do not promote transport or refine | `cfd/results/cfd02_s2_coarse_metadata.json`, `CFD02_S2_REPORT.md` |
| F18 | S2 does not meet the predeclared ~5% additional normalized-RMS reduction versus S1 through -20 to TDC, even as a failed-run diagnostic | S2/S1 normalized RMS 1.0468 at -20 CAD and 0.9987 at TDC; S2/flat is 0.8910 at TDC | SCREENING diagnostic only; no S2 geometry promotion | `cfd/results/cfd01_vs_cfd02_s2_tracer_mixing.json`, `cfd/results/cfd02_s1_vs_s2_tracer_mixing.json`, `CFD02_S2_REPORT.md` |
| F19 | The fixed 20% cumulative-mass outer-zone reprocessing reverses the earlier S1 two-zone interpretation: S1 retains more normalized core/shell contrast than flat at every requested comparison angle, including 1.3545x at TDC | At every saved angle, the dynamically selected shell contains exactly 20% of total mass; S1/flat normalized zone contrast is 1.1401 at -20 CAD, 1.3545 at TDC, 1.6299 at +20 CAD, and 1.7418 at +45 CAD. S1 local fits have weak R2 (0.50-0.84) | METHOD CORRECTION; no S1 transport promotion or Cantera coupling | `cfd/results/cfd01_vs_cfd02_s1_mass_zone_mixing.json`, `CFD02_S1_REPORT.md`, `GATES.md` |
| F20 | Replacing S2's upwind tracer convection with `linearUpwind grad(tracer)` does not repair the scalar-conservation defect and introduces boundedness failure | Same S2 coarse geometry and controls; max tracer-inventory drift 0.0201883% = 2.01883e-4 relative and tracer minimum -0.0192431, while gas mass drift remains 5.9826e-7 relative and max Co 0.190825 | NUMERICAL FAILURE; scheme variant is not an acceptable drop-in | `cfd/results/cfd02_s2_linearupwind_metadata.json`, `CFD02_S2_REPORT.md`, `cfd/openfoam14/squish/README.md` |
| F21 | The S2 tracer-inventory loss was an unconverged tracer linear solve, not a moving-mesh, flux-dimension, or wall-flux defect. Converging the solve on the identical S2 coarse case closes the gate: inventory drift 1.663e-4 -> 9.94e-12 relative (solver fields), 1.63e-10 by the postprocessor, tracer in [0, 1], volume/Courant/mesh checks unchanged, physical answer moved <= 0.005% | OpenFOAM 14 `scalarTransport` function object solves `ddt(rho,s)+div(phi,s)-laplacian(rho D,s)=0` after `postSolve`; shared `"(U|e|tracer).*" relTol 0.01` entry gave one PBiCGStab iteration per step (final residual median 3.7e-8, max 1.2e-6), signed residual removed tracer fastest at -30 to -13 CAD; exact-keyword `tracer` entry `tolerance 1e-13; relTol 0` gives 2-3 iterations (final 3.7e-15 median), +7% runtime. Gas mass constant to 1.6e-10 and wall `phi` <= 2.6e-23 kg/s from solver-written fields | CONFIRMED numerical root cause and fix; one bounded, inventory-conserving treatment demonstrated on the S2 moving mesh | `CFD02_S2_SCALAR_ISOLATION_REPORT.md`, `cfd/results/cfd02_s2_tighttol_metadata.json`, `cfd/results/cfd02_scalar_inventory_audit.json`, `cfd/audit_scalar_inventory.py` |
| F22 | The promoted S1 coarse and flat fine histories carry the same unconverged-solve defect below the gate | Solver-field tracer-inventory drift: S1 coarse -6.826e-5 (monotonic, largest loss near -12 CAD), flat fine v8 max 2.404e-5 (sign-changing, final +1.09e-5); loss scales with squish intensity | OPEN for cross-geometry use: histories remain valid under their gates, but regenerate flat, S1 and S2 with the converged base `fvSolution` before any geometry decision; F14-F19 comparisons are provisional until then | `cfd/results/cfd02_scalar_inventory_audit.json`, `GATES.md` |
| F23 | Boundedness under the `scalarTransport` function object is not structural: it is solved against the thermodynamic density that `isothermalFluid::postSolve()` writes over the continuity solution, so its continuity consistency is only as good as the solver's continuity error (S2 sum-local <= 4.96e-5) | Source-verified in OpenFOAM 14 `applications/modules/isothermalFluid` and `src/functionObjects/solvers/scalarTransport`; upwind cannot go negative and no overshoot occurred in any stored case | METHOD NOTE; if Cantera coupling needs a scalar bounded by construction, carry it as an inert species in `multicomponentFluid` (solved in-loop against the `correctDensity()` density with the same `phi`; laminar `unityLewisFourier` reproduces `D = 1.408 nu`); not part of Issue #10 | `CFD02_S2_SCALAR_ISOLATION_REPORT.md` section 6 |
| F24 | Regenerating flat coarse/medium/fine and S1 coarse with the converged tracer solve conserves inventory to <= 1.5e-11 relative in every case, keeps tracer in [0, 1], and leaves every mixing answer within 0.14% of legacy: flat fine TDC `tau_mix` 10.655 -> 10.665 ms, +45 CAD 39.068 -> 39.097 ms; three-geometry ratios reproduce legacy to <= 0.001 with all six comparison gates `ok` | Same meshes, flow controls and initial tracer; S2 from F21; four concurrent single-processor solves | CONFIRMED numerical regeneration; supersedes the F22 provisional label on F14-F19 comparisons | `CFD02_REGEN_TIGHT_REPORT.md`, `cfd/results/cfd02_scalar_inventory_audit_tight.json`, `cfd/results/cfd01_scalar_history_*_tight.csv`, `cfd/results/cfd02_s1_tight_*` |
| F25 | Under shared, gate-clean numerics neither squish geometry reduces the fixed 20%-mass-zone core/shell contrast below flat at TDC: S1/flat 1.3541, S2/flat 1.2608; whole-domain normalized RMS is 0.892 and 0.891; S2/S1 is 0.9987 (RMS) and 0.9311 (zone). By the B1 rule, squish does not deliver a two-zone transport gain at the combustion window | Coarse squish meshes versus flat fine; +/-5 CAD fits R2 >= 0.999 | SCREENING geometry verdict for review: accept the flat-piston `tau(theta)` scale, no S3, no S1/S2 Cantera coupling; a medium-mesh S1 would be the only justified counter-check | `CFD02_REGEN_TIGHT_REPORT.md` section 5, `cfd/results/cfd01_vs_cfd02_s1_tight_mass_zone_mixing.json`, `cfd/results/cfd01_vs_cfd02_s2_tight_mass_zone_mixing.json` |

## Architecture decision

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| A1 | Retain the motor-driven display-engine architecture | No accepted default two-zone anchor/clearance/eccentricity case paid idealized compressor power; friction and gas exchange remain incomplete | SCREENING decision, not impossibility theorem | `BETA24_REPORT.md` |
| A2 | Canonical code is `microengine_rig.py` plus experimental `two_zone_model.py`; `microengine_v3.py` is retired | Beta2.5 repository | CONFIRMED project decision | README |

## Open work, in priority order

1. Review and merge the Issue #10 branch (converged tracer solve, audit tool, regenerated flat/S1/S2 histories, F21-F25). The root cause is found and the fix is demonstrated; the gate closes on merge, and Issue #10 closes after the F25 geometry verdict is reviewed.
2. Decide the B1 squish question from F25 under the regenerated numerics: the recommendation is to accept the flat-piston `tau(theta)` scale, run no S3, and couple no S1/S2 schedule into Cantera. A structurally bounded species-transport variant (F23) stays optional and would be validated against the converged function-object result before replacing it.
3. Digitize or obtain Burke et al. DME/methane point data and run the direct mechanism gate.
4. Audit/select Zhao parent pressure-dependent decomposition rates.
5. Build a calibrated leakage scaling dataset; exclude uncalibrated leak-down percentages from quantitative regression.
6. Replace the single-orifice ring-pack bracket with a multi-volume labyrinth model.
7. Hot leak-down/crankcase-flow fixture when target hardware exists.
8. Correct 720-degree friction/gas-exchange model and measure motoring torque.
9. Multi-cycle residual-gas chemistry in the two-zone model.
