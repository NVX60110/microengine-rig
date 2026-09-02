# Cantera adiabatic two-zone collapse preflight

Status: bounded diagnostic; no chemistry or model retuning.

## Scope

This preflight reproduces
`RigTests.test_two_zone_collapses_to_single_zone_when_adiabatic` with the
locally installed Cantera 3.2.0 and compares the canonical single-zone solver
with the pressure-coupled two-zone solver. The exact regression state is:

| quantity | value |
|---|---:|
| fuel | methane / GRI-Mech 3.0 |
| intake pressure, temperature | 1.2 bar, 300 K |
| equivalence ratio | 0.4 |
| bore, stroke, compression ratio | 8.5 mm, 7.0 mm, 7.0:1 |
| speed | 1200 rpm |
| wall / blow-by | adiabatic / off |
| two-zone default exchange time | 10 ms reciprocal exchange |

Only existing integration controls were varied: crank-angle output step
(`RigConfig.step_deg`) and the two-zone CVODE relative/absolute tolerances.
The existing two-zone rule `max_time_step = output_dt / 4` was retained in
every run. The single-zone solver uses the Cantera 3.2.0 `ReactorNet` defaults,
which were observed at runtime as `rtol=1e-9`, `atol=1e-15`; these are included
as an explicit two-zone comparison case.

Run command:

```text
python scripts/cantera_discrepancy_preflight.py
```

Machine-readable output: `results/cantera_discrepancy_preflight.json`.

## Reproduction of the reported failure

At the regression test's `step_deg=2.0`, with the current two-zone production
defaults (`rtol=1e-7`, `atol=1e-14`):

| observable | single zone | two zone | difference |
|---|---:|---:|---:|
| peak pressure (bar) | 17.628777981 | 17.521004654 | -0.107773327 (-0.61135%) |
| peak temperature (K) | 627.572429 | 626.581939 | -0.990489 |
| maximum fuel conversion | 3.0903e-13 | 2.8852e-13 | -2.0504e-14 |
| maximum inter-zone pressure difference (bar) | — | 9.78e-14 | — |

The conversion is effectively zero for this lean, 300 K methane case, so the
pressure/temperature discrepancy is not a chemistry-conversion transition.

## Step and tolerance sensitivity

With the two-zone tolerance set to the Cantera 3.2.0 single-zone defaults
(`rtol=1e-9`, `atol=1e-15`), the peak-pressure difference changes as follows:

| crank step (CAD) | single peak (bar) | two-zone peak (bar) | difference (bar) | relative |
|---:|---:|---:|---:|---:|
| 4.0 | 17.378418297 | 17.308734025 | -0.069684272 | -0.40098% |
| 2.0 | 17.628777981 | 17.509315643 | -0.119462338 | -0.67766% |
| 1.0 | 17.523222991 | 17.539316706 | +0.016093715 | +0.09184% |
| 0.5 | 17.550462097 | 17.555746566 | +0.005284468 | +0.03011% |
| 0.25 | 17.550945828 | 17.548141115 | -0.002804713 | -0.01598% |
| 0.125 | 17.550570452 | 17.550454771 | -0.000115682 | -0.00066% |

At the accepted fine step of 0.125 CAD, the corresponding temperature
difference is -0.000562 K and the conversion difference is +6.02e-16. The
0.25-to-0.125 CAD single-zone peak-pressure change is only 0.000375 bar,
showing that the fine-step reference is itself converged at the displayed
precision.

At the original 2 CAD step, changing tolerance alone does not produce a
monotonic answer: the two-zone pressure difference spans +0.4046 bar
(loose, 1e-5/1e-12) to -0.0360 bar (1e-9/1e-16). At 0.125 CAD, all tested
tolerance cases are within 0.0053% of the single-zone peak except the current
production pair, which is still only 0.154% different; the explicit Cantera
default pair is -0.00066%.

## Attribution

The evidence supports a numerical integration/control issue, specifically the
coarse crank-angle step and the two-zone solver's looser default tolerances
relative to the canonical single-zone ReactorNet. It does **not** support a
Cantera-version attribution: this preflight has one installed version only,
Cantera 3.2.0, and no cross-version result was generated. It also does not
support an actual model/chemistry discrepancy: when the existing step control
is refined to 0.125 CAD and the two-zone tolerances match the single-zone
Cantera defaults, the two calculations agree to 0.00066% in peak pressure,
0.0006 K in peak temperature, and approximately 6e-16 in conversion while
inter-zone pressure mismatch remains at numerical roundoff.

The current 2 CAD assertion is therefore testing an under-resolved numerical
case. Its 0.05 bar threshold is not a safe physical equivalence criterion at
that step: the reproduced -0.1078 bar difference fails even though the fine
case collapses.

## Recommendation

Do not retune chemistry. Before the RPM map, make the collapse check an
explicit fine-step preflight: use `step_deg <= 0.125` (the project's existing
transition-resolution rule), and set the two-zone default CVODE tolerances to
the explicit Cantera baseline `rtol=1e-9`, `atol=1e-15`, or pass those values
in the regression fixture. Retain the current coarse 2 CAD check only as a
diagnostic and do not interpret its pressure difference as a physical regime
change.

If changing production defaults is undesirable for runtime, the minimum code
correction is to expose/record the single-zone baseline tolerances and require
the fine-step collapse preflight before any RPM-dependent chemistry result is
promoted. No tolerance/code change was made by this diagnostic branch.

