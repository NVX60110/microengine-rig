# Research evidence index

This directory stores compact, source-grounded engineering notes that should survive chat history and agent handoffs.

## Evidence labels

Use one of these labels on quantitative claims and design inputs:

- **MEASURED EVIDENCE** — directly reported experimental measurement or source table.
- **LITERATURE-DERIVED CALCULATION** — calculation performed from published/source quantities without fitting to this project.
- **PROJECT MODEL RESULT** — output of `microengine-rig` or another explicitly named project simulation.
- **INFERENCE** — engineering interpretation, hypothesis, extrapolation, or design proposal.

Do not silently promote an inference or digitized plot value to measured evidence.

## Source handling

- Prefer primary papers, theses, manufacturer technical documents, and machine-readable experimental datasets.
- Record DOI/repository URL and enough bibliographic information to recover the source.
- Do not commit copyrighted journal PDFs merely for convenience. Store extracted facts, exact permitted data tables when appropriate, provenance, and hashes/URLs where useful.
- Keep **original measured quantities** distinct from corrected/adjusted quantities supplied by an author.
- Keep **static leak-down** distinct from **dynamic blow-by**, **cold** distinct from **hot** clearance, and **radial** distinct from **diametral** clearance.
- If a paper says supplementary data exist but the files have not been recovered, record that explicitly rather than reconstructing them from plots without labeling the reconstruction.

## Chemistry notes

- [`chemistry/BURKE2015_NOTES.md`](chemistry/BURKE2015_NOTES.md) — Burke et al. CH4/DME ignition-delay experiment and Mech 56.54 provenance.
- [`chemistry/ZINNER2008_NOTES.md`](chemistry/ZINNER2008_NOTES.md) — upstream 80/20 and 60/40 CH4/DME shock-tube dataset, including pre-ignition pressure/temperature adjustment method and tabulated-data appendix.
- [`chemistry/REDUCED_CHEMISTRY_CFD.md`](chemistry/REDUCED_CHEMISTRY_CFD.md) — literature precedent for using detailed chemistry for validation and reduced chemistry for expensive engine CFD.

## Current acquisition priority

Highest-value missing chemistry artifact: the **Burke et al. 2015 supplementary material** for DOI `10.1016/j.combustflame.2014.08.014`.

The paper states that experiment-level initial/compressed conditions and ignition-delay measurements were supplied as supplementary material, and that the experimental data plus CHEMKIN-format kinetics, thermodynamics, transport, and RCM inputs were distributed with the study. Until that package is recovered, do not describe the current Galway validation-panel catalog as the original numerical Burke dataset.
