"""Validate the provenance and numeric invariants of Zinner table extracts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "zinner2008" / "shock_tube_tabulated.csv"
STATUS_PATH = ROOT / "data" / "zinner2008" / "source_status.json"
REQUIRED = {
    "record_id", "mixture_number", "mixture_label", "ch4_volume_fraction",
    "dme_volume_fraction", "equivalence_ratio", "temperature_adjusted_K",
    "pressure_adjusted_atm", "ignition_delay_us", "pressure_original_atm",
    "temperature_original_K",
    "adjustment_status", "ignition_target",
    "ignition_type", "facility", "source_instrument", "provenance", "notes",
}
EXPECTED_COUNTS = {1: 23, 2: 17, 3: 19, 4: 18, 5: 24, 6: 20, 7: 25, 8: 21}
MIXTURE = {
    1: ("80CH4_20DME", 0.80, 0.20, 2.0), 2: ("80CH4_20DME", 0.80, 0.20, 1.0),
    3: ("80CH4_20DME", 0.80, 0.20, 0.5), 4: ("80CH4_20DME", 0.80, 0.20, 0.3),
    5: ("60CH4_40DME", 0.60, 0.40, 2.0), 6: ("60CH4_40DME", 0.60, 0.40, 1.0),
    7: ("60CH4_40DME", 0.60, 0.40, 0.5), 8: ("60CH4_40DME", 0.60, 0.40, 0.3),
}

def load_rows(path: Path = CSV_PATH) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing required fields: {sorted(missing)}")
        return list(reader)

def validate(path: Path = CSV_PATH, status_path: Path = STATUS_PATH) -> list[dict[str, str]]:
    rows = load_rows(path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if len({row["record_id"] for row in rows}) != len(rows):
        raise ValueError("record_id values are not unique")
    counts = {number: 0 for number in EXPECTED_COUNTS}
    for row in rows:
        if not all(row[name].strip() for name in REQUIRED):
            raise ValueError(f"blank required value in {row.get('record_id')!r}")
        number = int(row["mixture_number"])
        if number not in MIXTURE:
            raise ValueError(f"unexpected mixture number: {number}")
        label, ch4_expected, dme_expected, phi_expected = MIXTURE[number]
        counts[number] += 1
        if row["mixture_label"] != label:
            raise ValueError(f"wrong mixture label: {row['record_id']}")
        if abs(float(row["ch4_volume_fraction"]) - ch4_expected) > 1e-9 or abs(float(row["dme_volume_fraction"]) - dme_expected) > 1e-9:
            raise ValueError(f"wrong blend fractions: {row['record_id']}")
        if abs(ch4_expected + dme_expected - 1.0) > 1e-9 or abs(float(row["equivalence_ratio"]) - phi_expected) > 1e-9:
            raise ValueError(f"wrong mixture metadata: {row['record_id']}")
        if float(row["temperature_adjusted_K"]) <= 0 or float(row["pressure_adjusted_atm"]) <= 0 or float(row["temperature_original_K"]) <= 0 or float(row["pressure_original_atm"]) <= 0 or float(row["ignition_delay_us"]) <= 0:
            raise ValueError(f"nonpositive table value: {row['record_id']}")
        populated = bool(row["high_temperature_correlation_us"].strip()) + bool(row["low_temperature_correlation_us"].strip())
        if populated != 1:
            raise ValueError(f"exactly one correlation column must be populated: {row['record_id']}")
        if "Zinner 2008" not in row["provenance"] or "TABULATED DATA" not in row["provenance"] or "printed p." not in row["provenance"] or "PDF p." not in row["provenance"]:
            raise ValueError(f"missing thesis/page provenance: {row['record_id']}")
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"row counts by mixture disagree: {counts}")
    if status["rows_ingested"] != len(rows):
        raise ValueError("source_status.json row count disagrees with CSV")
    return rows

if __name__ == "__main__":
    print(f"validated {len(validate())} Zinner rows")
