# Burke Mech_56.54 package

This directory contains the three raw CHEMKIN-format files published by the
University of Galway for the methane/DME mechanism associated with Burke et al.,
*Combustion and Flame* 162 (2015) 315--330, DOI
[`10.1016/j.combustflame.2014.08.014`](https://doi.org/10.1016/j.combustflame.2014.08.014).

| file | public source | SHA-256 |
|---|---|---|
| `56.54_c3_chem.dat.txt` | [reaction mechanism](https://universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/ethers/56.54_c3_chem.dat.txt) | `C18CEFE98BDBEF7568DAA50B72C4A3871653FFABCA2E371834A151C61FD8BD89` |
| `56.54_therm.dat.txt` | [thermodynamics](https://universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/ethers/56.54_therm.dat.txt) | `E4E4866D21CB80C1EE636C3829BA2B48DD7F4F9E899676E43FDC1030144FA3DD` |
| `56.54_tran.dat.txt` | [transport](https://universityofgalway.ie/media/researchcentres/combustionchemistrycentre/files/mechanismdownloads/ethers/56.54_tran.dat.txt) | `E9412904407B917CC17EA2B71FA87AA038AAC1DEA42F6323C21483CE09DE2D1B` |

Hashes above are SHA-256 of the exact LF-normalized bytes committed to Git.
Windows worktrees may materialize these text files with CRLF; the provenance
test normalizes CRLF to LF before checking the committed-byte digest.

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
  --alias CH4=ch4 --alias CH3OCH3=ch3och3 --alias O2=o2 --alias N2=n2
```

If a future CSV uses the readable `DME` synonym instead of the canonical
`CH3OCH3` schema token, add `--alias DME=CH3OCH3`. The gate follows that alias
to the explicit mechanism mapping above; it never changes the CSV schema.

Cantera emits two NASA-polynomial continuity warnings for the source `oh*` and
`ch*` records at 1000 K. The mechanism loads, validates, and evaluates with
Cantera 3.2; these source-data warnings are retained in the validation notes
and are not silently corrected.
