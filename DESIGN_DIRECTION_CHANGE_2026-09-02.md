# Design Direction Change — 2026-09-02

Status: **project-direction handoff**. This document does not replace `PLAN.md`, `FINDINGS.md`, `GATES.md`, or accepted numerical reports. It exists so a future AI agent can resume the broader vehicle/product direction after the originating chat is deleted.

Repository state when this handoff was prepared: `main` at `573f3df8fab9a28a5f9711c94019e4091370f89d` (`docs: promote signed valve periodicity gate`). Future agents must read the current `PLAN.md`, `FINDINGS.md`, and `GATES.md` for the latest engine-physics status instead of treating old cycle numbers in this file as canonical.

## 1. Direction change

The project started primarily as a miniature combustion-engine simulation effort centered on the existing ~8.5 mm bore / 7.0 mm stroke V6 and DME/CH4 HCCI/SACI questions.

The broader product direction is now:

> Build a genuine functional internal-combustion automobile that is externally approximately 1:18 scale, with boutique-model exterior fidelity, while allowing hidden internal machinery to deviate from strict 1:18 scale wherever that improves feasibility.

`microengine-rig` remains the engine-science laboratory for combustion, chemistry, leakage, thermal fit, CFD, cycle modeling, and validation. The engine work is not abandoned. The new rule is that vehicle packaging becomes a first-class design constraint and the current engine geometry is not automatically the final production geometry.

## 2. Product vision

- approximately 1:18 exterior dimensions;
- exterior silhouette should be essentially indistinguishable from a high-end BBR/Amalgam-style model at normal viewing distance;
- no bulged hood, raised rear deck, widened body, or obvious exterior packaging anomaly;
- custom body/chassis is allowed and expected;
- hidden internal scale fidelity is **not** required;
- cabin/front volume may conceal batteries, ECU, ignition electronics, motor controller, pumps, wiring, sensors, fuel hardware, etc. behind a visually accurate thin interior shell;
- boutique materials/processes are allowed if justified: precision machining, watchmaking-scale components, sapphire windows, advanced coatings, additive manufacturing, selective-fit parts;
- possible distant positioning is a $50k–$100k+ collector/mechanical-art product;
- far-future idea: multiple 1:18 GTE/OEM-style teams racing real micro-combustion cars live/online. This is **not current scope**.

The car is 1:18. The engine does not have to be a geometrically exact 1:18 copy of the corresponding full-size OEM engine.

## 3. Vehicle architecture families

### Ferrari / rear-mid-engine exotic

- 488-like exterior -> likely V8 theme;
- 296-like exterior -> likely V6 theme;
- internal engine architecture does not need to copy Ferrari;
- a 488-like car may use a compact 90-degree two-valve V8 with a small-block/model-engine packaging philosophy if that is easier than a literal Ferrari DOHC layout;
- cylinder count and sound character may matter aesthetically more than matching Ferrari's exact cam arrangement, valve count, injection architecture, bore/stroke, or accessory layout;
- flat-plane versus cross-plane V8 remains a later sound/firing-order decision, not a current assumption.

### Front-engine production/sports-car mule

Useful precedent:

- Honda Civic / K-series swap culture;
- Mazda Miata swaps;
- Mustang/Coyote/small-block packaging;
- Chevrolet small-block/LS-style swaps;
- motorcycle-engine swaps and compact sportbike engines.

Use this data for layout/topology and packaging practice: sump swaps, radiator relocation, accessory deletion, steering/header conflicts, gearbox fit, driveshaft/axle geometry, firewall/hood clearance. Do not blindly divide every full-size mechanical correlation by 18.

## 4. Scavenge different industries for different questions

| Precedent | What to use it for |
|---|---|
| Civic / Miata / Mustang / small-block swaps | packaging topology and relocation strategies |
| Ferrari / GTE / supercars | rear-mid-engine proportions, wheel/suspension/exhaust relationships |
| Ducati V4 / compact motorcycles | dense four-stroke mechanical packaging, oversquare layouts |
| Toyan / Cison / Conley / Micro Cirrus / Cox / historic model engines | miniature combustion, valves, ignition, lubrication, sealing |
| Jacob & Co / watchmaking / micro-mechanics | manufacture of tiny cranks, rods, pistons, gears; **not combustion validation** |
| tiny compressed-air / CO2 V engines | mechanical miniaturization precedent only; **not proof of combustion feasibility** |

Scale-specific physics still need our own simulation/measurement because surface-to-volume ratio, leakage fraction, heat transfer, lubrication, valve-flow Reynolds number, and clearances do not scale linearly.

## 5. 8.5 mm is not the maximum bore

The current ~8.5 mm bore engine is now treated as:

- the geometry already represented in the science stack;
- potentially an instrumented development mule / scale bridge;
- **not** an assumed production optimum;
- **not** an upper bore limit.

Larger bore may help:

- valve diameter and seat width;
- spark-plug boss packaging;
- port-fuel hardware;
- combustion-chamber roof area;
- cooling structure;
- head-thread strength;
- liner/head wall thickness;
- machining/metrology access;
- leakage as a fraction of trapped charge.

The next packaging study should explicitly test approximately:

`8.5, 9, 10, 11, 12, 13, 14, 15, 16 mm`

and stop where whole-car packaging or robust manufacturability becomes the real limit. Do not assume 16 mm will fit.

### Oversquare direction

Very oversquare geometry is allowed and may be useful because a large bore with a shorter stroke preserves head area while reducing crank throw, deck height, piston travel, mean piston speed, and crankcase size.

Exploratory examples only, not accepted designs:

- 8.5 x 5.0 mm;
- 10 x ~5.5 mm;
- 12 x ~6 mm;
- other ratios potentially approaching ~2:1 if chamber shape, piston guidance, heat transfer, compression ratio, and durability remain defensible.

Do not inherit automotive bore/stroke ratios automatically.

## 6. Cylinder count follows product theme more than exact OEM layout

Working rule:

> The body/theme may determine cylinder count; the physics and packaging determine the internal engine architecture.

Examples:

- 488-like boutique car -> V8;
- 296-like boutique car -> V6;
- front-engine engineering mule -> inline-4 may be easiest.

A future V12 is possible but **do not study it now**. Additional cylinders will strongly penalize bank length and likely force smaller bores.

## 7. Combustion direction changed, but HCCI work stays

Do **not** delete or invalidate existing DME/CH4 HCCI/SACI work. It remains useful for:

- autoignition/preignition risk;
- temperature/pressure sensitivity;
- mechanism validation;
- future SACI/HCCI modes;
- general combustion-model capability.

Pure HCCI is no longer required to be the production baseline. The project now prefers a combustion architecture with more direct ignition authority if packaging permits it.

Future downselect, **after packaging is understood**:

A. methanol/nitromethane + glow ignition  
B. methanol/nitromethane + electronic spark  
C. gasoline + electronic spark  
D. DME/CH4 + spark/SACI/HCCI as a research mode

Two-stroke remains parked for now.

Nitromethane/methanol is explicitly acceptable if it materially simplifies miniature combustion. Fuel-borne lubricant / splash / mist lubrication may simplify or eliminate a pressure-oil system, but this must be tested rather than assumed.

## 8. Spark packaging is credible enough to study seriously

Miniature-engine precedent includes roughly 10-40, 8-40, and smaller custom spark-plug classes. Treat an ~8-40-class package (~4 mm-class threaded body) as a realistic starting CAD envelope, with a smaller custom plug as an aggressive future case.

The question is no longer simply "is spark too large?" It is:

> Can the chosen bore/head package a useful plug boss, two valves, adequate bridge material, cooling, and assembly margin?

Start with one ignition element per cylinder. Do not add dual plugs unless CFD/combustion/head geometry gives a reason.

### Controlled-glow research concept

A future "smart glow" lane may study:

- low-thermal-mass element;
- PWM/current control;
- per-cylinder current/voltage sensing;
- resistance-derived heater temperature;
- temperature schedules for start/idle/high rpm.

This may reduce scatter but should not be presumed to have spark-like crank-angle authority. Diesel-industry ideas worth scavenging later include electronically regulated glow temperature, cylinder-selective control, pressure-sensing glow plugs, and cycle-to-cycle combustion-phasing correction. Do not import diesel common-rail hardware by default.

## 9. Fuel metering direction

Direct injection is **not** required and should have to earn its complexity.

Preferred early architecture to study:

`fuel reservoir -> regulation -> compact metering valve/carburetion -> short runner or common plenum -> intake valve -> cylinder`

The metering actuator may live remotely in the cabin/front, with only a small line/runner/nozzle near the engine. This matters because conventional automotive injector packages do not scale well while compact industrial/microfluidic electronic metering shows that remote small-volume dosing is plausible.

Port injection / premixed intake should be the baseline comparison before miniature direct injection.

## 10. Ferrari 488 GTE reference-mesh work from the design-pivot thread

A detailed Ferrari 488 GTE model package was supplied locally. Prior inspection reported:

- approximately 418 scene nodes;
- approximately 178 meshes;
- approximately 62 materials;
- visible wheel/chassis/cockpit/rear-engine-bay/suspension-adjacent detail;
- approximate full-size coordinate envelope ~4.73 m long x ~2.19 m wide x ~1.19 m high;
- normalized to 1:18: approximately **262.8 x 121.4 x 66.1 mm**.

Do not treat the decorative stock engine inside the model as authoritative Ferrari engineering CAD.

Useful source geometry is primarily:

- exterior silhouette;
- wheel/tire locations;
- axle reference;
- body/deck ceiling;
- cockpit-visible region;
- rear chassis/suspension intrusion;
- diffuser/exhaust region.

Hidden stock internals are not sacred because the eventual car uses a custom chassis.

### Third-party source archive / license caution

The supplied raw archive is **not committed** with this note because redistribution/license status was not established and it is ~68 MB.

Local filename used during study:

`unpacked-ferrari-488-gte.zip`

SHA-256:

`da74787efbc804fa706248858f170e9c291d7c2e0348e19a9a70f39e045ee6a4`

If exact source geometry is required and the archive is not present, reacquire/request it and verify provenance/hash before analysis.

## 11. Preserved visual/3D handoff assets

Generated inspection renders:

- `assets/2026-09-02/Ferrari_488_GTE_full_VTK.png`
- `assets/2026-09-02/Ferrari_488_GTE_rear_cutaway_top.png`
- `assets/2026-09-02/Ferrari_488_GTE_rear_cutaway_iso.png`

These are inspection renders, not dimensional proof by themselves.

Project-authored lightweight GLBs:

### `assets/2026-09-02/f488_gte_1_18_outer_envelope_proxy.glb`

Simple 1:18 bounding-envelope / coordinate-frame proxy using the reported ~262.8 x 121.4 x 66.1 mm outer envelope. **Not the Ferrari surface mesh; do not use for final collision decisions.**

### `assets/2026-09-02/v8_8p5x5_packaging_seed.glb`

Conceptual 90-degree V8 packaging seed with an 8.5 mm bore class, 5.0 mm stroke concept, four cylinders per bank, and crude crankcase/head/flywheel-motor-interface envelopes. **Not engineering CAD.** It exists only as a CARPACK/HEADPACK seed and should be replaced with parametric CadQuery solids.

## 12. Tool stack identified

### Trimesh

Use for mesh loading, scene hierarchy/transforms, sectioning, collision testing, spatial queries, and mesh exports.

### VTK

Use for independent visualization, cross-sections/cutaways, and screenshot verification.

### CadQuery + OpenCascade/OCP

Preferred headless parametric solid-geometry path for cylinders/liners, crankcase, heads, valve/seat/boss envelopes, ignition bosses, ports, booleans, STEP/BREP export.

### Blender

Useful later for game/model mesh cleanup, removing decorative stock components, transparent/cutaway views, and final visual rendering. Do not use Blender as the micron-scale dimensional source of truth.

### FreeCAD

Potentially useful for visible CAD inspection, assemblies, and later FEM/human inspection.

### OpenFOAM

Retain for later valve/port flow, mixture motion, combustion CFD, and wall/CHT work when those become decision-limiting.

### Structural FEA

Later add CalculiX, Code_Aster, FreeCAD FEM, or suitable commercial tooling for head/plug-thread stress, crank/rod stress, thermal distortion, bore/seat movement, and vibration/durability.

## 13. MCP direction

Do **not** install a pile of MCP servers before the underlying CLI/headless workflow is proven.

Preferred sequence:

1. reproduce CadQuery + trimesh + VTK workflow directly;
2. evaluate CadQuery MCP for parametric CAD interaction;
3. FreeCAD MCP for visible CAD/assemblies;
4. Blender MCP for mesh cleanup/rendering;
5. BeamNG automation/MCP later.

Review third-party MCP source before installation and record source/version/permissions/security implications. MCP should expose a working engineering tool, not substitute for one.

## 14. BeamNG direction

BeamNG is potentially valuable **later** as the vehicle-dynamics layer:

`microengine-rig -> validated torque/inertia/fuel/thermal maps -> vehicle model -> BeamNG -> gearing/diff/tires/handling/races`

Potential future stack:

- BeamNG.drive / BeamNG.tech;
- BeamNGpy;
- Lua/JBeam powertrain definitions;
- optional custom MCP wrapper.

BeamNG is not the combustion solver and should not replace Cantera/OpenFOAM/cycle modeling.

## 15. Next engineering gate: CARPACK / HEADPACK

The next major job should be packaging, not another broad combustion pivot.

Working names:

- `CARPACK`: whole-car legal-volume / powertrain packaging analysis;
- `HEADPACK`: parametric engine/head generator and head-specific packaging checks.

### CARPACK first milestone

1. Reacquire/import the detailed Ferrari mesh if available.
2. Normalize to 1:18 mm units and a documented coordinate frame.
3. Identify exterior hard envelope, wheel/tire keep-outs, axle centers, suspension/chassis intrusion, cockpit-visible region, rear deck ceiling, diffuser/exhaust region.
4. Remove/ignore decorative stock drivetrain where custom chassis makes it irrelevant.
5. Derive an approximate `LEGAL_POWERTRAIN_VOLUME`.
6. Reserve real allowances for structure, wheel/suspension motion, transmission/differential, exhaust, cooling, and assembly/manufacturing margin.

### HEADPACK first milestone

Generate crude but parametric:

- 90-degree V8;
- 120-degree V6;
- 2 valves/cylinder initially;
- cylinders/liners and pitch;
- crankcase/crank envelope;
- heads;
- valve heads/stems/seats;
- ignition boss;
- intake/exhaust port envelopes;
- cam/rocker/pushrod or SOHC envelope;
- flywheel/electric-assist interface;
- transmission placeholder.

Do not optimize horsepower yet.

### Bore sweep

At minimum:

`8.5 / 9 / 10 / 11 / 12 / 13 / 14 / 15 / 16 mm`

with several oversquare stroke ratios.

For each candidate report:

- displacement;
- bank length/width/height;
- total engine envelope;
- cylinder pitch;
- valve-size allowance;
- ignition-boss allowance;
- minimum body/chassis clearance;
- tire/suspension clearance;
- estimated wall/bridge margin;
- remaining support-system volume;
- first limiting collision / geometry.

Distinguish **ABSOLUTE GEOMETRIC FIT** from **ROBUST MANUFACTURABLE FIT**. A 0.1 mm non-intersection is not a successful design.

## 16. Why packaging comes before fuel/ignition downselect

Available head diameter may change which combustion system wins:

- if ~12–14 mm bores fit, spark and two-valve packaging becomes much easier;
- if geometry must stay near ~8.5 mm, glow or a smaller custom ignition element may gain value;
- if a remote metering valve can live elsewhere, electronic port fueling may be easier than expected;
- cooling and valvetrain choices depend on actual free volume.

Therefore do not lock nitro-vs-gasoline or glow-vs-spark until the first CAD packaging sweep exists.

## 17. Thermal work remains relevant

Keep the existing thermal RC, axial thermal-fit, warm-flow fixture, and sealing work.

Long-term chain:

`combustion/cycle -> local wall heat flux -> solid thermal field -> expansion/distortion -> hot clearance / valve-seat / bore geometry -> leakage & friction`

OpenFOAM can later contribute conjugate heat-transfer data; structural FEA can predict distortion/stress. The existing RC model remains screening until calibrated/replaced with measured or CFD-derived local thermal loads.

## 18. Electronics/support-system philosophy

Do not copy a full-size car accessory layout.

Likely simplifications:

- battery powered; no alternator unless later justified;
- electric assist motor can potentially serve as starter;
- coils/controllers/sensors can live remotely in front/cabin volumes;
- MAP may use a small pressure passage to a remotely mounted MEMS sensor;
- coolant/oil pumps exist only if thermal/lubrication analysis requires them;
- fuel-borne lubricant / splash / mist may be considered for model-engine fuels;
- conventional pump/filter/oil-gallery architecture is not assumed;
- wiring is an optimized micro harness, not a scaled automotive loom.

## 19. Evidence labels for the new work

Preserve the existing hierarchy:

**MEASURED EVIDENCE -> LITERATURE-DERIVED CALCULATION -> PROJECT MODEL RESULT -> INFERENCE**

For packaging add:

**SOURCE GEOMETRY -> DERIVED GEOMETRY -> PROXY/CONCEPT GEOMETRY**

Never present a game/model-kit mesh as Ferrari manufacturing CAD. Never present bounding-box fit as proof of valves, cooling, sealing, lubrication, assembly, or durability.

## 20. Resume checklist for any AI agent

1. Read this file.
2. Read current `PLAN.md`, `FINDINGS.md`, `GATES.md` and relevant cycle/thermal reports.
3. Do not delete/retune HCCI/DME work just because the product direction broadened.
4. Locate/reacquire the detailed Ferrari 488 GTE source mesh if exact collision geometry is required; verify hash/provenance.
5. Build CARPACK/HEADPACK using the smallest reproducible CadQuery + trimesh + VTK stack.
6. Use the lightweight GLBs only as proxies/seeds, never as final source geometry.
7. Run bore/package sweep before the broad fuel/ignition downselect.
8. Only after packaging compare methanol/nitro glow, methanol/nitro spark, gasoline spark, and DME/CH4 spark/SACI/HCCI.
9. BeamNG, detailed electronics, full CFD, and marketing renders follow the packaging gate.

## 21. Repository organization

A separate whole-car repo such as `microcar-platform` / `microcar-gte` may eventually be cleaner, with `microengine-rig` as the upstream engine-physics dependency.

That split was discussed but deliberately **not executed yet**. For now this direction note lives in `microengine-rig` so no information is lost while the architecture is still moving.

---

## Bottom line

The main design sequence is now:

> **What is the largest robust multicylinder four-stroke package that fits inside a visually exact 1:18 exterior?**
>
> **Then, given the head volume we actually have, what controllable fuel/ignition architecture is the simplest reliable choice?**

The existing engine-science work remains the foundation. Packaging is the next major decision gate.