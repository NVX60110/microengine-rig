# MicroEngine Virtual Rig — Beta 2.4 Two-Zone Report

> Beta 2.5 correction: the primary conversion metric now uses exact global
> fuel inventory. The accepted Beta 2.4 anchors change negligibly, but coarse
> stiff hot cases must be regenerated. See `BETA25_REPORT.md`.

## Executive result

Beta 2.4 changes the interpretation of the hot-wall effect. In Beta 2.3 the
entire homogeneous charge instantly received wall heat. In the two-zone model,
the 560 K wall still adds net energy to the gas, but that energy initially stays
in a wall-adjacent zone. Limited transport to the core prevents the global
preheating that triggered the single-zone runaway.

At the default 20% boundary-zone mass and 10 ms mixing time, every valid 2-3 µm
anchor case from both DME mechanisms becomes bounded partial oxidation. The
5 µm cases lose positive gross work. No default two-zone design case pays for
the idealized compressor.

This is the strongest evidence so far that the single-zone model overstates the
ability of a hot ceramic wall to ignite the whole charge. It is not validation
of a specific quench thickness or mixing time.

## Model added

`two_zone_model.py` creates two independent Cantera reactors:

- A reactive core with no direct chamber-wall heat transfer
- A wall-adjacent zone receiving the full chamber-wall heat-transfer area
- A moving internal wall that exchanges volume and keeps pressures nearly equal
- Configurable inter-zone heat transfer
- Equal counterflow mass controllers that exchange species and enthalpy on a
  user-specified mixing time
- Physical thin-annulus leakage with clearance, skirt length, gas viscosity and
  eccentricity retained

The external piston walls preserve the exact total slider-crank volume change.
Chemical fuel destruction is integrated separately in each zone, so exchange
between zones does not masquerade as reaction.

The default uncertainty inputs are:

| Input | Default |
|---|---:|
| Initial boundary-zone mass | 20% |
| Inter-zone mixing time | 10 ms |
| Inter-zone heat-transfer coefficient | 100 W/m2/K |
| Interface area | One piston area |
| Pressure-equalization coefficient | 5e-5 m/(s Pa) |
| Leakage allocation | Proportional to zone mass |

These are modeling parameters, not measured turbulence, boundary-layer
thickness or quench distance.

## Numerical verification

The nonreacting adiabatic two-zone model collapses back to the canonical
single-zone result:

| Diagnostic | Single zone | Two zone |
|---|---:|---:|
| Peak pressure | 17.523 bar | 17.534 bar |
| Peak temperature | 626.58 K | 626.68 K |
| Fuel conversion | approximately zero | approximately zero |

At the shared reacting anchor, the crank-step convergence is:

| Mechanism | Step [deg] | Gross IMEP [bar] | Conversion | Max dP/dCA [bar/deg] |
|---|---:|---:|---:|---:|
| Skeletal 39 | 0.2500 | 1.0446 | 36.568% | 4.208 |
| Skeletal 39 | 0.1250 | 1.0431 | 36.583% | 4.654 |
| Skeletal 39 | 0.0625 | 1.0412 | 36.577% | 4.726 |
| Skeletal 39 | 0.03125 | 1.0418 | 36.601% | 4.754 |
| LLNL 79 | 0.2500 | 0.6580 | 29.098% | 2.641 |
| LLNL 79 | 0.1250 | 0.6552 | 29.096% | 2.703 |
| LLNL 79 | 0.0625 | 0.6538 | 29.107% | 2.726 |
| LLNL 79 | 0.03125 | 0.6537 | 29.113% | 2.733 |

Changing the pressure-equalization coefficient from 5e-5 to 7e-5 changes
skeletal IMEP by 0.00003 bar and LLNL IMEP by 0.00019 bar. Maximum zone-pressure
difference falls from about 0.072 to 0.054 bar. The chemistry result is not an
artifact of the accepted pressure-coupling value.

The 66-case campaign has 63 accepted results. Two intentionally weak
pressure-coupling cases exceed the 0.10 bar mismatch screen. One 30%-boundary,
5 ms skeletal case enters a violent transition while remaining sensitive to
the coupling coefficient; it is rejected rather than interpreted.

## Default anchor comparison

All rows below use 3 µm concentric clearance, 20% boundary mass, 10 ms mixing,
CR 7 and 1200 rpm.

| Mechanism / anchor | Single branch | Single IMEP | Two-zone branch | Two-zone IMEP | Two-zone conversion | Core / boundary Tmax |
|---|---|---:|---|---:|---:|---:|
| Skeletal, phi .40 / 2.3 bar | Rapid | 8.75 | Cool partial | 1.04 | 36.6% | 901 / 823 K |
| Skeletal, phi .35 / 2.6 bar | Cool partial | 4.91 | Cool partial | 0.91 | 36.3% | 889 / 822 K |
| Skeletal, phi .35 / 3.0 bar | Rapid | 10.76 | Cool partial | 1.21 | 38.4% | 893 / 832 K |
| LLNL, phi .40 / 2.3 bar | Rapid | 9.11 | Cool partial | 0.66 | 29.1% | 867 / 765 K |
| LLNL, phi .35 / 2.6 bar | Rapid | 9.33 | Cool partial | 0.59 | 30.0% | 861 / 771 K |
| LLNL, phi .35 / 3.0 bar | Rapid | 11.07 | Cool partial | 0.78 | 31.5% | 863 / 786 K |

The default model therefore does not merely smear the single-zone cliff. It
removes the global hot branch at all three anchors and leaves a weaker DME-led
partial-oxidation event.

## Shared-anchor chemistry

The fine 0.0625-degree traces give:

| Diagnostic | Skeletal 39 | LLNL 79 |
|---|---:|---:|
| Peak pressure | 46.10 bar | 43.71 bar |
| Maximum pressure rise | 4.73 bar/deg | 2.73 bar/deg |
| CA50 | -9.16 deg ATDC | -5.07 deg ATDC |
| Total fuel-consumption proxy | 36.58% | 29.11% |
| DME consumed | 68.21% | 54.43% |
| Methane consumed | 6.30% | 4.87% |
| Core reaction extent / initial total fuel | 30.57% | 24.18% |
| Boundary reaction extent / initial total fuel | 6.00% | 4.92% |
| Wall energy, gas to wall | -48.3 mJ | -65.9 mJ |

The negative wall-energy sign means the 560 K wall heats the charge. Yet the
two-zone calculation reacts less than the homogeneous one because wall energy
is localized instead of being distributed instantly through the core. This
reverses the earlier inference that a hot wall necessarily improves whole-charge
ignition.

Approximately 83% of the modeled chemical reaction extent occurs in the core.
The core heat-release peaks at -9.9 degrees (skeletal) and -5.8 degrees (LLNL).
The much weaker boundary peaks occur later, at -4.5 and +4.7 degrees. The wall
zone is not completely inert, but it is delayed and contributes little methane
oxidation.

## Mixing is now the dominant unknown

The shared-point sensitivity is non-monotonic:

- With no inter-zone mass exchange, both mechanisms produce negligible or
  negative-work reaction for 10-30% boundary mass.
- At 20% boundary mass and 5 ms mixing, the skeletal mechanism reaches 64.3%
  conversion and 3.57 bar IMEP; LLNL reaches 36.5% and 0.80 bar.
- At 20% and 10-20 ms, both remain on bounded partial branches.
- At 30% and 5 ms, LLNL transitions to 96.7% conversion, 1866 K and
  29.9 bar/degree. The corresponding skeletal case also trends toward runaway
  but fails the pressure-coupling robustness screen.

The important control variable may therefore be radial transport—not boost or
blend ratio alone. Faster mixing can transport wall heat and reactive
intermediates into the core; slower mixing can isolate both zones enough that
neither sustains useful reaction.

This model prescribes mixing rather than predicting it. The bifurcation is a
request for data, not a design setting.

## Sealing and eccentricity survive the spatial correction

At the shared point:

| Mechanism | Clearance | IMEP e=0 | IMEP e=0.5 |
|---|---:|---:|---:|
| Skeletal | 2 µm | 1.72 | 1.59 bar |
| Skeletal | 3 µm | 1.04 | 0.75 bar |
| Skeletal | 5 µm | -0.94 | -1.61 bar |
| LLNL | 2 µm | 1.14 | 1.06 bar |
| LLNL | 3 µm | 0.66 | 0.42 bar |
| LLNL | 5 µm | -1.14 | -1.65 bar |

Two-zone physics does not remove the sealing requirement. It makes the useful
work margin smaller, so piston rock and hot clearance matter even more.

## Power conclusion

None of the 36 accepted anchor/clearance/eccentricity design cases produces
positive gross-indicated-minus-compressor power. This strengthens the case for
an electrically driven display engine. It still is not a brake-power theorem:
the compressor model is idealized, the cycle has no valves or pumping loop,
and friction remains absent.

## What the model still cannot claim

- No resolved thermal boundary-layer thickness
- No radical adsorption, flame-wall chemistry or measured quench distance
- No turbulence or piston-induced velocity field
- No crevices, ring flutter, oil film, taper or piston rock dynamics
- No multi-cycle residual-gas chemistry in the two zones
- No wall-temperature equilibrium during this campaign
- No intake/exhaust valves, pumping work, friction or brake output

The boundary zone is a controlled spatial bracket. It must not be described as
CFD or as a validated two-zone HCCI model.

## Engineering decision

Keep the 90/10 motor-driven architecture. Retain 2-3 µm hot-clearance development
as a primary manufacturing experiment. Do not increase boost to recover the
single-zone power prediction until radial transport is measured or bounded.

The highest-value hardware measurements are now:

1. Motored and firing in-cylinder pressure at several wall temperatures.
2. Fast wall/liner thermometry or two-color optical temperature where feasible.
3. Hot leak-down and crankcase mass flow versus piston temperature and position.
4. Exhaust CO, CO2, formaldehyde and unburned hydrocarbon measurements.

The next software step should replace the arbitrary mixing time with a small
family of transport closures tied to thermal diffusivity, molecular diffusion
and piston-speed scaling, then propagate their uncertainty rather than selecting
one preferred value.
