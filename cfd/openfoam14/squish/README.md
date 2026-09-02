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
