import math
import unittest

from leakage_scaling import (
    analyze_record,
    differential_leak_ratio,
    effective_cda_mm2,
    isentropic_mass_flux_per_cda,
    static_absolute_regression,
)
from physics.annulus import clearance_to_area


class LeakageScalingTests(unittest.TestCase):
    def test_choked_flux_is_independent_of_further_downstream_drop(self):
        a = isentropic_mass_flux_per_cda(6.0, 1.0, 300.0)
        b = isentropic_mass_flux_per_cda(6.0, 0.5, 300.0)
        self.assertAlmostEqual(a, b, places=10)

    def test_effective_area_round_trip(self):
        flux = isentropic_mass_flux_per_cda(6.0, 1.0, 300.0)
        true_cda_mm2 = 0.012
        mdot = flux * true_cda_mm2 * 1e-6
        recovered = effective_cda_mm2(mdot, 6.0, 1.0, 300.0)
        self.assertAlmostEqual(recovered, true_cda_mm2, places=12)

    def test_geometry_only_differential_tester_is_relative_only(self):
        row = {
            "mode": "static_differential",
            "bore_mm": "80",
            "stroke_mm": "80",
            "temperature_K": "300",
            "ambient_pressure_bar_abs": "1.0",
            "tester_supply_pressure_bar_abs": "6.5",
            "tester_cylinder_pressure_bar_abs": "5.8",
            "reference_orifice_diameter_mm": "1.016",
        }
        result = analyze_record(row)
        self.assertEqual(result["eligibility"], "static_relative")
        self.assertGreater(result["leak_to_reference_cda_ratio"], 0.0)
        self.assertNotIn("leak_cda_mm2", result)

    def test_calibrated_differential_tester_produces_absolute_area(self):
        ref_cda = 0.25
        row = {
            "mode": "static_differential",
            "bore_mm": "80",
            "stroke_mm": "80",
            "temperature_K": "300",
            "ambient_pressure_bar_abs": "1.0",
            "tester_supply_pressure_bar_abs": "6.5",
            "tester_cylinder_pressure_bar_abs": "5.8",
            "reference_cda_mm2": str(ref_cda),
        }
        result = analyze_record(row)
        expected = ref_cda * differential_leak_ratio(6.5, 5.8, 1.0, 300.0)
        self.assertEqual(result["eligibility"], "static_absolute")
        self.assertAlmostEqual(result["leak_cda_mm2"], expected, places=12)

    def test_dynamic_blowby_is_not_inverted_to_static_area(self):
        row = {
            "mode": "dynamic_blowby",
            "bore_mm": "80",
            "stroke_mm": "53",
            "mass_flow_kg_s": "0.0001",
        }
        result = analyze_record(row)
        self.assertEqual(result["eligibility"], "dynamic_flow")
        self.assertNotIn("leak_cda_mm2", result)
        self.assertGreater(result["mass_flow_mg_s_per_cc"], 0.0)

    def test_synthetic_inverse_square_scaling_recovers_minus_two(self):
        rows = []
        # Geometrically similar cylinders: Vd ~ B^3. Let CdA ~ B, so
        # CdA/Vd ~ B^-2 by construction.
        for index, bore in enumerate((20.0, 30.0, 45.0, 70.0)):
            stroke = bore
            vd = math.pi * bore**2 * stroke / 4000.0
            rows.append({
                "eligibility": "static_absolute",
                "bore_mm": bore,
                "cylinder_displacement_cc": vd,
                "leak_cda_mm2": 1e-3 * bore,
                "dataset_family": f"family_{index % 2}",
            })
        result = static_absolute_regression(rows)
        self.assertEqual(result["status"], "screening")
        self.assertAlmostEqual(result["slope_log_cda_per_vd_vs_log_bore"], -2.0, places=10)

    def test_annulus_comparison_respects_viscosity(self):
        low_mu = clearance_to_area(3.0, 6.5, T=300.0, mu=1.8e-5)
        high_mu = clearance_to_area(3.0, 6.5, T=300.0, mu=3.6e-5)
        self.assertAlmostEqual(low_mu / high_mu, 2.0, places=10)


if __name__ == "__main__":
    unittest.main()
