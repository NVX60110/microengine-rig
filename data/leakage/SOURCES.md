# Leakage source ledger

This file tracks candidate sources before numerical extraction. Presence here does **not** make a source quantitative evidence.

## Standardized differential tester

### FAA AC 43.13-1B
- Type: measurement-method standard / guidance.
- Use: establishes how a differential compression tester works and documents a standard restrictor family.
- Restrictor for cylinder bore <5.00 in: 0.040 in diameter, 0.250 in long, 60 degree approach.
- Transfer: suitable for grouping comparable standardized tester records and computing leak/reference effective-area ratios from the two pressures.
- Limit: geometry alone is not a calibrated absolute `CdA`; do not infer absolute leak area without reference-flow calibration/discharge information.
- URL: https://www.faa.gov/documentLibrary/media/Advisory_Circular/43.13-1B.pdf

## Dynamic blow-by candidates

### Aghdam et al. (2010)
- Paper: *Validation of a blowby model using experimental results in motoring condition with the change of compression ratio and engine speed*.
- DOI: 10.1016/j.expthermflusci.2009.10.021
- Engine: single-cylinder research engine, bore 80 mm, effective stroke 53 mm.
- Conditions reported in public article text: CR 7.6 / 10.2 / 12.4 and 750 / 1500 / 2000 rpm, motoring study with measured cylinder pressure.
- Candidate use: dynamic blow-by / crevice-model evidence.
- Extraction rule: enter quantitative flow only if a directly recoverable measured flow or adequately specified inversion quantity is present in the full paper. Do not infer flow from model agreement alone.

### Koszalka et al. (2022)
- Existing repo anchor: `sealing_prior.py`.
- Use today: ring-pack model structure, wear sensitivity, and broad uncertainty width.
- Quantitative upgrade: extract measured blow-by values only with table/figure provenance and operating condition metadata.

### Energies 14 (2021) 8566
- Paper: *Implementation of a Multi-Zone Numerical Blow-by Model and Its Integration with CFD Simulations for Estimating Collateral Mass and Heat Fluxes in Optical Engines*.
- Public table provides 79.0 mm bore, 81.3 mm stroke and detailed ring/crevice geometry; tuned orifice discharge coefficients are also reported.
- Use: model-architecture and geometry anchor; quantitative measured-flow use requires tracing which values are experimental versus tuned/model-derived.

## Static small-engine targets still needed

Highest-value missing evidence is a **small-bore calibrated leak fixture** or direct mass-flow measurement. Priority search bands:
- model/RC glow or gasoline engines, roughly 10-30 mm bore;
- small industrial / chainsaw / motorcycle cylinders, roughly 30-60 mm bore;
- same-tester families spanning multiple bores;
- any published fixture reporting actual leakage flow at known pressure and temperature.

One trustworthy 10-30 mm direct-flow dataset is more valuable to the 8.5 mm extrapolation than many additional automotive service-manual percentages.
