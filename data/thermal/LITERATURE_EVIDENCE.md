# Thermal-literature evidence ledger

This lane separates source recovery from model inputs. A source can be
important without supplying an ingestible piston/liner temperature pair. A
reported temperature difference is retained with its source and transferability
warning; it is not silently converted into an 8.5 mm prior.

## Recovered, quantitative but non-transferable values

- **Frank & Heywood, SAE 910558 (1991)** — the publisher abstract reports a
  controlled 50 K piston-temperature variation in a single-cylinder
  spark-ignited direct-injection engine by changing coolant/oil conditions. The
  result demonstrates thermal-control sensitivity, but gives no local
  piston/liner pair for this miniature geometry. It is recorded as
  `piston_temperature_control_span`, `50 K`, qualitative sensitivity only.
  [SAE record](https://saemobilus.sae.org/papers/effect-piston-temperature-hydrocarbon-emissions-a-spark-ignited-direct-injection-engine-910558)
- **Najafabadi et al., Journal of Mechanical Science and Technology (2014)** —
  the public abstract reports approximately 70 K crown-temperature reduction
  with piston cooling-jet operation and an approximately 50 K internal piston
  gradient. Exact baseline temperatures and the local liner state are not
  exposed in the indexed abstract, so both values are retained as qualitative
  sensitivity observations only.
  [DOI record](https://doi.org/10.1007/s12206-013-1183-7)
- **Kruggel, SAE 710578 (1971)** — a public bibliographic summary reports 36
  piston and 12 cylinder thermocouple locations on an 80 mm-bore air-cooled
  two-stroke test engine, operated up to 2800 rpm. The counts are measurement
  topology, not temperature points, and are retained only to inform future
  instrumentation planning.
  [Public summary](https://eurekamag.com/research/103/544/103544865.php)

## High-value sources with no point table recovered

- **Tian et al., SAE 2010-32-0018** — the AP .09/Hornet-scale test bench is the
  closest identified engine lineage (approximately 12.5 mm bore × 12 mm
  stroke). Its abstract confirms cylinder and crankcase pressure, air/fuel
  flow, torque and a verified miniature blow-by model, but not the paired
  `P,T,clearance,flow` points needed for calibration.
  [SAE record](https://saemobilus.sae.org/papers/experimental-tests-simulations-a-15-cc-miniature-glow-ignition-two-stroke-engine-2010-32-0018)
- **Menon, University of Maryland thesis (2010)** — repository metadata covers
  seven miniature glow engines spanning approximately 0.16–7.5 cm³ and
  documents loss-measurement methods. The full thesis remains a recovery target;
  no thermal point table was ingested here.
  [Repository record](https://drum.lib.umd.edu/items/a1920304-5162-42cd-9b2a-01904ee6dcd6/full)
- **Furuhama, Tada & Nakamura, JSME (1964)** — the open J-STAGE article
  describes moving-piston thermocouple measurements, including a 40 mm-stroke
  two-stroke motorcycle engine tested up to 8000 rpm. The accessible PDF is a
  scanned figure document; without a controlled digitization pass, no absolute
  temperature curve is promoted.
  [J-STAGE article](https://www.jstage.jst.go.jp/article/jsme1958/7/26/7_26_422/_article)
- **Ishibashi et al., SETC 2019-32-0548** — the public abstract describes
  telemetry measurement of the complete piston temperature distribution from
  cold start through warm-up while accounting for cylinder-wall temperature.
  The paper is paywalled here and supplies no point values to the ledger.
  [JSAE record](https://tech.jsae.or.jp/paperinfo/en/content/conf2019-07.34/)
- **CCEFP/AP .09 report family** — open annual reports preserve the AP .09
  free-piston/compressor lineage and qualitative evidence that taper/reaming
  changes warm clearance and blow-by. No absolute flow row with simultaneous fit
  and temperature metadata was recovered.
  [CCEFP Year 6 report](https://www.ccefp.org/wp-content/uploads/2016/05/CCEFP_Y6_Volume_2.pdf)

## Newly recovered near-scale and architecture evidence

- **Shang et al., Science Progress (2020)** — the 0.99 cc test engine is
  explicitly a no-piston-ring, air-cooled two-stroke with 11.25 mm bore and
  10 mm stroke. The paper reports approximately 70 W maximum output, friction
  power above 40 W and a highest-speed region near 18,000 rpm; its cylinder-head
  temperature is reported over roughly 160–200 °C. These are useful near-scale
  thermal-magnitude and operating-context observations, not a piston/liner
  temperature pair or blow-by calibration.
  [Open-access article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10451914/)
- **Shang et al., Applied Sciences (2024)** — a roughly 9.0 × 8.6 mm HCCI
  engine was tested with the cylinder block controlled at 70, 90, 110 and
  130 °C. The reported combustion and intake changes establish that wall
  thermal state is first-order at this scale, but block temperature is not a
  local liner-TDC or piston temperature and is not used as a clearance prior.
  [Open PDF](https://pure.tue.nl/ws/portalfiles/portal/352894799/applsci-14-07359.pdf)
- **Tada & Furuhama, JSME (1964)** — in a ringed farm-type gasoline engine,
  the abstract reports as much as 81% of piston heat flowing through rings and
  ring lands to the cylinder wall at 3500 rpm/full load, with a piston-back
  heat-transfer coefficient of 35–60 kcal/(m² h °C), approximately 40.7–69.8
  W/(m² K). This is deliberately retained as ringed-architecture evidence only;
  it is not a ringless skirt-to-liner conductance.
  [JSME abstract](https://doi.org/10.1299/kikai1938.30.350)
- **Furuhama & Tada, JSME (1961)** — the ring-gap apparatus reports a leakage
  discharge coefficient of 0.8–0.9 (mean about 0.86) near working-engine
  states and leakage-gas temperature approximately equal to piston-surface gas
  temperature. This is a ring-pack/orifice input, not a ringless annulus input.
  [J-STAGE abstract](https://doi.org/10.1299/jsme1958.4.684)
- **MECOA manufacturer FAQ (2022)** — the ABC description states that the
  piston/liner set is intentionally tapered or choked when cold and becomes
  effectively straight as the cylinder reaches operating temperature. It gives
  no taper magnitude, local temperature pair or clearance table, so it remains
  qualitative manufacturer evidence rather than a numeric fit datum.
  [Manufacturer FAQ](https://www.mecoa.com/faq/abc/abc.htm)

These additions still do **not** recover a quantitative ringless
piston↔liner heat-transfer coefficient, oil-film thermal resistance, or ABC
taper profile. They support separating ringed and ringless thermal topologies
and support the plausibility of an order-of-10-µm cold-fit screen, but they do
not narrow the existing calculated envelope or change the canonical leakage
evidence dataset.

## What is deliberately not in the measurement CSV

The often-cited 284–326 °C crown range and approximately 42 K circumferential
variation from a small two-stroke study were not entered as point measurements
in this pass because the exact figure/page extraction and test-condition pairing
were not independently recovered. They remain a documented recovery target,
not a hidden prior. The same rule applies to any AP .09 airflow or blow-by value
seen only in a graph or secondary summary: digitization is acceptable later only
with figure/page provenance and an explicit uncertainty.

## Reproduction

```bash
python scripts/analyze_thermal_literature.py
python -m unittest tests/test_thermal_literature.py -v
```

At the current revision the ledger contains thirteen sources and twenty
reported context/method/sensitivity values, but zero paired piston/liner
temperature rows. The analysis script therefore produces no empirical
clearance prior and no change to the canonical leakage evidence dataset.
