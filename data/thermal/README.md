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
* `thermal_state_history.csv`: final-cycle node temperatures, signed hot
  clearance for the sampled cold fits, and positive-clearance annulus
  sensitivity rows for the primary Al-4032/4140 pair.
* `thermal_state_uncertainty.csv`: the bounded 54-case engineering sensitivity
  grid. Its fractions are not production probabilities.
* `thermal_state_summary.json`: compact campaign metadata, node capacities,
  conductive links, material-pair summaries and percentile envelope.
* `figures/`: three decision plots written only with `--plots`.

Classification is explicit in the JSON: measured, literature-derived,
calculated, assumed and extrapolated inputs are not silently mixed. Zero or
negative hot clearance is retained as contact/interference and has no annulus
flow value.

