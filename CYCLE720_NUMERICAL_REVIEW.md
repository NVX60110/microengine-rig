# 720-CAD Engine-Cycle Numerical Review

Status: independent implementation review, based on `origin/main` at
`47d568d`.

This memo is a preflight for the minimum complete four-stroke model. It does
not implement valves, residual carry-over, friction, crank dynamics, or a new
chemistry model. It is intended as a falsification and regression checklist
for the implementation lane.

## What the current code actually represents

`microengine_rig.py` builds the slider-crank geometry with `theta = 0` at TDC
and `theta = +/-pi` at BDC. Its reacting solver integrates only
`-180 to +180 CAD`: compression from BDC to TDC followed by expansion back to
BDC. `RigConfig.cycle_revolutions = 2.0` is used for the full four-stroke
period in thermal-cycle bookkeeping, but it does not make the reacting solver
a 720-CAD gas-exchange model.

`two_zone_model.py` has an optional arbitrary initial state and exports an end
state, but it explicitly describes that state as a one-revolution snapshot,
not an exhaust-valve model or a four-stroke cycle. Its gross work excludes gas
exchange and friction.

Therefore the existing 1,200-rpm result is a closed-pass project-model result.
It is not yet a stable-idle result, a residual prediction, a pumping result, or
a motor-sizing result.

## Recommended phase convention

Use an external four-stroke cycle angle `theta4_deg` on `[-360, +360]`, with
the modeled firing TDC at `0 CAD`. This preserves the current closed-pass
interval exactly in the middle of the new cycle:

| interval | piston event | valve state to be scheduled |
|---|---|---|
| `-360 -> -180` | intake TDC to BDC | intake primarily open |
| `-180 -> 0` | BDC to firing TDC | compression; intake closed |
| `0 -> +180` | firing TDC to BDC | expansion/power; valves closed |
| `+180 -> +360` | BDC to exhaust TDC | exhaust primarily open |

The wrapped endpoints `-360` and `+360` are the same geometric TDC state, but
they are not the same event label: the former is the intake-side cycle start
and the latter is the exhaust-side cycle end. A serialized cycle must retain
the event phase rather than sorting angles modulo 360 and losing that
distinction.

An equivalent implementation may use `[0, 720]` with expansion first, but it
must provide an explicit mapping back to the convention above. At `N` rpm:

```text
t_rev       = 60 / N              seconds
t_4stroke   = 120 / N              seconds
omega       = 2*pi*N / 60          rad/s
dt          = radians(dtheta)/omega
```

At 1,200 rpm these are 50 ms and 100 ms, respectively. A 0.125-CAD step is
approximately 17.36 microseconds. The report must expose both periods; a
one-revolution value must never be called a four-stroke period.

## Required regression invariants

The implementation should first run a deterministic `valves=off,
friction=off, motor=off` bridge mode. It should start from the same BDC state
and reproduce the accepted current solver over `-180 -> +180` with the same
mechanism, wall, leakage, timestep, and Cantera tolerances. Compare the full
pressure, temperature, volume, mass, conversion, and work traces—not only peak
pressure. A reasonable initial gate is:

* geometry and volume: absolute error no larger than the existing recorded
  numerical precision;
* mass balance: existing closed-cylinder relative gate `1e-4` or tighter;
* reacting P/T and conversion: a declared relative/absolute tolerance set from
  a same-process baseline, with no unexplained drift;
* work: signed `int(p dV)` agreement, including the same angle convention.

The bridge must not reinitialize the state at 0 CAD or silently replace the
second half of the 720-CAD interval with fresh charge. Any discrepancy must be
reported as a regression failure before valves or motor controls are enabled.

Minimum geometry/timing tests:

1. `V(-360) = V(0) = V(+360) = V_TDC` and
   `V(-180) = V(+180) = V_BDC` to floating-point tolerance.
2. The rod/stroke ratio and slider-crank volume match `build_geometry()` at
   every bridge angle.
3. `t_rev` and `t_4stroke` are correct at 800, 1,200, 2,000, and 5,000 rpm.
4. A constant-pressure closed cycle has zero net gas work over 720 CAD.
5. With both valves closed, no blow-by, and no reactions, total mass and every
   species inventory remain constant while volume changes.
6. A disabled 720 wrapper does not alter the existing closed-pass result.

## Conservation and state equations

For a one-zone open reactor, the tracked mass equation is

```text
d(m Y_k)/dt = sum(mdot_in * Y_in,k) - sum(mdot_out * Y_out,k)
              + V * omega_k * W_k
```

The corresponding total-energy accounting must use the same signed flows:

```text
dU/dt = Q_wall - p*dV/dt
        + sum(mdot_in * h_in) - sum(mdot_out * h_out)
```

Chemical reaction energy is supplied by the Cantera thermochemical state; it
must not be added a second time as a separate heat-release source. Valve flow
enthalpy is upstream-state enthalpy for the chosen idealized control volume.
If the 720 model retains two zones, valve inflow/outflow allocation and
inter-zone exchange must conserve the sum of both zones. Pressure
equalization must not create or remove energy.

The implementation should export, per cycle:

* start/end total mass and mass residual;
* start/end species vectors and max species residual;
* integrated intake, exhaust, leakage, and reverse-flow masses;
* gas work, wall heat, intake work, exhaust work, and pumping MEP;
* reaction heat-release integral as a diagnostic, not a second energy source;
* start/end specific enthalpy/internal energy and energy residual;
* pressure/temperature and wall-state closure.

For a converged periodic state, the state at `+360` must equal the mapped state
at the next `-360`. It is not enough for the final pressure to look plausible.
The residual composition must be the model's exhaust result, not a frozen
vector copied from the prescribed-residual experiment.

## Valve-flow model requirements and pitfalls

A first-order valve model is adequate for this stage if it is inspectable. For
each valve, use a nonnegative scheduled effective area or `CdA(theta)` and a
compressible orifice relation of the form

```text
mdot = Cd*A_eff*P_up/sqrt(R*T_up) * Psi(P_down/P_up, gamma)
```

where `Psi` has explicit choked and unchoked branches. The flow sign must be
selected from the instantaneous upstream/downstream absolute pressures. A
nominal intake or exhaust direction must not suppress physically possible
backflow during overlap or blowdown. Zero area must mean zero flow exactly.

Keep these inputs separate:

* valve opening/closing angles;
* peak effective area;
* discharge coefficient;
* manifold/reservoir pressure and temperature;
* valve-flow backflow policy.

Do not hide a valve timing or area choice in a calibration factor. Start with a
small declared bracket and sensitivity runs, not an optimization. The first
question is whether gas exchange is first-order, not which cam is optimal.

The valve schedule must be sampled at the same crank-angle step as the reactor
advance. For trapezoidal flow integration, use endpoint rates from the same
state that advances the reactor. Avoid counting the `+360` endpoint as another
finite timestep. Record cumulative inflow/outflow independently for each valve
and direction.

## Residual definition and convergence

Use the end state after exhaust as the input to the next cycle. A useful
reported residual fraction is

```text
f_res = mass of burned-gas marker remaining after exhaust /
        total mass trapped at next intake close
```

Also report residual mass at exhaust-valve-close and at intake-valve-close;
these are different quantities in a model with valve overlap or backflow.
The exact burned-gas marker must be stated: a species set, elemental tracer,
or an explicitly defined mass fraction. `CO2 + H2O` alone is not a universal
burned-gas definition if incomplete oxidation is material.

Residual periodicity requires all of the following, on the same phase point:

* total mass closure;
* maximum species-vector difference below a declared tolerance;
* temperature and pressure closure;
* specific enthalpy/internal-energy closure;
* wall-state closure if the wall is dynamic;
* crank-speed waveform closure if dynamics are enabled.

An iteration cap with a decreasing residual is still unresolved. A cool branch
that appears stable over eight cycles is a trend until the declared fixed-point
gate passes. Conversely, a solver error, NaN, rejected integration state, or
missing cycle output is a numerical failure, not extinction.

## Crank and motor dynamics

Use a single explicit sign convention and include it in every output. With
positive torque in the selected crank direction:

```text
I*domega/dt = tau_gas + tau_motor - tau_friction - tau_load
```

For a prescribed-speed run, report the motor torque required to enforce that
speed; do not imply that the gas torque was dynamically sufficient. For a
free-running or controlled-speed run, integrate the speed state and serialize
the controller settings, initial speed, inertia, load, and torque limits.

Gas torque should come from the instantaneous pressure-volume derivative (or
the equivalent generalized force), not from gross work divided by an assumed
angle. Over one complete cycle:

```text
W_gas = integral(p dV) = integral(tau_gas dtheta)
```

Report separately:

* gross gas work and gross IMEP;
* pumping work/PMEP from intake and exhaust;
* friction work/FMEP from the friction bracket;
* net indicated work;
* controller/motor work, peak torque, RMS torque, peak power, and RMS power.

Average motor power alone is insufficient. A motor may need substantial peak
torque to cover compression or a weak combustion cycle even when cycle-average
work is small. Do not assign work to the unmodeled revolution or call a
closed-pass positive IMEP a self-sustaining idle.

The first controller should be deliberately simple and bounded, such as a
specified-speed torque controller with explicit saturation. A controller that
injects unlimited torque or silently clips negative speed is a numerical aid,
not evidence of stable operation. A useful robustness test perturbs the speed,
residual state, wall temperature, and torque command and checks return toward
the same periodic waveform.

## Friction and motoring bracket

Keep friction outside the combustion model. Use a separately documented
low/central/high resisting-torque bracket, with units and provenance. Do not
convert an arbitrary full-size FMEP correlation directly to 8.5 mm without a
valid scaling argument. If the bracket is only an engineering sensitivity,
label it as such.

At minimum, the output should make it possible to distinguish:

```text
positive gross gas work
positive net ICE work after pumping/friction
motor-assisted speed maintenance
```

If no defensible friction prior can be sourced, keep friction disabled in the
first gas-exchange regression and publish that omission explicitly; do not
silently set it to zero in the final idle conclusion.

## Numerical test matrix before a campaign

The implementation should pass a staged matrix, in this order:

1. Nonreacting, adiabatic, valves/friction/motor off: geometry, mass, and
   work-sign tests.
2. Reacting closed-pass bridge: reproduce the accepted `-180 -> +180` rows.
3. Valves on, reactions off, fixed manifold reservoirs: verify mass flow,
   pressure direction, backflow, and pumping work against a synthetic case.
4. Valves on, reactions off, repeated cycles: verify fresh-charge replacement
   and residual composition convergence without combustion complexity.
5. Reacting 720-CAD cycle, fixed speed, friction off: verify chemistry and
   energy accounting.
6. Add friction bracket, then crank inertia and bounded motor control.
7. Perturb the converged cycle state and require return/decay, or label it
   neutrally stable/unstable rather than “stable idle.”

The first requested production points should remain bounded: 1,000, 1,200,
1,500, and 2,000 rpm; the existing 2/3/5 micrometre annular brackets; and the
three established mechanisms. Do not launch a broad RPM, valve-timing, fuel,
CFD, or sealing campaign until this staged matrix passes.

## Numerical determinism and failure handling

Use deterministic mechanism species order, explicit JSON/CSV field ordering,
and a serialized cycle-start state containing phase, pressure, temperature,
composition, wall state, crank speed, and controller state. Independent runs
should reproduce status and key outputs; byte identity is desirable for JSON
artifacts but floating-point tolerances must be declared.

Store every failed case with a machine-readable `screen_class` such as
`numerical_failure`, `physical_implausible`, or `unresolved_periodic_state`.
Never turn a solver timeout into “no ignition.” Preserve the error type, last
valid angle/cycle, accepted-step count, and numerical settings.

## What can and cannot be claimed at 8.5 mm

If the staged model finds a periodic 720-CAD solution, the defensible claim is:

> A periodic solution exists under the declared valve, manifold, thermal,
> leakage, friction, chemistry, and controller assumptions.

That is a project-model result. It does not validate the absolute leakage law,
hot radial clearance, lubricant behavior, valve discharge coefficient, or
actual idle COV. It also does not establish that a ringless 8.5-mm piston will
run without scuffing.

If the model fails to close, report which gate failed and whether the failure
is numerical, transient, or physical within the model. Do not promote 1,200 rpm
as stable merely because the old closed-pass result was positive, and do not
declare the engine concept impossible from a single uncalibrated leakage or
friction bracket.

The first physical quantities most likely to change the decision remain local
hot piston/liner clearance and taper, dynamic leakage, motoring friction versus
crank angle, valve discharge behavior, and residual fraction. The simulator
can rank sensitivities, but it cannot manufacture those measurements.

## Reviewer conclusion

The minimum complete model is justified, but it should be treated as a staged
regression experiment rather than a single large campaign. The highest-risk
implementation errors are phase wrapping at the two TDC endpoints, mixing a
one-revolution end state with a fresh intake state, double-counting chemical
heat, using one-way valve flow during pressure reversal, and reporting average
motor power without the torque waveform. Passing the closed-pass bridge before
enabling each new subsystem is the main protection against attributing a code
regression to chemistry or physics.
