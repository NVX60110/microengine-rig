# C1 warm direct-flow leak-down fixture

Status: **ready for hardware implementation; no physical measurements have yet
been accepted into the leakage evidence ledger.** This document turns Issue
#13 into a measurement that can test the thermal-fit and annular-flow screens
without treating a consumer leak-down percentage as an absolute leak area.

## Objective and scope

Use a 10–15 mm reference cylinder first. The fixture should measure the chain

`temperature -> local hot fit -> direct mass flow`

at controlled static pressure. Static direct-flow rows and dynamic crankcase
blow-by rows remain separate. No fuel, ignition, or combustion is required.
The experiment is a validation of the existing `physics/thermal_clearance.py`
and `physics/annulus.py` calculations, not a new sealing model.

## Mechanical and pressure arrangement

Use a pressure-rated cylinder/liner cartridge with a piston that can be locked
at repeatable axial positions (compression TDC first, then selected positions).
Provide:

- regulated dry air or nitrogen supply and isolation valve;
- pressure-rated upstream chamber, downstream/crankcase collection line, and
  a manually reachable dump valve;
- relief valve set below the lowest-rated component, tubing, or sensor;
- mechanical crank/TDC lock and a guarded stand-off during first tests;
- leak-check ports around the head/gasket and valve paths so total leakage is
  not silently interpreted as piston/liner leakage.

Do not pressurize above the initial 6.5 bar absolute matrix. Any 25–45 bar
point belongs to a separately rated pressure design and is outside this task.

## Channels and local pairing

At every axial station, measure a bore diameter and the piston diameter at the
matching axial location and orientation. Record diametral dimensions and let
the reducer derive radial clearance. Record thrust and anti-thrust readings,
roundness, taper, and the sign convention for taper.

Temperature sensors must be paired with the same station: piston crown/upper
land and skirt stations, and the corresponding liner TDC band and lower-liner
stations. Do not pair a skirt temperature with a remote TDC liner value when
reporting a local gap. The chamber gas temperature is a separate channel used
for viscosity and flow conversion.

Minimum measured channels are:

- piston and liner temperature at each paired station;
- chamber/upstream absolute pressure, downstream/crankcase absolute pressure,
  and ambient pressure;
- direct mass flow, or volumetric flow with reference pressure and temperature;
- gas temperature, lubricant identity/quantity/condition;
- cold bore/piston dimensions, roundness, taper, and axial position.

Use `data/leakage/measurement_schema.csv` as the row contract. Every channel
uncertainty is a one-standard-deviation value supplied by the instrument or
dimensional calibration record; these are engineering sensitivity inputs, not
production statistics.

## Static measurement matrix

For each pressure/temperature/lubrication state, acquire at least three
stabilized repeats:

| Variable | Initial levels |
|---|---|
| Cylinder pressure | 2.0, 4.0, 6.5 bar absolute |
| Thermal state | room temperature; moderate warm; higher warm only if safely supported |
| Piston position | compression TDC, then documented axial stations |
| Lubrication | as-assembled/wet condition with identity, quantity and run-in state recorded |
| Repeats | 3 or more after a stated pressure/temperature stability interval |

Record the actual stabilized pressure and temperatures, not only regulator
settings. Repeat the cold geometry survey after the warm campaign if thermal
taper or piston growth may have changed the metrology datum.

The inlet flow and crankcase-outlet flow should be recorded when practical.
Their difference is a closure diagnostic; it is not permission to assign all
total leakage to the annulus if valve, head, gasket, or fixture paths are
present.

## Sensor sizing (not a leakage prediction)

The current annulus screen spans roughly 0.1–100 mg/s over the 2–7 µm hot-fit
and pressure/temperature sensitivity ranges. At approximately 1 bar and 293 K,
that is about 0.005–5 standard L/min for air. The existing 8.5 mm bracket at
about 6.5 bar absolute is approximately 0.015–0.31 standard L/min. These are
model-coverage numbers only.

Preferred flow arrangement:

- low-range mass-flow channel: 0–0.5 standard L/min full scale, resolution or
  repeatability at least 0.005 standard L/min (about 0.1 mg/s near ambient);
- alternate high-range channel: 0–5 standard L/min for gross leakage and
  fixture/path faults;
- report calibration gas, reference pressure/temperature, zero drift and
  uncertainty for the active channel.

Other preferred specifications are absolute pressure ranges covering 0–8 bar
with ≤0.1% span uncertainty, differential pressure only as a supplementary
diagnostic, piston/liner temperature uncertainty ≤2 K after calibration, gas
temperature uncertainty ≤2 K, and dimensional resolution better than 0.5 µm
diameter (0.25 µm radial) at the reference cylinder. If those dimensional
targets are unavailable, report the actual uncertainty and let the Monte Carlo
screen show whether the fit is informative.

## Calibration and run procedure

1. Survey bore and piston at all axial/angular stations; record instrument IDs,
   zero checks, roundness and taper.
2. Calibrate temperature channels against a traceable reference at room and
   warm points; document attachment location and thermal lag.
3. Zero the flow channel with the test volume isolated, then span it with a
   traceable flow standard over the low range; verify the high-range channel
   separately if used.
4. Zero and span absolute pressure channels against a calibrated reference;
   check the downstream and ambient channels together for common-mode offset.
5. If a reference restriction is used, distinguish **reference geometry** from
   a **calibrated reference CdA**. Geometry alone is not an absolute flow
   calibration.
6. Leak-check the empty fixture and head/valve paths before inserting the
   piston/liner article.
7. Lock the piston, establish the requested pressure gradually, wait for the
   stated stabilization criterion, and acquire a time block rather than one
   instantaneous value.
8. Repeat after changing pressure, temperature, lubricant condition, or axial
   position. Preserve raw time series and calibration files alongside the CSV.

## Reduction and acceptance

Run:

```bash
python scripts/reduce_leakdown_experiment.py input_measurements.csv \
  --output-csv data/leakage/reduced_experiment_results.csv \
  --output-json data/leakage/reduced_experiment_results.json \
  --mc-samples 2000
```

The reducer reconstructs each local hot clearance from the matching measured
temperatures, retains negative/zero clearance as contact, and evaluates the
existing annulus model only for positive clearance. It reports measured flow,
pressure-specific effective CdA, measured/model ratio, uncertainty percentiles
and an unconstrained log-flow/log-clearance exponent with a normal-theory 95%
interval. Dynamic blow-by rows are retained but never inverted to a steady
CdA without a pressure history/model.

The canonical `data/leakage/records.csv` is not modified by this pipeline. A
row can enter that evidence ledger only after provenance, calibration, pressure,
temperature, geometry and uncertainty satisfy the existing acceptance gates.

## What this fixture can decide

The first useful physical campaign should determine whether the reconstructed
hot clearance is in the modeled envelope, whether leakage follows an exponent
near (but not forced to) three, whether the annulus model is systematically high
or low, and how lubrication and axial taper change the result. It cannot answer
those questions from nominal cold fit or synthetic data alone. The same local
paired measurements are the minimum needed before judging an 8.5 mm ringless
architecture or deciding that a ring, different material pair, or active thermal
management is required.
