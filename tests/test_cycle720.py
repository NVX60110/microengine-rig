import json
import unittest
from unittest.mock import patch

from cycle720 import (
    Cycle720Options,
    FrictionBracket,
    MotorController,
    ValveConfig,
    _advance_lumped,
    _fresh_state,
    phase_at,
    serialize_cycle_state,
    simulate_cycle720,
)
from microengine_rig import RigConfig, build_geometry


class Cycle720Tests(unittest.TestCase):
    def test_phase_map_is_four_stroke_and_wraps(self):
        self.assertEqual([phase_at(x) for x in (-360, -180, 0, 180, 360)],
                         ["intake", "compression", "combustion-expansion", "exhaust", "exhaust"])
        self.assertEqual(phase_at(720), "combustion-expansion")

    def test_state_serialization_is_sorted_and_stable(self):
        state = {"mass_kg": 1e-6, "T_K": 400, "P_bar": 2,
                 "speed_rpm": 1200, "Y": {"O2": 0.2, "N2": 0.8}}
        encoded = serialize_cycle_state(state)
        self.assertEqual(encoded, serialize_cycle_state(dict(reversed(state.items()))))
        self.assertEqual(list(json.loads(encoded)["Y"]), ["N2", "O2"])

    def test_disabled_path_delegates_to_canonical_two_zone(self):
        config = RigConfig(step_deg=5.0)
        fake_rows = [{"deg": -180.0, "effectivePressure_bar": 1.0},
                     {"deg": 0.0, "effectivePressure_bar": 2.0},
                     {"deg": 180.0, "effectivePressure_bar": 1.0}]
        fake_summary = {"end_state": {"T_K": 500.0, "P_bar": 1.0,
                                      "Y": {"CH4": 0.1, "O2": 0.2, "N2": 0.7}},
                        "initial_trapped_mass_mg": 1.0,
                        "mass_retained_end_fraction": 0.9,
                        "gross_indicated_work_mJ": 1.0}
        with patch("cycle720.simulate_two_zone", return_value=(fake_rows, fake_summary)) as solver:
            result = simulate_cycle720(config, Cycle720Options(step_deg=5.0))
        solver.assert_called_once()
        self.assertTrue(result["closed_pass"])
        self.assertTrue(result["regression"]["gate"])
        self.assertAlmostEqual(result["regression"]["mapped_firing_tdc_pressure_bar"], 2.0)
        self.assertAlmostEqual(result["rows"][1]["effectivePressure_bar"], 2.0)
        self.assertAlmostEqual(result["regression"]["canonical_gross_work_mJ"], 1.0)
        self.assertEqual([row["cycle_deg"] for row in result["rows"]], [-180.0, 0.0, 180.0])
        self.assertAlmostEqual(result["cycle_state_out"]["mass_kg"], 0.9e-6)

    def test_lumped_valve_step_conserves_positive_mass_and_returns_state(self):
        config = RigConfig(fuel_profile="methane", intake_temperature_K=300.0,
                           intake_pressure_bar=1.2, equivalence_ratio=0.4)
        geometry = build_geometry(config)
        state = _fresh_state(config, geometry.volume(0.0))
        valve = ValveConfig(0.0, 200.0, effective_area_m2=1e-7)
        # No pressure drop here, so the step is a closed adiabatic volume step.
        next_state, net = _advance_lumped(config, state, geometry.volume(0.0),
                                          geometry.volume(0.01), 1e-5, valve, None, "in")
        self.assertGreater(next_state["mass_kg"], 0.0)
        self.assertEqual(net, 0.0)
        self.assertGreater(next_state["T_K"], 0.0)

    def test_option_validation_rejects_bad_valve_and_motor(self):
        config = RigConfig()
        with self.assertRaises(ValueError):
            Cycle720Options(intake_valve=ValveConfig(10, 0)).validate(config)
        with self.assertRaises(ValueError):
            Cycle720Options(motor_enabled=True, motor=MotorController(target_rpm=1000)).validate(config)


if __name__ == "__main__":
    unittest.main()
