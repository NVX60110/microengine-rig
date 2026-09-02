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

## Near-scale miniature-engine evidence

### Tian / University of Minnesota, SAE 2010-32-0018 — AP .09 miniature engine
- Paper: *Experimental Tests and Simulations of A 1.5 cc Miniature Glow-Ignition Two-Stroke Engine*.
- DOI: 10.4271/2010-32-0018.
- Engine class: AP .09 / AP Hornet-scale glow engine, approximately 1.5 cc.
- Geometry independently documented for the AP Hornet lineage: 12.5 mm bore, 12 mm stroke, 1.47-1.475 cc displacement.
- Experiment: dedicated motoring/firing bench measured cylinder pressure, crankcase pressure, brake torque, fuel flow, air flow and emissions. The authors state that a piston-cylinder blow-by model suitable for miniature engines was developed and verified from the measurements.
- Transfer: this is the closest public experimental lineage found so far to the 8.5 mm target bore and is high-priority near-scale evidence.
- Current quantitative status: **not yet an accepted leakage record**. Publicly indexed abstract/metadata confirms the measured quantities and model verification but does not expose enough point-level blow-by flow/pressure data to recover a calibrated `CdA` without the full paper/underlying data.
- URL: https://saemobilus.sae.org/papers/experimental-tests-simulations-a-15-cc-miniature-glow-ignition-two-stroke-engine-2010-32-0018

### University of Maryland miniature-engine scaling thesis — AP Hornet geometry anchor
- Source: *The Scaling of Performance and Losses in Miniature Internal Combustion Engines*.
- AP Hornet geometry reported: 12.5 mm bore, 12 mm stroke, 1.47 cc displacement; geometric compression ratio 13.3.
- Use: geometry/performance anchor for identifying the exact miniature-engine family used in related CCEFP work.
- Leakage use: qualitative/identification only; no accepted calibrated leak-flow datum extracted from the indexed text.
- URL: https://api.drum.lib.umd.edu/server/api/core/bitstreams/3ae6ca8c-b068-4d07-90dc-7f5bf6a95b3c/content

### CCEFP free-piston engine/compressor program — AP .09 piston/liner family
- Source family: CCEFP annual reports, University of Minnesota.
- The free-piston engine/compressor used AP .09 model-engine cylinder hardware with 12.5 mm engine bore and 12 mm nominal stroke lineage.
- The program explicitly modeled blow-by leakage as a design loss and used the AP .09 liner in prototypes.
- A later report documents the stock AP piston/liner as an ABC-style thermal-fit system: the room-temperature liner is tapered with negative clearance near TDC so that the seal improves when warm.
- Reported geometry intervention: stock liner about 12.48 mm near TDC; engine liner reamed to about 12.51 mm and compressor liner to about 12.55 mm. The report states that the larger warm clearance increased blow-by leakage.
- Transfer: strong near-scale evidence that thermal taper/clearance and lubrication dominate sealing behavior at ~12.5 mm bore; supports testing hot and cold states rather than treating one room-temperature radial clearance as universal.
- Quantitative leakage status: qualitative/geometry evidence only until absolute flow-versus-pressure values are recovered.
- URLs:
  - https://www.ccefp.org/wp-content/uploads/2016/05/Y5_Ann_Rep_VOL_2.pdf
  - https://www.ccefp.org/wp-content/uploads/2016/05/CCEFP_Y6_Volume_2.pdf
  - https://www.ccefp.org/wp-content/uploads/2016/05/CCEFP_Annual_Report_Vol_2_Y9_REDUCED.pdf

### AP Hornet commercial/secondary geometry confirmation
- AP Hornet .09 is documented as an ABC two-stroke engine with 12.5 mm bore and approximately 1.47 cc displacement.
- Use: cross-check only, not leakage evidence.
- URLs:
  - https://hobbyking.com/en_us/ap-09a.html
  - https://www.model-engine-world.co.uk/ap.htm

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

## First-pass search conclusion

The 10-30 mm literature search found a **high-value 12.5 mm experimental lineage**, but no openly indexed point table yet satisfies the C1 absolute-area acceptance gate. Therefore:

- do not populate `records.csv` with inferred AP Hornet leak rates;
- do not regress a bore exponent yet;
- prioritize obtaining the full SAE 2010-32-0018 paper or underlying University of Minnesota data because it is the closest identified experimentally verified miniature-engine blow-by source;
- preserve the CCEFP taper/reaming observations as qualitative near-scale evidence that thermal clearance and oil state must be explicit variables in any hardware fixture.

## Static small-engine targets still needed

Highest-value missing evidence remains a **small-bore calibrated leak fixture** or direct mass-flow measurement. Priority search bands:
- model/RC glow or gasoline engines, roughly 10-30 mm bore;
- small industrial / chainsaw / motorcycle cylinders, roughly 30-60 mm bore;
- same-tester families spanning multiple bores;
- any published fixture reporting actual leakage flow at known pressure and temperature.

One trustworthy 10-30 mm direct-flow dataset is more valuable to the 8.5 mm extrapolation than many additional automotive service-manual percentages.
