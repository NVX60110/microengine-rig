# Friction and valve-flow evidence lane

## Scope

This lane supplies bounded inputs for the future 720-crank-degree engine-cycle
model. It does not modify the canonical chemistry, the one-revolution two-zone
solver, or any CFD case. The outputs are screening helpers and must not be read
as hardware calibration.

The repository previously recorded that its exact `0.018--0.044 bar` FMEP
screen was not accepted: it undercounted journal work and evaluated only 360
degrees for a four-stroke cycle. The new helper therefore exposes an explicit
low/central/high sensitivity bracket and uses the correct four-stroke period
`120/N` seconds.

## Friction/motoring bracket

`physics/friction_bracket.py` defines 0.05, 0.15, and 0.30 bar FMEP as
**project sensitivity assumptions**. They are not measured values and are not
claimed to be literature-derived. The low mean piston speed (0.28 m/s at
1200 rpm) motivates screening them, but does not determine FMEP.

For displacement `Vd`, positive FMEP is a loss:

```text
W_friction = FMEP * Vd
tau_equiv  = W_friction / (4*pi)
P_friction = W_friction * N/120
```

The `4*pi` denominator is the work-equivalent constant torque over 720 CAD.
The torque is intentionally not a crank-angle friction trace. It omits
journal load, piston secondary motion, ring friction, lubrication regime,
temperature, speed dependence and accessory load. A motoring-torque trace at
the target hardware is the required calibration experiment.

At the nominal 8.5 x 7.0 mm geometry (`Vd = 0.3971 cc`, approximate), the
bracket corresponds to the following 1200-rpm screen:

| FMEP | work/cycle | equivalent torque | friction power |
|---:|---:|---:|---:|
| 0.05 bar | 1.99 mJ | 0.158 mN m | 0.0199 W |
| 0.15 bar | 5.96 mJ | 0.475 mN m | 0.0596 W |
| 0.30 bar | 11.91 mJ | 0.949 mN m | 0.119 W |

These are calculated from the stated assumptions, not observations. They are
small compared with the nominal closed-cycle gross indicated work, but a
complete model still needs pumping work, multi-cylinder/accessory loads and
the motor controller before a stable idle can be promoted.

## Valve/orifice helper

`physics/valve_flow.py` uses a prescribed effective area and a standard ideal-
gas compressible orifice relation. The area is a half-sine between explicit
opening and closing crank angles, with no claim that it represents a cam,
port, curtain area, or discharge coefficient for the final engine.

The convention is one 720-CAD cycle with firing TDC at 0/720:

```text
0--180 expansion | 180--360 exhaust | 360--540 intake | 540--720 compression
```

The helper returns signed mass flow (positive cylinder to port), a choking
flag, peak flow, and integrated mass. Its `flow_work_J` is an enthalpy-flow
diagnostic; it is not engine pumping work. Pumping work is separately computed
as:

```text
W_pump = integral((p_cylinder - p_reference) dV)
PMEP   = W_pump / Vd
```

The sign is preserved. A negative loop work is a pumping loss. This prevents
valve enthalpy transport from being accidentally counted as p-V pumping work.

For a first sensitivity screen, effective area and timing should be varied as
inputs (for example, a factor-of-two area bracket and an event timing shift),
not optimized. The project has a prior low-Mach valve-area screen at 1200 rpm,
but its extrapolation to high RPM was explicitly not validated. There is no
quantitative discharge-coefficient calibration for the 8.5 mm hardware in the
public ledger.

## Calibration limits and next use

The future 720-CAD model should first use disabled-valve regression mode, then
enable these helpers with a small timing/area bracket. It must calculate
residual mass and composition from the valve events, retain pumping MEP
separately from FMEP, and close mass/energy over repeated cycles. A positive
closed-pass gross IMEP is not sufficient.

The decisive measurements remain: crank-angle-resolved motoring torque at
several RPMs, cylinder/port pressure traces, valve lift or effective area,
mass flow, and (for sealing) paired local piston/liner temperatures and direct
leakage. Until those exist, all friction and valve coefficients in this lane
are assumptions or transparent mathematical closures.

