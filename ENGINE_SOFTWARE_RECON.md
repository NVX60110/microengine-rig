# External engine-simulation software reconnaissance

Status: technical-lead screening, 2026-09-02. No external package was imported
or used to calibrate the canonical engine model during the low-idle campaign.

The decision classes in this note mean:

* **ADOPT** — directly useful now, with a bounded reproducibility gate;
* **ADAPT** — reuse a subsystem, algorithm, or interface after an isolated test;
* **BENCHMARK** — independent comparison only;
* **SCAVENGE** — use equations, data, or validation practice rather than code;
* **REJECT** — do not spend integration effort in the current phase.

These labels are project decisions, not general quality ratings. A full-size
automotive model is not presumed valid at 8.5 mm bore.

## Current decision table

| Candidate | Decision | Useful scope | Principal limit / required gate |
|---|---|---|---|
| [Cantera 3.2](https://cantera.org/stable/reference/reactors/index.html) | **ADOPT** | Existing detailed-chemistry reactor network and CPU-process parameter sweeps | Keep one independent `Solution`/reactor network per process. The documented sparse preconditioner applies to mole-reactor formulations, not automatically to the current two-zone reactor topology. Any reactor refactor must reproduce the accepted 0.125-CAD reference before timing claims. |
| [LibICE-post](https://github.com/RamogninoF/LibICE-post) | **ADAPT / BENCHMARK** | Independent pressure-trace, p-V, and rate-of-heat-release postprocessing | It is a postprocessor, not the missing 720-CAD gas-exchange/idle-stability solver. First comparison should ingest one accepted synthetic trace and reproduce gross indicated work without changing canonical results. |
| [OpenWAM](https://github.com/CMT-UPV/OpenWAM) | **BENCHMARK / SCAVENGE** | Future valves, ducts, wave action, pumping-loop and residual-gas comparison | The public code line is old and license/integration status needs review. Correlations were not validated here at miniature scale. Do not fork it into this repository. |
| [OpenModelica / MVEMLib](https://build.openmodelica.org/Documentation/MVEMLib.html) | **BENCHMARK** | Later motor-flywheel-controller and mean-value hybrid-system studies | Mean-value SI/CI components do not resolve this DME/CH4 closed-cycle chemistry or miniature heat/leakage physics. Use only after a measured or validated torque map exists. |
| [OpenFOAM Foundation 14](https://openfoam.org/version/14/) | **ADOPT, bounded** | Preserve the validated wedge-axis cold-flow reference; possible later fixed-wall-temperature/CHT coefficient partition | No new CFD is decision-limiting in the current idle campaign. A heat-transfer run is justified only if crown/liner heat-flux partition remains the dominant uncertainty after the 0D envelope. |
| [NVIDIA AmgX](https://github.com/NVIDIA/AMGX) | **REJECT for now** | Potential sparse-linear-solver acceleration for much larger future CFD systems | It is a solver library, not a drop-in OpenFOAM-14 engine solver. Integration and host/device overhead are unlikely to pay on the accepted small wedge case. Reconsider only if an isolated matrix/reference case matches existing gates and materially improves end-to-end time. |
| [ReynoldsFlow](https://github.com/vyastreb/reynoldsflow) | **ADAPT / BENCHMARK** | Future nonuniform rough-gap or taper leakage calculations | Its documented model is steady, incompressible, isoviscous thin-gap flow between immobile walls. It does not establish piston-skirt lubrication, cavitation, squeeze-film dynamics, contact, or gas compressibility. Keep outside `physics/annulus.py` until a measured profile requires it. |
| [OpenPulse](https://github.com/MOPT-UFSC/OpenPulse) | **BENCHMARK later** | Exhaust/intake piping acoustic modes and electric/structural pulsation studies | Time-harmonic low-frequency pipeline acoustics is not nonlinear valve blowdown or idle combustion. It is downstream of a validated 720-CAD pressure/flow boundary condition. |
| [ReSpecTh](https://osf.io/nbmzv/) | **ADOPT as evidence lane** | Machine-readable ignition-delay/flame-speed validation records with metadata | Preserve author-supplied versus digitized provenance and facility-specific ignition definitions. It cannot replace the missing Burke point table unless the exact experiment and criterion are present. |
| [Engine Combustion Network](https://ecn.sandia.gov/data/) | **SCAVENGE** | Validation discipline and selected spray/combustion datasets | ECN engine/spray hardware is not a direct geometric or injection analogue. Do not calibrate the miniature premixed engine from it. |

## Performance decision

The MSI GE76 host has an Intel i7-12700H (14 cores / 20 logical processors)
and an RTX 3070 Ti Laptop GPU. The useful current acceleration path is bounded
CPU process parallelism for independent Cantera cases. Four workers were used
for the low-idle campaign to avoid memory and stiff-integrator contention.

GPU migration is not justified by hardware availability alone. The accepted
OpenFOAM wedge-axis fine case already reduced wall time from 1,882 s to 229 s
while preserving the validated observables within 1.6%. A different CFD
distribution, linear solver, or GPU path must first reproduce that reference
inside the existing mass, Courant, volume, tracer, and answer-convergence
gates and then improve end-to-end wall time materially.

## Highest-value bounded follow-ups

1. Use LibICE-post only as an independent indicated-work/ROHR calculation on
   one exported accepted pressure trace.
2. Build the missing 720-CAD gas-exchange/residual/pumping model locally, then
   use OpenWAM only as a trend benchmark at matched boundary conditions.
3. Retain ReynoldsFlow as an isolated future benchmark if measured axial gap,
   taper, or roughness data make a two-dimensional leakage path necessary.
4. Keep GPU/AmgX work parked until a larger CFD problem becomes both
   decision-limiting and linear-solver dominated.

No candidate removes the current need for measured piston/liner temperatures,
friction or motoring torque, direct warm leakage, and cycle-to-cycle idle data.
