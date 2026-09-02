# Zinner table ingestion report

Status: recovered and validated from the user-provided copy of the thesis.

## Exact coverage

| Printed table | PDF page | Blend | phi | Rows |
|---|---:|---:|---:|---:|
| Mix #1 | 55 (69) | 80/20 CH4/DME | 2.0 | 23 |
| Mix #2 | 55 (69) | 80/20 CH4/DME | 1.0 | 17 |
| Mix #3 | 56 (70) | 80/20 CH4/DME | 0.5 | 19 |
| Mix #4 | 56 (70) | 80/20 CH4/DME | 0.3 | 18 |
| Mix #5 | 57 (71) | 60/40 CH4/DME | 2.0 | 24 |
| Mix #6 | 57 (71) | 60/40 CH4/DME | 1.0 | 20 |
| Mix #7 | 58 (72) | 60/40 CH4/DME | 0.5 | 25 |
| Mix #8 | 59 (73) | 60/40 CH4/DME | 0.3 | 21 |
| **Total** | | | | **167** |

Each table row was transcribed as printed. The two correlation columns are
mutually exclusive in the thesis layout: the populated value is stored in the
corresponding CSV column and the other is blank. This is not a missing-data
imputation.

## Interpretation boundaries

The adjusted temperature and pressure are the thesis' average-state adjustment
outputs. The original pressure and temperature are retained alongside them.
The `tau_ign` column is the reported endwall total ignition delay in microseconds;
the CSV does not relabel it as an adjusted delay. The thesis describes the
pressure-rise method and endwall pressure transducers in its methodology.

The appendix does not label each row by facility. Although the thesis describes
the Aerospace Corporation and Aul/Petersen shock tubes, this ingestion leaves
`facility` as `not_stated_per_appendix_row`. Assigning a facility based only on
pressure would be an unsupported inference.

The rows are measured Zinner shock-tube table data. They are not digitized from
plots and are not asserted to be the complete Burke et al. (2015) data set.
