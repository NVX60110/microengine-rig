# CFD-02 S2 medium-squish coarse report

S2 was run as the single bounded coarse screen after the S1 metric audit. It
uses the same cold, closed-cylinder, laminar OpenFOAM 14 setup and 0.15-CAD
timestep cap as CFD-01/S1. No reacting chemistry or canonical Cantera model
was changed.

## Geometry and numerical result

- Bore 8.5 mm, stroke 7.0 mm, CR 7.75, rod/stroke 1.6, 1200 rpm.
- Bowl radius 3.00 mm, squish width 1.25 mm, TDC gap 0.35 mm.
- Exact constant-CR recess: 1.378845 mm; analytic TDC volume error is below
  `3e-14%`.
- 2,823 cells, one processor; Python wall runtime 237.59 s and OpenFOAM
  execution/clock time 224.49/224 s; 3,195 accepted steps.
- `checkMesh` passed at BDC, TDC, and +180 CAD.
- Maximum Courant 0.19083 and maximum slider-crank volume error 0.14992%.
- Gas mass drift passed at `5.983e-7` relative and tracer remained in `[0,1]`.

The run **fails the scalar-inventory gate**: maximum mass-weighted tracer
inventory drift is `0.0167264%`, or `1.67264e-4` relative, above the required
`1e-4` relative (`0.01%`) limit. The failure is explicit in
`cfd/results/cfd02_s2_coarse_metadata.json`; no S2 transport value is promoted
as a validated result. This is a scalar-conservation failure, not a solver
crash or mesh/volume failure.

## Comparison diagnostics (not promoted)

The comparison tool marks both S2 JSONs `status: gate_failed` and retains the
normalized-RMS and +/-5-CAD fit for diagnosis only.

| target | S2/flat initial-normalized RMS | S2/S1 initial-normalized RMS | S2 vs S1 fit tau (ms) |
|---:|---:|---:|---:|
| -20 CAD | 0.9443 | 1.0468 | 23.27 vs 35.15 |
| 0 CAD (TDC) | 0.8910 | 0.9987 | 27.07 vs 43.33 |
| +20 CAD | 0.8829 | 0.9756 | 46.12 vs 54.53 |
| +45 CAD | 0.8941 | 0.9567 | 54.76 vs 85.37 |

Relative to S1, S2 does not meet the predeclared “roughly 5% additional
normalized-RMS reduction through -20 to TDC” threshold: it is worse at -20
CAD (1.0468) and effectively unchanged at TDC (0.9987). Because the scalar
inventory gate failed, even these trends remain diagnostic rather than a
geometry decision.

## Constant-mass-fraction zone audit

The fixed-radius shell was also replaced by a nominal 20% outer zone selected
by cumulative mass at each output. Under that zone-style diagnostic, S2/flat
normalized core/shell contrast is 1.179 at -20 CAD and 1.261 at TDC; S2 retains
more contrast, not less. The +/-5 CAD S2 TDC fit has poor log-linearity
(`R2=0.013`), so it is not a promoted timescale. The zone result reinforces
that the prior fixed-radius/global-only squish conclusion cannot be used as a
validated two-zone design result.

## Tracer-scheme check

A separate S2 coarse rerun with `div(phi,tracer) Gauss linearUpwind grad(tracer)`
was performed under `/home/gflip/OpenFOAM/cfd02-squish-linearupwind`. It also
fails: inventory drift is `0.0201883%` (`2.01883e-4` relative), and tracer
undershoot reaches `-0.0192431`. Mesh, gas mass, volume, and Courant checks
remain clean, so this one-line change is not an acceptable fix. The variant is
retained as an explicit failed diagnostic; no cubic scheme or further squish
run is authorized yet.

## Decision

Do not spend medium/fine CFD on S2, do not run S3, and do not feed S1/S2 into
Cantera. The constant-mass-fraction audit invalidates the earlier S1
two-zone/global-only promotion, and the S2 scalar-inventory loss remains a
correctable numerical-treatment question (e.g. scalar solver or mesh
resolution). No squish transport result is promoted until a geometry-independent
metric passes both conservation and boundedness gates.

## Artifacts

- `cfd/results/cfd02_s2_coarse_scalar_history.csv`
- `cfd/results/cfd02_s2_coarse_mixing_time.csv`
- `cfd/results/cfd02_s2_coarse_metadata.json`
- `cfd/results/cfd01_vs_cfd02_s2_tracer_mixing.json`
- `cfd/results/cfd02_s1_vs_s2_tracer_mixing.json`
- `cfd/results/cfd01_vs_cfd02_s2_mass_zone_mixing.json`
- `cfd/results/cfd02_s1_vs_s2_mass_zone_mixing.json`
- `cfd/results/cfd02_s2_linearupwind_metadata.json`
- `cfd/results/cfd02_s2_linearupwind_scalar_history.csv`
- `cfd/results/cfd02_s2_linearupwind_mixing_time.csv`
