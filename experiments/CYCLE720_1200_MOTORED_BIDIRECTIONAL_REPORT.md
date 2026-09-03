# 1,200-rpm motored signed-valve diagnostic

## Purpose and scope

This bounded diagnostic isolates the gas-exchange/state-map question before
reacting chemistry, friction, crank inertia, or motor control are enabled. It
uses the canonical 8.5 mm × 7.0 mm slider-crank geometry, 7.75:1 compression
ratio, 3 bar / 300 K intake reservoir, 1 bar / 350 K exhaust reservoir, 1,200
rpm, and the existing fixed 560 K wall / 300 W m^-2 K^-1 heat-transfer screen.
The crank speed is prescribed. It is **not** a reacting engine cycle and does
not establish a stable idle.

The new path evaluates signed compressible-orifice flow from cylinder to port.
When pressure reverses, the incoming mass carries the reservoir composition
and enthalpy; cylinder-to-port flow carries the pre-step cylinder state. Both
directions use the same choked/unchoked relation. The exhaust reservoir is
explicitly initialized with the fresh-charge composition because a bare
Cantera mechanism object has an arbitrary mechanism-default composition. This
fix prevents reverse exhaust flow from injecting an unintended reactive
mixture into a nonreacting diagnostic.

## Accounting and map

Each step records valve name, signed mass flow (positive cylinder-to-port),
direction, choking, pressure, mass, temperature, piston work, and wall heat.
The complete-cycle balances are:

```text
m_end = m_start + m_valve,in - m_valve,out
U_end = U_start + H_valve,in - H_valve,out - W_piston + Q_wall
```

Species balances use the same transfer vectors. A Poincare-map norm is reported
only as a scaled diagnostic:

```text
sqrt(mass_rel^2 + (delta_T/300 K)^2 + pressure_rel^2 + species_max^2)
```

The component residuals, not this combined norm, are the closure quantities.
No fixed-point acceleration is applied; direct cycling is the reference.

## Results

The recorded artifact uses a 2 CAD output step and three direct cycles. It
remains explicitly unresolved as a periodic state:

| cycle | map norm | mass change | temperature change | enthalpy change | end pressure |
|---:|---:|---:|---:|---:|---:|
| 1 | — | — | — | — | 1.02649 bar |
| 2 | 3.3386e-2 | 1.4429e-2 | 5.256 K | 5.6110e-2 | 1.00136 bar |
| 3 | 1.8943e-2 | 1.0833e-2 | 4.629 K | 5.2345e-2 | 0.99951 bar |

The cycle-3 state is not within the strict periodic gate. The shorter run is
therefore a transient diagnostic, not a stable-state claim. A separate 5 CAD
cross-check over 12 cycles also remained unresolved, with map norms varying
between approximately 0.0107 and 0.0652; the coarse map should not be used to
infer convergence.

An extended direct-cycle check was run after the accounting correction. At the
validated 2 CAD step, 12 cycles remained outside the strict state gate. The
map norm was non-monotonic: it reached 0.00179 at cycle 5, then rose to 0.03097
at cycle 10 and ended at 0.00286 at cycle 12. The component state changes also
oscillated (cycle-to-cycle temperature changes ranged from 0.11 to 7.18 K).
A separate 5 CAD, 20-cycle check showed the same behavior, with map norms from
0.00803 to 0.06517 and a final norm of 0.03978. These bounded runs establish
that direct cycling has not reached a reproducible periodic state; they do not
prove that no fixed point exists.

At the 2 CAD cycle-3 endpoint, the independent accounting checks were:

| quantity | value |
|---|---:|
| mass-balance residual / initial mass | -2.14e-14 |
| energy-balance residual | 4.79e-9 J |
| maximum species-balance residual | 2.33e-21 kg |
| intake mass in / out | 1.4483 / 0.5018 mg |
| exhaust mass in / out | 0.0713 / 1.0183 mg |
| intake reverse-flow samples | 46 / 101 |
| exhaust reverse-flow samples | 3 / 100 |

Thus the revised diagnostic closes its own transfer accounting to roundoff,
while homologous state convergence is a separate failure. Reverse flow is not
negligible: it occurs mainly during intake, with a smaller exhaust reversal.

## Temperature excursion diagnosis

The extrema below are **project-model outputs**, not measured temperatures.
They are taken from the last direct 2 CAD motored cycle and include their
homologous crank angle, pressure, mass, active valve/direction, wall heat rate,
and piston-work rate:

| extremum | CAD | T | pressure | mass | valve / direction | wall heat | piston work rate |
|---|---:|---:|---:|---:|---|---:|---:|
| minimum | +176 | 410.34 K | 1.156 bar | 0.4424 mg | exhaust / cylinder-to-port | 14.62 W | 0.182 W |
| maximum | -6 | 860.40 K | 40.85 bar | 0.9863 mg | closed / closed | — | — |

For comparison, the 5 CAD twelve-cycle run gave a final-cycle minimum of
408.97 K at +175 CAD and maximum of 847.87 K at -5 CAD. The 2 CAD and 5 CAD
extrema are therefore similar in magnitude, unlike the earlier pathological
low-temperature failure. The minimum occurs during late expansion/exhaust
near a roughly 1 bar manifold state, where piston expansion work cools the
lump before exhaust replacement and wall heat restore it. The result is
consistent with a reversible motored expansion screen under this closure; it
does not validate a reacting cylinder temperature history.

## Software defect exposed and fixed

The original valve-enabled wrapper's exhaust reservoir set only `T` and `P`.
For a mechanism-backed Cantera phase that leaves the mechanism's arbitrary
default composition in place. With signed reverse flow this can inject an
unintended composition and produce nonphysical composition/energy excursions
or UV-root failures. The motored diagnostic now sets exhaust `T`, `P`, and the
fresh-charge `X` vector explicitly. Adaptive internal substeps re-evaluate
flow direction and choking and avoid arbitrary 10/50% mass clipping; only a
positivity safeguard remains for a mathematically empty explicit step.

## Reproduction

From the repository root:

```bash
python scripts/run_motored_valve_diagnostic.py --step-deg 2 --cycles 3
```

The JSON artifact is `results/cycle720_1200_motored_bidirectional.json`.
For a deliberately coarse stability cross-check:

```bash
python scripts/run_motored_valve_diagnostic.py --step-deg 5 --cycles 12
```

The extended direct-cycle checks used the same runner with `--step-deg 2
--cycles 12` and `--step-deg 5 --cycles 20`; their JSON outputs were kept in
the local temporary directory because they are audit runs rather than
canonical result artifacts.

The current result is suitable for diagnosing valve/state semantics only.
Before a reacting 1,200-rpm periodic idle run, the next required work is to
establish the same accounting and state-map behavior with the valve-enabled
reacting kernel, then add pumping, friction, crank dynamics, and motor control
in separate gated stages.
