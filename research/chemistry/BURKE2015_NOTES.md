# Burke et al. 2015 — CH4/DME ignition-delay validation notes

## Source

U. Burke, K. P. Somers, P. O'Toole, C. M. Zinner, N. Marquet, G. Bourque, E. L. Petersen, W. K. Metcalfe, Z. Serinyel, H. J. Curran, **“An ignition delay and kinetic modeling study of methane, dimethyl ether, and their mixtures at high pressures,”** *Combustion and Flame* 162(2), 315–330 (2015).

DOI: `10.1016/j.combustflame.2014.08.014`

Open accepted-manuscript record recovered from NUI/University of Galway ARAN.

## Why this matters to microengine-rig

This is a primary validation source for the DME/CH4 chemistry lane. It contains new ignition-delay measurements for pure methane, pure DME, 80/20 CH4/DME and 60/40 CH4/DME mixtures and develops/validates Mech 56.54, the DME mechanism upstream of the AramcoMech 2.0 DME submechanism currently under review.

Do **not** use the paper merely as evidence that “DME ignites quickly.” Its main value is the experimental matrix, ignition-delay definition, facility treatment, pressure-dependent DME chemistry, and mechanism-validation target.

## Experimental envelope — MEASURED EVIDENCE

The paper reports new experimental ignition-delay data spanning approximately:

- Temperature: **600–1600 K**
- Pressure: **7–41 atm** for the combined study envelope
- Equivalence ratio: **phi = 0.3, 0.5, 1.0, 2.0**
- Facilities: **three shock tubes plus one rapid compression machine (RCM)**
- Fuels: pure CH4, 80/20 CH4/DME, 60/40 CH4/DME, pure DME

The authors state that new ignition-delay measurements were obtained using three different shock tubes and an RCM. High-pressure pure-fuel data were also obtained.

### Mixture definitions from Table 3 — MEASURED EVIDENCE

Mole percentages reported by the paper:

| Mix | Fuel family | CH4 % | DME % | O2 % | Diluent % | phi |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 100% CH4 | 3.055 | 0.000 | 20.367 | 76.578 | 0.3 |
| 2 | 100% CH4 | 4.990 | 0.000 | 19.960 | 75.050 | 0.5 |
| 3 | 100% CH4 | 9.506 | 0.000 | 19.011 | 71.483 | 1.0 |
| 4 | 100% CH4 | 17.361 | 0.000 | 17.361 | 65.278 | 2.0 |
| 5 | 80/20 CH4/DME | 2.228 | 0.557 | 20.423 | 76.792 | 0.3 |
| 6 | 80/20 CH4/DME | 3.646 | 0.911 | 20.051 | 75.392 | 0.5 |
| 7 | 80/20 CH4/DME | 6.974 | 1.743 | 19.177 | 72.106 | 1.0 |
| 8 | 80/20 CH4/DME | 12.829 | 3.207 | 17.640 | 66.324 | 2.0 |
| 9 | 60/40 CH4/DME | 1.535 | 1.024 | 20.471 | 76.970 | 0.3 |
| 10 | 60/40 CH4/DME | 2.516 | 1.677 | 20.127 | 75.680 | 0.5 |
| 11 | 60/40 CH4/DME | 4.829 | 3.220 | 19.317 | 72.634 | 1.0 |
| 12 | 60/40 CH4/DME | 8.939 | 5.959 | 17.878 | 67.224 | 2.0 |
| 13 | 100% DME | 0.000 | 2.058 | 20.576 | 77.366 | 0.3 |
| 14 | 100% DME | 0.000 | 3.383 | 20.298 | 76.319 | 0.5 |
| 15 | 100% DME | 0.000 | 6.545 | 19.634 | 73.821 | 1.0 |
| 16 | 100% DME | 0.000 | 12.285 | 18.428 | 69.287 | 2.0 |

The paper states N2 and O2 were mixed at 3.76:1 and test mixtures were prepared by partial pressure.

## Ignition-delay definitions and facility treatment

### RCM — MEASURED METHOD

- Compression time approximately **16 ms**.
- Ignition delay `tau_ign` defined from **end of compression to maximum rate of pressure rise**.
- Compressed pressure and ignition delay were reproducible to within **15%** at each compressed temperature according to the paper.
- Compressed temperature was calculated from initial state, composition and measured compressed pressure using an adiabatic compression/expansion calculation with temperature-dependent gamma.
- Non-reactive experiments were used to derive volume-time histories so heat loss could be represented in simulation.

### Shock tubes — MEASURED METHOD

- NUIG and two TAMU shock-tube facilities were used.
- Shock-tube ignition delay was inferred primarily from the **endwall pressure rise**; CH* or OH* chemiluminescence served as corroborating diagnostics in TAMU experiments.
- TAMU reflected-shock temperature uncertainty is reported as **10 K at time zero** for the described method.
- The TAMU facilities had relatively large driven-section diameters (>15 cm); typical boundary-layer-induced post-shock pressure rise near the endwall was reported as **2%/ms or less**.
- For some long-delay NUIG cases, non-ideal pressure rise was represented using an imposed volume profile rather than assuming a perfectly constant-volume history.

These definitions matter when comparing Cantera ignition-delay predictions: the code should match the experiment’s event definition and thermodynamic history rather than compare an arbitrary temperature-rise threshold against a plotted value.

## Supplementary-data status

**RECOVERY TARGET — not yet recovered as original machine-readable Burke supplement.**

The paper explicitly states:

- initial and compressed pressure/temperature and ignition-delay measurements for all RCM experiments were provided as **Supplementary Material**;
- additional shock-tube pressure traces were provided as **Supplementary Material**;
- the **experimental data** and CHEMKIN-format kinetics, thermodynamics and transport-property files were included as **Supplementary Material**;
- CHEMKIN-format RCM input files were also made available through the Galway combustion site.

Therefore, the original point-level Burke numerical dataset existed. The current Galway validation-panel catalog must not be mislabeled as that original dataset.

## Chemistry/model findings

### Mech 56.54 provenance — LITERATURE MODEL

Mech 56.54 was assembled from:

- the H2/CO submechanism of Keromnes et al.;
- the C1–C2 base mechanism of Metcalfe et al./AramcoMech 1.3;
- the then-recent propene mechanism of Burke et al.;
- a revised DME submechanism.

The authors used experimental data from this study plus literature flow-reactor, JSR, RCM, shock-tube, shock-tube speciation, flame-speed and flame-speciation measurements for validation.

### Pressure-dependent DME chemistry — LITERATURE MODEL RESULT

The paper emphasizes pressure-dependent treatment of low-temperature DME chemistry. The most consequential term identified was the pressure dependence of methoxymethyl-radical beta-scission:

`CH3OCH2 <=> CH3 + CH2O`

The authors report that including pressure dependence for this pathway materially changes ignition-delay prediction and that the other pressure-dependent low-temperature pathways had smaller influence on the final model predictions.

This is directly relevant to any mechanism comparison at microengine compression pressures. Do not replace this chemistry with a pressure-independent high-pressure-limit rate without explicitly testing the consequence.

### Important low-temperature pathways — LITERATURE MODEL RESULT

The paper identifies the competition involving hydroperoxy-alkyl radical fate as highly important. In particular, under representative low-temperature DME conditions:

- `CH2OCH2O2H -> CH2O + CH2O + OH` is strongly inhibiting relative to chain branching;
- `CH2OCH2O2H + O2 <=> O2CH2OCH2O2H` is strongly promoting.

The model sensitivity work also identifies DME + OH abstraction as an important promoting route in CH4/DME blends.

## Blend behavior relevant to the project

### MEASURED EVIDENCE + author interpretation

At roughly **1361 K**, `phi = 1.0`, and approximately **7–10 atm**, the paper reports representative ignition delays of:

- pure methane: **884 us**
- 80/20 CH4/DME: **152 us**
- 60/40 CH4/DME: **108 us**
- pure DME: **59 us**

Thus adding only 20% DME to methane reduced ignition delay by a factor of about **5.8** in that comparison.

This supports the project hypothesis that relatively modest DME fractions can control ignition behavior even when methane is the majority fuel. It does **not** by itself establish that the same blend will autoignite in the microengine; the engine follows a moving P/T history with heat loss, leakage and residuals.

## Rules for using this source in microengine-rig

1. Prefer recovered point-level supplementary data over plot digitization.
2. If plots must be digitized, mark every row as `LITERATURE-DERIVED / DIGITIZED`, retain panel identity and digitization uncertainty, and do not call it raw data.
3. Match experimental ignition-delay definitions when validating mechanisms.
4. Preserve facility identity and any non-ideal pressure/volume treatment.
5. Do not retune a mechanism to the project engine before first measuring its disagreement against the Burke/Zinner validation envelope.
6. Mechanism agreement with Burke is chemistry validation, **not** validation of microengine heat transfer, leakage, mixing or combustion completeness.

## Immediate follow-up

- Recover the original Burke 2015 Supplementary Material if possible.
- Zinner’s tabulated upstream 80/20 and 60/40 shock-tube rows are already ingested as the separate, explicitly identified dataset [`data/zinner2008/shock_tube_tabulated.csv`](../../data/zinner2008/shock_tube_tabulated.csv) (167 rows; see its README and ingestion report).
- Compare Zhao, LLNL, AramcoMech 2.0 and Burke/Mech 56.54-compatible chemistry against the recovered experimental rows before selecting a canonical ignition-delay mechanism for OP-IDLE.
