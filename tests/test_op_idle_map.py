import unittest
from unittest.mock import patch

from scripts.op_idle_map import (
    RPM_GRID,
    STRICT_STEP_DEG,
    base_config,
    central_options,
    classify,
    jobs,
    run_job,
)


def screening_summary(**changes):
    result = {
        "gross_imep_bar": 1.0,
        "max_fuel_consumed_fraction": 0.40,
        "peak_temperature_K": 950.0,
        "max_pressure_rise_bar_per_deg": 5.0,
        "CA50_deg_atdc": 0.0,
        "max_interzone_pressure_difference_bar": 0.01,
        "mass_retained_end_fraction": 0.90,
        "initial_trapped_mass_mg": 1.0,
        "gross_indicated_work_mJ": 10.0,
        "gross_indicated_power_W_per_cylinder": 1.0,
        "peak_pressure_bar": 50.0,
        "peak_pressure_deg_atdc": 0.0,
        "peak_core_temperature_K": 950.0,
        "peak_boundary_temperature_K": 900.0,
        "max_pressure_rise_deg_atdc": 0.0,
        "blowby_mass_out_mg": 0.1,
        "blowby_mass_in_mg": 0.0,
        "mass_balance_residual_mg": 0.0,
        "max_volume_closure_error_mm3": 0.0,
        "CA10_deg_atdc": -5.0,
        "CA90_deg_atdc": 10.0,
        "fuel_profile": "dme_zhao_sk39",
        "mechanism": "mechanisms/dme_zhao_sk39.yaml",
        "fuel_composition": "ch3och3:0.25, CH4:0.75",
        "mass_retained_end_fraction": 0.90,
        "mixing_time_min_observed_ms": 10.0,
        "mixing_time_max_observed_ms": 30.0,
        "branch": "cool_partial_candidate",
        "wall_energy_gas_to_wall_mJ": 1.0,
    }
    result.update(changes)
    return result


class OpIdleMapTests(unittest.TestCase):
    def test_strict_transition_controls_and_correct_periods(self):
        config = base_config(rpm=1200.0)
        self.assertEqual(config.step_deg, STRICT_STEP_DEG)
        self.assertAlmostEqual(60.0 / config.rpm, 0.05)
        self.assertAlmostEqual(120.0 / config.rpm, 0.10)
        options = central_options()
        self.assertEqual(options.integrator_rtol, 1e-9)
        self.assertEqual(options.integrator_atol, 1e-15)

    def test_rpm_grid_is_bounded_and_ordered(self):
        self.assertEqual(RPM_GRID, (800.0, 1000.0, 1200.0, 1500.0, 2000.0, 3000.0, 5000.0, 7500.0, 10000.0))
        self.assertEqual(len(jobs("baseline")), len(RPM_GRID) * 3)
        baseline = [
            {"status": "ok", "rpm": 1000.0, "mechanism_case": mechanism, "screen_class": "marginal"}
            for mechanism in ("dme_zhao_sk39", "dme_zhao_full", "dme_llnl_2004")
        ] + [
            {"status": "ok", "rpm": 1200.0, "mechanism_case": mechanism, "screen_class": "robust"}
            for mechanism in ("dme_zhao_sk39", "dme_zhao_full", "dme_llnl_2004")
        ]
        self.assertEqual(len(jobs("refine", baseline_rows=baseline)), 3 * 3)
        retry = jobs("retry")
        self.assertEqual(len(retry), 1)
        self.assertEqual(retry[0]["config_patch"]["step_deg"], 0.0625)
        self.assertEqual(len(jobs("uncertainty")), 18)

    def test_screen_gate_labels_do_not_claim_stable_idle(self):
        result = classify(screening_summary())
        self.assertEqual(result["screen_class"], "robust")
        self.assertEqual(result["stable_idle_status"], "unresolved")
        self.assertTrue(result["gate_pass"])

        result = classify(screening_summary(max_pressure_rise_bar_per_deg=11.0))
        self.assertEqual(result["screen_class"], "implausible")
        self.assertEqual(result["limiting_mechanism"], "rapid_heat_release")

    def test_supported_work_proxy_is_a_lower_bound(self):
        result = classify(screening_summary(gross_imep_bar=-0.2))
        self.assertEqual(result["limiting_mechanism"], "nonpositive_gross_work")

    @patch("scripts.op_idle_map.simulate_two_zone")
    def test_bookkeeping_adds_timing_tdc_trace_and_motor_proxy(self, simulate):
        rows = [
            {"deg": -180.0, "effectivePressure_bar": 3.0, "coreTemperature_K": 300.0, "boundaryTemperature_K": 300.0},
            {"deg": 0.0, "effectivePressure_bar": 60.0, "coreTemperature_K": 900.0, "boundaryTemperature_K": 850.0},
            {"deg": 180.0, "effectivePressure_bar": 4.0, "coreTemperature_K": 450.0, "boundaryTemperature_K": 430.0},
        ]
        simulate.return_value = (rows, screening_summary(gross_indicated_work_mJ=-2.0))
        result = run_job({"identity": {"case": "test", "mechanism_case": "dme_zhao_sk39", "uncertainty_factor": "none"}, "config_patch": {"rpm": 1200.0}})
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["four_stroke_period_s"], 0.10)
        self.assertAlmostEqual(result["reacting_tdc_pressure_bar"], 60.0)
        self.assertAlmostEqual(result["reacting_tdc_core_temperature_K"], 900.0)
        self.assertAlmostEqual(result["reacting_tdc_boundary_temperature_K"], 850.0)
        self.assertAlmostEqual(result["minimum_motor_work_proxy_mJ"], 2.0)
        self.assertGreater(result["minimum_motor_torque_proxy_Nm"], 0.0)
        self.assertEqual(result["transition_step_deg"], STRICT_STEP_DEG)
        self.assertEqual(result["stable_idle_status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
