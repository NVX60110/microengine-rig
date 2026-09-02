# Microengine Rig — Beta 2.6

Headless Cantera screening rig for an 8.5 x 7.0 mm miniature compression-
ignition display engine. The working architecture is motor-driven: combustion
provides authentic pressure, sound, and exhaust chemistry, not assumed net
propulsion.

Read [`FINDINGS.md`](FINDINGS.md) before using a result. The project rule is:

> Every number carries its conditions, status, and producing script.

## Canonical code

- `microengine_rig.py` — single-zone regression solver, JSON sweeps, finite
  wall state, physical annular/orifice leakage, fuel profiles.
- `two_zone_model.py` — experimental pressure-coupled core/boundary extension.
- `mechanism_gate.py` — parent-retention and ChemKED experimental gates.
- `operability_sensitivity.py` — correct max-dP/dt temperature-sensitivity map.
- `scripts/fuel_temperature_sensitivity.py` — reproducible 40-bar fuel,
  dilution, and signed ignition-delay-slope hypothesis screen.
- `residual_fixed_point.py` — prescribed residual-composition fixed-point
  adapter around the one-revolution two-zone model; not a valve/720-CAD model.
- `two_zone_temperature_stability.py` — three-mechanism CR transition campaign.
- `sealing_prior.py` — public-data evidence ledger and explicit sealing brackets.
- `uncertainty_campaign.py` — mechanism x mixing x sealing robustness runner.
- `two_zone_tolerance_check.py` — production/strict CVODE comparison.
- `physics/annulus.py` — standalone pressure-aware leakage diagnostic.

The former `model/microengine_v3.py` is retired. It remains in Git history but
is not a second canonical implementation.

## Install and test

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

Tested with CPython 3.12 and Cantera 3.2 on Linux x86-64.

## Run a headless engine case

```bash
.venv/bin/python microengine_rig.py \
  --set fuel_profile=dme_zhao_sk39 \
  --set fuel_blend_partner=CH4 \
  --set fuel_primary_mole_fraction=0.25 \
  --set equivalence_ratio=0.40 \
  --set intake_pressure_bar=2.3 \
  --set intake_temperature_K=300 \
  --set wall_mode=fixed \
  --set wall_temperature_K=560 \
  --set blowby_mode=annular \
  --set annular_radial_clearance_um=3 \
  --csv run.csv --summary run.json
```

For a batch, pass `--sweep grid.json --jobs 4`. Confirm every transition at
0.125 crank degree or finer.

## Run the mechanism gates

```bash
.venv/bin/python mechanism_gate.py parent \
  --skeleton mechanisms/dme_zhao_sk39.yaml \
  --parent mechanisms/dme_zhao_full.yaml \
  --fuel CH3OCH3:1 --pressure-bar 40 \
  --output-prefix zhao_parent_retention

git clone --depth 1 https://github.com/pr-omethe-us/ChemKED-database.git ckdb
git clone --depth 1 https://github.com/jiweiqi/CollectionOfMechanisms.git mechs

.venv/bin/python mechanism_gate.py chemked \
  --mechanism mechs/n-Heptane_C7H16/Nordin_42s_168r_1998/mech_41s168r.yaml \
  --fuel-species C7H16 \
  --data 'ckdb/n-heptane/Ciezki 1993/*.yaml' \
  --data 'ckdb/n-heptane/Fieweger 1997/*.yaml'
```

A parent match means the reduction retained its source behavior. It does not
mean the parent matches experiment.

## Run the Beta 2.6 uncertainty pilot

```bash
.venv/bin/python uncertainty_campaign.py --scope pilot --jobs 4
.venv/bin/python plot_beta26.py
```

Use `--scope full` only after the pilot is reviewed; it expands the CR, boost,
mixing, sealing and mechanism grid.

## Beta 2.6 result

The mixing closure is not monotonic. In the 72-case 3-bar pilot, fast 2.4-3.2 ms
exchange produced no accepted cases; 100 ms exchange often lost useful work.
With a 3 micrometre/e=.5 annular bracket and central 12-34 ms exchange, CR 7.75
and 8.0 passed the conservative screen across all three mechanisms. This is a
conditional model result, not hardware validation.

Public automotive blow-by data now constrains model structure and broad
degradation trends, but does not set an absolute 8.5 mm leak area. Direct
DME/methane ignition data at 600-1600 K, 7-41 atm and phi .3-2.0 has been
identified for the next chemistry gate. See [`BETA26_REPORT.md`](BETA26_REPORT.md).

## CFD transport status

The OpenFOAM 14 cold-flow case and squish-screen tooling live under
`cfd/openfoam14/`. The current CFD-01 flat-piston histories and CFD-02 S1/S2
diagnostics are committed under `cfd/results/`. Read
[`CFD02_ZONE_REPROCESS_REPORT.md`](CFD02_ZONE_REPROCESS_REPORT.md) before
interpreting a squish comparison: the constant-mass-fraction audit invalidated
the earlier global-only S1 two-zone conclusion, and both tested S2 tracer
schemes currently fail scalar gates. No reacting coupling is included.

## Limits

This is a screening model, not CFD or a calibrated engine. The two-zone mixing
time, inter-zone heat transfer, and boundary mass are prescribed. There is no
validated quench closure, valve train, 720-degree friction model, oil film,
piston rock dynamics, or brake-power prediction. Direct DME experimental
point-data ingestion, CFD calibration of radial exchange, a multi-volume ring
labyrinth, and eventual hot leak-down hardware remain open.

The current sealing thermal-state screen is documented in
[`THERMAL_STATE_REPORT.md`](THERMAL_STATE_REPORT.md); its calculated proxy
temperatures are not hardware measurements.
