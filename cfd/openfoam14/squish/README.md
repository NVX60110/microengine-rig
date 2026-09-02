# CFD-02 S1 mild squish

S1 is the first constant-compression-ratio squish geometry. It uses a stepped
3.25 mm bowl radius, 1.00 mm squish width, 0.50 mm TDC land gap, and 0.918 mm
bowl recess. The analytic TDC volume is matched to the flat-piston CR 7.75
volume before the mesh chord/axis regularisation error.

Run only the coarse case first:

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig
python3 cfd/openfoam14/squish/run_squish_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish \
  --overwrite
```

The script runs BDC/TDC/+180 `checkMesh`, the native v14 moving-piston solver,
and the existing mass/volume/tracer postprocessor. It writes the transient
case under `/home/gflip/OpenFOAM/cfd02-squish/s1_coarse` and promotes only the
S1 coarse history to `cfd/results/cfd02_s1_coarse_scalar_history.csv`. Gate
metrics and the requested -20/0/+20/+45 CAD points are also written to
`cfd/results/cfd02_s1_coarse_metadata.json` and
`cfd/results/cfd02_s1_coarse_mixing_time.csv`. The mixing table includes the
same -90, -45, -20, 0, +20, +45, and +90 CAD checkpoints used by CFD-01.

To re-check an existing S1 run without invoking OpenFOAM:

```bash
python3 cfd/openfoam14/squish/run_squish_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish \
  --validate-only
```

To regenerate the geometry-independent comparison from stored CFD-01 v8 fine
and S1 fields (post-processing only):

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

The comparison reports raw mass-weighted RMS amplitude ratios as the primary
cross-geometry result and retains per-case-initial-normalized RMS as a
secondary diagnostic. It also reports the +/-5 CAD log-linear fit and R2.
