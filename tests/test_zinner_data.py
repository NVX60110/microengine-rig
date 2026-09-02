import csv
import json
import unittest

from scripts.validate_zinner_data import CSV_PATH, EXPECTED_COUNTS, STATUS_PATH, validate


class ZinnerDataTests(unittest.TestCase):
    def test_exact_counts_and_mapping(self):
        rows = validate()
        self.assertEqual(len(rows), 167)
        counts = {number: 0 for number in EXPECTED_COUNTS}
        for row in rows:
            counts[int(row["mixture_number"])] += 1
        self.assertEqual(counts, EXPECTED_COUNTS)
        self.assertEqual(sum(row["mixture_label"] == "80CH4_20DME" for row in rows), 77)
        self.assertEqual(sum(row["mixture_label"] == "60CH4_40DME" for row in rows), 90)

    def test_original_adjusted_and_correlation_fields_are_preserved(self):
        with CSV_PATH.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        fields = set(rows[0])
        for field in (
            "temperature_adjusted_K", "pressure_adjusted_atm", "ignition_delay_us",
            "pressure_original_atm", "temperature_original_K",
            "high_temperature_correlation_us", "low_temperature_correlation_us",
            "provenance",
        ):
            self.assertIn(field, fields)
        self.assertTrue(any(row["low_temperature_correlation_us"] for row in rows))
        self.assertTrue(any(row["high_temperature_correlation_us"] for row in rows))

    def test_status_is_recovered_but_not_burke_complete(self):
        status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "recovered_local_attachment")
        self.assertEqual(status["rows_ingested"], 167)
        self.assertEqual(status["data_classification"], "measured_zinner_shock_tube_table")
        self.assertIn("complete Burke", status["provenance_policy"])


if __name__ == "__main__":
    unittest.main()
