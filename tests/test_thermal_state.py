import unittest

from physics.thermal_state import (
    ConductiveLink,
    HistoryPoint,
    ThermalNode,
    ThermalRCConfig,
    default_links,
    default_nodes,
    gas_areas_m2,
    heat_transfer_coeff_W_m2K,
    run_thermal_rc,
)


def flat_history(temperature=300.0, pressure=1.0):
    return [
        HistoryPoint(-180.0, pressure, temperature, 0.0, 0.001),
        HistoryPoint(0.0, pressure, temperature, 0.0, 0.001),
        HistoryPoint(180.0, pressure, temperature, 0.0, 0.0),
    ]


class ThermalStateTests(unittest.TestCase):
    def test_default_network_has_requested_physical_nodes(self):
        nodes = default_nodes(ThermalRCConfig())
        self.assertEqual(
            [node.name for node in nodes],
            ["piston_crown", "piston_skirt", "rod_crank", "liner_tdc", "liner_lower", "head_deck", "block"],
        )
        self.assertGreater(sum(node.capacity_J_K for node in nodes), 0.0)
        self.assertTrue(default_links())
        self.assertGreater(next(node for node in nodes if node.name == "block").external_conductance_W_K, 0.0)

    def test_material_conductivity_scales_screening_links(self):
        base = default_links(ThermalRCConfig())
        ceramic = default_links(ThermalRCConfig(piston_conductivity_W_mK=25.0, liner_conductivity_W_mK=25.0))
        self.assertLess(ceramic[0].conductance_W_K, base[0].conductance_W_K)
        self.assertLess(ceramic[3].conductance_W_K, base[3].conductance_W_K)

    def test_conventional_skirt_has_no_direct_chamber_gas_area(self):
        areas = gas_areas_m2(ThermalRCConfig(), 0.0)
        self.assertEqual(areas["piston_skirt"], 0.0)
        self.assertGreater(areas["liner_tdc"], 0.0)
        self.assertGreater(areas["liner_lower"], 0.0)

    def test_constant_h_does_not_heat_without_gas_delta(self):
        config = ThermalRCConfig(max_warmup_cycles=4, min_warmup_cycles=1, convergence_tolerance_K=1e-12)
        result = run_thermal_rc(
            flat_history(), config, piston_cte=20e-6, liner_cte=12e-6,
            nodes=tuple(ThermalNode(n.name, n.mass_kg, n.cp_J_kgK, 300.0, 300.0, 0.0) for n in default_nodes(config)),
            links=tuple(ConductiveLink(link.node_a, link.node_b, 0.0) for link in default_links()),
        )
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["piston_skirt_min_K"], 300.0, places=10)
        self.assertAlmostEqual(result["liner_tdc_max_K"], 300.0, places=10)

    def test_gas_heating_separates_piston_and_liner_nodes(self):
        config = ThermalRCConfig(max_warmup_cycles=20, min_warmup_cycles=2, convergence_tolerance_K=1e-6)
        result = run_thermal_rc(
            flat_history(temperature=1000.0, pressure=10.0), config,
            piston_cte=20e-6, liner_cte=12e-6,
        )
        self.assertGreater(result["piston_skirt_max_K"], 300.0)
        self.assertGreater(result["liner_tdc_max_K"], 300.0)
        self.assertGreater(result["piston_skirt_max_K"] - 300.0, 0.0)

    def test_angle_correlation_is_explicit_and_state_dependent(self):
        base = ThermalRCConfig(h_model="angle_correlation")
        reference = HistoryPoint(0.0, 10.0, 700.0, 0.28, 0.001)
        high_speed = HistoryPoint(0.0, 40.0, 700.0, 2.0, 0.001)
        self.assertAlmostEqual(heat_transfer_coeff_W_m2K(reference, base), 600.0, places=8)
        self.assertGreater(heat_transfer_coeff_W_m2K(high_speed, base), 600.0)

    def test_inverse_window_is_reported(self):
        result = run_thermal_rc(
            flat_history(temperature=800.0, pressure=10.0),
            ThermalRCConfig(max_warmup_cycles=5, min_warmup_cycles=1),
            piston_cte=20e-6, liner_cte=12e-6,
        )
        bounds = result["required_cold_clearance_for_hot_2_to_5_um"]
        self.assertIn("lower_bound_um", bounds)
        self.assertIn("upper_bound_um", bounds)
        self.assertLess(bounds["lower_bound_um"], bounds["upper_bound_um"])
        self.assertTrue(result["periodic_converged"])
        self.assertLess(result["periodic_info"]["periodic_residual_K"], 1e-8)
        self.assertLess(result["periodic_info"]["cycle_energy_balance_relative"], 1e-10)
        row = result["history_rows"][0]
        self.assertIn("hot_clearance_crown_liner_tdc_3p0_um", row)
        self.assertIn("hot_clearance_skirt_liner_lower_3p0_um", row)
        self.assertIn("hot_clearance_min_path_3p0_um", row)
        self.assertIn("startup_clearance_3um", result)
        self.assertEqual(len(result["cycle_rows"]), 5)
        self.assertIn("min_path_hot_clearance_3um", result["cycle_rows"][0])


if __name__ == "__main__":
    unittest.main()
