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

## Operability and two-zone behavior

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| O1 | The claimed -0.06 to -0.27 flat sensitivity window was a solver-step artifact | Handoff script maximized raw `T_now-T_previous`, not dT/dt | RETRACTED | `operability_sensitivity.py`, `BETA25_REPORT.md` |
| O2 | Correct max-dP/dt slopes at 45 bar are not flat | 25/75 DME/CH4, phi .40; Zhao slope -2.30 at 850 K, -2.89 at 900 K, -2.68 at 950 K; LLNL -2.84, -4.05, -7.09 | SCREENING chemistry diagnostic | `operability_sensitivity.csv` |
| O3 | Bounded partial oxidation can persist above 1000 K | At 2.3 bar: Zhao sk39 CR8.25 reaches 1219 K/75.3%/5.9 bar-per-deg; full CR8 reaches 1169 K; at 3 bar all lineages remain bounded at CR7.75, 1026-1200 K | SCREENING, one prescribed spatial closure | `two_zone_transition_*.json` |
| O4 | A nearby hot transition remains and is mechanism-dependent | 2.3 bar: first hotter samples sk39 CR8.5, full CR8.25, LLNL CR8.25; 3.0 bar: all hot at CR8.0 | SCREENING | `two_zone_transition_*.csv` |
| O5 | Localizing wall heat suppresses the Beta2.3 homogeneous runaway at the shared CR7 anchor | 2.3 bar, baseline closure: sk39 1.04 bar/36.6%/901 K; LLNL .66 bar/29.1%/867 K | CONFIRMED across two lineages within model | `two_zone_campaign.csv`, `BETA24_REPORT.md` |
| O6 | Radial mixing closure is the dominant model-form uncertainty | Boundary mass 10-30%, mixing 0-20 ms; branches span no reaction to runaway | SCREENING | `two_zone_campaign.csv` |

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

## Numerics and method

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| N1 | Zero-point dataset loads must fail loudly | ChemKED parsing | CONFIRMED safeguard | `mechanism_gate.py`, test suite |
| N2 | Primary two-zone conversion must use global fuel inventory | Initial + inflow - outflow - remaining | CONFIRMED bookkeeping correction | `two_zone_model.py` |
| N3 | Source-term integration is retained only for reaction localization | Stiff hot branches can accumulate outer-step quadrature error | CONFIRMED safeguard | component residuals + inventory metric |
| N4 | Accepted Beta2.4 shared-anchor results are crank-step converged | .25 to .03125 degree: sk39 IMEP 1.0446 to 1.0418; LLNL .6580 to .6537 | CONFIRMED numerical convergence | `two_zone_convergence.csv` |

## Architecture decision

| ID | Finding | Conditions | Status | Evidence |
|---|---|---|---|---|
| A1 | Retain the motor-driven display-engine architecture | No accepted default two-zone anchor/clearance/eccentricity case paid idealized compressor power; friction and gas exchange remain incomplete | SCREENING decision, not impossibility theorem | `BETA24_REPORT.md` |
| A2 | Canonical code is `microengine_rig.py` plus experimental `two_zone_model.py`; `microengine_v3.py` is retired | Beta2.5 repository | CONFIRMED project decision | README |

## Open work, in priority order

1. Replace prescribed mixing time with thermal/molecular/piston-motion transport closures.
2. Direct DME experimental regression using a citable dataset and matching criterion.
3. Audit/select Zhao parent pressure-dependent decomposition rates.
4. Hot leak-down/crankcase-flow fixture across piston temperature and position.
5. Correct 720-degree friction/gas-exchange model and measure motoring torque.
6. Multi-cycle residual-gas chemistry in the two-zone model.
