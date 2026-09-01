# Mechanism provenance

Mechanisms are versioned model inputs, not interchangeable libraries. Preserve
source, conversion command, active pressure-rate choices, validation range, and
license information with every result.

## Zhao 2008 DME skeleton and parent

Public mirror used: `jiweiqi/CollectionOfMechanisms`, commit current at the
2026-09-01 retrieval. Repository license: MIT. Original mechanism citation:

Zhao Z, Chaos M, Kazakov A, Dryer FL. *Thermal decomposition reaction and a
comprehensive kinetic model of dimethyl ether.* International Journal of
Chemical Kinetics 2008;40:1-18. DOI `10.1002/kin.20285`.

```bash
git clone --depth 1 https://github.com/jiweiqi/CollectionOfMechanisms.git mechs

python -m cantera.ck2yaml \
  --input=mechs/ethers/methoxymethane_DME/zhao2008/sk39/chem.inp \
  --thermo=mechs/ethers/methoxymethane_DME/zhao2008/sk39/therm.dat \
  --transport=mechs/ethers/methoxymethane_DME/zhao2008/sk39/tran.dat \
  --output=mechanisms/dme_zhao_sk39.yaml --permissive

python -m cantera.ck2yaml \
  --input=mechs/ethers/methoxymethane_DME/zhao2008/kin20285-chem.inp \
  --transport=mechs/ethers/methoxymethane_DME/zhao2008/kin20285-tran.dat \
  --output=mechanisms/dme_zhao_full.yaml --permissive
```

Both conversions use
`explicit-third-body-duplicates: mark-duplicate` in the phase entry to preserve
the source reactions Cantera identifies as overlapping third-body forms.

- sk39: 39 species, 175 reactions.
- full: 55 species, 290 reactions.

The full source warns that DME and ethanol decomposition rates are
pressure-dependent and requires choosing a pressure-appropriate Arrhenius fit.
The distributed source activates the 1-atm DME decomposition rate. That choice
has not been audited for 25-90 bar engine states. Do not call the full file a
truth mechanism until it is.

`dme_zhao_sk39.yaml` is identical in species/equations/rates to the Beta2.2-2.4
file formerly named `dme_luo_sk39.yaml`; that earlier attribution was wrong.

## LLNL DME 2004

Official source: <https://combustion.llnl.gov/mechanisms/dimethyl-ether>

```bash
python -m cantera.ck2yaml --input=dme_24_mech.txt \
  --thermo=dme_24_therm.txt --transport=dme_24_tran_dat.txt \
  --output=llnl_dme_2004.yaml --permissive
```

Result: 79 species, 660 reactions. The phase uses
`explicit-third-body-duplicates: mark-duplicate` for two source overlaps.
Verify LLNL redistribution terms before republishing beyond this private study.

## n-heptane acceptance controls

From `jiweiqi/CollectionOfMechanisms/n-Heptane_C7H16/`:

- Nordin 41 species / 168 reactions: experimental positive control.
- Peters 21 species: LTC negative control.

Experimental data:

```bash
git clone --depth 1 https://github.com/pr-omethe-us/ChemKED-database.git ckdb
```

Beta2.5 uses the Ciezki/Adomeit 1993 and Fieweger 1997 n-heptane shock-tube
sets because they declare pressure maximum-dP/dt ignition. The public ChemKED
database contained no DME dataset at retrieval time.

## Acceptance sequence

1. Load and verify phase/species/reaction count.
2. Run `mechanism_gate.py parent` when a parent exists.
3. Run `mechanism_gate.py chemked` wherever criterion-compatible data exists.
4. Record all rejected/failed datapoints; zero loaded is a hard failure.
5. Run the same engine points across independent lineages and report the
   envelope and transition interval—not a single preferred number.
