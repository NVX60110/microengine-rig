# CFD-01 findings addendum

This addendum audits `CFD01_REPORT.md` against the stored CFD-01 result files.
It is intended to accompany the report when the CFD branch is merged.

Conditions unless stated: 8.5 x 7.0 mm, CR 7.75, 1200 rpm, cold closed
cylinder, passive tracer, flat piston, OpenFOAM 14, three meshes
(2706 / 5289 / 10455 cells), outer radial shell held at approximately 20% of
cylinder volume.

## Findings

| ID | Finding | Conditions | Status |
|---|---|---|---|
| CFD1 | Flat-piston transport near TDC is consistent with molecular diffusion; fitted piston-strain coefficient is zero | Fine mesh, closure fit | CONFIRMED within CFD-01 model |
| CFD2 | `tau_mix` at TDC is 10.655 ms on the fine mesh | sampled +0.042 CAD | CONFIRMED numerical result |
| CFD3 | TDC answer is approximately mesh-converged: coarse 10.27 / medium 10.35 / fine 10.65 ms | requested 0 CAD | CONFIRMED numerical convergence (~4% coarse/fine spread) |
| CFD4 | Beta 2.4's 10 ms prescribed timescale was close to the measured flat-piston value where combustion phasing is most relevant | roughly +/-20 CAD | SCREENING model implication |
| CFD5 | `tau_mix` varies strongly with crank angle; a single scalar mixing time is not an adequate full-cycle closure | fine history | CONFIRMED within CFD-01 |
| CFD6 | Mixing is concentrated on compression/near-TDC; late expansion approaches a concentration-difference plateau as the chamber grows | full fine history | CONFIRMED qualitative trend |
| CFD7 | The report's +90 CAD phrase "local DeltaC sign reversal" should not be interpreted as physical un-mixing. The direct `DeltaC` history remains positive; the negative local derivative is noise-sensitive differentiation of a nearly flat trace | +90 CAD onward | CORRECTED interpretation |
| CFD8 | +45 CAD is not mesh-converged: coarse 24.67 / medium 32.11 / fine 39.07 ms | requested +45 CAD | OPEN; fine value is a lower bound |
| CFD9 | Zone definition is stable: the outer-shell volume fraction remains approximately 0.1984, so the zone boundary does not sweep through the gas and manufacture transport | moving cycle | CONFIRMED numerical check |
| CFD10 | Slider-crank volume closure is approximately 0.1407% with no material drift across meshes | all meshes | CONFIRMED |
| CFD11 | Very large fitted maximum mixing times in the flat late-cycle region are closure blow-up, not measured physical times | late expansion | OPEN method issue |
| CFD12 | A fixed-length pure-diffusion closure cannot reproduce the measured crank-angle schedule. Preserve and interpolate measured `tau(theta)` before attempting a lower-order fit | full cycle | METHOD NOTE |
| CFD13 | Closed-domain mass conservation has not yet been promoted as a CFD-01 result | moving mesh | OPEN; mandatory before CFD-02 |
| CFD14 | `correctPhi` should be re-evaluated before CFD-02; timestep reduction is not a substitute for demonstrating flux/mass consistency | moving mesh | OPEN numerics |

## Diffusion-scale cross-check

The earlier hand estimate `L^2/D` is a raw diffusion timescale. The first
eigenmode of a bounded diffusion problem decays with a characteristic factor
`pi^2`, giving

`tau_1 ~ L^2 / (pi^2 D)`.

Using the CFD-01 length/diffusivity scale gives approximately 10.8 ms, close to
the 10.655 ms TDC result. This agreement supports the interpretation that the
flat-piston case contains no important hidden convective mixing near TDC. It
does not prove that a squish geometry will remain diffusion-dominated.

## Mesh-convergence caveat

The stored `cfd01_mesh_convergence.csv` checks mesh size, Courant, runtime, and
volume closure, but its generic `error` column is empty. Mesh convergence of the
**transport answer** must therefore be computed from the per-mesh scalar-history
files. TDC passes approximately; +45 CAD does not.

Future campaigns should make this answer-convergence table a generated artifact,
not a post-hoc review step.

## What CFD-01 bought

The main result is the absence of an extra flat-piston stirring mechanism.
Near TDC, the measured exchange timescale is explainable by ordinary diffusion.
That narrows CFD-02 to a much cleaner question:

**Does intentional squish generate enough convective radial transport to move
the two-zone chemistry branch?**

If yes, use the CFD-derived `tau(theta)` schedule in the Cantera ensemble. If
no, freeze transport near the measured flat-piston schedule and stop optimizing
unresolved stirring.
