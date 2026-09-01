# Findings ledger

Every entry records the **conditions** it was computed at. A claim without conditions is not a finding.

Status: `CONFIRMED` (cross-checked or validated) · `SCREENING` (single model, plausible) · `RETRACTED` (shown wrong) · `OPEN`

Baseline geometry unless stated: **8.5 × 7.0 mm, CR 7, rod ratio 1.6, 1200 rpm, V6 (2.38 cc)**

---

## 1. Architecture

| # | Finding | Conditions | Status |
|---|---|---|---|
| 1.1 | Net power and controllability are not simultaneously achievable | 8.5×7 mm, 1200 rpm, φ 0.40, 25% DME, 560 K wall, CR 7–18, 1.0–2.3 bar | SCREENING — bounded to explored region only, **not a theorem** |
| 1.2 | 90/10 electric-motor architecture is the working assumption | as above | SCREENING |
| 1.3 | Compression ratio substitutes for boost and removes compressor cost entirely | 1.0 bar intake, CR 13, 3 µm | SCREENING — deficit −6 W → −1.6 W, sign unchanged |
| 1.4 | 1200 rpm is near-optimal — crossover of Arrhenius delay (wants slow) vs 1/(bore·rpm) losses (wants fast) | φ 0.40, 25% DME, 560 K, 3 µm, 1.8 bar | SCREENING — 400 rpm gives Da 4.4 and *worse* IMEP |

## 2. Chemistry

| # | Finding | Conditions | Status |
|---|---|---|---|
| 2.1 | Fuel must have low-temperature chemistry. Methane, methanol, and CH3OH/CH4 e-fuel blends do not ignite | CR 7, 1200 rpm, 800 K wall, with blowby | CONFIRMED across mechanisms |
| 2.2 | DME sk39 faithfully reproduces its Zhao-2008 parent | pure DME, φ 1.0, 40 bar, 650–1100 K | **CONFIRMED** — NTC ratio 1.52 vs 1.51; delays within 5–15% |
| 2.3 | A ~40-species skeletal LTC mechanism can match shock-tube data to ~1.5× | n-heptane, 99 pts, Ciezki 1993 + Fieweger 1997, ≤60 bar | **CONFIRMED vs EXPERIMENT** — Nordin-41: median 1.53, 85% within 2×, 99% within 3× |
| 2.4 | Species count alone is insufficient — LTC pathways must be retained | same dataset | **CONFIRMED** — Peters-21 off by **154×** below 900 K, 22 non-ignitions |
| 2.5 | The Zhao-vs-LLNL 2× IMEP disagreement is ~the intrinsic uncertainty of the state of the art, not a defect | φ 0.40, 2.3 bar shared anchor | SCREENING — **report ±50% chemistry error bar on all IMEP; do not chase** |
| 2.6 | Bias direction is favourable: reduced mechanisms under-predict reactivity ~1.5×, so real boundaries sit at lower boost/CR/wall T than modelled | n-heptane evidence, inferred for DME | SCREENING |
| 2.7 | Blend ratio is a combustion-phasing control (RCCI). Pure DME over-advances | φ 0.40, 550 K, 0.004 mm² | SCREENING |
| 2.8 | ~~The engine sits in a self-stabilising NTC region~~ | — | **RETRACTED** — d(ln τ)/d(ln T) is negative everywhere for the 25/75 blend at φ 0.40; NTC is washed out by dilution and lean operation |
| 2.9 | The cool branch is stabilised by *flat* sensitivity, not positive. 900–950 K at 45 bar gives −0.06 to −0.27 vs −13 on the hot branch (~50× flatter). Higher pressure flattens further | 25/75 DME/CH4, φ 0.40 | SCREENING — replaces 2.8; **first argument for boost on stability grounds** |

## 3. Sealing

| # | Finding | Conditions | Status |
|---|---|---|---|
| 3.1 | Sealing is the binding constraint on work output | all explored | CONFIRMED both codes |
| 3.2 | Annulus and orifice models have **different pressure exponents** — annulus ṁ∝P², orifice ṁ∝P, so A_eq ∝ P_up. **No fixed CdA represents an annulus across a pressure sweep** | 10–80 bar | **CONFIRMED** — source of a 2.3× error in an earlier clearance table |
| 3.3 | Equivalent leak areas at 50 bar: 2 µm→0.00037, 3 µm→0.00124, 5 µm→0.00572 mm² | 50 bar, 1100 K, 8 mm skirt, concentric | CONFIRMED — matches Beta 2.3 canonical annulus |
| 3.4 | ~~Valve seat leakage is comparable to the entire piston annulus at 0.1 µm~~ | — | **RETRACTED** — orifice model misapplied; ~100× overstated |
| 3.5 | Valve seat spec is **<0.5 µm** (0.25 µm = 1.3% of 3 µm piston leak; 1.0 µm = 81%; 2.0 µm = 651%) | 45 bar, 1100 K, 3.5 mm valve, 0.3 mm seat width, 2 valves | SCREENING — routine lapping, manufacturing note not risk item |
| 3.6 | Ringless ABC is a hypothesis, not a solution — Toyan/CISON four-strokes use rings; ringless is two-stroke practice | — | OPEN — physical reason: four-stroke at 1200 rpm has ~17× the leak residence time of a 20,000 rpm two-stroke |
| 3.7 | Eccentricity costs more than the entire 5→3 µm improvement | e=0.5, two-zone | CONFIRMED (Beta 2.4) |

## 4. Thermal

| # | Finding | Conditions | Status |
|---|---|---|---|
| 4.1 | Wall temperature is the primary ignition lever; intake temperature is nearly irrelevant | n-dodecane, CR 7, 1200 rpm | SCREENING — T_in 300→500 K moved burn 85.5%→84.6% |
| 4.2 | Compression ratio cannot substitute for wall temperature | 450 K wall, CR 5–16 | SCREENING — no ignition at any CR |
| 4.3 | ~~Compression heating survives the wall at 1200 rpm (Fo ≈ 0.05)~~ | — | **RETRACTED** — compression is 25 ms not 6 ms; **Fo ≈ 0.5**, the wall reaches the core |
| 4.4 | ~~A hot wall improves whole-charge ignition~~ | — | **RETRACTED by Beta 2.4** — localised wall heat removes the runaway at all three anchors |
| 4.5 | Thermal balance is a heater problem, not a cooler problem. Passive loss at 550 K: 34 W bare, 18.7 W insulated, vs ~21 W indicated | V6, 38×35×40 mm block, 293 K ambient | SCREENING — ±50% on convection coefficients |
| 4.6 | Water cannot reach 277 °C without ~61 bar. Coolant must be heat-transfer oil or air+electric trim | — | CONFIRMED (saturation curve) |
| 4.7 | Wet vs dry sleeve is irrelevant — Bi ≈ 0.0035, wall is isothermal through thickness | h 300 W/m²K, 2 mm Al | CONFIRMED |

## 5. Subsystems previously unexamined

| # | Finding | Conditions | Status |
|---|---|---|---|
| 5.1 | **Friction is not a problem.** FMEP 0.018–0.044 bar with oil; 0.129–0.258 bar dry on DLC; vs 0.66–1.04 bar indicated | 1200 rpm, mean piston speed **0.28 m/s** | SCREENING — Gaussian pressure trace, ring+skirt lumped |
| 5.2 | ~~FMEP ∝ 1/L makes small engines friction-dominated~~ | — | **RETRACTED** — true at normal piston speeds; at 0.28 m/s vs 8–20 m/s full-size it does not apply |
| 5.3 | **Gas exchange is not a problem at 1200 rpm.** Mach index Z = 0.0149 vs 0.6 limit — 40× headroom, adequate to ~48,000 rpm | 3.5 mm valve, 0.8 mm lift, Ci 0.35 | SCREENING — literature warning applies at 20,000–100,000 rpm |
| 5.4 | Residuals 7.9%; PMEP is **positive +0.80 bar** when boosted | P_int 1.8, P_exh 1.0 bar | SCREENING |
| 5.5 | **Lubrication is solvable by axial thermal gradient** — only 14.3% of the liner (7.7% at CR 13) must be at 560 K | CR 7, 7 mm stroke, 1.167 mm clearance height | SCREENING |
| 5.6 | Nothing conventional survives 287 °C. Mineral 150, PAO/ester 250 → out. Polyol ester 300 marginal; MoS2 350, DLC 350, WS2 450 → OK | 560 K wall | CONFIRMED (literature limits) |

## 6. Exhaust and acoustics

| # | Finding | Conditions | Status |
|---|---|---|---|
| 6.1 | ~~0.7 m of folded runner serves both CO oxidation residence and 120 Hz quarter-wave~~ | — | **RETRACTED** — flow computed at 550 K, chemistry required at 1000 K |
| 6.2 | At consistent 1000 K: flow 213 cc/s, residence volume 18.5–26 cc, **1.28–1.79 m** of 4.3 mm tube. Sound speed 634 m/s → 120 Hz quarter-wave **1.32 m** | V6, 1200 rpm, 2.3 bar intake | SCREENING — coincidence holds at ~1.30 m, only for 120 Hz |
| 6.3 | V6 firing fundamental at 1200 rpm is 60 Hz → 2.64 m quarter-wave. 120 Hz requires a V12 at 1200 rpm or a V6 at 2400 | — | CONFIRMED (arithmetic) |

## 7. Numerics and method

| # | Finding | Conditions | Status |
|---|---|---|---|
| 7.1 | The +7 bar branch is step-converged: IMEP +7.14 → +7.01 across 8× refinement (0.5 → 0.0625°) | 1.5 bar, φ 1.1, 550 K, 0.004 mm² | CONFIRMED |
| 7.2 | v3 and canonical Beta 2.2 agree to 0.009 bar IMEP — this is **implementation agreement, not validation**. Same Cantera, same mechanism, same 0-D assumption | shared anchor | CONFIRMED as a code cross-check only |
| 7.3 | Caching γ and R per crank step: 20% speedup, IMEP shifts 1.9% | 0.125° step | OPEN — needs 4-point convergence check before adopting as default |
| 7.4 | Runtime is dominated by Cantera property crossings in `mdot_out` (24%), not the orifice math (7.5%) | profiled, 0.125° | CONFIRMED |
| 7.5 | Bare `except` in dataset parsing silently discarded all 99 points and reported "0 loaded" — a null result that looked clean | — | METHOD NOTE — audit parsing paths for this pattern |

---

## Open items

1. **Direct DME experimental validation.** ChemKED-database has no DME. ReSpecTh registration pending (manual verification, ~1 day). §2.3/2.4 give an indirect bound only — n-heptane's alkane peroxy chemistry differs from ether peroxy chemistry.
2. **Radial mixing closure.** Beta 2.4's dominant uncertainty. Mixing time is prescribed (10 ms default), not predicted. Needs a transport closure tied to thermal diffusivity, molecular diffusion, and piston-speed scaling.
3. **Sealing reality.** Eccentricity, oil film, taper, thermal growth, DME lubricity. Requires a hot leak-down fixture — the tester is a ~$40 tool, the data does not exist anywhere.
4. **Balance, vibration, manufacturing method.** Never examined.

## Recommended next builds

- **Mechanism acceptance gate** as a standing CI step: (a) NTC-vs-parent ratio, (b) ChemKED regression where data exists. Both in `tools/`.
- **Third mechanism** — keep Zhao-full alongside sk39 and LLNL so reduction error and lineage disagreement can be separated in every comparison.
- **New map objective** — instead of mapping where it *ignites*, map where **|d(ln τ)/d(ln T)| is minimised**. That is the operability metric, computable from constant-volume runs with no engine cycles.
- **NTC stability test in two-zone** — push core past 1000 K and check whether the cool branch collapses. Tests §2.9 mechanistically.
- **Valve seat as a second leak path** in the rig — same annular machinery, plus a lift schedule.
