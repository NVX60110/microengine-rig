# C1 thermal-clearance and sealing feasibility

## Executive result

This is a calculated screening campaign, not a hardware recommendation or a
calibration.  It replaces the question “is 3 µm enough?” with a temperature-
and-material-dependent fit envelope.

For the representative aluminum-piston/steel-liner pair (EN AW-4032 / 4140,
reference temperature 293.15 K), the cold radial clearance required for a
positive 2–5 µm hot clearance is approximately:

| piston / liner state | 2 µm hot | 3 µm hot | 5 µm hot |
|---|---:|---:|---:|
| 450 / 400 K, 8.5 mm | 9.66 | 10.66 | 12.65 µm |
| 500 / 450 K, 8.5 mm | 11.10 | 12.09 | 14.09 µm |
| 550 / 450 K, 8.5 mm | 15.49 | 16.49 | 18.48 µm |
| 500 / 450 K, 12.5 mm | 15.38 | 16.38 | 18.37 µm |

Thus a nominal 3 µm cold radial clearance is not a robust hot fit for this
pair unless the piston and liner temperatures are unusually close or thermal
management is deliberately designed around it.  The calculations retain
negative clearance as interference; they never convert contact into a fake
leak area.

The single most valuable next experiment is a warm, instrumented leak fixture
on a 10–15 mm reference cylinder that measures temperature, dimensional fit,
pressure, and flow in the same run.  It should measure the chain
`temperature -> hot fit -> leakage`, not a generic leak-down percentage.

## Model and scope

For bore diameter `Db` and cold **radial** clearance `c`, the reference piston
diameter is `Dp = Db - 2c`.  With integrated linear strains `eps_p` and
`eps_l` from each material's own reference temperature,

```
c_hot = 0.5 * [Db(1 + eps_l) - Dp(1 + eps_p)]
```

The one-half is the diameter-to-radius conversion.  The implementation is
[`physics/thermal_clearance.py`](physics/thermal_clearance.py); it reports
cold clearance, both diameter growths, clearance change, hot clearance, and
an interference flag.  It accepts scalar CTEs or piecewise cumulative-strain
profiles.  Negative values are intentional physical warnings.

The hot clearance is passed to [`physics/annulus.py`](physics/annulus.py) only
when it is strictly positive.  Zero clearance is treated as contact, just like
negative clearance, and receives no annulus flow value.  The existing annulus model remains an uncalibrated
screen with its cubic clearance dependence and eccentricity multiplier; it is
not a measured blow-by law.  Cold static leak-down rows and hot dynamic
in-cylinder rows are separate in the output.

No CFD, reacting chemistry, canonical Cantera model, or S3 geometry was
changed in this campaign.

## Campaign definition

The reproducible driver is
[`scripts/thermal_clearance_sweep.py`](scripts/thermal_clearance_sweep.py).
The committed run contains 78,720 clearance/leakage rows and 160 uncertainty
rows:

* bore/stroke: 8.5/7.0 mm and 12.5/12.0 mm;
* cold radial clearance: 0–20 µm in 0.5 µm increments;
* piston temperatures: 350, 450, 550, 650 K;
* liner temperatures independently: 300, 400, 500 K;
* screened eccentricity ratios: 0 and 0.5;
* pressure states: 6.5→1 bar cold static, then 10, 25, 45, and 60 bar→1
  bar hot dynamic screening states;
* air viscosity: Sutherland approximation; annulus skirt length 8 mm at
  8.5 mm bore and 12 mm at the reference bridge scale.

The machine-readable outputs are:

* [`data/sealing/thermal_clearance_sweep.csv`](data/sealing/thermal_clearance_sweep.csv)
* [`data/sealing/thermal_clearance_uncertainty.csv`](data/sealing/thermal_clearance_uncertainty.csv)
* [`data/sealing/thermal_clearance_summary.json`](data/sealing/thermal_clearance_summary.json)

The sweep is analytical/vectorized in problem size; the uncertainty rows use
4,000 seeded Monte Carlo samples per combination only to propagate explicitly
assumed tolerances.

## Material evidence

The property file is
[`data/materials/thermal_properties.json`](data/materials/thermal_properties.json).
Values are literature/datasheet inputs, not measurements of this engine:

| designation | pair role | CTE treatment | conductivity reference |
|---|---|---|---:|
| EN AW-4032-T6 | aluminum piston | cumulative profile, 20–200 °C | 154 W/m·K at 20 °C |
| AA 2618-T61 | aluminum piston | NIST/datasheet cumulative profile | 147 W/m·K at 20 °C |
| 6061-T6 | aluminum liner screen | profile to 20–300 °C; high-end value marked estimated | 167 W/m·K |
| 42CrMo4 / 4140 | steel piston or liner | profile to 400 °C | 42.6 W/m·K |
| EN-GJL-250 gray iron | liner screen | profile to 400 °C | about 48.5 W/m·K at 100 °C |
| Kyocera SN201B silicon nitride | ceramic piston screen | profile 40–800 °C | 25 W/m·K |

Primary/handbook-quality links are preserved with each material row.  For
example, the 4032 datasheet reports approximately 19.4×10⁻⁶ K⁻¹ CTE and
154 W/m·K conductivity
([Aluminium Bozen EN AW-4032 datasheet](https://www.aluminiumbozen.com/images/pdf/schede_leghe/Datasheet_alloy_4032.pdf));
NIST gives temperature-interval CTE values for wrought aluminum alloys
([NIST aluminum properties](https://materialsdata.nist.gov/bitstream/handle/11115/179/Properties%20of%20Wrought%20Aluminum.pdf));
4140 data are from the Einsal material sheet
([42CrMo4 / 1.7227](https://einsal.com/en/materials/material-database/material/pdf/1.7227));
and the ceramic values are from the manufacturer SN201B sheet
([Kyocera SN201B](https://www.kyocera-fineceramics.de/fileadmin/user_upload/Download/werkstoffdatenblaetter/siliziumnitrid/Kyocera_Fineceramics_Europe_SN201B.pdf)).

The screened pairs are aluminum/steel, aluminum/gray iron, aluminum/aluminum,
steel/steel, and silicon-nitride/steel or gray iron.  CTE alone is not a
material selection: thermal conductivity and gradients, brittleness, surface
finish, lubrication, tribology, and manufacturability remain unmodeled.
The same-CTE steel/steel pair has the smallest differential-expansion penalty
in this calculation, but that is not a recommendation for the engine.

## Temperature and fit sensitivity

For Al 4032 / 4140 at 8.5 mm, the worst-corner temperature screen around a
450 K piston / 400 K liner is:

| cold radial clearance | ±25 K independent error | ±50 K independent error |
|---:|---:|---:|
| 3 µm | −8.38 to −0.98 µm | −11.90 to +2.72 µm |
| 8 µm | −3.36 to +4.03 µm | −6.87 to +7.73 µm |

At 12.5 mm the same spans widen to −13.74…−2.86 µm and −18.91…+2.58 µm
for 3 µm, and −8.72…+2.15 µm and −13.89…+7.59 µm for 8 µm.  The larger
bore therefore does not reduce absolute thermal mismatch; the differential
diameter change scales roughly with bore.  It may help practical metrology,
but that benefit is not assumed here.

The tolerance study is deliberately labeled an engineering sensitivity, not a
production probability.  It assumes independent ±1 µm **diameter** errors on
bore and piston, ±5% CTE uncertainty, and independent uniform piston/liner
temperature errors of ±25 or ±50 K.  Representative Al 4032 / 4140 results:

| bore | nominal cold | temperature error | interference | <1 µm | 1–3 µm | 3–5 µm | ≥5 µm |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8.5 | 3 µm | ±25 K | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 8.5 | 8 µm | ±25 K | 42.2% | 22.5% | 29.5% | 5.8% | 0.0% |
| 8.5 | 10 µm | ±25 K | 8.3% | 14.2% | 41.1% | 31.1% | 5.5% |
| 8.5 | 8 µm | ±50 K | 46.3% | 11.5% | 20.8% | 14.0% | 7.5% |
| 12.5 | 8 µm | ±25 K | 91.9% | 5.3% | 2.9% | 0.0% | 0.0% |
| 12.5 | 10 µm | ±50 K | 59.2% | 8.9% | 13.3% | 9.7% | 9.0% |

This is why a nominal value should not be promoted without measured hot fit
and a known axial/thermal state.

## What the leakage coupling says

The model gives a useful sensitivity envelope, not an absolute prediction.  At
8.5 mm, Al 4032 / 4140, 550/450 K, and 45→1 bar at 1100 K:

| cold clearance | hot clearance | annulus flow, e=0 | annulus flow, e=0.5 |
|---:|---:|---:|---:|
| 3 µm | −10.56 µm | interference; no annulus value | interference; no annulus value |
| 16 µm | 2.51 µm | 3.21 mg/s | 4.42 mg/s |
| 20 µm | 6.53 µm | 56.5 mg/s | 77.7 mg/s |

For comparison, a 3 µm positive **cold** annulus at 6.5→1 bar and 300 K
returns 0.975 mg/s in the same uncalibrated model.  The large change with
clearance is expected from the existing `h³` annulus scaling; it is not
evidence that the real engine leaks those exact flows.  The cold static and
hot dynamic lanes must remain separate.

## Design-question answers

1. **Is 3 µm cold meaningful?** It is a meaningful geometric bracket, but for
   an aluminum piston in a cooler steel/iron liner it is commonly overwhelmed
   by differential expansion.  The 8.5 mm screen needs roughly 10–18 µm cold
   for a 2–5 µm hot target across the representative aluminum/steel states.
2. **Temperature error sensitivity:** ±25 K already moves the 3 µm aluminum/
   steel case by about 7.4 µm at 8.5 mm; ±50 K moves it by about 14.6 µm.
3. **Manufacturability:** a 2–5 µm hot window is not credible from a nominal
   cold drawing alone.  It requires roundness, taper, axial temperature, and
   diameter measurement capability at substantially sub-micrometre *relative*
   repeatability, plus a known thermal state.  The present study does not
   claim a process capability.
4. **12–12.5 mm bridge:** absolute thermal mismatch is larger, not smaller,
   although a larger part may be easier to probe and fixture.
5. **Widest calculated window:** matched steel/steel minimizes CTE mismatch in
   this model; aluminum/aluminum can also be favorable when both temperatures
   track.  Silicon nitride/steel retains large positive clearance and often
   needs a cold interference to land in 2–5 µm.  None is promoted because
   tribology, heat flow, fracture risk, finish, and production are outside the
   model.
6. **Ringless plausibility:** hot interference makes the present annulus
   concept invalid; very large hot clearance makes its `h³` leakage rapidly
   grow; and a broad uncertainty distribution means the nominal target is not
   controlled.  Those are reasons to test a ring, thermal management, or a
   larger bench mule—not reasons to choose one architecture from this model.

## Issue #13 fixture connection

The 10–15 mm reference fixture should measure at defined axial/angular
locations:

* cold liner bore, roundness, and taper;
* piston diameter at skirt, crown-side, and thrust/anti-thrust axes;
* piston and liner temperatures independently, with sensor calibration;
* chamber and ambient pressure;
* flow-metered mass flow or volumetric flow with gas temperature;
* lubricant grade, viscosity/temperature, quantity, and wetting state.

Suggested matrix:

* **cold static:** 293 K hardware, 1→6.5 bar differential, repeated at 2, 3,
  5, 8, 10, and 15 µm measured radial fit;
* **warm static/motored:** piston/liner pairs at approximately 350/325,
  450/400, and 550/450 K, with 6.5, 25, and 45 bar states;
* at every point record a dimensional measurement before/after the pressure
  hold and log transient temperature and flow.

For sensor sizing only, the present annulus screen spans roughly 1 mg/s at a
few micrometres and tens of mg/s by 6–7 µm at 45 bar/1100 K, with much larger
values at higher clearance.  A practical first fixture should therefore cover
approximately 0.1–100 mg/s, resolve at least 0.1 mg/s near the low end, and
measure pressure and gas temperature well enough to normalize the flow.  This
is a range recommendation for instrumentation coverage, not a prediction of
actual engine leakage.

## AP .09 / Hornet evidence status

The near-scale audit remains qualitative in
[`data/leakage/NEAR_SCALE_AUDIT.md`](data/leakage/NEAR_SCALE_AUDIT.md).  The
SAE/University of Minnesota/CCEFP search did not recover a trustworthy,
machine-readable absolute airflow table with all required geometry and
temperature metadata.  No row was added to `records.csv`; no graph was
silently promoted to original tabulated data.  A future digitized point must
identify figure/page, digitization method, and an explicit uncertainty.

## Reproduction and status

From the repository root:

```powershell
python scripts/thermal_clearance_sweep.py --samples 4000 --plots
python -m unittest tests/test_thermal_clearance.py -v
python -m py_compile physics/thermal_clearance.py scripts/thermal_clearance_sweep.py
```

The figures emitted by the optional plotting flag are kept under
[`data/sealing/figures`](data/sealing/figures).  All conclusions above are
classified as calculated or assumed unless explicitly identified as
literature-derived.  No sealing architecture is promoted by C1.
