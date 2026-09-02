# Pure-DME + EGR stability hypothesis

Status: **hypothesis only**. Do not use as a design default until Issue #4 (direct Burke DME/CH4 validation) is complete enough to justify mechanism choice.

## Claim to test

A single-fuel DME architecture with controlled EGR/residual gas may provide a more stable autoignition-phasing lever than the current methane-retarded DME blend.

The external Fable 5.1 handoff reported favorable local ignition-delay slopes for CO/H2O-rich EGR at one 0-D state. Those values are not yet reproduced in the repository and the reported stability slope `S` is not formally defined here.

## Required experiment

1. Define stability metric explicitly, e.g. a signed derivative of ignition delay with temperature over a finite local interval. Record units and sign convention.
2. Reproduce the external table at the exact reported state (`~925 K`, `~40 bar`) with versioned mechanism, composition, phi, integration criterion and tolerance.
3. Cross-check at minimum Zhao sk39, Zhao full and LLNL; add Burke Mech_56.54 if conversion/validation succeeds.
4. Sweep EGR fraction and EGR constituent composition instead of using one frozen exhaust vector.
5. Separate thermal dilution from chemical composition where practical (N2/CO2/H2O controls).
6. Iterate exhaust composition -> EGR -> next-cycle chemistry until a periodic/fixed-point state is reached. A one-pass frozen exhaust composition is not enough to establish negative feedback.
7. Perturb wall temperature, residual fraction and EGR fraction and require the claimed stabilizing sign to persist over a finite neighborhood.
8. Only after 1-7, test the surviving cases in the two-zone/repeated-cycle engine model.

## Promotion gate

Do not promote pure DME + EGR as the architecture unless:
- the qualitative stabilizing trend survives at least two experimentally credible DME mechanisms;
- direct Burke validation does not disqualify those mechanisms in the relevant temperature/pressure regime;
- the repeated-cycle fixed point is bounded rather than drifting to extinction/runaway;
- the result remains inside pressure-rise/temperature limits under modest perturbations.

## Literature note

Published DME/HCCI work supports EGR as a phasing/control lever, but steam/CO2/N2 have distinct thermal and chemical effects. Steam can chemically accelerate DME ignition relative to equivalent N2 dilution in parts of the high-pressure regime, so no EGR constituent should be labeled a universal retarder without state-specific kinetics.
