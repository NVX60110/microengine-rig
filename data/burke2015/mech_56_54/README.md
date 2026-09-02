# Burke Mech_56.54 package

This directory contains the three raw CHEMKIN-format files published by the
University of Galway for the methane/DME mechanism associated with Burke et al.,
*Combustion and Flame* 162 (2015) 315--330, DOI
[`10.1016/j.combustflame.2014.08.014`](https://doi.org/10.1016/j.combustflame.2014.08.014).

| file | public source | SHA-256 |
|---|---|---|
| `56.54_c3_chem.dat.txt` | [reaction mechanism](https://universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/ethers/56.54_c3_chem.dat.txt) | `972E24FA01C18A0976C8BB3F8DDD1CD42202F1E0C21CC76E4B37A99843D7CEE0` |
| `56.54_therm.dat.txt` | [thermodynamics](https://universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/ethers/56.54_therm.dat.txt) | `16EC58F97B310EC9AFD49769910F788D49743E4F917A7A5F90FAE99CF0118A7C` |
| `56.54_tran.dat.txt` | [transport](https://universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/ethers/56.54_tran.dat.txt) | `D349C4B3D13A19ADD614E1424C4DDDF3EBC6EF763B888955E265062ADD35DF90` |

The raw files are preserved unchanged. Run
`python scripts/convert_burke56_54.py` from the repository root to create the
Cantera 3.2 YAML at `mechanisms/burke_mech_56_54.yaml`. The converter removes
only known package artefacts in a temporary thermo input: duplicate NASA
records for `hoch2o2h`, `hoch2o2`, and `och2o2h`; two unused malformed C5
records; and decorative separator lines. It does not alter the reaction file.

The resulting phase contains 113 species and 710 reactions. The source uses
lower-case species names, so Burke CSV runs must pass explicit aliases when a
dataset uses the project's upper-case convention, for example:

```bash
python burke2015_gate.py \
  --mechanism mechanisms/burke_mech_56_54.yaml \
  --data data/burke2015/points.csv \
  --alias CH4=ch4 --alias DME=ch3och3 --alias O2=o2 --alias N2=n2
```

Cantera emits two NASA-polynomial continuity warnings for the source `oh*` and
`ch*` records at 1000 K. The mechanism loads, validates, and evaluates with
Cantera 3.2; these source-data warnings are retained in the validation notes
and are not silently corrected.
