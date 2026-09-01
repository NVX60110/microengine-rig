# CFD-01 cold-flow tracer report

CFD-01 is complete and validated as a nonreacting, closed-cylinder baseline.
It measures volume-weighted exchange between a core and an outer 20%-volume
radial shell; it does not add reacting chemistry or change the canonical
Cantera model.

## Solver and case

- Platform: WSL2, Ubuntu 24.04.3 LTS; OpenFOAM v14 (`Build :
  14-7b05503f98a8`); ParaView 5.11.2.
- Geometry: 8.5 mm bore, 7.0 mm stroke, compression ratio 7.75, rod/stroke
  ratio 1.6 (11.2 mm rod), 1200 rpm.
- User time: -180 to +180 crank angle degrees ATDC, with the native v14
  `engine` user-time and `crankConnectingRodMotion` mover adapted from
  `tutorials/XiFluid/kivaTest`.
- Initial state: air, 3.0 bar, 300 K. Laminar momentum, no-slip walls,
  adiabatic walls, closed cylinder, and zero scalar flux at all solid/symmetry
  boundaries.
- The outer shell is selected from cell centres using
  `r > (B/2) sqrt(0.8)`, approximately 0.45 mm thick. A 50 micrometre
  axis-core regularisation and 5-degree symmetry sector keep the mesh valid;
  the sector is scaled back to a full-cylinder volume for reporting.
- The piston patch begins at the lower face at -180 CAD and translates in +z,
  matching the v14 mover sign convention. The Python slider-crank volume
  comparison remains within 0.141% at every recorded output (requirement:
  0.2%).

## Mesh and numerical validation

All runs used one processor. `checkMesh` passed at BDC (-180 CAD), TDC (0
CAD), and after motion (+180 CAD) for every mesh. Standard `checkMesh` is the
gate; the deliberately thin symmetry-sector cells are not evaluated with the
full-3D `-allGeometry` determinant heuristic.

| mesh | radial x azimuthal x axial | cells | nominal spacing (mm) | runtime (s) | logged max Co | max volume error (%) | status |
|---|---:|---:|---:|---:|---:|---:|---|
| coarse | 22 x 3 x 41 | 2,706 | 0.20 | 161.83 | 0.2073 | 0.1407 | ok |
| medium | 43 x 3 x 41 | 5,289 | 0.10 | 472.37 | 0.3229 | 0.1407 | ok |
| fine | 85 x 3 x 41 | 10,455 | 0.05 near wall | 1,536.10 | 0.3732 | 0.1407 | ok |

The control dictionary starts at `deltaT 0.5` CAD with adaptive stepping capped
at `maxDeltaT 0.15` CAD and `maxCo 0.15`. The largest logged Courant number is
0.3732, below the required 0.5 limit. Scalar, cell-volume, and cell-centre
fields are written every three accepted steps. The fine history contains 1,866
rows from -180 to +179.989 CAD; its largest crank-angle gap is 0.45 degree,
meeting the 0.5-degree sampling requirement.

## Fine-mesh mixing result

For each output, `DeltaC = mean(C_wall) - mean(C_core)` and the local rate is
`k_mix = -d ln(abs(DeltaC))/dt`, using a centred finite difference in physical
time. `tau_mix = 1/k_mix` is reported only when the local rate is positive.

| requested CAD | sampled CAD | DeltaC | k_mix (s^-1) | tau_mix (ms) |
|---:|---:|---:|---:|---:|
| -90 | -90.050 | 0.55113 | 35.287 | 28.339 |
| -45 | -44.891 | 0.41592 | 61.393 | 16.289 |
| -20 | -20.102 | 0.31918 | 91.938 | 10.877 |
| 0 (TDC) | 0.042 | 0.24415 | 93.854 | 10.655 |
| +20 | +20.012 | 0.19354 | 70.925 | 14.099 |
| +45 | +44.874 | 0.16363 | 25.596 | 39.068 |
| +90 | +90.030 | 0.15831 | -1.325 | undefined |

The compression-side and early-expansion values fall in or close to Beta 2.6's
central 11.9-33.8 ms bracket (with the TDC point at 10.7 ms just below it).
They do not reproduce the provisional fast 2.4-3.2 ms bracket or the 100 ms
slow bracket as a sustained interval. The +90-degree negative derivative is a
local DeltaC sign reversal, so a positive exchange time is not defined there;
it is retained in the CSV rather than silently converted into a result.

## Reusable closure and artifacts

`cfd_mixing_closure.py` fits the positive finite portions of the fine history to
`k_mix = pi^2 D/L^2 + C_s |u_p|/B` and writes a `TwoZoneOptions`-shaped JSON
payload. The bounded fit enforces the model's nonnegative strain coefficient;
for this baseline the fitted strain term is zero and the fitted diffusivity is
`3.588e-6 m^2/s`. This is a CFD-01 closure parameterization, not a universal
sealing requirement.

The representative ParaView image is rendered at -90 CAD with the piston patch
overlaid on the scalar slice: `cfd/results/cfd01_piston_tracer.png`.

Required result files are in `cfd/results/`; the runnable template and exact
WSL commands are in `cfd/openfoam14/README.md`. After the CFD run, Cantera
3.2.0 was installed in WSL and the quick existing test suite was rerun with
`python -m unittest discover -s tests -v`: 19 tests passed and one pre-existing
two-zone adiabatic-collapse tolerance check differed by 0.117 in its reported
metric. No CFD or uncertainty campaign was rerun, and no canonical model files
were changed.
