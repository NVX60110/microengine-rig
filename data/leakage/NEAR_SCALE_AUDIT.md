# Near-scale leakage evidence audit

Status: first public-source pass for C1 sealing.

## Question

Can public 10-30 mm bore engine/compressor evidence provide calibrated leakage data that can be converted to effective `CdA` and used in the bore-scaling regression?

## Result

Not yet. The search found a very relevant 12.5 mm experimental lineage, but the openly indexed material does not expose a point-level leak-flow dataset with enough pressure/temperature metadata to enter `data/leakage/records.csv` as absolute quantitative evidence.

## Best near-scale source: AP .09 / AP Hornet lineage

Geometry:
- bore: 12.5 mm
- stroke: 12 mm
- displacement: about 1.47-1.475 cc
- piston/liner architecture: ABC-style aluminum piston / brass chrome-plated liner in the commercial engine lineage

The University of Minnesota SAE paper `2010-32-0018` reports a dedicated 1.5 cc AP .09 test bench. Motoring and firing tests measured cylinder pressure, crankcase pressure, brake torque, fuel flow, air flow and emissions, and the measured data were used to develop and verify a piston-cylinder blow-by model for miniature engines.

That makes this the closest identified experimental blow-by study to the 8.5 mm target. However, the publicly indexed abstract does not provide the point-level blow-by flow/pressure data needed for a direct `CdA` inversion.

## Thermal-clearance evidence from CCEFP free-piston prototypes

CCEFP later reused the AP .09 piston/liner family in a free-piston engine/compressor program.

The annual-report lineage documents:
- a tapered stock liner with negative cold clearance near TDC;
- approximately 12.48 mm liner diameter near TDC before reaming;
- engine liner reamed to about 12.51 mm;
- compressor liner reamed to about 12.55 mm;
- the explicit observation that larger warm clearance increased blow-by leakage.

This evidence is not an absolute leak-rate datum, but it is directly relevant to fixture design: a static room-temperature clearance alone is not a sufficient sealing descriptor at this scale. Temperature, lubrication, axial piston position/taper and running clearance must be recorded.

## C1 acceptance decision

No AP Hornet / CCEFP numerical row is entered into `records.csv` from this pass because:
- no point-level direct mass/volumetric leak flow was recovered from the indexed public text;
- no differential reference `CdA` or calibrated fixture curve was recovered;
- inferring leak flow from model agreement, liner reaming, engine performance or qualitative statements would violate the C1 gate.

## Search implication

The next highest-value acquisition target is the full SAE 2010-32-0018 paper or author/University of Minnesota source data. It is substantially more valuable than adding more full-size automotive service-manual leak-down percentages because its 12.5 mm bore is only 47% larger than the target 8.5 mm bore.

If the full paper still lacks recoverable point values, the practical path should shift toward our own same-fixture direct-flow measurements on a 10-20 mm ABC/model-engine cylinder rather than force a literature regression.

## Sources

- SAE 2010-32-0018: https://saemobilus.sae.org/papers/experimental-tests-simulations-a-15-cc-miniature-glow-ignition-two-stroke-engine-2010-32-0018
- University of Maryland miniature-engine scaling thesis: https://api.drum.lib.umd.edu/server/api/core/bitstreams/3ae6ca8c-b068-4d07-90dc-7f5bf6a95b3c/content
- CCEFP Year 5 report: https://www.ccefp.org/wp-content/uploads/2016/05/Y5_Ann_Rep_VOL_2.pdf
- CCEFP Year 6 report: https://www.ccefp.org/wp-content/uploads/2016/05/CCEFP_Y6_Volume_2.pdf
- CCEFP Year 9 reduced report: https://www.ccefp.org/wp-content/uploads/2016/05/CCEFP_Annual_Report_Vol_2_Y9_REDUCED.pdf
