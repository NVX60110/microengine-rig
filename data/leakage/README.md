# Leakage evidence schema

This directory is for **measured sealing evidence**, not guessed microengine priors.

## Modes

### `static_direct`
A static leakage fixture reports mass flow directly, or reports volumetric flow at a known pressure and temperature. Required for absolute `CdA`:

- `bore_mm`, `stroke_mm`
- `temperature_K`
- `upstream_pressure_bar_abs`, `downstream_pressure_bar_abs`
- either `mass_flow_kg_s` or `volume_flow_L_min` plus `volume_flow_pressure_bar_abs` and `volume_flow_temperature_K`

### `static_differential`
A two-gauge differential tester with a reference restriction. Required:

- `tester_supply_pressure_bar_abs`
- `tester_cylinder_pressure_bar_abs`
- `ambient_pressure_bar_abs`
- `temperature_K`

If `reference_cda_mm2` is known from calibration, the record enters the absolute-area lane. If only `reference_orifice_diameter_mm`/geometry is known, the record enters the standardized-relative lane and reports only `leak_to_reference_cda_ratio`.

**Do not infer absolute `CdA` from reference diameter alone.** A geometric diameter does not provide the restriction's discharge coefficient.

FAA AC 43.13-1B is a useful standardized-tester anchor: for aircraft cylinders under 5.00 in bore, it specifies a 0.040 in diameter, 0.250 in long restrictor with a 60 degree approach. That defines a tester family; it does not by itself provide an absolute calibrated `CdA`.

### `dynamic_blowby`
Direct crankcase/blow-by mass or referenced volumetric flow. Keep this separate from static leak-down. Record RPM, compression ratio, load/motored condition, and whether cylinder-pressure history is available.

Do not turn a cycle-averaged blow-by measurement into one steady `CdA` unless the pressure history and inversion model are supplied.

## Columns

The template intentionally contains more fields than any one record needs.

Core provenance:
- `record_id`
- `dataset_family`
- `mode`
- `source_url`
- `provenance`
- `uncertainty_fraction`
- `notes`

Geometry / engine:
- `bore_mm`
- `stroke_mm`
- `cylinders`
- `seal_architecture`
- `thermal_state`
- `rpm`
- `compression_ratio`
- `load_label`
- `pressure_trace_available`

Gas state:
- `gas`
- `gas_constant_J_kgK`
- `gamma`
- `temperature_K`
- `ambient_pressure_bar_abs`

Direct-flow lane:
- `upstream_pressure_bar_abs`
- `downstream_pressure_bar_abs`
- `mass_flow_kg_s`
- `volume_flow_L_min`
- `volume_flow_pressure_bar_abs`
- `volume_flow_temperature_K`

Differential-tester lane:
- `tester_supply_pressure_bar_abs`
- `tester_cylinder_pressure_bar_abs`
- `reference_cda_mm2`
- `reference_orifice_diameter_mm`
- `reference_orifice_length_mm`
- `reference_family`

## Quantitative acceptance rule

A record is not promoted because it *looks* like leak-down data. It must carry enough metadata for the applicable physical conversion. Unspecified `% leakage`, `80/70`, forum numbers, or service-manual pass/fail values remain qualitative unless the fixture/pressure definition is documented.

## Analysis

```bash
python leakage_scaling.py data/leakage/records.csv \
  --output data/leakage/results.json
```

The script reports:
- evidence-lane counts;
- pressure-aware effective `CdA` for accepted static absolute records;
- leak/reference `CdA` ratio for standardized uncalibrated differential tests;
- direct dynamic blow-by flow normalized per cylinder displacement;
- `log(CdA/Vd)` versus `log(bore)` screening regression once at least three absolute records exist;
- 95% slope interval and leave-one-dataset-family-out sensitivity;
- the existing 8.5 mm 2/3/5 um annular brackets evaluated at a stated room-temperature leak-down comparison condition.

The 8.5 mm extrapolation remains a screening comparison until small-engine hardware data exists.

## Thermal-fit linkage (C1)

`THERMAL_CLEARANCE_REPORT.md` and `data/sealing/` contain a separate
analytical screen that converts cold radial fit plus independent piston/liner
temperatures and material strain profiles into signed hot radial clearance.
Positive hot clearance is passed to `physics/annulus.py` for a sensitivity-only
flow estimate; negative clearance is retained as an interference warning and
has no annulus flow value.  These calculated rows are not measured leakage and
must not be merged into `records.csv` or the calibrated static/dynamic
regressions.

The screen reinforces the fixture requirement: record axial bore/piston
dimensions, taper, piston and liner temperature, pressure, gas state, and
lubricant condition together with direct flow.  A warm fit measurement is the
missing link between the existing engineering clearance brackets and a
credible hot blow-by datum.
