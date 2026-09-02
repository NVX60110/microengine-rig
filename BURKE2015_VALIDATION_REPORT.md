# Burke 2015 DME/CH4 validation lane

Status: **mechanism package recovered and converted; direct experimental gate
blocked pending point-level data**.

## What was recovered

The University of Galway [mechanism-download page](https://universityofgalway.ie/combustionchemistrycentre/mechanismdownloads/)
provides the reaction, thermodynamic, and transport files associated with the
Burke et al. paper, *Combustion and Flame* 162 (2015) 315--330,
[DOI 10.1016/j.combustflame.2014.08.014](https://doi.org/10.1016/j.combustflame.2014.08.014).
The raw files are preserved under
[`data/burke2015/mech_56_54/`](data/burke2015/mech_56_54/), including SHA-256
hashes and the exact source URLs.

`scripts/convert_burke56_54.py` converts those CHEMKIN files with Cantera 3.2's
`ck2yaml`. The source thermo file has duplicate NASA records, decorative
separator lines, and two unused malformed C5 records. The converter removes
only those known records in a temporary input; raw source files are untouched.
The resulting [`mechanisms/burke_mech_56_54.yaml`](mechanisms/burke_mech_56_54.yaml)
contains 113 species and 710 reactions and loads with Cantera 3.2.0.

The source package uses lower-case names (`ch4`, `ch3och3`, `o2`, `n2`). Burke
CSV runs use the canonical upper-case `CH3OCH3` schema token and pass explicit
mechanism aliases; the package README gives the exact command. A readable
`DME` token remains an optional alias to canonical `CH3OCH3`, and the gate
follows that two-step mapping. The smoke test confirms
the required fuel, oxidizer, radical, and product species and evaluates a
20-bar, 1000-K state with mixture-averaged transport. Two source NASA
polynomial continuity warnings (`oh*`, `ch*` at 1000 K) are retained rather
than silently corrected.

## Direct experimental data status

The bounded acquisition search checked the Galway page and package, paper and
accepted-manuscript mirrors, publisher metadata/API, and public mechanism/data
indexes. It did not recover the original numeric ignition-delay table or a
machine-readable supplementary point file. The paper's figures and searchable
text confirm the scope (pure CH4, pure DME, 80/20 and 60/40 blends, multiple
shock tubes and an RCM, approximately 600--1600 K and 7--41 atm), but those
facts are not point-level validation rows.

Accordingly:

- `data/burke2015/points.csv` has not been created or populated;
- `records.csv` and the canonical Cantera model were not modified;
- `burke2015_gate.py` was not run against fabricated or graph-estimated data;
- no usable-point, factor-2, factor-3, low-temperature, mixture, pressure, or
  facility metrics are claimed.

The direct gate remains ready for an original table or a separately named
digitized dataset. If digitization becomes necessary, every row must retain
figure/page provenance and an explicit digitization uncertainty, and OH/OH*
criteria must remain unsupported until a matching diagnostic is implemented.

## Next bounded action

Request the supplementary point file from the Burke/Curran group or the
University of Galway repository contact. If no original file is released,
digitize only the project-relevant 80/20 and 60/40 curves with a declared
uncertainty and keep that dataset separate from original measured tables. Then
run `burke2015_gate.py` for Zhao sk39, Zhao full, LLNL79, and this recovered
Mech_56.54 phase with explicit species aliases and the experiment's own
ignition criterion.
