# Microengine Rig Beta 2.6 — Public-data and transport uncertainty

## Outcome

Beta 2.6 replaces the single prescribed inter-zone mixing time with a
diffusion-plus-piston-strain uncertainty closure, adds two-zone support for an
orifice leakage bracket, and runs a 72-case mechanism x mixing x sealing pilot.

No point passes every deliberately broad sealing and mixing case. A useful
conditional island does survive: at 3.0 bar intake, the 3 micrometre/e=0.5
annular bracket with the central 12-34 ms mixing closure passes the conservative
screen for all three chemical mechanisms at both CR 7.75 and CR 8.0.

This is not yet a hardware design point. It identifies the scalar that CFD must
measure: the crank-angle-dependent core/boundary exchange time.

## Model additions

### Diffusion-strain closure

The two-zone exchange rate is now

    k_mix = pi^2 D/L^2 + C_s |u_p|/B
    tau_mix = 1/k_mix

with explicit lower and upper bounds. `D`, `L`, and `C_s` are uncertainty inputs,
not fitted turbulence constants. The pilot brackets were:

| Case | Observed exchange-time range | Interpretation |
|---|---:|---|
| Slow | 100 ms | diffusion/strain lower bound after clipping |
| Central | 11.9-33.8 ms | provisional working closure |
| Fast | 2.36-3.17 ms | strong homogenization bound |

### Sealing model classes

The pilot includes a sealed reference, two ringless annular brackets, and a
single-orifice ring-pack proxy. The latter is intentionally pessimistic: a real
ring pack is an unsteady series of inter-ring/behind-ring volumes and passages,
not one opening directly to the crankcase.

Public evidence is stored in `sealing_prior.py`. It changes which model classes
we include, but does not claim that an 84 mm automobile engine measures the
absolute leakage of an 8.5 mm cylinder.

## Pilot campaign

Conditions common to all cases: 8.5 x 7.0 mm, 1200 rpm, 3.0 bar intake, 300 K
intake, 25/75 mol% DME/methane, phi 0.40, 560 K fixed wall, 20% initial boundary
mass. Mechanisms: Zhao sk39, Zhao full55, and LLNL79. CR: 7.75 and 8.0.

The conservative acceptance screen requires positive gross IMEP, 10-90% fuel
conversion, peak temperature below 1600 K, maximum pressure rise no greater
than 10 bar/degree, and CA50 between -15 and +20 degrees ATDC.

| Result | CR 7.75 | CR 8.0 |
|---|---:|---:|
| Acceptable cases / 36 | 11 | 9 |
| Mechanisms passing, 3um/e=.5 + central mixing | 3/3 | 3/3 |
| Mechanisms passing any fast-mixing seal | 0/12 | 0/12 |
| Mechanisms passing 5um/e=.5 | 0/9 | 0/9 |
| Mechanisms passing 0.006 mm2 one-stage orifice | 0/9 | 0/9 |

The 3 micrometre/e=.5 central-mixing envelopes were:

| CR | Gross IMEP range | Maximum Tmax | Maximum MPRR |
|---|---:|---:|---:|
| 7.75 | 0.638-1.867 bar | 932 K | 7.27 bar/deg |
| 8.0 | 0.715-3.882 bar | 1082 K | 8.01 bar/deg |

Every accepted pilot case retained at least 87.4% of end-cycle cylinder mass.
That is a necessary condition in this campaign, not a universal sealing target:
fully sealed fast-mixing cases still entered rapid heat release.

## Public leakage data

Useful sources exist, but not as a drop-in Honda correction factor.

- Koszalka (2004) describes compressible critical/subcritical flow through a
  multi-volume ring labyrinth and reports that ring/groove side-passage area can
  exceed end-gap area by more than one order of magnitude.
- Koszalka and Koszalka (2022) used an 84 x 90 mm, CR12, three-ring gasoline
  engine at 2000 rpm. Their coupled ring-flow/motion/oil model agreed with
  measured blow-by within 15%; a 300,000 km wear extrapolation increased flow
  56-60%.
- Aghdam and Kazemi (2010) validates blow-by modeling under motoring while
  varying speed and compression ratio—exactly the clean experimental approach
  wanted for future microengine hardware.
- Published power-scaled crankcase-flow rules vary by roughly 2-3x and their
  compiler explicitly cautions against treating them as universal.

These sources validate architecture and uncertainty width. They do not preserve
bore/residence-time scaling, ring geometry, oil state or pressure history, so
they cannot identify the microengine's absolute throat area.

## Direct DME validation source found

The largest chemistry gap is now actionable. Burke et al. (2015) measured pure
DME, pure methane, 80/20 CH4/DME, and 60/40 CH4/DME ignition delays using three
shock tubes and a rapid-compression machine over 600-1600 K, 7-41 atm, and phi
0.3, 0.5, 1.0, and 2.0. This covers the project's 20-25% DME and lean, boosted
region unusually well.

The accepted manuscript is public, but machine-readable point data was not
located. The next chemistry task is to obtain author/supplementary tables or
digitize the relevant 80/20 curves with uncertainty metadata, then pass them
through `mechanism_gate.py` using each facility's ignition criterion.

Source: U. Burke et al., *Combustion and Flame* 162 (2015) 315-330,
https://doi.org/10.1016/j.combustflame.2014.08.014.

## Numerics

The LLNL mechanism stalled in three stiff pilot cases at CVODE's default trace
species tolerances. The production two-zone tolerance is now rtol=1e-7 and
atol=1e-14. Repeating representative Zhao and LLNL central-mixing cases at
1e-9/1e-15 changed gross IMEP by 0.004 and 0.010 bar respectively and peak
temperature by less than 0.5 K. All 72 pilot cases then completed; no null was
treated as a physical outcome.

The check is reproducible with `two_zone_tolerance_check.py`; its complete
conditions and deltas are stored in `beta26_tolerance_check.json`.

## CFD decision

The next CFD is nonreacting and axisymmetric. It does not need detailed
chemistry. A moving-piston OpenFOAM case should transport a passive radial
scalar and report its core/boundary decay rate versus crank angle. The fitted
rate replaces the provisional `D`, `L`, and `C_s` brackets.

OpenFOAM 14 is the preferred local route because it is free, supports engine
mesh motion, and installs on Windows through WSL. SimScale Community is a
no-install alternative, but projects are public; an academic plan may provide
private projects and core hours.

## Files

- `two_zone_model.py` — dynamic mixing closure and orifice/annular brackets
- `sealing_prior.py` — public evidence ledger and explicit sealing cases
- `uncertainty_campaign.py` — headless pilot/full ensemble runner
- `beta26_uncertainty.csv/json` — 72 complete cases
- `beta26_uncertainty_summary.csv` — grouped robustness results
- `plot_beta26.py`, `beta26_uncertainty_audit.png` — mechanism-pass map
- `two_zone_tolerance_check.py`, `beta26_tolerance_check.json` — numerical audit
