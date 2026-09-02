import unittest

from physics.thermal_clearance import (
    ThermalStrainProfile,
    annulus_leakage_from_clearance,
    calculate_clearance,
    cold_clearance_for_hot_target_um,
)


class ThermalClearanceTests(unittest.TestCase):
    COMMON = dict(
        piston_reference_temperature_K=293.15,
        liner_reference_temperature_K=293.15,
    )

    def test_identical_materials_and_temperatures_preserve_radial_clearance(self):
        result = calculate_clearance(
            bore_diameter_mm=8.5,
            cold_radial_clearance_um=3.0,
            hot_piston_temperature_K=500.0,
            hot_liner_temperature_K=500.0,
            piston_cte_per_K=20e-6,
            liner_cte_per_K=20e-6,
            **self.COMMON,
        )
        # The liner and piston strains match, but the piston diameter is
        # smaller by 2c at the reference state.  Its matching strain therefore
        # also expands the radial gap by c*strain (not exactly zero).
        expected = 3.0 * (1.0 + 20e-6 * (500.0 - 293.15))
        self.assertAlmostEqual(result.hot_radial_clearance_um, expected, places=8)
        self.assertAlmostEqual(result.clearance_change_um, expected - 3.0, places=8)
        self.assertFalse(result.interference)

    def test_hot_high_cte_piston_in_lower_cte_liner_interferes(self):
        result = calculate_clearance(
            bore_diameter_mm=8.5,
            cold_radial_clearance_um=0.0,
            hot_piston_temperature_K=550.0,
            hot_liner_temperature_K=400.0,
            piston_cte_per_K=23e-6,
            liner_cte_per_K=11e-6,
            **self.COMMON,
        )
        self.assertLess(result.hot_radial_clearance_um, 0.0)
        self.assertTrue(result.interference_flag)

    def test_negative_hot_clearance_is_not_clamped(self):
        result = calculate_clearance(
            bore_diameter_mm=8.5,
            cold_radial_clearance_um=0.0,
            hot_piston_temperature_K=600.0,
            hot_liner_temperature_K=300.0,
            piston_cte_per_K=25e-6,
            liner_cte_per_K=10e-6,
            **self.COMMON,
        )
        self.assertLess(result.hot_radial_clearance_um, 0.0)
        leakage = annulus_leakage_from_clearance(
            result.hot_radial_clearance_um,
            pressure_up_bar=45.0,
            temperature_K=1100.0,
        )
        self.assertEqual(leakage["leakage_status"], "interference_invalid_annulus")
        self.assertIsNone(leakage["mass_flow_kg_s"])

    def test_known_hand_calculation(self):
        # Db=10 mm, c=5 um, both +100 K; Dp=9.990 mm.
        # Dp grows by 19.980 um and Db by 10.000 um, leaving 0.010 um radial.
        result = calculate_clearance(
            bore_diameter_mm=10.0,
            cold_radial_clearance_um=5.0,
            hot_piston_temperature_K=393.15,
            hot_liner_temperature_K=393.15,
            piston_cte_per_K=20e-6,
            liner_cte_per_K=10e-6,
            **self.COMMON,
        )
        self.assertAlmostEqual(result.piston_diameter_growth_um, 19.98, places=8)
        self.assertAlmostEqual(result.liner_bore_growth_um, 10.0, places=8)
        self.assertAlmostEqual(result.hot_radial_clearance_um, 0.01, places=6)

    def test_bore_scale_mismatch_scales_with_diameter(self):
        kwargs = dict(
            cold_radial_clearance_um=0.0,
            hot_piston_temperature_K=550.0,
            hot_liner_temperature_K=450.0,
            piston_cte_per_K=20e-6,
            liner_cte_per_K=12e-6,
            **self.COMMON,
        )
        small = calculate_clearance(bore_diameter_mm=8.5, **kwargs)
        large = calculate_clearance(bore_diameter_mm=12.5, **kwargs)
        self.assertAlmostEqual(large.clearance_change_um / small.clearance_change_um, 12.5 / 8.5, places=8)

    def test_profile_matches_constant_cte_when_slope_is_constant(self):
        profile = ThermalStrainProfile(((293.15, 0.0), (393.15, 0.002)))
        result = calculate_clearance(
            bore_diameter_mm=10.0,
            cold_radial_clearance_um=5.0,
            hot_piston_temperature_K=393.15,
            hot_liner_temperature_K=393.15,
            piston_cte_per_K=profile,
            liner_cte_per_K=profile,
            **self.COMMON,
        )
        self.assertAlmostEqual(result.hot_radial_clearance_um, 5.01, places=8)

    def test_inverse_target_clearance(self):
        kwargs = dict(
            bore_diameter_mm=8.5,
            target_hot_clearance_um=3.0,
            hot_piston_temperature_K=500.0,
            hot_liner_temperature_K=450.0,
            piston_cte_per_K=20e-6,
            liner_cte_per_K=13e-6,
            **self.COMMON,
        )
        cold = cold_clearance_for_hot_target_um(**kwargs)
        result = calculate_clearance(cold_radial_clearance_um=cold, **{k: v for k, v in kwargs.items() if k != "target_hot_clearance_um"})
        self.assertAlmostEqual(result.hot_radial_clearance_um, 3.0, places=8)


if __name__ == "__main__":
    unittest.main()
