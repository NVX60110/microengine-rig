# MicroEngine Virtual Rig — Beta 2.5 Validation and Stability Audit

## Executive result

Beta 2.5 adds a mechanism acceptance gate and then uses it to audit the claims
that arrived with the new handoff. The n-heptane experimental regression is
reproducible. The Zhao sk39 DME mechanism also reproduces its supplied parent
closely. Neither fact directly validates the DME/methane engine calculation.

The most important correction is numerical: the previously reported nearly
flat ignition-delay sensitivity was calculated from the temperature increment
per adaptive CVODE step, not from a time derivative. With maximum dP/dt as the
ignition criterion, the flat window disappears. The two-zone cool branch still
exists, but its stability cannot be attributed to that claimed flatness.

A direct two-zone CR experiment finds bounded partial oxidation above 1000 K.
It then transitions abruptly to a hot branch over 0.25 CR or less in several
mechanisms. The transition location—not a universal ±50% IMEP error bar—is the
useful chemistry uncertainty for design.

## 1. Experimental mechanism gate

`mechanism_gate.py` has two deliberately separate modes:

1. `parent`: asks whether a reduction retained its source mechanism.
2. `chemked`: asks whether a mechanism reproduces measured delays.

The ChemKED parser checks that each point declares pressure/max-dP/dt ignition,
records every rejected point, and raises on a zero-point load. This structurally
prevents the clean-looking `0 loaded` failure that motivated the audit.

### n-heptane shock-tube regression

Conditions: 99 ChemKED points from Ciezki/Adomeit 1993 and Fieweger 1997,
pressure no greater than 60 bar, adiabatic constant-volume reactor, ignition at
maximum dP/dt, 0.5 s integration ceiling.

| Mechanism | Usable / 99 | Median sim/exp | Within 2x | Low-T median |
|---|---:|---:|---:|---:|
| Nordin 41sp | 99 | 1.527 | 84.8% | 1.351 (41 points) |
| Peters 21sp | 65 | 0.659 | 10.8% | 100.0 (8 ignited points) |

Peters has 34 nonignitions at the 0.5 s ceiling. Extending the ceiling to 2 s
gives 72 usable points and a low-temperature median near 164x. Therefore the
exact Peters headline is timeout-sensitive; the robust conclusion is that it
fails the LTC region badly. Nordin's result reproduces the handoff.

This experiment bounds what one n-heptane skeletal mechanism can achieve. It
does not transfer a statistical error distribution to DME.

## 2. Zhao skeleton versus parent

Conditions: pure DME/air, phi 1.0, 40 bar, 650-1100 K, adiabatic
constant-volume, maximum dP/dt.

| Metric | Result |
|---|---:|
| Common ignitions | 10 |
| Median sk39/full delay | 1.062 |
| Range | 1.007-1.163 |
| sk39 NTC strength | 1.522 |
| full NTC strength | 1.465 |

The reduction-retention gate passes. However, the full Zhao source explicitly
requires pressure-specific rates for DME decomposition and the distributed file
activates its 1-atm fit. The parent calculation at 40 bar is therefore an
internal lineage comparison, not certification of the parent.

The repository's old `dme_luo_sk39` attribution was also wrong. A fresh
conversion from the Zhao sk39 CHEMKIN source has identical species, equations,
and forward rate constants. The canonical name is now `dme_zhao_sk39`; the old
name remains only as a deprecated configuration alias.

## 3. Temperature-sensitivity claim retracted

The handoff's sensitivity script chose ignition time from the largest raw
temperature increment between adaptive solver steps:

```text
d = T_now - T_previous
```

That is not dT/dt. It is proportional to the integrator's chosen step size and
can flatten where CVODE takes small steps. Beta 2.5 instead computes the delay
at maximum dP/dt, matching the shock-tube criterion, and then takes a centered
finite difference of ln(delay) versus ln(temperature).

At 45 bar for the 25/75 mol% DME/methane blend, phi 0.40:

| Mechanism | 850 K | 900 K | 950 K | 1000 K |
|---|---:|---:|---:|---:|
| Zhao sk39 | -2.30 | -2.89 | -2.68 | -4.97 |
| LLNL 79 | -2.84 | -4.05 | -7.09 | -9.12 |

These slopes are less steep than the hottest branch in parts of the map, but
they are not -0.06 to -0.27 and not approximately 50x flatter. The claimed
flat-sensitivity stabilization is retracted.

## 4. Direct two-zone temperature test

Common conditions: 8.5 x 7.0 mm, 1200 rpm, 25/75 mol% DME/methane, phi 0.40,
560 K wall, 3 micrometre concentric annulus, 20% boundary mass, 10 ms mixing,
100 W/m2/K inter-zone heat transfer. Fine transition samples use 0.125 degree
crank steps.

### 2.3 bar intake

| Mechanism | Highest sampled bounded point | First hotter point |
|---|---|---|
| Zhao sk39 | CR 8.25: 1219 K, 75.3%, 5.36 bar IMEP, 5.9 bar/deg | CR 8.50: 1877 K, 92.6%, 46.7 bar/deg |
| Zhao full | CR 8.00: 1169 K, 65.7%, 4.11 bar, 5.6 bar/deg | CR 8.25: 1749 K, 91.4%, 12.5 bar/deg |
| LLNL 79 | CR 8.00: 932 K, 41.4%, 1.27 bar, 3.7 bar/deg | CR 8.25: 1604 K, 90.3%, 3.9 bar/deg; rapid by CR 8.50 |

### 3.0 bar intake

| Mechanism | Highest sampled bounded point | First hot point |
|---|---|---|
| Zhao sk39 | CR 7.75: 1187 K, 71.0%, 6.32 bar, 7.9 bar/deg | CR 8.00: 1840 K, 92.1%, 39.3 bar/deg |
| Zhao full | CR 7.75: 1200 K, 74.4%, 7.02 bar, 8.0 bar/deg | CR 8.00: 1857 K, 92.3%, 47.0 bar/deg |
| LLNL 79 | CR 7.75: 1026 K, 60.2%, 4.74 bar, 5.1 bar/deg | CR 8.00: 1849 K, 92.7%, 40.8 bar/deg |

The cool branch therefore does not collapse merely because the core exceeds
1000 K. Zhao carries a bounded branch to about 1200 K under this closure. But
all lineages show a nearby abrupt secondary transition. The parent/skeleton
difference at 2.3 bar and CR 8.25 also demonstrates that a good global
ignition-delay match does not guarantee an identical bifurcation boundary.

For control-oriented screening, use the worst-lineage transition interval and
retain at least one sampled CR increment below it. This is not yet a hardware
margin because radial mixing remains prescribed.

## 5. Conversion bookkeeping correction

The original two-zone display integrated net fuel source terms with an outer
crank-step trapezoid. In stiff hot cases this could exceed 100% even while the
reactor itself conserved mass. Beta 2.5 now defines primary conversion from
global inventory:

```text
initial fuel + fuel inflow - fuel outflow - remaining fuel
```

The source-term integral remains available only to estimate whether reaction
occurred in the core or boundary zone. Numerical acceptance still checks total
and component mass residuals.

## 6. Corrections to the subsystem ledger

- The valve-seat annulus correction is physically preferable to treating the
  seat as a knife-edge orifice. The specific claim that a sub-0.5 micrometre
  hot effective gap is routine still needs leak-down data.
- The supplied FMEP screen undercounts journal energy per four-stroke cycle and
  evaluates piston work over 360 rather than 720 degrees. Its exact
  0.018-0.044 bar oil-lubricated result is not accepted as validated. Low mean
  piston speed remains favorable, but friction needs a corrected 720-degree
  model and hardware motoring torque.
- A low Mach index indicates generous valve-flow area at 1200 rpm. Linear
  extrapolation to 48,000 rpm is not a validated valve-train limit.
- An axial liner temperature gradient is a promising lubrication architecture,
  not proof that lubrication is solved.

## Engineering decision

Keep Beta 2.4's pressure-coupled two-zone solver as the canonical experimental
model and retire the competing v3 implementation. Add the acceptance gates to
every new mechanism. Do not assign a universal ±50% uncertainty to IMEP;
publish the mechanism envelope and the sampled transition interval instead.

The next decisive experiment remains hardware: measure hot leak-down and
motored/firing pressure while independently varying wall temperature. In
software, replace the fixed 10 ms inter-zone mixing time with transport closures
tied to diffusivity and piston motion, then repeat the transition map as an
uncertainty ensemble.
