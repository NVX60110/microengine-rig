# CFD-02 zone-definition and tracer-scheme audit

This audit reprocessed the stored CFD-01 fine, S1 coarse, and S2 coarse field
directories. It did not rerun OpenFOAM for the zone audit. A second, separate
S2 coarse solve tested the requested one-line tracer convection change.

## 1. Constant-mass-fraction zone

The legacy diagnostic uses the CFD-01 radial cutoff. That cutoff is stable for
the flat piston but samples a changing chamber fraction on the stepped bowls.
The audit therefore selects cells from the liner inward at every saved output,
ranking by cylindrical radius and fractionally weighting the boundary cell so
the outer zone contains exactly 20% of the instantaneous integrated gas mass.
The complementary cells form the core. This is the CFD-01-equivalent nominal
20% two-zone diagnostic; the fixed-radius fields remain in the histories for
regression and traceability.

| history | legacy fixed-radius shell-volume range | mass-fraction zone shell-mass range | max tracer inventory drift |
|---|---:|---:|---:|
| flat CFD-01 fine | 0.198352--0.198352 | 0.200000--0.200000 | 0.002456% |
| S1 coarse | 0.086521--0.167420 | 0.200000--0.200000 | 0.006834% |
| S2 coarse | 0.071277--0.193123 | 0.200000--0.200000 | 0.016726% (gate fail) |

The normalized zone-contrast ratio is candidate contrast divided by flat
contrast, with each case normalized by its own initial zone contrast:

| crank angle | S1 / flat | S2 / flat |
|---:|---:|---:|
| -20 CAD | 1.1401 | 1.1791 |
| TDC | **1.3545** | **1.2613** |
| +20 CAD | 1.6299 | 1.6525 |
| +45 CAD | 1.7418 | 1.5141 |

A ratio above one means more of the case's initial core/shell contrast remains.
Thus the earlier global-RMS-only statement that S1 retained less segregation
does not survive as a two-zone result. The S1 local +/-5 CAD fits are weakly
log-linear (R2 0.50--0.84); the S2 TDC fit is unusable (R2=0.013). These are
screening diagnostics, not promoted instantaneous mixing times.

## 2. Tracer-scheme check

The S2 coarse geometry was rerun with
`div(phi,tracer) Gauss linearUpwind grad(tracer)` under the same controls. The
variant remained mesh-, volume-, gas-mass-, and Courant-clean, but failed both
scalar gates:

- maximum tracer-inventory drift: `0.0201883%` (`2.01883e-4` relative),
  above the `1e-4` limit;
- tracer minimum: `-0.0192431`, violating the `[0,1]` boundedness gate.

The original upwind S2 run fails inventory conservation at `0.0167264%` while
remaining bounded. Therefore `linearUpwind` is not an acceptable drop-in fix,
and no cubic or additional squish run is promoted from this audit.

## Decision

The stored S1/S2 comparisons are now explicitly split into global normalized
RMS and constant-mass-fraction zone diagnostics. Neither supports a validated
squish design conclusion while S2 fails scalar conservation. Do not run S3,
refine S1/S2, or couple a squish schedule into Cantera until the scalar
transport treatment is isolated and passes both inventory and boundedness
gates.

## Reproduction

Reprocess a stored case with:

```bash
python3 cfd/openfoam14/cold_flow_tracer/scripts/postprocess_history.py \
  /path/to/case --output cfd/results/history.csv
```

Generate the two-zone comparison with:

```bash
python3 cfd/compare_tracer_mixing.py \
  cfd/results/cfd01_scalar_history_fine.csv \
  cfd/results/cfd02_s1_coarse_scalar_history.csv \
  --metric mass_fraction_zone --targets -90 -45 -20 0 20 45 90 \
  --window-cad 5 --output cfd/results/cfd01_vs_cfd02_s1_mass_zone_mixing.json
```

The S2 variant command and all promoted/failed artifacts are listed in
`cfd/openfoam14/squish/README.md`.
