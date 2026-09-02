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
checks the lumped valve step. With the gas-to-wall sign handled correctly and
the outlet enthalpy taken from the pre-step gas state, the reacting kernel's
internal-energy residual is about `0.0013 J` in that cycle and the exhaust
transition residual is approximately `3e-10 J`. The latter is effectively
closed at this resolution; it is not evidence of a separate exhaust mapping
defect. The remaining energy residual is step-dependent and is retained as a
diagnostic until the complete periodic state is closed.

## Result

The run covered 12 consecutive cycles at 1,200 rpm and 5 CAD step. The mass
balance residual was approximately -0.00074 to -0.00089 mg per cycle. Relative
to the reacting kernel's 1.63 mg initial mass this is about 4.5–5.5e-4, and
relative to the cycle-start mass it is about 3.5–4.4e-3, so it does **not** meet
the strict 1e-6 periodic mass gate. It is consistent with a rate-integration /
quadrature residual, not the 3–50% homologous-state drift.

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
evidence that the 1,200-rpm concept is stable. The energy accounting is
internally consistent in the bounded diagnostic after the outlet-state and
wall-heat corrections, but the state remains non-periodic and the residual is
not yet a passing promotion gate.

## Quadrature refinement

Fresh one-cycle runs were repeated at 5, 2, 1 and 0.5 CAD. The mass residual
decreases strongly with step size. The total energy residual tracks the
closed-kernel residual and also decreases; the independently computed intake
and exhaust transition residuals are near numerical zero after the outlet-state
correction:

| step | mass residual (mg) | mass residual / cycle start | mass residual / kernel start | total energy residual (J) | closed-kernel energy residual (J) |
|---:|---:|---:|---:|---:|---:|
| 5.0 CAD | -8.94e-4 | -4.41e-3 | -5.48e-4 | 1.32e-3 | 1.32e-3 |
| 2.0 CAD | -9.01e-5 | -4.44e-4 | -5.73e-5 | 6.19e-4 | 6.19e-4 |
| 1.0 CAD | -2.80e-5 | -1.38e-4 | -1.78e-5 | 2.89e-4 | 2.89e-4 |
| 0.5 CAD | -1.63e-6 | -8.04e-6 | -1.04e-6 | 2.77e-4 | 2.77e-4 |

Thus the mass trend is consistent with trapezoidal rate-integration error, not
an unexplained 3.19% state drift. However, even at 0.5 CAD the residual is
`8.04e-6` relative to the cycle-start mass, above the existing `1e-6` gate; it
must not be reported as closed without finer resolution or a justified
numerical tolerance. The energy residual is now the same order as the
closed-kernel residual, and the isolated intake/exhaust transitions are below
`1e-9 J` in these checks. The periodic state itself remains an explicit
blocker before friction, crank dynamics or motor control are enabled.

## Diagnostic limitations

The valve implementation is a one-way compressible-orifice screen: the
current case does not model reverse valve flow, valve dynamics, or a resolved
manifold. Intake/exhaust accounting therefore cannot establish physical valve
timing or volumetric efficiency. Flow-rate clipping at a fraction of the lumped
mass and the two-zone-to-lump end-state reconstruction are additional numerical
approximations. These limitations are why the diagnostic distinguishes
accounting residuals from a converged engine-cycle claim.

## Reproduction

```powershell
python scripts/run_cycle720_1200_accounting.py
```

The generated result is `results/cycle720_1200_accounting.json`. It is a
project-model artifact and must not be added to measured leakage or chemistry
datasets.
