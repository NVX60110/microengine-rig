# CFD-02 constant-CR squish campaign

CFD-02 compares stepped-bowl squish geometries while holding bore, stroke,
compression ratio, rpm, initial state and solver controls fixed.  Cross-geometry
mixing is judged primarily with each case's mass-weighted tracer RMS normalized
by that case's own initial RMS.  Raw RMS is retained as a secondary amplitude
because the same radial tracer seed occupies a different initial mass/volume
fraction when the chamber shape changes.

## S1 mild squish — complete

S1 uses:

- bowl radius: 3.25 mm
- squish width: 1.00 mm
- TDC squish gap: 0.50 mm
- bowl recess: 0.918 mm

The completed coarse run is under
`/home/gflip/OpenFOAM/cfd02-squish/s1_coarse` when regenerated locally.  Its
promoted history is `cfd/results/cfd02_s1_coarse_scalar_history.csv`.

Revalidate the stored S1 case without rerunning OpenFOAM:

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig
python3 cfd/openfoam14/squish/run_squish_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish \
  --validate-only
```

## S2 medium squish — bounded coarse screen

S2 is the only new CFD solve authorized after the S1 metric audit.  It uses:

- bowl radius: 3.00 mm
- squish width: 1.25 mm
- TDC squish gap: 0.35 mm
- exact constant-CR bowl recess: 1.378845 mm
- coarse radial split: 15 bowl + 7 land cells
- 7 lower-bowl axial cells and 38 upper axial cells

Run:

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig
git pull

python3 cfd/openfoam14/squish/run_s2_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish \
  --overwrite
```

The runner writes the transient case under
`/home/gflip/OpenFOAM/cfd02-squish/s2_coarse` and promotes:

- `cfd/results/cfd02_s2_coarse_scalar_history.csv`
- `cfd/results/cfd02_s2_coarse_mixing_time.csv`
- `cfd/results/cfd02_s2_coarse_metadata.json`

S2 has the same numerical gates as S1 plus an explicit closed-cylinder tracer
inventory gate (`<=1e-4` relative): volume closure <=0.2%, mass drift <=1e-4
relative, tracer in [0,1], max Courant <=0.5, output spacing <=0.5 CAD, and
`checkMesh` at BDC/TDC/+180 CAD.

## Cross-geometry comparison

Regenerate the current flat/S1 comparison if required:

```bash
python3 cfd/openfoam14/cold_flow_tracer/scripts/postprocess_history.py \
  /home/gflip/OpenFOAM/cfd01-cold-flow-tracer-v8/fine \
  --output cfd/results/cfd01_scalar_history_fine.csv
python3 cfd/openfoam14/cold_flow_tracer/scripts/postprocess_history.py \
  /home/gflip/OpenFOAM/cfd02-squish/s1_coarse \
  --output cfd/results/cfd02_s1_coarse_scalar_history.csv
python3 cfd/compare_tracer_mixing.py \
  cfd/results/cfd01_scalar_history_fine.csv \
  cfd/results/cfd02_s1_coarse_scalar_history.csv \
  --targets -90 -45 -20 0 20 45 90 --window-cad 5 \
  --output cfd/results/cfd01_vs_cfd02_s1_tracer_mixing.json
```

After S2 completes, compare it both to flat and to S1:

```bash
python3 cfd/compare_tracer_mixing.py \
  cfd/results/cfd01_scalar_history_fine.csv \
  cfd/results/cfd02_s2_coarse_scalar_history.csv \
  --targets -90 -45 -20 0 20 45 90 --window-cad 5 \
  --output cfd/results/cfd01_vs_cfd02_s2_tracer_mixing.json

python3 cfd/compare_tracer_mixing.py \
  cfd/results/cfd02_s1_coarse_scalar_history.csv \
  cfd/results/cfd02_s2_coarse_scalar_history.csv \
  --targets -90 -45 -20 0 20 45 90 --window-cad 5 \
  --output cfd/results/cfd02_s1_vs_s2_tracer_mixing.json
```

Interpret the initial-normalized RMS ratio as the primary cumulative mixing
metric.  A ratio below 1 means the candidate has a smaller fraction of its own
initial segregation remaining at that crank angle.  Also retain the +/-5 CAD
log-linear decay fit and R2: S1 already showed that cumulative mixing can improve
while the local TDC decay rate becomes slower.

Do not refine S1 or S2 and do not couple either schedule into Cantera until the
S2 coarse history has been reviewed against both references.
