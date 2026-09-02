# Residual carry-over fixed-point screen

Status: **SCREENING adapter only; not a periodic engine model**.

## Method

The existing pressure-coupled two-zone solver integrates only `-180` to `+180`
crank angle (one revolution). `residual_fixed_point.py` wraps that solver with a
declared map:

1. Construct a fresh charge with the configured fuel, oxidizer, and fresh-charge
   equivalence ratio `phi_fresh`.
2. Take the complete mass-aggregated composition and enthalpy state at the end
   of the preceding modeled revolution.
3. Mix fresh and residual streams with `f_res` equal to the stated fraction of
   total intake charge. The current experiment uses a **mass basis**.
4. Pressure-normalize both streams to the configured intake pressure, conserve
   their mass-weighted enthalpy adiabatically, and solve for the mixed intake
   temperature at that fixed pressure.
5. Repeat until the mixed intake composition and temperature change are below
   `max |delta Y_i| <= 1e-8` and `|delta T| <= 1e-3 K`, or the iteration bound is
   reached.

The exported end pressure is the piston-area-weighted two-zone pressure;
composition and enthalpy are mass-aggregated. The pressure mismatch between
zones remains separately gated rather than being hidden by that aggregation.

The fresh charge remains at `phi_fresh`; the complete mixed charge does not.
Outputs therefore include tracked-fuel mass fraction, O2 mass fraction, and a
`tracked_fuel_to_O2_ratio_relative_to_fresh` diagnostic. The latter is only a
ratio proxy, not an elemental equivalence ratio, because residual products and
partly oxidized fragments do not share the fresh-fuel stoichiometry.

Fuel conversion is normalized to the total tracked-fuel mass in each mixed
initial charge (the existing two-zone inventory convention), not to fresh-cycle
fuel alone.

The first map input is fresh charge itself (a cold-start initialization), not a
frozen guessed exhaust vector. Every subsequent input is generated from the
preceding cycle's full exported end state.

## Numerical controls

The bounded physical screen uses Cantera 3.2 settings from the PR #24 gate:
`step_deg=0.125`, `rtol=1e-9`, and `atol=1e-15`. The two-zone pressure,
volume, and mass gates remain applicable. Results retain the existing warning
that gross work excludes gas exchange and friction.

## Scope limits

This map does not model intake or exhaust valves, valve timing, pumping work,
gas exchange, exhaust blowdown, friction, crank inertia, motor torque, or a
720-CAD four-stroke cycle. It must not be called internal EGR hardware
evidence. The fixed point means only that this explicitly stated composition
operator converges (or fails to converge).

## Results

The compact JSON companion is `results/residual_fixed_point_anchor.json`. The
reproducible command is:

```text
python residual_fixed_point.py --fractions 0.05,0.30 --max-iterations 8
```

It uses the current OP_IDLE nominal screen: CR 7.75, 1200 rpm, 25 mol% DME /
75 mol% methane, `phi_fresh=0.40`, 3.0 bar intake, 300 K intake, 560 K fixed
wall, 20% boundary mass, diffusion/strain mixing, 3 micrometre annular
clearance with eccentricity 0.5, and the Zhao sk39 mechanism. It screens
`f_res=0.05` and `0.30` for a bounded endpoint bracket; it is intentionally
not a multi-mechanism or dense fraction sweep.

Interpretation must use the `converged` field. A row that reaches the maximum
iteration count with decreasing deltas is an unresolved map convergence, not a
periodic-state proof. The branch and chemistry outputs remain one-revolution
two-zone screening values.

The endpoint screen was bounded to 8 iterations, with decreasing deltas and no
observed branch drift:

| `f_res` | branch at final iterate | final `max |delta Y|` | final `|delta T|` | final Tmax | final gross IMEP | gates |
|---:|---|---:|---:|---:|---:|---|
| 0.05 | cool partial candidate | 1.49e-7 | 4.81e-4 K | 1122.9 K | 3.761 bar | pass |
| 0.30 | cool partial candidate | 2.58e-6 | 7.40e-3 K | 1138.4 K | 1.950 bar | pass |

The per-row gate fields in the JSON are the mass-balance residual, maximum
component mass-balance residual, maximum inter-zone pressure mismatch, maximum
volume closure error, retained end mass, and `numerical_gate_status`; the
stated checks are pressure <= 0.10 bar, volume <= 0.20 mm3, and mass/component
residuals <= 1e-3 mg.
At the final iterates, the two rows reported pressure mismatch 0.0413/0.0301
 bar, volume closure 0.0644/0.0623 mm3, mass residual
`2.08e-7/-4.39e-7` mg, maximum component residual
`1.17e-7/6.20e-8` mg, and retained mass 0.8815/0.8972 (5%/30%). Both gate
statuses are `pass`.

The JSON records Cantera 3.2.0, the repo-relative mechanism path, and its
SHA-256 so the mechanism input is auditable.

Two separate-process executions of the exact CLI command produced byte-identical
JSON outputs (audit files removed after comparison). This confirms deterministic
species ordering and matching statuses/key outputs for the committed run.

Thus the cool branch is bounded over these eight map applications. Neither
endpoint met both fixed-point tolerances by iteration 8 in the committed
artifact, although both showed decreasing deltas (the 5% case was within
`1.5e-7` in composition and `4.8e-4 K` in temperature). The correct conclusion
is **unresolved but trending toward convergence at both endpoints**; there is
no evidence here for drift to extinction or runaway. The mixed intake
tracked-fuel/O2 proxy falls from 1.0 on the cold-start map input to 0.975 at
`f_res=0.05` and 0.842 at `f_res=0.30`; this also demonstrates why
`phi_fresh=0.40` must not be read as the whole mixed-charge equivalence ratio.
