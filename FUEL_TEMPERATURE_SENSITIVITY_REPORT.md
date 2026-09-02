# Fuel / temperature sensitivity campaign

Status: **bounded chemistry screen; hypothesis evidence only**

The supplied `1-fuel-design.py` and `2-fuel-design2.py` files were treated as
untrusted, hypothesis-generating inputs. Their SHA-256 hashes are recorded in
`results/fuel_temperature_sensitivity.json`; the prototype largest-temperature-
step detector was not used.

## Reproduction

```text
python scripts/fuel_temperature_sensitivity.py --include-burke --output-dir results
python -m unittest tests.test_fuel_temperature_sensitivity -v
```

The script resolves mechanisms relative to the repository root. It records
Cantera version, mechanism hashes, composition, pressure, temperature grid,
criterion, tolerances, failures, and every point in the JSON/CSV outputs.

## Definition and numerical controls

All points use 40 bar, adiabatic constant-volume chemistry and the same
repository detector: accepted-step maximum dP/dt, qualified only after a
400 K temperature rise and integrated through a 1000 K rise. Cantera 3.2.0 is
run with `rtol=1e-9`, `atol=1e-15` (the strict controls justified by PR #24).
The common grid is 875, 885, ..., 975 K (11 points).

For delays that ignite at both endpoints, the signed endpoint secant is

```text
S = ln(tau_975 / tau_875) / ln(975 / 875)
```

Ordinary ignition therefore has **S < 0**. Adjacent 10 K local slopes and a
non-monotonicity flag are reported; a positive endpoint S or positive local
segment is not a self-stabilization result and is not promoted as feedback.

## Scope

- Zhao sk39, Zhao full, LLNL DME 2004 are the primary lineages.
- Burke Mech_56.54 is included only as a compatible package screen; its direct
  point-level Burke validation gate remains blocked, as recorded in the existing
  validation report.
- The complete DME/CO 25/75 dilution table (air, N2+4, CO2+4, H2O+2) is run on
  every primary lineage (and Burke when enabled).
- The supplied partner screen (CH4, H2, CO, C2H6, C2H4 at DME fractions
  0.15/0.25/0.40/0.60) is bounded to Zhao sk39. Common CH4, CO, and pure-DME
  controls and the full DME/CO dilution table provide cross-lineage checks.
- Frozen synthetic EGR uses 0/20/40% of the Beta-2.3-like exhaust vector. It
  is a one-pass composition screen, not a repeated-cycle residual fixed point.

## Interpretation

Read the machine-readable `metadata.summaries` table for exact values. The
decision rule is qualitative: a candidate is only a shape hypothesis if all
11 points ignite without numerical failure, the endpoint and local slopes are
inspected together, and the sign survives the independent mechanism check.
No row establishes engine stability, negative feedback, a target RPM window,
or a design default. The existing `experiments/EGR_HYPOTHESIS.md` promotion
requirements (periodic repeated-cycle state, mechanism evidence, and bounded
perturbations) remain in force.

## Decision-relevant results

The recorded run used all 11 temperatures for every row (`summary_count=86`,
`row_count=946`; 21 cases per primary mechanism plus the bounded Zhao partner
fraction screen, and 17 Burke diagnostic cases). Values below are `tau_925` in
milliseconds, endpoint S over 875–975 K, and the minimum/maximum adjacent
10-K local S.

| mechanism | fuel case | tau925 ms | endpoint S | local S range |
|---|---|---:|---:|---:|
| Zhao sk39 | pure DME | 0.776 | +2.367 | +1.974…+2.514 |
| Zhao full | pure DME | 0.733 | +2.388 | +2.152…+2.606 |
| LLNL79 | pure DME | 0.797 | −1.841 | −6.074…+1.127 |
| Burke diagnostic | pure DME | 0.611 | +1.882 | +0.284…+3.593 |
| Zhao sk39 | DME/CH4 25/75 | 3.938 | −2.822 | −3.163…−2.478 |
| Zhao full | DME/CH4 25/75 | 3.867 | −2.763 | −3.061…−2.449 |
| LLNL79 | DME/CH4 25/75 | 3.333 | −5.920 | −8.579…−3.417 |
| Burke diagnostic | DME/CH4 25/75 | 3.525 | −3.616 | −7.349…−0.488 |
| Zhao sk39 | DME/CO 25/75 | 1.323 | +0.006 | −0.196…+0.293 |
| Zhao full | DME/CO 25/75 | 1.282 | +0.055 | −0.179…+0.383 |
| LLNL79 | DME/CO 25/75 | 1.339 | −3.698 | −7.220…−0.750 |
| Burke diagnostic | DME/CO 25/75 | 1.240 | −0.775 | −3.298…+1.064 |
| Zhao sk39 | DME/CO + N2+4 | 5.499 | −4.403 | −5.567…−3.498 |
| Zhao full | DME/CO + N2+4 | 5.435 | −4.375 | −5.569…−3.452 |
| LLNL79 | DME/CO + N2+4 | 4.975 | −8.107 | −9.563…−6.183 |
| Burke diagnostic | DME/CO + N2+4 | 4.284 | −1.702 | −8.858…+28.003 |
| Zhao sk39 | DME/CO + CO2+4 | 4.234 | −4.299 | −5.760…−3.213 |
| Zhao full | DME/CO + CO2+4 | 4.159 | −4.214 | −5.713…−3.131 |
| LLNL79 | DME/CO + CO2+4 | 4.019 | −8.560 | −9.942…−6.614 |
| Burke diagnostic | DME/CO + CO2+4 | 5.067 | −6.231 | −8.738…−4.186 |
| Zhao sk39 | DME/CO + H2O+2 | 2.839 | −3.071 | −3.593…−2.533 |
| Zhao full | DME/CO + H2O+2 | 2.804 | −3.009 | −3.585…−2.456 |
| LLNL79 | DME/CO + H2O+2 | 2.642 | −6.094 | −8.334…−3.596 |
| Burke diagnostic | DME/CO + H2O+2 | 1.997 | +0.701 | −6.835…+29.574 |

No DME/CO+diluent case simultaneously lies in the 2–5 ms band and retains a
nonnegative or near-flat S across Zhao **and** LLNL; Burke's unvalidated
diagnostic rows do not change that conclusion. The nominally near-flat Zhao
DME/CO row is below target delay and has local sign changes. CO2/N2 dilution
can move delay into the target band, but its S is decisively negative on all
three primary mechanisms. H2O+2 reaches the target on Zhao/LLNL but is also
decisively negative. Therefore no fuel, dilution, or frozen-EGR architecture
is promoted from this campaign.
