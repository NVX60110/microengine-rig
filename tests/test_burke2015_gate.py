from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import unittest

from burke2015_gate import load_burke_csv, _select_delay


class _Result:
    delay_dPdt_s = 0.001
    delay_dTdt_s = 0.002


class Burke2015GateTests(unittest.TestCase):
    def _write(self, directory: str, rows: list[dict[str, str]]) -> Path:
        path = Path(directory) / "points.csv"
        fieldnames = [
            "temperature_K", "pressure_bar", "ignition_delay_s",
            "equivalence_ratio", "composition_json", "ignition_target",
            "ignition_type", "facility", "mixture_label", "provenance",
            "ignition_delay_uncertainty_fraction", "temperature_uncertainty_K",
            "pressure_uncertainty_bar", "notes",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_valid_row_preserves_metadata(self):
        with TemporaryDirectory() as directory:
            path = self._write(directory, [{
                "temperature_K": "900",
                "pressure_bar": "40",
                "ignition_delay_s": "0.0015",
                "equivalence_ratio": "1.0",
                "composition_json": json.dumps({"CH4": 0.04, "CH3OCH3": 0.01, "O2": 0.20, "N2": 0.75}),
                "ignition_target": "pressure",
                "ignition_type": "d/dt max",
                "facility": "example_shock_tube",
                "mixture_label": "80CH4_20DME",
                "provenance": "supplement table X row 1",
                "ignition_delay_uncertainty_fraction": "0.10",
                "temperature_uncertainty_K": "5",
                "pressure_uncertainty_bar": "0.5",
                "notes": "test only",
            }])
            points, metadata, rejected = load_burke_csv([path])
            self.assertEqual(len(points), 1)
            self.assertEqual(rejected, [])
            label = points[0].source_file
            self.assertEqual(metadata[label]["facility"], "example_shock_tube")
            self.assertAlmostEqual(metadata[label]["ignition_delay_uncertainty_fraction"], 0.10)

    def test_bad_row_is_rejected_and_zero_points_fail(self):
        with TemporaryDirectory() as directory:
            path = self._write(directory, [{
                "temperature_K": "900",
                "pressure_bar": "40",
                "ignition_delay_s": "-1",
                "equivalence_ratio": "1.0",
                "composition_json": json.dumps({"CH4": 1}),
                "ignition_target": "pressure",
                "ignition_type": "d/dt max",
                "facility": "fixture",
                "mixture_label": "pure_CH4",
                "provenance": "test",
            }])
            with self.assertRaisesRegex(RuntimeError, "Zero Burke CSV points"):
                load_burke_csv([path])

    def test_delay_selection_does_not_substitute_criterion(self):
        from mechanism_gate import ExperimentalPoint

        pressure = ExperimentalPoint(900, 40, 0.001, 1.0, {"CH4": 1}, "x", "pressure", "d/dt max")
        temperature = ExperimentalPoint(900, 40, 0.001, 1.0, {"CH4": 1}, "x", "temperature", "d/dt max")
        ohstar = ExperimentalPoint(900, 40, 0.001, 1.0, {"CH4": 1}, "x", "OH*", "onset")
        self.assertEqual(_select_delay(pressure, _Result()), 0.001)
        self.assertEqual(_select_delay(temperature, _Result()), 0.002)
        self.assertIsNone(_select_delay(ohstar, _Result()))


if __name__ == "__main__":
    unittest.main()
