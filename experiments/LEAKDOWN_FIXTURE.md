# Small-engine direct-flow leak-down fixture

Status: **planned hardware validation**, not yet measured.

The purpose of this fixture is to produce sealing data that can enter C1 without relying on consumer leak-down percentages or an unknown reference restrictor.

## Measurement concept

Use clean dry air or nitrogen only. No fuel and no combustion.

Pressurize the closed cylinder near compression TDC and measure:

1. cylinder absolute pressure;
2. gas temperature near the fixture/cylinder;
3. regulated inlet mass flow;
4. crankcase-outlet mass flow where practical;
5. ambient/crankcase pressure.

The upstream direct flow provides total cylinder leakage. Crankcase flow isolates the ring/piston/liner path from valve/head leakage and provides a mass-closure check.

## Target range

The current 8.5 mm ringless-annulus model, evaluated only as a sizing bracket at approximately 6.5 bar absolute and room temperature, predicts roughly `0.015-0.31 standard L/min` across the existing 2-5 um / eccentricity brackets. This is **not a hardware prediction**; it only indicates that a low-flow sensor is preferable to an automotive-scale flow meter.

Select instrumentation with enough headroom for a small reference engine that leaks more than the target brackets. A two-range setup is preferable if one sensor cannot resolve both sub-0.1 SLPM leakage and multi-SLPM gross leakage.

## First test article

A Toyan-class or similar small four-stroke reference engine is useful because it provides a real ring/liner/valve system before target hardware exists. Record exact bore, stroke, ring count, piston/liner materials, lubrication state, and test temperature.

A second engine with a meaningfully different bore is more valuable than repeated tests on the same bore for the scaling study.

## Test matrix

Minimum first article:

- pressure: approximately 2, 4, and 6.5 bar **absolute** cylinder pressure;
- position: compression TDC first; additional piston positions only where valve state and flow path remain interpretable;
- thermal state: room-temperature/cold and one repeatable warmed condition if safe and practical;
- lubrication: as-assembled/lightly lubricated state documented; do not mix dry and oiled results without labeling them;
- repeats: at least three stabilized readings per condition.

For every point record the actual pressure and temperature rather than only the regulator setting.

## Flow-path checks

Before interpreting total leakage as ring leakage:

- monitor/listen for intake-valve leakage;
- monitor/listen for exhaust-valve leakage;
- check head/gasket leakage;
- measure crankcase outlet flow if possible;
- compare inlet and identified outlet flows for closure.

If valve/head leakage is material, retain the total-leak datum but do not use it as piston/ring calibration.

## Safety / fixture controls

- mechanically restrain the engine and positively lock the crank near TDC;
- use pressure-rated tubing/fittings and a relief valve below the weakest component rating;
- put a shutoff/dump valve within reach and pressurize gradually;
- use a barrier/stand-off arrangement during first pressure tests;
- keep ignition disabled and use no flammable charge;
- do not heat a pressurized fixture beyond component/sensor ratings.

## Reduction to C1 data

For each accepted static point:

`measured mdot + P_cyl + P_ambient + T -> effective CdA(P,T)`

Do not assume the effective area is pressure-independent. Plot inferred `CdA` versus cylinder pressure first. If it varies materially, preserve the pressure dependence rather than forcing a scalar seal area.

For ringless target comparisons, evaluate `physics/annulus.py` at the **same pressure, temperature, viscosity, diameter, and flow length** as the fixture point.

For ringed reference engines, do not back-calculate a literal radial piston clearance from one `CdA`; use the measurement to constrain a ring-pack/labyrinth model class.

## Scaling campaign

The high-value dataset is several engines spanning bore, all measured on this same direct-flow fixture. Suggested priority:

1. model/Toyan-class: ~10-30 mm bore;
2. small industrial/motorcycle: ~30-60 mm bore;
3. research/automotive anchors: ~60-100 mm bore.

A same-fixture small-bore series carries much more weight in the 8.5 mm extrapolation than unrelated service-manual leak-down percentages.
