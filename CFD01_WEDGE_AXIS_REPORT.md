# CFD-01 wedge-axis treatment (Issue #17)

Scope: the bounded experiment defined in Issue #17. Replace the CFD-01
sector's 50 micrometre `symmetry` axis core with OpenFOAM's standard
single-cell `wedge` axis, add a small initial `deltaT`, keep `maxCo 0.15` and
`maxDeltaT 0.15`, screen on flat coarse, then run medium and fine because
coarse removed the artifact without moving the answer. Chemistry, piston
geometry, tracer seed and transport coefficients are unchanged. S1/S2 keep
their own sector meshes and are not touched here.

Result: the artifact is removed outright on every mesh, the fine case runs
8.2 times faster, and on the fine reference mesh every transport observable
is within 1.6% of the converged sector baseline. Adoption is proposed for
review; the runner default remains `sector` until then.

## 1. Attribution: initial step versus axis treatment

Both coarse cases use `deltaT 0.01` CAD initially; only the axis differs.

| coarse case | innermost ring r (mm) | axis max velocity at -140 CAD (m/s) | Co max / p90 | steps | runtime (s) | answer gate |
|---|---:|---:|---:|---:|---:|---|
| sector, `deltaT0 0.5` (converged reference) | 0.166 | 1.55 | 0.207 / 0.151 | 2,580 | 230 (batch) | baseline |
| sector, `deltaT0 0.01` | 0.166 | 1.66 | 0.190 / 0.151 | 2,579 | 163 | 0.35% |
| wedge, `deltaT0 0.01` | 0.129 | **0.213** (piston 0.215) | 0.096 / 0.087 | 2,409 | 55 | 1.34% |

The small initial step removes only the first-step Courant spike; the axis
jet is unchanged in the sector case (1.66 m/s, 48% of steps Courant-bound).
The wedge removes it: the innermost-ring velocity equals the piston speed,
the step sits at the 0.15 CAD cap on 99% of steps, and no step is
Courant-bound.

## 2. Wedge results on all three meshes

Runner: `run_cfd01.py --axis wedge --initial-delta-t 0.01`, base controls.
Runtimes are single concurrent jobs (coarse alone; medium and fine as a
pair) and are compared with the converged sector runs from
`CFD02_REGEN_TIGHT_REPORT.md`.

| mesh | cells (sector -> wedge) | steps (sector -> wedge) | runtime s (sector -> wedge) | speed-up | Co max / mean | volume closure | gas mass drift (solver fields) | tracer inventory drift | tracer bounds | checkMesh BDC/TDC/+180 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| coarse | 2,706 -> 902 | 2,580 -> 2,409 | 230 -> 55 | 4.2x | 0.096 / 0.004 | 0.1269% | `1.7e-10` | `8.3e-12` | `[0, 1]` | OK |
| medium | 5,289 -> 1,763 | 2,580 -> 2,409 | 709 -> 112 | 6.3x | 0.146 / 0.005 | 0.1269% | `1.9e-10` | `5.7e-12` | `[0, 1]` | OK |
| fine | 10,455 -> 3,485 | 5,595 -> 2,465 | 1,882 -> 229 | **8.2x** | 0.150 / 0.007 | 0.1269% | `4.8e-7` | `4.0e-12` | `[0, 1]` | OK |

Volume closure is the planar-chord error alone (no core omission). The fine
wedge's gas-mass drift of `4.8e-7` is larger than the sector's `1e-10` but
200 times inside the `1e-4` gate; it appears with the 0.15 CAD steps that
the sector never reached on the fine mesh. Fine output volume fell from
11 GB to 1.8 GB.

### 2.1 Axis velocity, the required output

Innermost-ring maximum velocity (m/s) against crank angle, all three wedge
meshes (they agree to three decimals), with piston speed:

| CAD | -178 | -160 | -140 | -120 | -90 | -60 | -30 | 0 | +30 | +90 | +140 | +179 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| wedge axis | 0.012 | 0.110 | 0.214 | 0.314 | 0.428 | 0.441 | 0.285 | 0.007 | 0.268 | 0.439 | 0.226 | 0.019 |
| piston | 0.010 | 0.107 | 0.215 | 0.321 | 0.440 | 0.441 | 0.279 | 0.000 | 0.278 | 0.440 | 0.215 | 0.005 |
| sector fine axis (F26) | 5.35 | 3.85 | 5.46 | 3.61 | 2.64 | 1.47 | 0.60 | 0.08 | 0.64 | 2.75 | | 4.21 |

Radial profile at -140 CAD on the fine wedge: `|U| = 0.214` m/s, purely
axial, identical across the first five rings (`r = 0.033` to `0.226` mm);
the global maximum is `0.243` m/s at `r = 3.87` mm near the piston-liner
corner, i.e. the physical corner flow. The maximum-Courant cell is no longer
at the axis. No new localized artifact appears at the collapsed axis edge,
the wedge patches, or the triangular head/piston faces.

Volume-weighted RMS radial velocity by radial band, fine sector versus fine
wedge (m/s): inside `r = 1` mm the sector carries `0.04-0.08` of spurious
radial motion against `0.0007-0.002` in the wedge; in the `2-3.8` mm band
where the tracer front lives the two agree within 3% at every angle
(e.g. -60 CAD: 0.0162/0.0557 sector, 0.0162/0.0555 wedge). The artifact
never stirred the front, which is why the promoted transport answers
survived it.

### 2.2 Transport observables against the converged sector references

Relative change wedge versus sector at the same mesh (reference values from
`cfd01_scalar_history_*_tight.csv`):

| mesh | CAD | `DeltaC` | `tau_mix` | normalized RMS | 20%-mass-zone contrast |
|---|---:|---:|---:|---:|---:|
| fine | -20 | +0.54% | -0.32% | +0.46% | -0.7% |
| fine | 0 | +0.94% | -0.40% | +0.60% | -0.5% |
| fine | +20 | +0.69% | -0.84% | +0.61% | -0.9% |
| fine | +45 | +0.41% | +1.57% | +0.53% | -1.3% |
| medium | 0 | +1.23% | -0.19% | +0.61% | +6.1% |
| coarse | 0 | +1.34% | +0.04% | +0.52% | +5.4% |

Answer gate (5% on `DeltaC` and finite `tau_mix` at -20/0/+20/+45 CAD):
coarse 1.34%, medium 1.53%, fine 1.57%, all pass. Fine-mesh TDC `tau_mix`:
10.665 -> 10.622 ms.

The 20%-mass-zone contrast differs by 5-7% on coarse and medium but by less
than 1.3% on fine, with the raw wedge/sector ratio at TDC going
1.066 -> 1.058 -> 1.003 from coarse to fine. Neither formulation's zone
contrast is monotone in mesh (sector TDC 0.251 / 0.268 / 0.248, wedge
0.265 / 0.284 / 0.247), so the gap is coarse-mesh discretization
sensitivity of that metric, not a physical difference, and it converges
away on the reference mesh. Consequence for existing findings: the S1 and
S2 comparisons in F25 are coarse screens against a fine flat reference and
therefore carry a zone-contrast uncertainty of this order (about 7%) on the
squish side. That does not reverse S1/flat 1.354 or S2/flat 1.261 at TDC.

## 3. Reading against the Issue #17 promotion gate

| gate | fine wedge | status |
|---|---|---|
| volume closure <= 0.2% | 0.1269% | pass |
| gas mass and tracer inventory gates | `4.8e-7`, `4.0e-12` | pass |
| tracer bounded | `[0, 1]` | pass |
| requested transport observables within 5% of converged flat baseline | max 1.57% (`tau_mix` +45 CAD); zone contrast within 1.3% | pass |
| axis peak velocity toward physical scale, no new artifact | 0.214 m/s at 0.215 m/s piston; global max at the wall corner | pass |
| fine runtime materially improves before any higher `maxCo` | 1,882 -> 229 s | pass |

Recommendation for review: adopt `wedge` as the CFD-01 axis treatment and
the `_wedge` histories as the flat references, then convert the S1/S2 mesh
generators to the same axis treatment before any further squish comparison
so the three geometries share numerics. Keep `maxCo 0.15` and `maxDeltaT
0.15`; with the artifact gone the fine step is cap-bound on 85% of steps,
and any Courant change is a separate gated question. The runner default
stays `sector` in this branch so nothing changes silently.

## Reproduction

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig
for lvl in coarse medium fine; do
  python3 cfd/openfoam14/cold_flow_tracer/scripts/run_cfd01.py --mesh $lvl \
    --axis wedge --initial-delta-t 0.01 --overwrite \
    --run-root /home/gflip/OpenFOAM/cfd01-axis/wedge_dt0p01
  python3 cfd/openfoam14/cold_flow_tracer/scripts/postprocess_history.py \
    /home/gflip/OpenFOAM/cfd01-axis/wedge_dt0p01/$lvl \
    --output cfd/results/cfd01_scalar_history_${lvl}_wedge.csv
done
python3 cfd/audit_scalar_inventory.py /home/gflip/OpenFOAM/cfd01-axis/wedge_dt0p01/{coarse,medium,fine} \
  --labels flat_coarse_wedge flat_medium_wedge flat_fine_wedge \
  --output cfd/results/cfd01_wedge_inventory_audit.json
# attribution control
python3 cfd/openfoam14/cold_flow_tracer/scripts/run_cfd01.py --mesh coarse \
  --axis sector --initial-delta-t 0.01 --overwrite \
  --run-root /home/gflip/OpenFOAM/cfd01-axis/sector_dt0p01
```

## Artifacts

- `cfd/results/cfd01_scalar_history_{coarse,medium,fine}_wedge.csv`,
  `cfd/results/cfd01_{coarse,medium,fine}_wedge_run_metadata.json`
- `cfd/results/cfd01_wedge_inventory_audit.json`
- `run_cfd01.py --axis {sector,wedge} --initial-delta-t`,
  `run_timestep_sweep.py --axis --initial-delta-t`, `tests/test_cfd01_wedge.py`
- Run roots: `/home/gflip/OpenFOAM/cfd01-axis/wedge_dt0p01/{coarse,medium,fine}`,
  `/home/gflip/OpenFOAM/cfd01-axis/sector_dt0p01/coarse`
