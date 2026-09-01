# Mechanism provenance

Mechanism files are **not committed** — they are large, and regenerating them from the released sources preserves provenance. Do not substitute a newer mechanism without updating this file.

## Sources

All obtained from `jiweiqi/CollectionOfMechanisms` (public GitHub, ~90 MB):

```bash
git clone --depth 1 https://github.com/jiweiqi/CollectionOfMechanisms.git mechs
```

## DME — Zhao et al. 2008 (Princeton), skeletal 39 species

Path: `mechs/ethers/methoxymethane_DME/zhao2008/sk39/`

```bash
python -m cantera.ck2yaml --input=chem.inp --thermo=therm.dat \
    --transport=tran.dat --output=dme_sk39.yaml --permissive
```

Then add to the phase entry to suppress the HCOOH third-body duplicate warning:

```yaml
  explicit-third-body-duplicates: mark-duplicate
```

Result: **39 species, 175 reactions.** Contains CH3OCH3, CH4, H2 and C2 species, so DME/methane and DME/hydrogen blends are testable within one consistent kinetic model. Does **not** contain CH3OH.

> Caveat carried from Beta 2.2: this skeleton's YAML cites a turbulent DME jet-flame paper. Treat as a trend model. However, FINDINGS §2.2 establishes that it reproduces its parent's NTC to within 1%.

## DME — Zhao et al. 2008, full parent, 55 species

Path: `mechs/ethers/methoxymethane_DME/zhao2008/`

```bash
python -m cantera.ck2yaml --input=kin20285-chem.inp \
    --transport=kin20285-tran.dat --output=dme_zhao_full.yaml --permissive
```

Same duplicate-flag edit required. Result: **55 species, 290 reactions.**

> The source header warns that several DME and ethanol decomposition reactions are pressure-dependent and that the user must select rates appropriate to the applied pressure range. Not yet audited for our 25–90 bar range.

## n-heptane — validation reference

Path: `mechs/n-Heptane_C7H16/`

- `Nordin_42s_168r_1998/mech_41s168r.yaml` — **41 sp, 168 rxn. Validated: median 1.53× vs experiment, 85% within 2×.** Fuel species `C7H16`.
- `Peters2002/Peters30/chem_peters.yaml` — 21 sp. **Fails LTC by 154×.** Retained only as a negative control for the acceptance gate.
- `llnl_v3.1/nc7_ver3.1_mech.yaml` — 631 sp, reference, slow (~6 s load).

## Experimental data

```bash
git clone --depth 1 https://github.com/pr-omethe-us/ChemKED-database.git ckdb
```

ChemKED/ReSpecTh format. Contains n-heptane (Ciezki 1993, Fieweger 1997, and 14 other sets), n-pentane, butanols, toluene, methyl esters. **No DME.**

Direct DME data requires ReSpecTh registration: https://respecth.elte.hu — free, manual verification, JS-gated so not scriptable.

## Gotchas

- `nDodecane_Reitz.yaml` (bundled with Cantera) uses a **Redlich-Kwong** equation of state and must be rebuilt as ideal-gas before `IdealGasReactor` accepts it. Handled in `model/microengine_v3.py`.
- The two DME mechanisms use different capitalisation for the methane partner: `CH4` with the Zhao lineage, `ch4` with LLNL.
- ChemKED `equivalence-ratio` is a **scalar**, while `temperature`, `pressure` and `ignition-delay` are **lists**. Parsing it as a list throws, and a bare `except` will silently discard the entire dataset.
