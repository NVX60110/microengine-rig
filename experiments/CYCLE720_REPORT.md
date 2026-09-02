# Minimum viable 720-CAD cycle scaffold

Status: infrastructure only; no new engine operating point is promoted.

`cycle720.py` wraps the accepted `two_zone_model.py` one-revolution reacting
solve in an explicit four-stroke schedule. The cycle is labelled -360..+360
CAD: intake TDC=-360, intake BDC=-180, firing TDC=0, expansion BDC=+180,
and exhaust ends at +360. The canonical -180..+180 BDC-to-BDC trace therefore
maps directly, without a hidden 360-degree rotation. The schedule is:

| crank angle (CAD) | phase |
|---:|---|
| -360–-180 | intake |
| -180–0 | compression |
| 0–180 | combustion/expansion |
| 180–360 | exhaust |

The intake and exhaust paths are an inspectable ideal-gas lump with configurable
effective valve area, discharge coefficient, timing, pressure reservoirs and
first-order `p dV + h dm` energy accounting. They are a project-model screen,
not valve CFD or a calibrated discharge model. Residual gas is not prescribed:
the end state from one complete cycle is the input state to the next cycle.

The default disabled-feature path calls `simulate_two_zone` directly with its
strict tolerances. This is the regression contract: it preserves the existing
closed compression/combustion/expansion result while exposing the 720-CAD phase
and state interfaces around it. `iterate_periodic_720` requires closure in mass,
species, specific enthalpy, temperature and speed; a cycle count cutoff is
reported as non-converged rather than promoted as stable idle.

Crank bookkeeping reports gas torque, pumping work, friction work and motor
torque peak/RMS. The current speed update is an explicit postprocessed torque
integration at fixed crank-angle time steps; it does not yet feed variable speed
back into chemistry or valve timing. Friction values and controller constants
are assumed/project-model inputs, not literature calibration.

## Reproduction

From the repository root:

```bash
python -m unittest tests.test_cycle720 -v
python scripts/run_cycle720.py --rpm 1200 --step-deg 2 --cycles 3
python scripts/run_cycle720.py --rpm 1200 --step-deg 2 --cycles 3 --enable-valves
```

The second command remains a bounded smoke screen. It is not evidence that a
stable 1200-rpm engine cycle exists. The first command verifies the direct
closed-pass delegation and unit-level lumped-state contracts.

## Deliberate limitations and next gate

The scaffold does not include valve lift profiles, flow reversal within a
valve event, cylinder-wall heat transfer during gas exchange, a ring-pack
model, lubrication, inertia-coupled variable-speed chemistry, or a sourced
friction bracket. The next bounded experiment should first compare the
disabled wrapper against the accepted closed-pass rows, then enable gas
exchange, then residual convergence, pumping, friction, inertia and motor
control one layer at a time at 1000/1200/1500/2000 rpm. No coefficient should
be tuned to preserve 1200 rpm.
