# Reduced chemistry for engine CFD — literature precedent

## Source

David Martinez Morett, **“A Reduced Chemical Kinetic Mechanism for Computational Fluid Dynamics Simulations of High Brake Mean Effective Pressure, Lean-Burn Natural Gas Engines,”** M.S. thesis, Colorado State University, Fall 2012.

This source is not a direct calibration source for the microengine. Its value is methodological: it shows a validated workflow in which detailed chemistry is used to screen/validate mechanisms and reduced mechanisms are then used to make engine CFD computationally tractable.

## Why this matters to microengine-rig

The project currently uses Cantera for detailed 0-D chemistry and OpenFOAM for flow/mixing. If future reacting CFD becomes decision-limiting, directly embedding a large DME/CH4 mechanism everywhere in the mesh may be unnecessarily expensive.

This thesis provides evidence for a staged strategy:

1. validate detailed chemistry against experiments;
2. identify a reduced mechanism that preserves the observables important to the target regime;
3. verify the reduction independently against the detailed mechanism and experiments;
4. only then use the reduced chemistry inside expensive CFD.

This is a **future performance strategy**, not permission to reduce the current chemistry before the Burke/Zinner validation lane is complete.

## Computational motivation — LITERATURE CONTEXT

The thesis notes that chemistry cost grows rapidly with mechanism size because every retained species adds transported/source equations and stiffness. In its 2012 engine-design context, the author regarded roughly one day for a combustion-cycle calculation on a PC or small cluster as a practical target and argued that reduced mechanisms were necessary for design-iteration CFD.

The absolute runtimes are hardware/software-era specific and should not be transferred to the current MSI workstation. The scaling lesson remains useful.

## Tools/workflow used in the source

- **CHEMKIN PREMIX** for 1-D freely propagating laminar flame-speed calculations.
- **CHEMKIN 0-D homogeneous constant-volume reactor** for thermal ignition-delay calculations.
- **CONVERGE CFD + SAGE detailed-chemistry solver** for engine CFD.
- Experimental flame-speed and ignition-delay data used as validation targets.
- Reaction-path and sensitivity analysis used to understand which chemistry could be retained/modified.

## Mechanism sizes compared — LITERATURE DATA

The thesis evaluated a range of full and reduced natural-gas/methane mechanisms, including:

- GRI-Mech 3.0: 51 species / 325 reactions
- DRM22: 22 / 104
- DRM19: 19 / 84
- USC II: 109 / 784
- Konnov 0.5: 125 / 1205
- Zhao et al. 2008: 52 / 290
- Zsely reduced mechanisms: approximately 48 species / 186–251 reactions
- MD19: 19 / 84
- Nagy21-Burke-MD19: 21 / 58

These mechanisms were developed for methane/natural-gas conditions, not for the project’s DME-heavy ignition problem. Do not copy them into the canonical engine model simply because they are small.

## High-pressure lean flame-speed example — LITERATURE RESULT

At the source’s selected high-pressure lean methane conditions, mechanism choice produced large differences in predicted flame speed. For example, at 20 atm and `phi = 0.7`, the thesis reports:

- experimental laminar flame speed: approximately **2 cm/s**
- GRI-Mech 3.0: **3.84 cm/s** (~92% high)
- DRM22: **3.90 cm/s** (~95% high)
- MD19: **2.58 cm/s** (~29% high)
- Nagy21-Burke-MD19: **1.90 cm/s** (~5% low)

The project lesson is not that Nagy21-Burke-MD19 is “best” for DME. The lesson is that a reduced mechanism can be compact yet materially more accurate in its intended calibration regime than a widely used larger mechanism.

## Engine CFD comparison — LITERATURE RESULT

The thesis reports that in the studied natural-gas engine CFD case:

- DRM22 predicted combustion rate more than **25%** above the measured engine behavior.
- MD19 and Nagy21-Burke-MD19 produced combustion rates closer to the measured engine result.
- Predicted start/duration of combustion with DRM22 were about **8–10 crank-angle degrees** more advanced than experiment, whereas MD19 and Nagy21-Burke-MD19 were reported within about **6 crank-angle degrees**.
- Reported computational time was approximately **147 h for DRM22** versus **133 h for MD19**, about a 10% reduction for MD19 in that case.

Again, these are literature results for a full-size lean natural-gas engine and old hardware/software. Treat them as workflow evidence, not project performance predictions.

## Important warning from the source

The thesis describes an earlier situation where spark-model parameters, wall temperatures and turbulence settings had been adjusted to compensate for an over-predicted chemical burning rate from a mechanism. The author explicitly frames that as a deviation from realistic engine parameters.

That failure mode is directly relevant to microengine-rig:

> Do not compensate for wrong chemistry by tuning unrelated heat-transfer, turbulence, leakage, spark or wall-temperature parameters.

Each submodel should be validated against the observable it actually governs wherever possible.

## Recommended future project strategy — INFERENCE

If reacting CFD becomes necessary:

### Stage 1 — detailed chemistry reference

Use the best experimentally validated DME/CH4 mechanism in 0-D/1-D Cantera over the actual engine P/T/phi/residual envelope. Preserve ignition delay, key heat-release timing, major species and pressure dependence.

### Stage 2 — targeted reduction

Build or adopt a reduced mechanism specifically over the microengine’s regime. Reduction objective should be based on project observables, not generic species-count minimization.

Candidate preservation targets:

- ignition delay across evolving compression states
- low-temperature/NTC behavior where relevant
- DME/CH4 blend sensitivity
- laminar flame speed if a flame-propagation mode is used
- heat-release timing and peak heat-release rate
- major stable species needed for energy balance

### Stage 3 — validation gates

Require the reduced mechanism to reproduce the detailed reference and available experiment within predefined error bounds before using it in CFD.

### Stage 4 — reacting CFD only if decision-limiting

Do not launch reacting 3-D chemistry CFD merely because it is technically possible. Use it when a design decision depends on spatial flame/ignition behavior that the validated 0-D/1-D + cold-flow closure cannot answer.

## Classification for external-software reconnaissance

- CONVERGE/SAGE methodology: **BENCHMARK / SCAVENGE** unless a license becomes available.
- CHEMKIN methodology: **SCAVENGE**; Cantera can reproduce many 0-D/1-D validation functions without requiring CHEMKIN.
- Reduced-mechanism workflow: **ADAPT** as a future project architecture.
- MD19 / Nagy21-Burke-MD19 mechanism files themselves: **REJECT as canonical DME chemistry** without a dedicated applicability study; they are natural-gas/methane mechanisms, not validated replacements for the Burke DME chemistry lane.
