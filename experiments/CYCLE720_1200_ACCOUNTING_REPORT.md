# CFD-free 1,200-rpm 720-CAD accounting diagnostic

## Purpose

This bounded experiment diagnoses the existing valve-enabled 720-CAD gate at
one operating point. It does not enable friction, crank dynamics, motor
control, CFD, or chemistry retuning. The calculation uses the project wrapper
with the canonical 8.5 mm × 7.0 mm geometry, 7.75:1 compression ratio, fixed
560 K wall, Zhao SK39 DME/CH4 profile, 3 µm annular screen and 0.5 eccentricity.
Valve area/timing and the annular leak law remain project-model assumptions.

## Accounting definition

For each cycle the complete mass balance is evaluated as

```text
m_start + m_intake,in + m_blowby,in
  - m_exhaust,out - m_blowby,out - m_end
```

The reacting two-zone segment reports its own blow-by terms. This is important:
the earlier 3.19% state drift was not interpretable from intake/exhaust alone,
because the annular model removes mass during compression/expansion.

Valve enthalpy in/out, blow-by enthalpy, total start/end enthalpy, piston work,
wall heat and an internal-energy residual are also recorded. Species vectors
for valve transfers use the Cantera mechanism species order. These are
bookkeeping diagnostics, not measurements or a calibrated open-system energy
model.

The intake-only energy accounting closes to about `1e-9 J` in cycle 1, which
checks the lumped valve step. The reacting kernel's internal-energy residual is
about `0.100 J` in that cycle and the exhaust transition residual is about
`-0.068 J`; these do not pass an energy gate. They are retained as a specific
state/energy-mapping defect to resolve before friction or crank dynamics are
enabled, rather than being hidden inside a periodicity failure.

## Result

The run covered 12 consecutive cycles at 1,200 rpm and 5 CAD step. The mass
balance residual was approximately -0.00074 to -0.00089 mg per cycle. Relative
to the reacting kernel's 1.63 mg initial mass this is about 4.5–5.5e-4, so it
does **not** meet the strict 1e-6 periodic mass gate. It is a small, repeatable
rate-integration/quadrature residual, not the 3–50% homologous-state drift.

Representative cycle 1 accounting was:

| quantity | value |
|---|---:|
| cycle-start mass | 0.20285 mg |
| cycle-end mass | 0.07540 mg |
| intake mass in | 1.42861 mg |
| exhaust mass out | 1.36089 mg |
| reacting-kernel blow-by out | 0.19607 mg |
| complete mass residual | -8.95e-4 mg |
| start/end temperature | 300.00 / 256.70 K |

The mass identity closes to the displayed accounting residual:

```text
0.20285 + 1.42861 - 1.36089 - 0.19607 - 0.07540
  = -0.00089 mg
```

Across cycles 2–12, the end-state temperature wandered from 184.8 K to
279.1 K and the homologous mass change remained 0.013–0.506 relative. The
state therefore did not approach a demonstrably periodic engine cycle in this
bounded run. The first classification is:

```text
conservation accounted for to a small quadrature residual;
periodic state unresolved;
no stable-idle promotion.
```

The observed state drift is consistent with a transient/open-system filling
and thermal-state problem under the assumed valve and leakage model. It is not
evidence that the 1,200-rpm concept is stable. The enthalpy/internal-energy
residual is not yet a passing closure gate; it identifies the next bookkeeping
task as a more faithful open-system energy/state mapping, especially around the
aggregated two-zone end state and valve transitions.

## Reproduction

```powershell
python scripts/run_cycle720_1200_accounting.py
```

The generated result is `results/cycle720_1200_accounting.json`. It is a
project-model artifact and must not be added to measured leakage or chemistry
datasets.
