import json
import unittest
from unittest.mock import patch

import cantera as ct

from cycle720 import (
    Cycle720Options,
    FrictionBracket,
    MotorController,
    ValveConfig,
    _advance_lumped,
    _fresh_state,
    _speed_step,
    phase_at,
    serialize_cycle_state,
    simulate_cycle720,
    simulate_motored_cycle720,
)
from microengine_rig import RigConfig, build_geometry
from scripts.run_cycle720 import _json_safe


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
        self.assertAlmostEqual(result["summary"]["four_stroke_period_s"], 0.10)

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

    def test_lumped_valve_step_can_return_accounting_details(self):
        config = RigConfig(fuel_profile="methane", intake_temperature_K=300.0,
                           intake_pressure_bar=1.2, equivalence_ratio=0.4)
        geometry = build_geometry(config)
        state = _fresh_state(config, geometry.volume(0.0))
        next_state, net, details = _advance_lumped(
            config, state, geometry.volume(0.0), geometry.volume(0.01),
            1e-5, None, None, "in", return_details=True)
        self.assertEqual(net, 0.0)
        self.assertEqual(details["mass_in_kg"], 0.0)
        self.assertEqual(details["mass_out_kg"], 0.0)
        self.assertTrue(details["internal_energy_out_J"] != 0.0)

    def test_bidirectional_lumped_step_preserves_reverse_port_to_cylinder_flow(self):
        config = RigConfig(fuel_profile="methane", intake_temperature_K=300.0,
                           intake_pressure_bar=1.0, equivalence_ratio=0.4)
        geometry = build_geometry(config)
        state = _fresh_state(config, geometry.volume(0.0))
        state.update({"P_bar": 0.5, "deg": 100.0})
        reservoir = ct.Solution("gri30.yaml", "gri30")
        reservoir.TPX = 300.0, 2.0e5, "CH4:0.01, O2:0.21, N2:0.78, AR:0.01"
        valve = ValveConfig(0.0, 200.0, effective_area_m2=1e-7)
        next_state, net, details = _advance_lumped(
            config, state, geometry.volume(0.0), geometry.volume(0.0),
            1e-5, valve, reservoir, "in", return_details=True,
            bidirectional=True)
        self.assertGreater(net, 0.0)  # net is positive into cylinder
        self.assertEqual(details["flow_direction"], "port_to_cylinder")
        self.assertGreater(details["mass_in_kg"], 0.0)
        self.assertEqual(details["mass_out_kg"], 0.0)
        self.assertTrue(details["choked"])
        self.assertGreater(next_state["mass_kg"], state["mass_kg"])

    def test_motored_diagnostic_reports_signed_flow_and_accounting(self):
        config = RigConfig(
            fuel_profile="methane", intake_pressure_bar=1.2,
            intake_temperature_K=300.0, equivalence_ratio=0.4,
            wall_mode="adiabatic", rpm=1200.0, step_deg=30.0,
        )
        options = Cycle720Options(
            step_deg=30.0, max_cycles=2, valves_enabled=True,
            bidirectional_valves=True,
            intake_valve=ValveConfig(-360.0, -160.0, effective_area_m2=1e-6),
            exhaust_valve=ValveConfig(160.0, 360.0, effective_area_m2=1e-6),
        )
        result = simulate_motored_cycle720(config, options)
        summary = result["summary"]
        self.assertEqual(len(result["rows"]), 25)
        self.assertIn(summary["diagnostics"]["minimum_temperature"]["cycle_deg"],
                      [row["cycle_deg"] for row in result["rows"]])
        self.assertIn("intake", summary["accounting"]["events"])
        self.assertIn("exhaust", summary["accounting"]["events"])
        self.assertAlmostEqual(summary["accounting"]["mass_balance_residual_kg"], 0.0, places=18)
        self.assertTrue(any(row["valve_flow_direction"] != "closed" for row in result["rows"]))

    def test_option_validation_rejects_bad_valve_and_motor(self):
        config = RigConfig()
        with self.assertRaises(ValueError):
            Cycle720Options(intake_valve=ValveConfig(10, 0)).validate(config)
        with self.assertRaises(ValueError):
            Cycle720Options(motor_enabled=True, motor=MotorController(target_rpm=1000)).validate(config)

    def test_disabled_crank_dynamics_holds_prescribed_speed(self):
        config = RigConfig(wall_mode="fixed", wall_temperature_K=560.0, step_deg=5.0)
        result = simulate_cycle720(config, Cycle720Options(step_deg=5.0))
        self.assertTrue(result["closed_pass"])
        self.assertAlmostEqual(result["cycle_state_out"]["speed_rpm"], config.rpm)

    def test_gas_exchange_stage_holds_speed_until_dynamics_enabled(self):
        options = Cycle720Options()
        speed, motor = _speed_step(RigConfig(), options, 1200.0, 1.0, 1.0e-4)
        self.assertEqual(speed, 1200.0)
        self.assertEqual(motor, 0.0)

    def test_four_stroke_timing_is_120_over_rpm(self):
        config = RigConfig(rpm=1200.0, wall_mode="fixed", wall_temperature_K=560.0,
                           step_deg=5.0)
        result = simulate_cycle720(config, Cycle720Options(step_deg=5.0))
        self.assertAlmostEqual(result["summary"]["one_revolution_period_s"], 0.05)
        self.assertAlmostEqual(result["summary"]["four_stroke_period_s"], 0.10)

    def test_runner_serializes_nonfinite_first_cycle_metrics_as_null(self):
        self.assertIsNone(_json_safe(float("inf")))
        self.assertEqual(_json_safe({"x": [float("-inf"), 1.0]}),
                         {"x": [None, 1.0]})


if __name__ == "__main__":
    unittest.main()
