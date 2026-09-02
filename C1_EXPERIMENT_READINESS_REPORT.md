# C1 experiment readiness report

Status: **calculated pipeline and fixture specification complete; physical
measurement campaign not yet run.** This branch does not add rows to
`data/leakage/records.csv`, does not claim a calibrated leak rate, and does not
promote a sealing architecture.

## What was built

- `data/leakage/measurement_schema.csv` is the strict row contract for a
  10–15 mm reference cylinder. It preserves diameter versus radial dimensions,
  local axial pairing, pressure/gas state, lubricant condition, flow-meter
  reference state, and per-channel uncertainties.
- `scripts/reduce_leakdown_experiment.py` reconstructs local hot clearance with
  `physics/thermal_clearance.py`; reports signed clearance, thermal growth,
  contact/interference, measured mass flow, pressure-specific effective CdA and
  the existing annulus-model flow for positive-clearance static rows.
- Static direct/differential and dynamic blow-by rows remain separate. Dynamic
  rows are explicitly marked `dynamic_not_inverted`; no steady CdA is inferred
  without a pressure history.
- Uncertainty propagation perturbs dimensions, paired temperatures, pressures,
  flow channel and viscosity. JSON output includes p05/p50/p95 intervals for
  hot clearance, measured CdA, modeled flow and measured/model ratio, plus a
  sensitivity ranking. The assumptions are independent Gaussian channel errors
  supplied by the experimenter, not production distributions.
- `experiments/WARM_LEAKDOWN_FIXTURE.md` specifies the pressure-rated fixture,
  measurement matrix, sensor coverage, calibration and repeat procedure.
- Synthetic rows exercise the pipeline in temporary files only. They are never
  copied into the canonical evidence ledger.

## Reduction contract

For each accepted local station the calculation is:

1. derive cold radial clearance from the measured diameters and cross-check any
   independently reported clearance;
2. pair piston and liner temperatures at that same station and calculate signed
   hot radial clearance;
3. if the mode is static and clearance is positive, evaluate
   `physics.annulus.py` with the actual bore, flow length, pressure, gas
   temperature, viscosity and eccentricity;
4. report measured/model flow ratio and pressure-specific effective CdA;
5. retain contact, missing-flow, nonpositive-pressure and dynamic rows with an
   explicit status rather than manufacturing a zero or steady leak value.

The h³ test fits `log(measured mass flow)` versus `log(positive hot clearance)`
only within like-for-like groups: cylinder, axial station, lubricant condition,
pressure pair, gas temperature, flow length and eccentricity are held fixed.
The exponent is free; three is an annulus expectation, not a constraint.

## Synthetic pipeline check

The test suite generates known annulus flows at 2, 3, 4 and 5 µm clearance and
recovers an exponent of 3.0. It also checks local hot-fit reconstruction,
measured/model ratio, explicit dynamic non-inversion, nonpositive pressure
handling, uncertainty output, and synthetic-file isolation. These checks prove
the reduction mechanics only; they are not hardware evidence.

## Sensor and fixture envelope

The current model is used only for sensor sizing. It spans approximately
0.1–100 mg/s over the clearance/pressure sensitivity screen, or about
0.005–5 standard L/min near 1 bar and 293 K. A practical two-range arrangement
is therefore a low channel around 0–0.5 standard L/min with ≤0.005 standard
L/min resolution and a 0–5 standard L/min fault/gross-leak channel. Absolute
pressure should cover at least 0–8 bar with about 0.1% span uncertainty; paired
temperature uncertainty should be about 2 K or better; and dimensional
resolution should be better than 0.5 µm diameter where feasible. These are
instrument requirements, not predicted hardware leakage.

The initial static matrix is 2.0, 4.0 and 6.5 bar absolute, room temperature,
one moderate warm state, and one higher warm state only if the fixture is rated
for it, with at least three stabilized repeats. Record actual pressure and
temperature, piston position, axial taper, lubricant state and raw calibration
metadata.

## Evidence boundaries

No AP .09/Hornet absolute airflow or blow-by point with simultaneous pressure,
temperature and fit metadata was recovered in this work. The existing
near-scale sources remain qualitative/geometry evidence; no graph-digitized or
inferred row was promoted. No synthetic row entered `records.csv`.

## Decision gate for the physical campaign

The next physical measurements must establish:

1. whether measured local hot clearance occupies the calculated envelope;
2. whether same-cylinder leakage has a fitted clearance exponent near three;
3. whether the annulus model is systematically high or low and by how much;
4. whether lubricant condition changes the effective flow correction;
5. whether taper/axial thermal gradients dominate nominal cylindrical clearance;
6. whether an 8.5 mm ringless fit remains plausible after those measurements;
7. what measured contact, leakage or repeatability result would force a ring,
   alternate material pair, larger mule or active thermal management.

Until those rows exist, the strongest defensible conclusion is methodological:
the project is ready to measure `temperature -> hot fit -> leakage`, but it has
no new hardware-calibrated sealing result.
