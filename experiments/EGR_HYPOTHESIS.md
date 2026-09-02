# Pure-DME + EGR stability hypothesis

Status: **hypothesis only**. Do not use as a design default until Issue #4 (direct Burke DME/CH4 validation) is complete enough to justify mechanism choice.

## Claim to test

A single-fuel DME architecture with controlled EGR/residual gas may provide a more stable autoignition-phasing lever than the current methane-retarded DME blend.

The external Fable 5.1 handoff reported favorable local ignition-delay slopes
for CO/H2O-rich EGR at one 0-D state. The bounded reproduction now defines the
signed diagnostic as

`S = d ln(tau_ign) / d ln(T)`

with ordinary ignition giving `S < 0`. `FUEL_TEMPERATURE_SENSITIVITY_REPORT.md`
and its CSV/JSON preserve the 40-bar, 875-975 K curves with a common max-dP/dt
criterion. No tested DME/CO+diluent recipe both reached the 2-5 ms target and
retained a nonnegative/near-flat response across Zhao and LLNL. This is a
negative architecture screen, not proof that EGR cannot be useful at an
evolving engine state.

The separate prescribed-residual adapter also shows why a frozen exhaust
vector is insufficient. At the nominal OP-IDLE anchor both its 5% and 30%
mass-residual maps remain unconverged at the bounded eight-iteration cap, even
though deterministic reruns reproduce the cool-branch trends exactly and the
independent numerical gates pass. Neither result is a valve-derived internal-
residual prediction or a 720-CAD stable cycle.

## Required experiment

1. Retain the implemented signed ignition-delay diagnostic and its local curve;
   do not rename it a system-stability metric.
2. Extend beyond the completed 40-bar constant-volume reproduction only when
   an actual evolving engine state or experimental target justifies it.
3. Keep the completed Zhao sk39/full and LLNL comparison; Burke Mech_56.54
   remains a compatibility diagnostic until point-level validation is available.
4. Sweep EGR fraction and EGR constituent composition instead of using one frozen exhaust vector.
5. Separate thermal dilution from chemical composition where practical (N2/CO2/H2O controls).
6. Extend the completed prescribed-residual adapter to a valve-derived 720-CAD
   periodic state before treating residual fraction as an engine output. A
   one-pass frozen exhaust composition is not enough to establish negative
   feedback.
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
