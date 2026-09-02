import unittest

from physics.thermal_fit_axial import (
    AxialFitConfig,
    AxialStation,
    evaluate_axial_fit,
    evaluate_temperature_rows,
    minimum_preheat_temperature_K,
    nonuniform_annulus_leakage,
)


class AxialThermalFitTests(unittest.TestCase):
    COMMON = {
        "piston_reference_temperature_K": 293.15,
        "liner_reference_temperature_K": 293.15,
        "piston_cte": 20e-6,
        "liner_cte": 20e-6,
        "stations": (AxialStation(0.0, "top"), AxialStation(10.0, "bottom")),
    }

    def test_hand_checked_axial_profile_and_radial_convention(self):
        result = evaluate_axial_fit(
            config=AxialFitConfig(bore_diameter_mm=10.0, axial_length_mm=10.0, cold_radial_clearance_um=5.0),
            piston_top_temperature_K=393.15,
            piston_bottom_temperature_K=293.15,
            liner_top_temperature_K=393.15,
            liner_bottom_temperature_K=293.15,
            **self.COMMON,
        )
        # At the top, equal 100 K strains preserve the radial gap plus c*eps:
        # 5*(1 + 20e-6*100) = 5.01 um.
        self.assertAlmostEqual(result["stations"][0]["hot_radial_clearance_um"], 5.01, places=8)
        self.assertAlmostEqual(result["stations"][1]["hot_radial_clearance_um"], 5.0, places=8)
        self.assertFalse(result["contact"])

    def test_contact_is_not_flow_and_zero_gap_is_flagged(self):
        result = evaluate_axial_fit(
            config=AxialFitConfig(bore_diameter_mm=8.5, axial_length_mm=8.0, cold_radial_clearance_um=0.0),
            piston_top_temperature_K=600.0,
            piston_bottom_temperature_K=600.0,
            liner_top_temperature_K=300.0,
            liner_bottom_temperature_K=300.0,
            piston_cte=25e-6,
            liner_cte=10e-6,
        )
        self.assertTrue(result["contact"])
        leakage = nonuniform_annulus_leakage(result["stations"], pressure_up_bar=4.0)
        self.assertEqual(leakage["leakage_status"], "contact_invalid_annulus")
        self.assertIsNone(leakage["mass_flow_kg_s"])

    def test_negative_local_cold_pinch_is_retained_as_contact(self):
        result = evaluate_axial_fit(
            config=AxialFitConfig(bore_diameter_mm=8.5, axial_length_mm=8.0, cold_radial_clearance_um=0.5, liner_taper_um=-2.0),
            piston_top_temperature_K=293.15,
            piston_bottom_temperature_K=293.15,
            liner_top_temperature_K=293.15,
            liner_bottom_temperature_K=293.15,
            piston_cte=20e-6,
            liner_cte=12e-6,
        )
        self.assertLess(result["stations"][0]["cold_radial_clearance_um"], 0.0)
        self.assertTrue(result["stations"][0]["cold_interference"])
        self.assertTrue(result["contact"])

    def test_conditional_preheat_exposes_temperature_split_assumption(self):
        # A liner 100 K hotter than the piston eventually opens a zero-cold-gap
        # fit under the CTE-only check. This is conditional, not a start gate.
        threshold = minimum_preheat_temperature_K(
            config=AxialFitConfig(bore_diameter_mm=8.5, axial_length_mm=8.0, cold_radial_clearance_um=0.0, contact_margin_um=11.0),
            piston_offset_K=0.0,
            liner_offset_K=100.0,
            piston_cte=10e-6,
            liner_cte=25e-6,
            required_margin_um=11.0,
        )
        self.assertEqual(threshold["threshold_type"], "minimum_safe")
        self.assertGreater(threshold["threshold_K"], 293.15)
        self.assertLess(threshold["threshold_K"], 700.0)

    def test_higher_cte_piston_can_lose_margin_with_common_preheat(self):
        result = minimum_preheat_temperature_K(
            config=AxialFitConfig(bore_diameter_mm=8.5, axial_length_mm=8.0, cold_radial_clearance_um=5.0, contact_margin_um=4.0),
            piston_cte=25e-6,
            liner_cte=10e-6,
            lower_bound_K=293.15,
            upper_bound_K=700.0,
            required_margin_um=4.0,
        )
        self.assertEqual(result["threshold_type"], "maximum_safe")
        self.assertLess(result["threshold_K"], 700.0)

    def test_nonuniform_positive_path_uses_narrowest_station(self):
        rows = [{"hot_radial_clearance_um": gap} for gap in (2.0, 4.0, 8.0)]
        result = nonuniform_annulus_leakage(rows, pressure_up_bar=6.5, temperature_K=400.0)
        self.assertEqual(result["leakage_status"], "annulus_positive_clearance")
        self.assertLess(result["equivalent_clearance_um"], 4.0)
        self.assertGreater(result["mass_flow_kg_s"], 0.0)

    def test_worst_clearance_retains_matching_pressure_temperature_state(self):
        rows = [
            {"deg": -180.0, "pressure_bar": 3.0, "gas_temperature_K": 300.0, "piston_crown_temperature_K": 440.0, "piston_skirt_temperature_K": 435.0, "liner_tdc_temperature_K": 398.0, "liner_lower_temperature_K": 394.0},
            {"deg": 60.0, "pressure_bar": 18.0, "gas_temperature_K": 720.0, "piston_crown_temperature_K": 460.0, "piston_skirt_temperature_K": 455.0, "liner_tdc_temperature_K": 398.0, "liner_lower_temperature_K": 394.0},
        ]
        evaluated = evaluate_temperature_rows(
            rows,
            config=AxialFitConfig(bore_diameter_mm=8.5, axial_length_mm=8.0, cold_radial_clearance_um=10.0),
            piston_cte=20e-6,
            liner_cte=12e-6,
        )
        worst = evaluated["worst_profile"]
        self.assertEqual(worst["source_row_index"], 1)
        self.assertEqual(worst["source_pressure_bar"], 18.0)
        self.assertEqual(worst["source_gas_temperature_K"], 720.0)
        paired = nonuniform_annulus_leakage(worst["stations"], pressure_up_bar=worst["source_pressure_bar"], temperature_K=worst["source_gas_temperature_K"])
        bdc = nonuniform_annulus_leakage(worst["stations"], pressure_up_bar=3.0, temperature_K=300.0)
        self.assertGreater(paired["mass_flow_kg_s"], bdc["mass_flow_kg_s"])


if __name__ == "__main__":
    unittest.main()
