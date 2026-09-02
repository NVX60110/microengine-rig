import csv
import hashlib
import json
import unittest
from pathlib import Path

from scripts.validate_burke_validation_plots import (
    MANIFEST,
    TEMPLATE,
    validate_manifest,
    validate_template,
    verify_file_hash,
)


ROOT = Path(__file__).resolve().parents[1]


class BurkeValidationPlotCatalogTests(unittest.TestCase):
    def test_catalog_is_provenance_only(self):
        manifest = validate_manifest()
        self.assertEqual(manifest["status"], "plot_catalog_only")
        self.assertFalse(manifest["ingestion_policy"]["canonical_records_csv_modified"])
        self.assertFalse(manifest["ingestion_policy"]["canonical_burke_points_added"])
        self.assertEqual(len(manifest["sources"]), 3)
        self.assertEqual(sum(len(source["panels"]) for source in manifest["sources"]), 23)

    def test_template_is_empty_and_contains_gate_plus_digitization_fields(self):
        fields = validate_template()
        self.assertIn("ignition_delay_s", fields)
        self.assertIn("source_pdf_page", fields)
        self.assertIn("digitization_uncertainty_fraction", fields)
        with TEMPLATE.open(newline="", encoding="utf-8") as handle:
            self.assertEqual(list(csv.DictReader(handle)), [])

    def test_recorded_hashes_are_well_formed_and_helper_matches_bytes(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        sample = b"a Galway source snapshot\n"
        expected = hashlib.sha256(sample).hexdigest().upper()
        sample_path = ROOT / "tests" / ".burke_validation_hash_sample"
        try:
            sample_path.write_bytes(sample)
            self.assertTrue(verify_file_hash(sample_path, expected))
            self.assertFalse(verify_file_hash(sample_path, "0" * 64))
        finally:
            sample_path.unlink(missing_ok=True)
        for source in manifest["sources"]:
            self.assertRegex(source["sha256"], r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
