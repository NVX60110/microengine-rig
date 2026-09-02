"""Validate the provenance-only Galway Burke validation-plot catalog.

This intentionally does not download, OCR, digitize, or create experimental
rows.  It checks the metadata needed before a separately labeled digitization
can be reviewed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/burke2015/validation_plots.json"
TEMPLATE = ROOT / "data/burke2015/digitized_points_template.csv"
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")


def validate_manifest(path: Path = MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["status"] == "plot_catalog_only"
    assert manifest["ingestion_policy"]["canonical_records_csv_modified"] is False
    assert manifest["ingestion_policy"]["plot_points_ingested"] is False
    source_ids = set()
    for source in manifest["sources"]:
        source_id = source["source_id"]
        assert source_id not in source_ids, source_id
        source_ids.add(source_id)
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https" and parsed.netloc == "c3.universityofgalway.ie"
        assert SHA256_RE.fullmatch(source["sha256"]), source_id
        assert source["download_bytes"] > 0
        assert source["page_count"] == max(panel["page"] for panel in source["panels"])
        pages = {(panel["page"], panel["panel"]) for panel in source["panels"]}
        assert len(pages) == len(source["panels"])
        for panel in source["panels"]:
            assert panel["mixture_label"]
            assert panel["equivalence_ratio"] > 0
            assert panel["pressure_atm"] > 0
            assert panel["y_scale"] in {"linear", "log10"}
    return manifest


def validate_template(path: Path = TEMPLATE) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    required = {
        "source_pdf_url", "source_pdf_sha256", "source_pdf_page", "source_panel",
        "temperature_K", "pressure_bar", "ignition_delay_s", "ignition_target",
        "ignition_type", "facility", "provenance", "x_axis_value",
        "x_axis_definition", "x_axis_units", "x_axis_scale", "y_axis_definition",
        "y_axis_units", "y_axis_scale", "digitization_method",
        "digitization_software", "digitization_uncertainty_fraction",
        "point_lineage", "point_status",
    }
    assert required.issubset(fields), sorted(required - set(fields))
    assert not rows, "The template must not contain unreviewed point values."
    return fields


def verify_file_hash(path: Path, expected_sha256: str) -> bool:
    """Verify a locally cached source PDF, without requiring it in Git."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return digest == expected_sha256.upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    args = parser.parse_args()
    manifest = validate_manifest(args.manifest)
    validate_template(args.template)
    print(f"validated {len(manifest['sources'])} source PDFs and "
          f"{sum(len(source['panels']) for source in manifest['sources'])} panels; "
          "no point rows ingested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
