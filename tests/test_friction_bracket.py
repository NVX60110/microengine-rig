import math
import unittest

from physics.friction_bracket import (
    DEFAULT_FRICTION_BRACKETS,
    equivalent_friction_torque_Nm,
    friction_metrics,
    friction_work_J,
)


class FrictionBracketTests(unittest.TestCase):
    def test_four_stroke_work_and_torque_use_4pi(self):
        work = friction_work_J(0.1, 1.0e-6)
        self.assertAlmostEqual(work, 0.01)
        self.assertAlmostEqual(equivalent_friction_torque_Nm(0.1, 1.0e-6), work / (4 * math.pi))

    def test_power_uses_120_rpm_cycle_rate(self):
        metrics = friction_metrics(0.1, 1.0e-6, 1200.0)
        self.assertAlmostEqual(metrics["four_stroke_period_s"], 0.1)
        self.assertAlmostEqual(metrics["friction_power_W"], 0.1)

    def test_defaults_are_explicit_assumptions(self):
        self.assertEqual([item.name for item in DEFAULT_FRICTION_BRACKETS], ["low", "central", "high"])
        self.assertTrue(all(item.status == "project_assumption" for item in DEFAULT_FRICTION_BRACKETS))


if __name__ == "__main__":
    unittest.main()

