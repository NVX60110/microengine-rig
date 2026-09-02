import math
import unittest

from physics.valve_flow import (
    ValveFlowConfig,
    effective_area_mm2,
    integrate_valve_history,
    pumping_work_from_pv,
    signed_valve_mdot,
)


class ValveFlowTests(unittest.TestCase):
    def setUp(self):
        self.valve = ValveFlowConfig(350.0, 570.0, 0.02, discharge_coefficient=0.7)

    def test_half_sine_area_and_four_stroke_timing(self):
        self.assertEqual(effective_area_mm2(300.0, self.valve), 0.0)
        self.assertAlmostEqual(effective_area_mm2(460.0, self.valve), 0.02)
        self.assertAlmostEqual(effective_area_mm2(350.0, self.valve), 0.0, places=12)

    def test_forward_choked_and_reverse_signed_flow(self):
        forward, choked = signed_valve_mdot(5e5, 700.0, 1e5, 350.0, 0.02)
        reverse, reverse_choked = signed_valve_mdot(1e5, 350.0, 5e5, 700.0, 0.02)
        self.assertGreater(forward, 0.0)
        self.assertTrue(choked)
        self.assertLess(reverse, 0.0)
        self.assertTrue(reverse_choked)
        self.assertAlmostEqual(abs(forward / reverse), 1.0, places=12)

    def test_history_integration_has_signed_mass_and_flow_work(self):
        theta = [350.0, 405.0, 460.0, 515.0, 570.0]
        result = integrate_valve_history(theta, [5, 5, 5, 5, 5], [700] * 5, 1.0, 350.0, self.valve, 1200)
        self.assertGreater(result["mass_to_port_kg"], 0.0)
        self.assertGreater(result["flow_work_J"], 0.0)
        self.assertEqual(len(result["mdot_kg_s"]), len(theta))

    def test_pressure_volume_work_preserves_sign(self):
        volumes = [1.0e-6, 2.0e-6, 1.0e-6]
        pressures = [2.0, 2.0, 1.0]
        result = pumping_work_from_pv(volumes, pressures, 1.0e-6)
        self.assertAlmostEqual(result["pumping_work_J_per_cycle"], 0.05)
        self.assertAlmostEqual(result["pumping_mep_bar"], 0.5)
        self.assertEqual(result["pumping_loss_magnitude_bar"], 0.0)


if __name__ == "__main__":
    unittest.main()
