# Microengine Rig — Beta 2.5

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
- `two_zone_temperature_stability.py` — three-mechanism CR transition campaign.
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

## Beta 2.5 result

The handoff's alleged nearly flat ignition-delay sensitivity was a numerical
artifact: it used temperature increment per adaptive solver step instead of a
time derivative. Correct max-dP/dt slopes are not flat.

The cool two-zone branch nevertheless survives above 1000 K, then transitions
abruptly over roughly 0.25 CR in the sampled maps. At 3.0 bar all three DME
lineages are bounded at CR 7.75 and hot at CR 8.0 under the default 20% boundary
mass / 10 ms mixing closure. See [`BETA25_REPORT.md`](BETA25_REPORT.md) and the
versioned files under `results/`.

## Limits

This is a screening model, not CFD or a calibrated engine. The two-zone mixing
time, inter-zone heat transfer, and boundary mass are prescribed. There is no
validated quench closure, valve train, 720-degree friction model, oil film,
piston rock dynamics, or brake-power prediction. Direct DME experimental
validation and hot leak-down hardware remain open.
