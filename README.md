# microengine-rig

8.5 mm bore miniature compression-ignition engine study. Shared working repo for Gabriel, Claude, and Codex.

## What this is

A screening rig for a ~0.4 cc/cylinder engine intended for a 1:18-scale model car. The engine is **motored** by an electric motor and contributes a minority of shaft power; the objective is authentic combustion, sound, and exhaust chemistry rather than net propulsion.

**Read [FINDINGS.md](FINDINGS.md) first.** It is the ledger of what is established, what is retracted, and under what conditions each number holds.

## Repo layout

```
FINDINGS.md              ledger of claims, conditions, and status  <- start here
model/                   the reacting single-cylinder model
tools/                   mechanism acceptance gate
physics/                 standalone first-principles screens
mechanisms/              provenance + regeneration instructions (files not committed)
```

## The one rule

**Every number carries the conditions it was computed at.**

Most errors in this project have been constants that outlived their assumptions — a leak area computed at 20 bar and used at 50, a volume flow computed at 550 K and used at 1000 K. Prefer functions over tables:

```python
# BAD  - silently forgets its conditions
LEAK_AREA_3UM = 0.00055

# GOOD - cannot be used without them
def equiv_area(clearance_um, P_up, T): ...
```

When adding to FINDINGS.md, the conditions field is required.

## Setup

```bash
python -m venv .venv && .venv/bin/pip install cantera pyyaml numpy
```

Mechanisms and experimental datasets are external — see `mechanisms/PROVENANCE.md`.

## Status

No hardware exists. No direct experimental validation of the DME chemistry has been performed. All output is screening-level with roughly ±50% chemistry uncertainty (see FINDINGS.md §2).
