# Galway validation-plot recovery memo

Status: **source graphics recovered; no numerical points ingested** (2026-09-02).

## What was recovered

The University of Galway AramcoMech 2.0 validation page exposes three direct
PDF downloads relevant to this lane:

| source | direct PDF | SHA-256 | pages | panels |
| --- | --- | --- | ---: | ---: |
| DME/CH4 Petersen | [`DME_CH4_ST_PETERSEN.pdf`](https://c3.universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/pdf/validation/DME_CH4_ST_PETERSEN.pdf) | `C5B419E41C81F0ACE1B064499D4602D27BFD77F4DF68181EB4093DD645AD737E` | 4 | 8 |
| pure-DME Petersen | [`DME_ST_PETERSEN.pdf`](https://c3.universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/pdf/validation/DME_ST_PETERSEN.pdf) | `D8BA6E5266F09DF759A43903F69B60336FDA20B837F243A97780A308DBD8B65A` | 6 | 12 |
| pure-DME Cook | [`DME_ST_COOK.pdf`](https://c3.universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/pdf/validation/DME_ST_COOK.pdf) | `AA7B4A2F41D49E5239B2DF3B405DF56DA396E056D803B6D912565C8AE70597F4` | 2 | 3 |

The catalog in [`validation_plots.json`](validation_plots.json) records the
page/panel conditions visible in the plots, including the 80/20 and 60/40
CH4/DME panels, pure-DME panels, x-axis transform, y-axis scale, and source
hashes. The downloaded PDFs were inspected locally and are not committed to
the repository; the URLs and hashes make a fetched snapshot auditable without
redistributing the source graphics.

## Why no points were added

These files are validation graphics, not the original Burke supplementary
point table. They contain black-square markers and mechanism curves, but the
public download does not expose the numerical attachment, marker lineage, or
point-level uncertainty. The PDF text layer is effectively empty, so OCR is
not a machine-readable recovery path. The plots are therefore useful as a
future digitization target but do not justify labeling estimated coordinates as
original Burke measurements.

The empty [`digitized_points_template.csv`](digitized_points_template.csv)
provides the strict Burke gate fields plus source PDF/page/panel, axis
transforms, marker, digitization method/software, point lineage, and required
digitization uncertainty. A future digitized row must be separately labeled
and must not be copied into `records.csv` or a canonical `points.csv` without
review. RCM and shock-tube ignition criteria must remain separate; in
particular, pressure-rise, OH*, and OH-emission criteria must not be silently
substituted for one another.

Validate the catalog and empty scaffold with:

```bash
python scripts/validate_burke_validation_plots.py
python -m unittest tests.test_burke_validation_plots -v
```

## Recovery path

1. Request the original supplementary file from the Burke/Curran group or
   publisher repository, preserving the reported ignition criterion and
   uncertainty.
2. Enumerate the ReSpecTh/OSF RKD archive and verify Burke's DOI and whether
   each record is author-supplied or digitized/transcribed.
3. Cross-check the 80/20 and 60/40 shock-tube lane against Zinner's 2008 UCF
   thesis before any digitization is promoted.
4. If those paths fail, digitize only selected panels with calibrated axes and
   a declared uncertainty, keeping the output in a separately named dataset.

The exact catalog does not claim that any black-square point is original Burke
data, and it does not change the direct-validation gate status.
