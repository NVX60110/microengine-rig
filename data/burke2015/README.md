# Burke 2015 CH4/DME ignition-delay data

This directory is reserved for the direct experimental gate associated with:

U. Burke et al., *An ignition delay and kinetic modeling study of methane,
dimethyl ether, and their mixtures at high pressures*, Combustion and Flame
162(2) (2015) 315-330. DOI: `10.1016/j.combustflame.2014.08.014`.

## Source status

As of 2026-09-01, public University of Galway assets located by the project
include:

- the accepted author manuscript;
- Mech_56.54 reaction, thermo, and transport files;
- RCM volume-time histories;
- the DME/CH4 validation PDF linked from the AramcoMech 2.0 validation page.

The raw Mech_56.54 package is now archived in
[`mech_56_54/`](mech_56_54/), with a reproducible Cantera 3.2 conversion to
[`mechanisms/burke_mech_56_54.yaml`](../../mechanisms/burke_mech_56_54.yaml).
The conversion and required-species smoke test are separate from the direct
experimental gate; installing a mechanism does not make its predictions an
experimental validation result.

A trustworthy machine-readable table of the paper's experimental ignition-delay
points has **not** yet been located. Do not fill `points.csv` by silently OCRing
or estimating low-resolution plots. Acquisition priority remains:

1. original author/supplementary point table;
2. archived/source plotting data;
3. careful figure digitization only if 1-2 fail, with explicit digitization
   provenance and uncertainty.

The bounded search through the Galway mechanism page, paper and accepted-
manuscript mirrors, publisher metadata, and public mechanism/data indexes did
not recover the original point table or supplementary numeric file. No Burke
experimental rows have therefore been fabricated or added. The published
figures remain usable as qualitative evidence and as a possible future
digitization target, but any digitized points must be placed in a separately
named dataset with figure/page coordinates and explicit uncertainty.

The Galway validation graphics themselves are cataloged in
[`validation_plots.json`](validation_plots.json), with direct URLs, retrieved
snapshot hashes, panel conditions, and axis transforms. The recovery memo
[`VALIDATION_PLOT_RECOVERY.md`](VALIDATION_PLOT_RECOVERY.md) explains why the
plots are not treated as point data. The empty
[`digitized_points_template.csv`](digitized_points_template.csv) is a future
scaffold only; it is not an input to `burke2015_gate.py` and contains no
unreviewed values.

## CSV schema

Use `template.csv` as the header. Required columns:

- `temperature_K`
- `pressure_bar`
- `ignition_delay_s`
- `equivalence_ratio`
- `composition_json` — complete gas composition as a JSON object, e.g.
  `{"CH4":0.04,"CH3OCH3":0.01,"O2":0.20,"N2":0.75}`
- `ignition_target` — preserve the experiment's actual diagnostic target
- `ignition_type` — preserve the experiment's actual definition
- `facility` — distinguish each shock tube and the RCM
- `mixture_label` — e.g. `80CH4_20DME`, `60CH4_40DME`, `pure_DME`
- `provenance` — original table/supplement or figure/page identifier

Optional columns:

- `ignition_delay_uncertainty_fraction` — `0.10` means a reported ±10% relative
  uncertainty; leave blank if unavailable
- `temperature_uncertainty_K`
- `pressure_uncertainty_bar`
- `notes`

Do not invent missing uncertainty values.

## Current regression diagnostics

`burke2015_gate.py` currently compares only criteria the Cantera gate can
reproduce exactly enough to name without substitution:

- `pressure` + `d/dt max` -> maximum simulated dP/dt
- `temperature` + `d/dt max` -> maximum simulated dT/dt

Other criteria are preserved in the CSV but reported as unsupported rather than
silently mapped to pressure ignition. Add an explicit diagnostic implementation
before using data based on OH/OH* emission, species thresholds, or another
facility-specific ignition definition.

Run example after real points are added:

```bash
python burke2015_gate.py \
  --mechanism mechanisms/dme_zhao_sk39.yaml \
  --data data/burke2015/points.csv \
  --max-pressure-bar 60 \
  --output-prefix burke2015_zhao_sk39
```

If a mechanism uses different species names, pass repeated mappings such as
`--alias CH3OCH3=ch3och3`. If a CSV uses `DME` as a readable synonym, map it
to the canonical schema token with `--alias DME=CH3OCH3`; the gate follows both
steps without altering the input schema.

Outputs include overall sim/experiment metrics plus facility, mixture, and exact
pressure stratification. They remain ignition-delay validation results, **not**
a universal engine-IMEP error bar.
