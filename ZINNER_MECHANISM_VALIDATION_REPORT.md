# Zinner mechanism-validation lane

## Scope

This lane compares the four locally archived mechanisms against the exact 167
rows from Christopher Zinner's 2008 Appendix **TABULATED DATA**. The rows are
measured shock-tube ignition delays; the adjusted and original thermodynamic
states are both retained in the source CSV. The default artifact uses the
thesis-adjusted state and can be regenerated with:

```text
python scripts/validate_zinner_mechanisms.py --basis adjusted
```

No mechanism parameters are fitted or changed. The output is a project-model
screen, not a replacement for the shock-tube facility model.

## Criterion and state treatment

Each row uses the listed CH4/DME fuel blend, equivalence ratio, and an air
oxidizer basis (`O2:N2 = 1:3.76`). Cantera 3.2.0 integrates an adiabatic,
constant-volume reactor with `rtol=1e-9`, `atol=1e-15`. The reported simulated
delay is maximum accepted-step `dP/dt` after a +400 K qualification rise,
continued through +1000 K. Zinner's measured event is endwall pressure rise,
so this is explicitly a **criterion proxy**; it does not model reflected-wave,
boundary-layer, or facility pressure history effects.

## Evidence classification

* Zinner delay and source conditions: **MEASURED EVIDENCE — Zinner shock-tube table**.
* Simulated delays and ratios: **PROJECT MODEL RESULT**.
* Any interpretation across mechanisms: **INFERENCE**, not calibration.

## Results

The machine-readable summary and all point-level statuses are in:

* `results/zinner_mechanism_validation_adjusted.json`
* `results/zinner_mechanism_validation_adjusted.csv`

The summary reports usable counts, no-ignition/numerical-failure rows, median
simulation/measurement ratio, and factor-2/factor-3 fractions by mechanism,
blend, equivalence ratio, pressure band (`<10`, `10–20`, `>=20 atm`), and the
thesis low/high-temperature split at 1175 K. A ratio is not treated as valid
when the solver does not qualify an ignition; those rows remain explicit
failures.

## Limits and next step

The comparison is useful for mechanism ranking and for identifying blend,
pressure, and equivalence-ratio regions that require a non-ideal shock-tube
history. It cannot validate the engine's heat transfer, leakage, mixing,
residuals, or a 720-CAD cycle. The next chemistry improvement, if the ratios
show strong state/criterion sensitivity, is to add the Zinner pressure-history
correction or recovered Burke supplement—not to retune the mechanisms.
