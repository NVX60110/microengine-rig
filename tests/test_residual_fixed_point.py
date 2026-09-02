import unittest
from unittest.mock import patch
import json
from pathlib import Path
import subprocess
import sys

from microengine_rig import RigConfig
from residual_fixed_point import (
    ResidualOptions,
    mix_fresh_and_residual,
    run_residual_fixed_point,
)
from two_zone_model import TwoZoneOptions, simulate_two_zone


class ResidualFixedPointTests(unittest.TestCase):
    def test_mass_mix_is_normalized_and_enthalpy_defined(self):
        config = RigConfig(fuel_profile="methane", equivalence_ratio=0.4,
                           intake_temperature_K=300.0, intake_pressure_bar=1.2)
        residual = {
            "T_K": 900.0,
            "P_bar": 1.2,
            "Y": {"CO2": 0.10, "H2O": 0.05, "N2": 0.85},
        }
        mixed = mix_fresh_and_residual(config, residual, 0.20, "mass")
        self.assertEqual(mixed["basis"], "mass")
        self.assertAlmostEqual(sum(mixed["Y"].values()), 1.0, places=12)
        self.assertGreater(mixed["T_K"], config.intake_temperature_K)
        self.assertAlmostEqual(mixed["P_bar"], config.intake_pressure_bar, places=12)

    def test_mole_mix_uses_molar_stream_basis(self):
        config = RigConfig(fuel_profile="methane", equivalence_ratio=0.4,
                           intake_temperature_K=300.0, intake_pressure_bar=1.2)
        residual = {"T_K": 700.0, "X": {"CO2": 0.2, "H2O": 0.1, "N2": 0.7}}
        mixed = mix_fresh_and_residual(config, residual, 0.10, "mole")
        self.assertEqual(mixed["basis"], "mole")
        self.assertAlmostEqual(sum(mixed["X"].values()), 1.0, places=12)
        self.assertAlmostEqual(mixed["P_bar"], config.intake_pressure_bar, places=12)

    def test_mixed_mapping_is_identical_across_processes(self):
        code = (
            "import json; from microengine_rig import RigConfig; "
            "from residual_fixed_point import mix_fresh_and_residual; "
            "c=RigConfig(fuel_profile='methane', equivalence_ratio=0.4, "
            "intake_temperature_K=300.0, intake_pressure_bar=1.2); "
            "r=mix_fresh_and_residual(c, {'T_K':700.0, 'Y':{'CO2':0.2, "
            "'H2O':0.1, 'N2':0.7}}, 0.2, 'mass'); "
            "print(json.dumps(r['Y']))"
        )
        root = Path(__file__).resolve().parents[1]
        outputs = [subprocess.check_output(
            [sys.executable, "-c", code], cwd=root, text=True
        ) for _ in range(2)]
        self.assertEqual(outputs[0], outputs[1])

    def test_two_zone_accepts_arbitrary_initial_composition_and_exports_end_state(self):
        config = RigConfig(
            fuel_profile="methane", equivalence_ratio=0.4,
            intake_temperature_K=300.0, intake_pressure_bar=1.2,
            wall_mode="adiabatic", blowby_mode="off", step_deg=5.0,
        )
        rows, summary = simulate_two_zone(
            config,
            TwoZoneOptions(integrator_rtol=1.0e-9, integrator_atol=1.0e-15),
            initial_state={
                "Y": {"CH4": 0.01, "O2": 0.20, "N2": 0.79},
                "T_K": 300.0, "P_bar": 1.2, "source": "test-state",
            },
        )
        self.assertTrue(rows)
        self.assertEqual(summary["initial_state"]["source"], "test-state")
        self.assertEqual(summary["initial_state"]["basis"], "mass")
        self.assertIn("Y", summary["end_state"])
        self.assertAlmostEqual(sum(summary["end_state"]["Y"].values()), 1.0, places=10)

    def test_driver_iterates_map_and_does_not_reuse_frozen_end_vector(self):
        config = RigConfig(step_deg=0.125)
        calls = []

        def fake_cycle(_config, _options, initial_state=None):
            calls.append(dict(initial_state["Y"]))
            y = dict(initial_state["Y"])
            # A bounded, non-constant synthetic cycle map for the loop test.
            ch4 = y.get("CH4", 0.0)
            end_ch4 = 0.20 + 0.50 * ch4
            end_y = {"CH4": end_ch4, "O2": 0.20, "N2": 0.80 - end_ch4}
            return [], {
                "end_state": {"T_K": 500.0 + 0.25 * ch4, "Y": end_y},
                "branch": "cool_partial_candidate",
                "peak_temperature_K": 900.0,
                "gross_imep_bar": 0.1,
                "max_fuel_consumed_fraction": 0.2,
                "max_pressure_rise_bar_per_deg": 1.0,
                "mass_balance_residual_mg": 0.0,
                "max_interzone_pressure_difference_bar": 0.01,
                "max_volume_closure_error_mm3": 0.01,
                "mass_retained_end_fraction": 0.99,
                "CH4_mass_balance_residual_mg": 0.0005,
            }

        with patch("residual_fixed_point.simulate_two_zone", side_effect=fake_cycle):
            report = run_residual_fixed_point(
                config,
                options=ResidualOptions(
                    residual_fractions=(0.20,), max_iterations=12,
                    composition_tolerance=1.0e-8,
                    temperature_tolerance_K=1.0e-6,
                ),
            )
        row = report["rows"][0]
        self.assertTrue(row["converged"])
        self.assertAlmostEqual(row["max_component_mass_balance_residual_mg"], 0.0005)
        self.assertEqual(row["numerical_gate_status"], "pass")
        self.assertGreater(row["iterations"], 1)
        self.assertGreater(len(calls), 1)
        self.assertNotEqual(calls[0]["CH4"], calls[1]["CH4"])
        # For end_CH4 = 0.20 + 0.50*input_CH4 and f_res=.20, the fixed
        # *mixed-input* state is x = .8*fresh + .2*(.20 + .5*x).  A loop that
        # feeds the already-mixed input back into the mixer converges to a
        # different value and must fail this assertion.
        fresh_ch4 = calls[0]["CH4"]
        expected = (0.80 * fresh_ch4 + 0.20 * 0.20) / 0.90
        self.assertAlmostEqual(calls[-1]["CH4"], expected, places=6)
        self.assertEqual(report["conditions"]["cycle_interval_deg"], "-180 to +180 (one revolution only)")


if __name__ == "__main__":
    unittest.main()
