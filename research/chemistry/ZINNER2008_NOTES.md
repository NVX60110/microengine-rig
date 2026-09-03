# Zinner thesis — upstream CH4/DME shock-tube dataset

## Source

Christopher Michael Zinner, **“Methane and Dimethyl Ether Oxidation at Elevated Temperatures and Pressure,”** M.S. thesis, University of Central Florida, Spring 2008.

UCF STARS record: `https://stars.library.ucf.edu/etd/3695`

The thesis is open access through UCF STARS.

### Bibliographic discrepancy

Burke et al. 2015 cites the Zinner M.S. thesis as 2006 in its reference list, while the UCF repository record and thesis front matter identify the M.S. thesis as **Spring 2008**; 2006 is Zinner’s B.S. year on the thesis front matter. Preserve this discrepancy when cross-referencing sources rather than silently treating the Burke reference-list year as definitive.

## Relationship to Burke 2015

Burke et al. states that the shock-tube results for the 80/20 and 60/40 CH4/DME blends had been described in Zinner’s thesis before archival publication in the 2015 paper.

Therefore this thesis is an **upstream experimental source** for part of the Burke blend dataset. It is not the complete Burke 2015 dataset: Burke additionally includes NUIG/tailored shock-tube, RCM, pure CH4 and pure DME results and other measurements.

## Experimental envelope — MEASURED EVIDENCE

The thesis abstract reports:

- Reflected-shock pressures: **0.8–35.7 atm**
- Temperatures: **913–1650 K**
- Equivalence ratios: **phi = 2.0, 1.0, 0.5, 0.3**
- Fuel blends: **80/20 CH4/DME** and **60/40 CH4/DME** by volume
- Ignition delay obtained from **shock-tube endwall pressure traces**

Two shock-tube facilities were used. The work was sponsored by Rolls-Royce Canada, which set the blend/equivalence-ratio test terms.

## Mixture matrix — MEASURED EVIDENCE

| Mix | phi | CH4 vol% of fuel | DME vol% of fuel | Target pressures (atm) |
|---:|---:|---:|---:|---|
| 1 | 2.0 | 80 | 20 | 20, 10, 1 |
| 2 | 1.0 | 80 | 20 | 35, 10, 1 |
| 3 | 0.5 | 80 | 20 | 20, 10, 1 |
| 4 | 0.3 | 80 | 20 | 35, 10, 1 |
| 5 | 2.0 | 60 | 40 | 20, 10, 1 |
| 6 | 1.0 | 60 | 40 | 35, 10, 1 |
| 7 | 0.5 | 60 | 40 | 20, 10, 1 |
| 8 | 0.3 | 60 | 40 | 35, 10, 1 |

The original plan was 1, 10 and 25 atm, but available diaphragms led the investigators to alternate roughly 20- and 35-atm high-pressure targets.

## Why adjusted states exist

### MEASURED OBSERVATION

The thesis reports sustained pressure/energy release between reflected-shock arrival and the main ignition event. Because the mixture was already chemically affecting the thermodynamic state before `tau_ign`, the authors developed pressure and temperature adjustments intended to represent the average conditions actually experienced before ignition.

This is important for mechanism validation. A simulation compared against Zinner data should explicitly state whether it is using:

1. the original reflected-shock `T`/`P`, or
2. the author-adjusted `T`/`P`.

Do not mix those columns silently.

The thesis reports an average adjustment across the dataset of approximately:

- **+13.9 K** in temperature
- **+0.8 atm** in pressure

Those are dataset-level summary values, not corrections to apply blindly to every row.

## Adjustment method — LITERATURE-DERIVED EXPERIMENT REDUCTION

The thesis uses pressure-trace levels before the main ignition event to estimate pressures at characteristic times and then derives corresponding temperatures using an isentropic relation with constant gamma. Time-averaged pressure and temperature are then formed over the pre-ignition interval.

For project ingestion, preserve both source columns when present rather than recomputing the adjustment from scratch unless a dedicated replication study is being performed.

## Appendix: TABULATED DATA — highest-value source artifact

The thesis contains an appendix explicitly titled **“TABULATED DATA”** beginning on thesis page 54.

The appendix provides point-level rows for the eight blend/equivalence-ratio cases and includes original and/or adjusted thermodynamic states, measured ignition delay, and correlation outputs. This is preferable to digitizing the corresponding Galway/Burke validation plots.

### Example rows from Mix #1 — MEASURED EVIDENCE

The source appendix identifies Mix #1 as 80/20 CH4/DME, `phi = 2.0`. A few rows are shown here only to lock provenance and schema; the full appendix should be ingested machine-readably by the dedicated data lane.

| Source T (K) | Source P (atm) | tau_ign (us) | Adjusted P (atm) | Adjusted T (K) |
|---:|---:|---:|---:|---:|
| 1487 | 12.4 | 39 | 13.2 | 1505 |
| 1384 | 13.8 | 84 | 14.8 | 1401 |
| 1195 | 17.0 | 477 | 17.7 | 1204 |
| 1020 | 19.1 | 1754 | 20.1 | 1030 |
| 1650 | 0.9 | 92 | 1.0 | 1656 |
| 1459 | 1.3 | 265 | 1.3 | 1472 |

The complete 167-row transcription is now preserved in
[`data/zinner2008/shock_tube_tabulated.csv`](../../data/zinner2008/shock_tube_tabulated.csv),
with row-level printed/PDF page provenance. The ingestion and source-hash
checks are documented in [`data/zinner2008/README.md`](../../data/zinner2008/README.md)
and [`data/zinner2008/INGESTION_REPORT.md`](../../data/zinner2008/INGESTION_REPORT.md).
The sample rows above are only a provenance anchor, not a substitute for that
machine-readable table.

## Correlation ranges — AUTHOR MODEL, not raw evidence

The thesis developed two empirical ignition-delay correlations from adjusted data:

- High-temperature correlation: **T >= 1175 K**, approximately **0.8–35.3 atm**
- Low-temperature correlation: **T <= 1175 K**, approximately **18.5–40 atm**

Use the correlations only as literature-derived summary models. For mechanism validation, prefer the underlying point-level measurements.

## Experimental trends reported by the author

### MEASURED EVIDENCE + author interpretation

- At pressures at or below roughly **10 atm**, increasing DME concentration consistently shortened ignition delay in these methane-based blends.
- At pressures above roughly **10 atm**, especially toward colder conditions, the ordering can change; fuel-rich mixtures with less DME may in some cases ignite faster.
- The author notes possible NTC behavior at temperatures colder than the measured high-pressure range.

These statements are useful guards against assuming a globally monotonic “more DME = always faster” rule.

## Data-ingestion requirements for microengine-rig

A canonical extracted dataset should preserve at minimum:

- source citation and repository record
- mix number
- CH4/DME fuel ratio
- equivalence ratio
- facility if identifiable per row
- original temperature
- original pressure
- measured ignition delay
- adjusted temperature
- adjusted pressure
- correlation outputs if retained, clearly marked as author-model values
- page/table provenance

Recommended evidence label for the measured rows: **MEASURED EVIDENCE — Zinner shock-tube measurement**.

Adjusted T/P should retain an additional field describing them as **author-reduced/adjusted experimental conditions**, not independent sensor measurements.

## Immediate project use

1. Use the ingested 167-row Appendix TABULATED DATA table and its provenance checks.
2. Cross-reference Zinner rows to the existing Burke 2015 panel catalog.
3. Do not assume every Burke 2015 plot point is present in Zinner; the later paper has a wider facility/data scope.
4. Use the point-level dataset for Cantera mechanism validation before any project-specific chemistry tuning.
