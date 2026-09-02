# CFD-02 S1 mild-squish coarse report

CFD-02 S1 is the first constant-compression-ratio squish experiment. It is a
nonreacting, closed-cylinder, laminar moving-mesh run with the same passive
radial tracer used by CFD-01. No chemistry or canonical Cantera model was
changed. This report records the coarse screening result only; S2 and the
medium/fine S1 meshes remain pending.

## Geometry and run

- Platform: WSL2 Ubuntu 24.04, OpenFOAM 14 (`Build: 14-7b05503f98a8`), one
  processor.
- Bore 8.5 mm, stroke 7.0 mm, CR 7.75, rod/stroke 1.6, 1200 rpm.
- S1: 3.25 mm bowl radius, 1.00 mm squish width, 0.50 mm TDC squish gap,
  0.918 mm bowl recess; analytic squish area fraction 41.52%.
- The analytic flat-piston clearance volume is 58.846685 mm3 and the S1 crown
  gives 58.834569 mm3, an error of -0.02059% (equivalent CR 7.75139 before
  mesh regularisation).
- The generated crown is a conformal stepped bowl: the bowl floor, vertical
  bowl wall, and outer squish land are all on the moving `piston` patch. The
  v14 `crankConnectingRodMotion` mover therefore translates the whole crown
  with the same 11.2 mm connecting rod used by CFD-01.

## Numerical gates

| item | S1 coarse result | gate | status |
|---|---:|---:|---|
| mesh cells | 2,763 (22 radial x 3 sector x 43 axial, split into 3 blocks) | recorded | pass |
| solver wall runtime | 200.33 s Python wall time; OpenFOAM 189.85 s execution / 190 s clock | recorded | pass |
| processor count | 1 | recorded | pass |
| accepted moving-mesh steps | 2,808 | recorded | pass |
| maximum Courant number | 0.2171 | <= 0.5 | pass |
| maximum slider-crank volume error | 0.16634% | <= 0.2% | pass |
| maximum relative mass drift | 5.9847e-7 (5.9847e-05%) | <= 1e-4 | pass |
| tracer range | [0, 1] | inside [0, 1] | pass |
| output cadence | 937 samples; maximum gap 0.45 CAD | <= 0.5 CAD | pass |
| `checkMesh` | BDC, TDC, and +180 CAD all `Mesh OK` | required times | pass |

The baseline `correctPhi=no` setting was retained. S1 has no continuity or
mass evidence that would justify reopening that CFD-01 decision.

## Transport result

`DeltaC = mean(C_wall) - mean(C_core)` and the local
`tau_mix = 1/[-d ln(abs(DeltaC))/dt]` are postprocessed from the full history.
The table compares the nearest S1 sample with the promoted CFD-01 fine-mesh
flat-piston value. The S1 derivative is a coarse screening diagnostic, not a
mesh-converged design value.

| requested CAD | S1 sampled CAD | S1 DeltaC | S1 tau (ms) | CFD-01 flat tau (ms) |
|---:|---:|---:|---:|---:|
| -90 | -89.814 | 0.53421 | 26.20 | 28.34 |
| -45 | -44.814 | 0.40113 | 18.75 | 16.29 |
| -20 | -20.064 | 0.33965 | 26.79 | 10.88 |
| 0 (TDC) | -0.125 | 0.31343 | 34.15 | 10.65 |
| +20 | +20.071 | 0.27774 | 17.95 | 14.10 |
| +45 | +45.008 | 0.23646 | 37.26 | 39.07* |
| +90 | +90.008 | 0.22607 | undefined | undefined |

`*` CFD-01 +45 is explicitly a lower-bound/unresolved derivative value. S1's
coarse TDC derivative is not faster than the flat-piston baseline; it is about
34 ms versus 10.65 ms. That is not yet a geometry verdict because the stepped
crown is only at the coarse level and the local derivative is noise-sensitive,
but it gives no reason to promote S1 as the squish winner. The direct S1
concentration contrast remains positive throughout the cycle; the +90 local
negative derivative is the same late-expansion plateau artifact seen in
CFD-01, not physical un-mixing.

## Reproducibility and outputs

The case is generated and run by
`cfd/openfoam14/squish/run_squish_cfd.py`. Use the commands in
`cfd/openfoam14/squish/README.md`; `--validate-only` reprocesses the existing
WSL case without invoking OpenFOAM. Promoted artifacts are:

- `cfd/results/cfd02_s1_coarse_scalar_history.csv`
- `cfd/results/cfd02_s1_coarse_mixing_time.csv`
- `cfd/results/cfd02_s1_coarse_metadata.json`

The next bounded experiment is S2 coarse. Do not feed this S1 coarse schedule
into Cantera until a geometry is selected and its transport answer is checked
at medium/fine resolution.
