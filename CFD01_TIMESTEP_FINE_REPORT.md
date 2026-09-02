# CFD-01 fine-mesh timestep validation and the axis-core velocity artifact

Purpose: test whether the fine CFD-01 case can run faster inside the existing
gates. The converged fine run (`CFD02_REGEN_TIGHT_REPORT.md`) takes 5,595
steps because 99% of its steps are Courant-bound at `maxCo 0.15` (median step
0.055 CAD against a 0.15 CAD cap), while `GATES.md` allows Courant up to 0.5
and the Issue #5 sweep showed a 0.25 CAD cap passes the answer gate. The test
was one gated run at `maxCo 0.45, maxDeltaT 0.25` plus a safer `maxCo 0.30`
twin, both judged against the converged fine history with the Issue #5 answer
gate (5% on `DeltaC` and finite `tau_mix` at -20/0/+20/+45 CAD) and the
Issue #10 inventory gate.

The run also exposed why the case is Courant-bound at all, which turned out
to be the more important result and is recorded in section 2.

## 1. Candidate runs

Runner: `run_timestep_sweep.py` extended with `--mesh`, `--max-co` and
`--reference-history` (the converged fine history as baseline), plus the
tracer-inventory gate. Both candidates ran concurrently on one processor each.

| setting | steps | runtime (s) | max Co | inventory drift | tracer bounds | run gate | answer gate |
|---|---:|---:|---:|---:|---|---|---|
| reference: `maxCo 0.15, maxDeltaT 0.15` (converged fine) | 5,595 | 1,882 (batch of four) | 0.373 | `1.3e-11` | `[0, 1]` | ok | baseline |
| `maxCo 0.30, maxDeltaT 0.25` | 5,228 | 1,950 (pair) | 1.580 | `1.4e-11` | `[0, 1]` | **failed**: max Co > 0.5 | not evaluated by the runner; +45 CAD `tau_mix` would fail (+9.8%) |
| `maxCo 0.45, maxDeltaT 0.25` | 5,063 | 1,891 (pair) | 2.888 | `1.9e-11` | `[0, 1]` | **failed**: max Co > 0.5 | not evaluated by the runner; all four angles within 0.8% |

### 1.1 Results

Neither candidate is adopted.

- **No speed-up.** The step counts fall by only 7% and 10% (5,228 and
  5,063 against 5,595) and the wall time does not move, because the step is
  set by the axis-core artifact of section 2 and not by the Courant target.
- **Run gate failed on the start-up spike.** Both runs open at the 0.25 CAD
  cap for six steps before the Courant controller reacts, and the artifact
  reaches Co 1.58 and 2.89 in those steps. The reference's reported maximum
  of 0.373 is the same start-up spike at the 0.15 cap; it is not a
  mid-cycle value. A small initial `deltaT` in `controlDict` would remove the
  spike in every case and belongs with the axis fix.
- **Answer sensitivity, for the record.** At `maxCo 0.45` the fixed-radius
  `DeltaC` and `tau_mix` stay within 0.8% of the reference at -20/0/+20/+45
  CAD, and the normalized RMS and 20%-mass-zone contrast within 0.6%. At
  `maxCo 0.30` the +45 CAD `tau_mix` moves from 39.10 to 42.94 ms (+9.8%),
  the known mesh- and step-sensitive late-cycle point (F7); the near-TDC
  values stay within 1.3%.
- Inventory, tracer bounds, volume closure (0.1407%) and output cadence
  (0.5 CAD) all pass in both runs; the failure is the Courant gate alone.

Per-run summaries: `cfd/results/cfd01_timestep_fine_co030.csv`,
`cfd/results/cfd01_timestep_fine_co045.csv`; solver-field audit
`cfd/results/cfd01_timestep_fine_inventory_audit.json`.

## 2. What sets the time step: a spurious axis-core velocity

At the same crank angle the reference and both candidates take the same
0.05 CAD step, yet their maximum Courant numbers are 0.15, 0.29 and 0.45
respectively while the mean Courant number is 0.002. The maximum is not the
physical flow. From the written fields, the maximum-velocity cell in every
case is the innermost axis-core ring (`r = 0.077 mm` on the fine mesh), and
the velocity there scales with whatever Courant allowance the run is given.

Innermost-ring maximum velocity, m/s, from the converged runs
(`axis` = innermost radial ring, piston speed for scale):

| case | innermost ring r (mm) | -178 CAD | -160 | -120 | -90 | -60 | -30 | 0 | +30 | +90 | +179 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| flat fine | 0.077 | 5.35 | 3.85 | 3.61 | 2.64 | 1.47 | 0.60 | 0.08 | 0.64 | 2.75 | 4.21 |
| flat medium | 0.107 | 4.59 | 3.05 | 2.50 | 1.93 | 1.30 | 0.35 | 0.10 | 0.28 | 1.97 | 3.13 |
| flat coarse | 0.166 | 0.03 | 2.25 | 1.55 | 1.01 | 0.53 | 0.28 | 0.17 | 0.31 | 0.44 | 1.56 |
| S1 coarse | 0.164 | 0.06 | 2.75 | 1.54 | 1.12 | 0.52 | 0.32 | 0.11 | 0.27 | 0.45 | 1.43 |
| S2 coarse | 0.170 | 0.02 | 2.06 | 1.40 | 0.87 | 0.48 | 0.28 | 0.21 | 0.34 | 0.44 | 2.36 |
| piston speed | | 0.01 | 0.11 | 0.32 | 0.44 | 0.44 | 0.28 | 0.00 | 0.28 | 0.44 | 0.01 |

Radial profile on the fine mesh at -140 CAD (piston 0.21 m/s): 5.46 m/s at
`r = 0.077 mm`, dominantly axial; 2.98 m/s at `r = 0.126 mm`, dominantly
radial inward; 1.46, 1.23, 1.17, 0.89 m/s in the next four rings; physical
values beyond about `r = 0.5 mm`. The pattern is an axial jet along the
axis core with a radial return in the neighbouring ring, present whenever the
piston is away from TDC, and it grows with mesh refinement (coarse 1.5-2.3,
medium 3-4.6, fine 5.5 m/s). This is the classic axis-singularity artifact
of a sector mesh whose axis is replaced by a small `symmetry` core patch: the
innermost cells are about 2 micrometres wide azimuthally on the fine mesh,
and the pressure-velocity coupling there supports a spurious mode.

Consequences:

- **Time step.** The artifact, not the flow, has set `deltaT` on every
  CFD-01/CFD-02 run so far. Raising `maxCo` lets the artifact grow rather
  than the step: at `maxCo 0.45` the axis velocity reaches 17.6 m/s. The
  physical Courant number (mean 0.002) would allow steps near the
  `maxDeltaT` cap throughout compression, i.e. roughly three to five times
  fewer steps.
- **Promoted answers are not contaminated.** The mass-weighted tracer at
  radii below 1 mm is exactly zero at every output on both the fine and
  coarse meshes; the shell tracer's diffusion front never passes inside
  2 mm. F1-F3 and the F24/F25 comparisons therefore stand. The artifact
  carries negligible mass and sits where the tracer is identically zero,
  which is also why `tau_mix` is mesh-converged while the artifact triples
  from coarse to fine.
- **Caveat for future metrics.** Any diagnostic that samples the axis region
  or uses whole-field velocity statistics must exclude the innermost rings
  until the artifact is removed. F1's "no hidden convective mixing" holds
  for the shell/core tracer, not for the axis-core velocity field.

Recommended fix, to be run as its own bounded numerics item, not adopted
here: replace the 50 micrometre `symmetry` core with either a true
single-cell `wedge` axisymmetric mesh (OpenFOAM's standard treatment of the
axis, no core patch) or a larger core radius kept inside the 0.2% volume
gate, then rerun flat coarse/fine and check that (a) the innermost-ring
velocity falls to the piston-speed scale, (b) the step becomes
`maxDeltaT`-bound, and (c) `tau_mix` at the requested angles stays within
the 5% answer gate. That change is expected to deliver most of the speed-up
that the Courant setting cannot.

## Reproduction

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig
python3 cfd/openfoam14/cold_flow_tracer/scripts/run_timestep_sweep.py \
  --mesh fine --caps 0.25 --max-co 0.45 \
  --reference-history cfd/results/cfd01_scalar_history_fine_tight.csv \
  --sweep-root /home/gflip/OpenFOAM/cfd01-timestep-fine \
  --output cfd/results/cfd01_timestep_fine_co045.csv --overwrite
```

Artifacts: `cfd/results/cfd01_timestep_fine_co045.csv`,
`cfd/results/cfd01_timestep_fine_co030.csv`,
`cfd/results/cfd01_timestep_fine_inventory_audit.json`.
