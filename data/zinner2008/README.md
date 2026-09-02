# Zinner (2008) CH4/DME shock-tube data

This directory contains an exact transcription of the **TABULATED DATA**
appendix in Christopher M. Zinner, *Methane and Dimethyl Ether Oxidation at
Elevated Temperatures and Pressure*, M.S. thesis, University of Central
Florida (2008), STARS record 3695 / CFE0002096.

## Contents

`shock_tube_tabulated.csv` contains 167 measured Zinner shock-tube rows:

- 80/20 CH4/DME by volume: Mix #1 (phi 2.0), #2 (1.0), #3 (0.5), #4 (0.3),
  77 rows total;
- 60/40 CH4/DME by volume: Mix #5 (phi 2.0), #6 (1.0), #7 (0.5), #8 (0.3),
  90 rows total.

The thesis table prints adjusted temperature/pressure, ignition delay, original
pressure/temperature, and one of two correlation columns. The CSV preserves the
numeric values and leaves the unprinted correlation column blank. Pressures are
atm and delays are microseconds, exactly as printed; no conversion is applied.

`adjustment_status=adjusted_state_not_delay` means that the reported average
state was adjusted by the thesis procedure. It does not claim that the measured
`tau_ign` itself was altered. The ignition target is the total endwall pressure
rise delay described in the thesis.

## Provenance and limits

Every row identifies the mixture, PDF page, printed page, and row number. The
source PDF was supplied locally and is not committed. Its SHA-256 is recorded
in `source_status.json` for identity checking. The thesis describes two shock
tube facilities, but the Appendix rows do not identify facility per row, so the
CSV deliberately uses `not_stated_per_appendix_row` rather than guessing.

These are measured Zinner shock-tube table rows, not digitized values and not a
complete Burke et al. (2015) supplemental dataset. Do not merge them into a
Burke validation table without an explicit scientific review.

Source record: https://stars.library.ucf.edu/etd/3695/
Legacy identifier: CFE0002096

## Reproduce and validate

From the repository root:

```text
python scripts/ingest_zinner_tabulated.py
python scripts/validate_zinner_data.py
python -m unittest tests.test_zinner_data
```

The ingestion script contains only the verbatim Appendix numeric rows; it does
not read or scrape a PDF and cannot infer missing values from figures.
