# Thermal-state RC outputs

These files are calculated screening artifacts from
`scripts/thermal_state_rc.py`. They are not measured temperatures or a CFD
heat-flux solution.

Run from the repository root:

```bash
python scripts/thermal_state_rc.py --plots
```

To replace the proxy with a measured or CFD history:

```bash
python scripts/thermal_state_rc.py \
  --history path/to/history.csv \
  --output-dir data/thermal
```

The input CSV needs `deg`, `P_bar`, and `T_K`; `pistonVelocity_m_s` is
optional. The history should span approximately one 360-degree revolution.

Files:

* `engine_history_proxy.csv` and `.metadata.json`: the current
  `microengine_rig.py`-generated p/T/speed proxy and its provenance.
* `thermal_state_history.csv`: periodic crank-angle node temperatures, local
  crown/TDC and skirt/liner pair clearances, minimum-path signed hot clearance
  for the sampled cold fits, and positive-clearance annulus sensitivity rows
  for the primary Al-4032/4140 pair.
* `thermal_state_warmup.csv`: the cold-start-to-120-cycle trajectory for the
  two primary heat-transfer closures, including cycle energy terms and the
  minimum paired hot clearance for a 3 µm cold fit.
* `thermal_state_uncertainty.csv`: the bounded 54-case engineering sensitivity
  grid. Its fractions are not production probabilities.
* `thermal_state_summary.json`: compact campaign metadata, node capacities,
  conductive links, ambient sink, periodic residual/energy checks,
  material-pair summaries and percentile envelope.
* `figures/`: three decision plots written only with `--plots`.

Classification is explicit in the JSON: measured, literature-derived,
calculated, assumed and extrapolated inputs are not silently mixed. Zero or
negative hot clearance is retained as contact/interference and has no annulus
flow value. `warmup_converged` and `periodic_converged` are separate: the
linear one-cycle fixed point can be solved even when the finite cold-to-warm
trajectory has not reached the 0.01 K criterion.

## Literature evidence lane

`literature_sources.csv` records source provenance and access status;
`literature_measurements.csv` contains only values recoverable from the cited
primary pages, open PDFs or manufacturer page, with transferability labels. It
now includes near-scale ringless head/block context and ringed heat-path/
leakage coefficients, but intentionally has no absolute paired piston/liner
temperature rows. Run:

```bash
python scripts/analyze_thermal_literature.py
```

The script writes `literature_transferables.csv` and
`literature_transferables.json`, deriving piston-minus-liner or normalized
quantities only when a single local paired record supplies all required
temperatures. Missing AP .09, 710578, Furuhama and SETC point tables, plus
ringless oil-film conductance and numeric ABC taper, remain recovery tasks; no
values are inferred from a graph or copied into the engine model.
