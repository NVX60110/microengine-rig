# Bounded low-idle operating map (Luna A)

## Decision summary

This campaign is a bounded reacting-screen map, not a stable-idle claim.  It
uses the accepted Beta 2.6 state: 8.5 mm bore, 7.0 mm stroke, rod/stroke 1.6,
CR 7.75, 3.0 bar intake, 300 K intake, phi 0.40, 560 K fixed wall,
25/75 DME/CH4, central diffusion/strain mixing, and the 3 µm/e=0.5 annular
bracket.  The full RPM grid is 800, 1000, 1200, 1500, 2000, 3000, 5000,
7500, and 10000 rpm, with all transition cases at 0.125 CAD and two-zone
CVODE tolerances rtol=1e-9, atol=1e-15.

The first all-mechanism robust *screen* is reported only after the refinement
and mechanism aggregation are complete.  `stable_idle_status` remains
`unresolved` at every row: the model has no friction, pumping, 720-degree gas
exchange, or cycle-to-cycle variability.  Positive gross IMEP therefore does
not establish self-sustaining idle.

For the final regenerated artifacts, the 1105.859375-rpm point is still
marginal for Zhao full (end retention 0.869995), while 1106.0546875 rpm is
robust for all three declared mechanisms.  The raw boundary bracket
**[1105.859375, 1106.0546875] rpm** is therefore **not a physical credibility
interval**: it is the nominal
numerical crossing interval of the campaign-specific 0.87 retention gate,
equivalent to an engineering screen near **1.11 krpm**.  1106.0546875 rpm is
the lowest tested all-mechanism robust screen under that arbitrary necessary
condition.  At that point the LLNL/Zhao-full/
Zhao-sk39 gross IMEP values are 0.6055/3.7623/3.7128 bar and end-mass
retention is 0.87583/0.87002/0.87010.  The adjacent lower point's first
limiter is trapped-mass loss under the necessary 0.87 screen, not a claimed
chemistry extinction boundary.

## Transparent labels

The existing GATES.md conservative screen is applied: positive gross IMEP,
10–90% inventory conversion, peak temperature below 1600 K, maximum pressure
rise no more than 10 bar/CAD, CA50 from -15 to +20 CAD ATDC, and two-zone
pressure mismatch no more than 0.10 bar.  A Beta 2.6 necessary-condition check
of at least 0.87 end-mass retention is also shown; it is not a universal seal
target.

- `robust`: every declared reacting-screen gate passes.
- `marginal`: positive gross work, but one or more bounded screen gates fail
  without the severe high-temperature/rapid-release branch.
- `implausible`: no positive gross work or a severe reaction branch.
- `stable_idle_status=unresolved`: always, for the missing hardware and
  four-stroke physics listed above.

The limiting mechanism is the first failed gate in the ordered screen and is
not a diagnosis beyond this model.  Numerical errors are recorded as
`numerical_failure`, never interpreted as extinction.

## Results and reproduction

Compact machine-readable outputs are:

- `results/op_idle_map_baseline.json` and `.csv` (27 cases: 3 mechanisms × 9
  RPM values, plus an across-mechanism aggregate by RPM);
- `results/op_idle_map_refine.json` and `.csv` (economical refinement around
  the observed lower boundary);
- `results/op_idle_map_refine2.json` and `.csv` (second boundary refinement);
- `results/op_idle_map_refine3.json` and `.csv` (final narrow boundary
  refinement);
- `results/op_idle_map_uncertainty.json` and `.csv` (one-factor-at-a-time
  uncertainty near the candidate lower boundary).
- `results/op_idle_map_retry.json` and `.csv` (single LLNL 1500-rpm
  numerical retry at 0.0625 CAD).

Run from the repository root:

```text
python scripts/op_idle_map.py --scope baseline --jobs 4
python scripts/op_idle_map.py --scope refine --jobs 4
python scripts/op_idle_map.py --scope refine2 --jobs 4
python scripts/op_idle_map.py --scope refine3 --jobs 4
python scripts/op_idle_map.py --scope uncertainty --jobs 4
python scripts/op_idle_map.py --scope retry --jobs 1
```

The worker count is intentionally capped at four on the available 14-core /
20-thread host to avoid Cantera oversubscription.  No CFD, squish coupling,
chemistry retuning, or unsupported residual/EGR model is used.

The baseline produced 10 robust, 3 marginal, 13 physical implausible rows, and
one numerical failure.  At the
low side, 800 rpm is implausible in all three mechanisms from high temperature
and rapid pressure rise; 1000 rpm is marginal from trapped-mass loss; the
1200-rpm aggregate is robust across all three mechanisms.  At high speed the
first limiter becomes nonpositive gross work/low conversion (the closed-cycle
work result), not a proven brake-torque limit.  The initial LLNL 1500-rpm row
hit the existing CVODES 100000-step ceiling; the bounded 0.0625-CAD retry
completed as robust with gross IMEP 0.82954 bar, peak temperature 856.997 K,
maximum pressure rise 2.37554 bar/CAD, CA50 +4.20524 CAD, and end retention
0.90667.  This is a numerical-resolution correction, not a chemistry change.

Each row stores compression-start pressure/temperature and the actual evolving
reacting-state TDC pressure with separate core and boundary TDC temperatures,
ignition/conversion and CA10/CA50/CA90, a compact
pressure-trace digest, gross work/IMEP, peak pressure and pressure rise,
wall heat, trapped mass/leakage, mass closure, event times, and a clearly
labeled lower-bound motor-work/torque proxy.  The event timing uses
`t_rev=60/N` and `t_4stroke=120/N`; onset is the first global inventory row at
1% conversion, while CA10 is based on cumulative chemical heat release.  No
constant-volume TDC delay is presented as path ignition delay.

## Limitations and next physical limiter

The annular 2/3/5 µm values and eccentricities are explicit uncalibrated
engineering brackets, not measured hot clearances.  The central mixing
closure remains a provisional model input.  Zhao parent pressure-dependent
rate selection and direct DME/CH4 mechanism validation remain open.  The
lowest screen boundary is therefore a conditional chemistry/transport/sealing
screen boundary; the first failed gate in the compact results identifies
whether the observed local limiter is trapped-mass loss, low/over-conversion,
phasing, rapid release, or high temperature.  Hardware stability and minimum
motor torque require measured leakage, friction/pumping, multi-cycle residual
chemistry, and full gas exchange.

At the final 1105.957031-rpm uncertainty midpoint, the reference row is
robust (3.7127 bar gross IMEP, 0.87009 retention).  The one-factor screen
shows strong sensitivity: 5 µm/e=0.5 and 5 µm/e=1.0 become nonpositive-work
cases; 3 µm/e=1.0 is also nonpositive-work; 3.5 bar intake, 350 K intake,
phi=0.5 and 600 K wall enter rapid-release or over-conversion branches.  The
2.3 bar intake, 280 K intake, 520 K wall and phi=0.3 rows remain positive-work
screen cases, with the 280 K row marginal on retention.  These are bounded
one-factor sensitivities, not probabilities or stable-idle predictions.
