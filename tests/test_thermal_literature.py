import csv
import unittest
from pathlib import Path

from scripts.analyze_thermal_literature import derive


class ThermalLiteratureTests(unittest.TestCase):
    def test_current_ledger_is_provenance_complete_and_has_no_paired_claim(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "data/thermal/literature_sources.csv").open(newline="", encoding="utf-8") as handle:
            sources = list(csv.DictReader(handle))
        with (root / "data/thermal/literature_measurements.csv").open(newline="", encoding="utf-8") as handle:
            measurements = list(csv.DictReader(handle))
        result = derive(sources, measurements)
        self.assertEqual(result["source_count"], 13)
        self.assertEqual(result["measurement_count"], 20)
        self.assertEqual(result["paired_temperature_count"], 0)
        self.assertEqual(result["unpaired_temperature_rows"], 0)
        self.assertTrue(all(row["source_id"] for row in sources))
        self.assertTrue(all(row["transferability"] != "direct_model_prior" for row in measurements))

        # Ringed coefficients and unpaired near-scale wall temperatures are
        # evidence context only; they must not become a clearance prior.
        self.assertTrue(any(row["transferability"] == "ringed_architecture_only" for row in measurements))
        self.assertTrue(any(row["transferability"] == "near_scale_thermal_magnitude_only" for row in measurements))
        self.assertTrue(all(row["classification"] == "literature_reported" for row in measurements))

    def test_complete_local_pair_derives_temperature_delta_and_normalized_ratio(self):
        sources = [{"source_id": "s1"}]
        measurements = [{
            "measurement_id": "m1", "source_id": "s1", "engine_id": "e1",
            "quantity": "paired", "location": "piston_skirt", "value": "",
            "unit": "K", "uncertainty": "", "ambient_temperature_K": "300",
            "piston_temperature_K": "500", "liner_temperature_K": "400",
            "transferability": "screening", "source_locator": "table-1", "notes": "test",
        }]
        result = derive(sources, measurements)
        metrics = {row["metric"]: row["value"] for row in result["derived"]}
        self.assertAlmostEqual(metrics["piston_minus_liner_temperature"], 100.0)
        self.assertAlmostEqual(metrics["(liner_minus_ambient)/(piston_minus_ambient)"], 0.5)

    def test_unknown_source_reference_fails_loudly(self):
        with self.assertRaises(ValueError):
            derive([{"source_id": "s1"}], [{"measurement_id": "m1", "source_id": "missing", "value": "1"}])


if __name__ == "__main__":
    unittest.main()
