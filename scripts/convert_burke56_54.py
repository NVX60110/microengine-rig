#!/usr/bin/env python3
"""Convert the public Galway Mech_56.54 CHEMKIN package for Cantera 3.2.

The distributed thermo file contains three duplicate NASA records, two unused
C5 records that do not parse as NASA7, and a decorative separator.  The raw
files are preserved unchanged under ``data/burke2015/mech_56_54``; this script
only removes those known source-package artefacts in a temporary input before
calling Cantera's ``ck2yaml`` converter.  It then removes the generated date
line so the tracked YAML is reproducible.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "burke2015" / "mech_56_54"
CHEM = SOURCE / "56.54_c3_chem.dat.txt"
THERMO = SOURCE / "56.54_therm.dat.txt"
TRAN = SOURCE / "56.54_tran.dat.txt"
OUTPUT = ROOT / "mechanisms" / "burke_mech_56_54.yaml"

# The first occurrence of each duplicate is retained.  These C5 records are
# not referenced by the downloaded C3 reaction mechanism and are malformed in
# the source thermo package, so omitting them is explicit and auditable.
DUPLICATE_NAMES = {"hoch2o2h", "hoch2o2", "och2o2h"}
UNUSED_MALFORMED_NAMES = {"1c5h91-3", "c5h9-5"}


def _header_name(line: str) -> str | None:
    if not line or line[0].isspace() or line.lstrip().startswith("!"):
        return None
    token = line.split(maxsplit=1)[0].lower()
    if token in {"thermo", "end"}:
        return None
    return token


def _clean_thermo(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    seen: set[str] = set()
    omitted: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("!"):
            omitted.append("decorative separator")
            index += 1
            continue
        name = _header_name(line)
        if name in DUPLICATE_NAMES or name in UNUSED_MALFORMED_NAMES:
            if name in DUPLICATE_NAMES and name not in seen:
                seen.add(name)
                result.extend(lines[index : index + 4])
            else:
                omitted.append(name or "unknown block")
            index += 4
            continue
        result.append(line)
        index += 1
    return "".join(result), omitted


def _make_deterministic_yaml() -> None:
    lines = OUTPUT.read_text(encoding="utf-8").splitlines(keepends=True)
    OUTPUT.write_text(
        "".join(line for line in lines if not line.lower().startswith("date:")),
        encoding="utf-8",
    )


def main() -> None:
    converter = shutil.which("ck2yaml")
    if converter is None:
        raise SystemExit("ck2yaml not found; install Cantera 3.2 first")
    if not all(path.exists() for path in (CHEM, THERMO, TRAN)):
        raise SystemExit("missing raw Galway Mech_56.54 package files")

    cleaned, omitted = _clean_thermo(THERMO.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="burke56_54_") as temp_dir:
        temp_thermo = Path(temp_dir) / THERMO.name
        temp_thermo.write_text(cleaned, encoding="utf-8")
        command = [
            converter,
            "--input",
            str(CHEM),
            "--thermo",
            str(temp_thermo),
            "--transport",
            str(TRAN),
            "--output",
            str(OUTPUT),
            "--name",
            "Burke_Mech_56_54",
        ]
        completed = subprocess.run(command, check=True, text=True)
    _make_deterministic_yaml()
    print(f"converted {OUTPUT.relative_to(ROOT)}")
    print(f"omitted source artefacts: {', '.join(omitted)}")


if __name__ == "__main__":
    main()
