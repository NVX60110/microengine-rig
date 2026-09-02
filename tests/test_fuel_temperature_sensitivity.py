import unittest
from unittest.mock import patch

from mechanism_gate import IgnitionResult
from scripts.fuel_temperature_sensitivity import (
    MECHANISMS,
    TEMPERATURES_K,
    _non_monotonic,
    _slopes,
    run_campaign,
)


class FuelTemperatureSensitivityTests(unittest.TestCase):
    def test_signed_s_and_nonmonotonic_detection(self):
        points = [
            {"temperature_K": 875, "delay_s": 4e-3, "status": "ignited"},
            {"temperature_K": 925, "delay_s": 3e-3, "status": "ignited"},
            {"temperature_K": 975, "delay_s": 3.5e-3, "status": "ignited"},
        ]
        endpoint, local = _slopes(points)
        self.assertLess(endpoint, 0.0)
        self.assertEqual(len(local), 2)
        self.assertTrue(_non_monotonic(points))

    def test_missing_point_does_not_become_physical_nonignition_slope(self):
        points = [
            {"temperature_K": 875, "delay_s": None, "status": "no_ignition"},
            {"temperature_K": 925, "delay_s": 3e-3, "status": "ignited"},
            {"temperature_K": 975, "delay_s": 2e-3, "status": "ignited"},
        ]
        endpoint, local = _slopes(points)
        self.assertIsNone(endpoint)
        self.assertEqual(len(local), 1)
        self.assertIsNone(_non_monotonic(points))

    @patch("scripts.fuel_temperature_sensitivity.constant_volume_ignition")
    def test_campaign_records_strict_criterion_and_common_grid(self, detector):
        detector.return_value = IgnitionResult(
            delay_dPdt_s=0.003, delay_dTdt_s=0.003,
            peak_dPdt_Pa_s=1.0e8, peak_dTdt_K_s=1.0e6,
            final_temperature_K=1900.0, final_pressure_bar=80.0, ignited=True,
        )
        rows, metadata = run_campaign(["zhao_sk39"], temperatures_K=TEMPERATURES_K)
        self.assertEqual(metadata["temperature_spacing_K"], 10)
        self.assertEqual(metadata["integrator"], {"rtol": 1e-9, "atol": 1e-15, "max_time_s": .30})
        self.assertTrue(rows)
        self.assertTrue(all("accepted-step maximum dP/dt" in row["ignition_criterion"] for row in rows))
        # Partner breadth is bounded to one lineage; the reference matrix is
        # still present and deterministic.
        self.assertEqual(metadata["summary_count"], 35)

    def test_primary_mechanisms_are_repo_relative(self):
        for name in ("zhao_sk39", "zhao_full", "llnl79"):
            self.assertTrue(MECHANISMS[name].path.is_file())
            self.assertFalse(MECHANISMS[name].relative_path.startswith("/"))
        self.assertEqual(len(TEMPERATURES_K), 11)


if __name__ == "__main__":
    unittest.main()
