# CFD-01/CFD-02 regeneration under the converged tracer solve

Purpose: regenerate the flat-piston CFD-01 meshes and the S1 coarse squish case
with the converged exact-keyword tracer solver entry from
`CFD02_S2_SCALAR_ISOLATION_REPORT.md`, then redo the flat/S1/S2 comparison so
all three geometries share one set of scalar numerics. This is the acceptance
path recorded on Issue #10; it makes no new geometry, no refinement and no
Cantera coupling.

Result: every regenerated case conserves tracer inventory to about `1e-11`
relative and stays inside `[0, 1]`; every mixing answer is within 0.14% of its
legacy value; and the three-geometry comparison reproduces the legacy ratios to
three or four decimals, now with all comparison gates `ok` instead of
`gate_failed`. The earlier verdicts stand on clean numerics.

## 1. Runs

All cases use the unchanged flow controls (`maxCo 0.15`, `maxDeltaT 0.15`,
`correctPhi no`, laminar, upwind tracer) and the base `fvSolution` with the
exact-keyword `tracer` entry (`tolerance 1e-13; relTol 0`). The tracer is
passive, so the flow, Courant and volume histories are identical to the legacy
runs; only the scalar solve changed. Four solves ran concurrently on one
processor each, so runtimes are not a clean comparison with the legacy
single-job timings.

| case | cells | run root | status | runtime (s) |
|---|---:|---|---|---:|
| flat coarse | 2,706 | `cfd01-cold-flow-tracer-v9/coarse` | ok | 230 |
| flat medium | 5,289 | `cfd01-cold-flow-tracer-v9/medium` | ok | 709 |
| flat fine | 10,455 | `cfd01-cold-flow-tracer-v9/fine` | ok | 1,882 |
| S1 coarse | 2,763 | `cfd02-squish-tight/s1_coarse` | ok (max Co 0.2171, checkMesh OK at BDC/TDC/+180) | 274 |
| S2 coarse | 2,823 | `cfd02-squish-tighttol/s2_coarse` (isolation report) | ok (max Co 0.1908) | 240 |

## 2. Scalar inventory from solver-written fields

`cfd/audit_scalar_inventory.py` on the regenerated cases
(`cfd/results/cfd02_scalar_inventory_audit_tight.json`):

| case | max gas-mass drift | max tracer-inventory drift | postprocessor drift (%) | tracer bounds | max wall `phi` (kg/s) |
|---|---:|---:|---:|---|---:|
| flat coarse | `1.3e-10` | `9.2e-12` | `1.26e-8` | `[4.6e-45, 0.99990]` | `2.6e-23` |
| flat medium | `1.0e-10` | `1.3e-11` | `1.03e-8` | `[7.9e-66, 1.0]` | `1.3e-23` |
| flat fine | `5.4e-10` | `1.3e-11` | `5.29e-8` | `[5.2e-92, 1.0]` | `6.6e-24` |
| S1 coarse | `3.7e-10` | `1.5e-11` | `1.63e-8` | `[2.3e-52, 0.99992]` | `2.6e-23` |
| S2 coarse | `1.6e-10` | `9.9e-12` | `1.63e-8` | `[1.1e-54, 0.99999]` | `2.6e-23` |

Legacy values for reference: flat fine `2.4e-5`, S1 `6.8e-5`, S2 `1.66e-4`.
The tracer solve now takes 2-3 PBiCGStab iterations per step to a final
normalized residual near `1e-14`.

## 3. Answer stability

Flat-piston fixed-radius `tau_mix` and the two cross-geometry metrics, legacy
versus converged:

| case | CAD | `tau_mix` legacy -> converged (ms) | change | normalized RMS | 20%-mass zone contrast |
|---|---:|---:|---:|---:|---:|
| flat coarse | 0 | 10.272 -> 10.274 | +0.03% | | |
| flat medium | 0 | 10.352 -> 10.359 | +0.06% | | |
| flat fine | -20 | 10.877 -> 10.882 | +0.05% | 0.565515 -> 0.565496 | 0.323780 -> 0.323819 |
| flat fine | 0 | 10.655 -> 10.665 | +0.09% | 0.530770 -> 0.530728 | 0.248210 -> 0.248288 |
| flat fine | +20 | 14.099 -> 14.118 | +0.14% | 0.493881 -> 0.493841 | 0.197132 -> 0.197248 |
| flat fine | +45 | 39.068 -> 39.097 | +0.07% | 0.454229 -> 0.454215 | 0.166770 -> 0.166896 |

F2/F3 (TDC `tau_mix` 10.27 / 10.36 / 10.67 ms, approximately mesh-converged)
and F7 (+45 CAD not converged) are unchanged in substance.

## 4. Three-geometry comparison under shared numerics

`cfd/compare_tracer_mixing.py` with the regenerated histories; candidate over
reference, +/-5 CAD windows. Legacy value -> converged value.

| pair | CAD | normalized-RMS ratio | 20%-mass-zone contrast ratio | fitted tau ref / cand (ms) |
|---|---:|---:|---:|---:|
| S1 / flat fine | -20 | 0.9021 -> 0.9021 | 1.1401 -> 1.1400 | 50.81 / 35.15 |
| S1 / flat fine | 0 | 0.8922 -> 0.8923 | **1.3545 -> 1.3541** | 39.49 / 43.32 |
| S1 / flat fine | +20 | 0.9050 -> 0.9051 | 1.6299 -> 1.6289 | 39.30 / 54.54 |
| S1 / flat fine | +45 | 0.9346 -> 0.9346 | 1.7418 -> 1.7405 | 42.49 / 85.38 |
| S2 / flat fine | -20 | 0.9443 -> 0.9444 | 1.1791 -> 1.1790 | 50.81 / 23.27 |
| S2 / flat fine | 0 | 0.8910 -> 0.8911 | **1.2613 -> 1.2608** | 39.49 / 27.07 |
| S2 / flat fine | +20 | 0.8829 -> 0.8830 | 1.6525 -> 1.6514 | 39.30 / 46.11 |
| S2 / flat fine | +45 | 0.8941 -> 0.8941 | 1.5141 -> 1.5129 | 42.49 / 54.75 |
| S2 / S1 | -20 | 1.0468 -> 1.0468 | 1.0342 -> 1.0342 | 35.15 / 23.27 |
| S2 / S1 | 0 | 0.9987 -> 0.9987 | 0.9311 -> 0.9311 | 43.32 / 27.07 |
| S2 / S1 | +45 | 0.9567 -> 0.9567 | 0.8693 -> 0.8692 | 85.38 / 54.75 |

Comparison status: all six regenerated JSONs report `status: ok` with no gate
failures (legacy: the two S2 comparisons were `gate_failed`).

## 5. Reading against the B1 decision rule

The B1 rule in `PLAN.md` asks whether squish materially reduces the TDC mixing
time below the flat-piston baseline while passing the numerical gates.

- On the two-zone quantity the chemistry model uses, the fixed 20%-mass outer
  zone, both squish geometries retain **more** core/shell contrast than flat at
  TDC: S1 1.354x, S2 1.261x. Their local zone-fit timescales are shorter
  before TDC and longer after it; the cumulative result at the combustion
  window is unfavourable.
- On the whole-domain normalized RMS, both are modestly ahead of flat at TDC
  (0.892 and 0.891), which is the earlier "changed history, not uniformly
  faster mixing" result (F16).
- S2 does not beat S1 on either metric through -20 to TDC (F18).

Recommendation for review, not a promotion: apply the second branch of the B1
rule. Accept the flat-piston molecular-diffusion scale (`tau(theta)` from the
converged CFD-01 fine history) as the transport baseline, do not run S3, and
do not couple an S1/S2 schedule into the two-zone model. The squish cases are
coarse-mesh screens; a reviewer who wants to keep the squish branch open would
need to justify a medium-mesh S1 against the 1.35x zone result, since mesh
refinement of the flat case moved TDC `tau_mix` by only 4%.

## 6. Caveats

- S1 and S2 remain coarse screens; no squish mesh-convergence study exists.
- The regenerated flat +45 CAD `tau_mix` is still not mesh-converged (F7).
- Runtimes rose 20-50% with four concurrent solves; the isolation report's
  +7% single-job figure is the fair cost of the converged solve.
- The S1 regeneration was launched with the pre-fix `run_squish_cfd.py`, which
  wrote its companion files under the promoted legacy names; those were moved
  to `cfd02_s1_tight_*` and the legacy files restored from git. The runner now
  derives companion names from `--output` and records the solver entry used.

## Reproduction

```bash
source /opt/openfoam14/etc/bashrc
cd /mnt/c/Users/gflip/OneDrive/Documents/"HTML siege"/microengine-rig

for lvl in coarse medium fine; do
  python3 cfd/openfoam14/cold_flow_tracer/scripts/run_cfd01.py --mesh $lvl \
    --overwrite --run-root /home/gflip/OpenFOAM/cfd01-cold-flow-tracer-v9 &
done
python3 cfd/openfoam14/squish/run_squish_cfd.py \
  --run-root /home/gflip/OpenFOAM/cfd02-squish-tight --overwrite \
  --output cfd/results/cfd02_s1_tight_scalar_history.csv &
wait

for lvl in coarse medium fine; do
  python3 cfd/openfoam14/cold_flow_tracer/scripts/postprocess_history.py \
    /home/gflip/OpenFOAM/cfd01-cold-flow-tracer-v9/$lvl \
    --output cfd/results/cfd01_scalar_history_${lvl}_tight.csv
done
python3 cfd/audit_scalar_inventory.py \
  /home/gflip/OpenFOAM/cfd01-cold-flow-tracer-v9/{coarse,medium,fine} \
  /home/gflip/OpenFOAM/cfd02-squish-tight/s1_coarse \
  /home/gflip/OpenFOAM/cfd02-squish-tighttol/s2_coarse \
  --labels flat_coarse_tight flat_medium_tight flat_fine_tight s1_coarse_tight s2_coarse_tight \
  --output cfd/results/cfd02_scalar_inventory_audit_tight.json
T="--targets -90 -45 -20 0 20 45 90 --window-cad 5"
F=cfd/results/cfd01_scalar_history_fine_tight.csv
S1=cfd/results/cfd02_s1_tight_scalar_history.csv
S2=cfd/results/cfd02_s2_tighttol_scalar_history.csv
python3 cfd/compare_tracer_mixing.py $F $S1 $T --output cfd/results/cfd01_vs_cfd02_s1_tight_tracer_mixing.json
python3 cfd/compare_tracer_mixing.py $F $S2 $T --output cfd/results/cfd01_vs_cfd02_s2_tight_tracer_mixing.json
python3 cfd/compare_tracer_mixing.py $S1 $S2 $T --output cfd/results/cfd02_s1_vs_s2_tight_tracer_mixing.json
python3 cfd/compare_tracer_mixing.py $F $S1 $T --metric mass_fraction_zone --output cfd/results/cfd01_vs_cfd02_s1_tight_mass_zone_mixing.json
python3 cfd/compare_tracer_mixing.py $F $S2 $T --metric mass_fraction_zone --output cfd/results/cfd01_vs_cfd02_s2_tight_mass_zone_mixing.json
python3 cfd/compare_tracer_mixing.py $S1 $S2 $T --metric mass_fraction_zone --output cfd/results/cfd02_s1_vs_s2_tight_mass_zone_mixing.json
```

## Artifacts

- Histories: `cfd/results/cfd01_scalar_history_{coarse,medium,fine}_tight.csv`,
  `cfd/results/cfd02_s1_tight_scalar_history.csv`, `_mixing_time.csv`,
  `_metadata.json`; run metadata `cfd/results/cfd01_{coarse,medium,fine}_tight_run_metadata.json`
- Audit: `cfd/results/cfd02_scalar_inventory_audit_tight.json`
- Comparisons: `cfd/results/cfd01_vs_cfd02_s1_tight_*.json`,
  `cfd01_vs_cfd02_s2_tight_*.json`, `cfd02_s1_vs_s2_tight_*.json`
- Legacy promoted files are unchanged and remain the record of the
  pre-fix numerics.
