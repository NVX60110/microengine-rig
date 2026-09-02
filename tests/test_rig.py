import math
from pathlib import Path
import unittest

from blowby_screen import run as run_blowby_screen
from boost_system_screen import boost_metrics
from mechanical_screen import mechanical_metrics
from two_zone_model import TwoZoneOptions, simulate_two_zone
from microengine_rig import (
    BUILTIN_FUELS,
    RigConfig,
    annular_eccentricity_factor,
    apply_config_patch,
    build_geometry,
    compressible_annular_mdot,
    compressible_orifice_mdot,
    geometry_summary,
    load_sweep,
    simulate,
)


class RigTests(unittest.TestCase):
    def test_7mm_1200rpm_piston_metrics(self):
        c = RigConfig(stroke_mm=7.0, rpm=1200.0)
        metrics = geometry_summary(c, build_geometry(c))
        self.assertAlmostEqual(metrics["mean_piston_speed_m_s"], 0.28, places=10)
        self.assertGreater(metrics["max_piston_speed_m_s"], metrics["mean_piston_speed_m_s"])

    def test_adiabatic_proxy_compression(self):
        c = RigConfig(ignition_mode="off", wall_mode="adiabatic", step_deg=0.25)
        _, summary = simulate(c)
        expected = c.intake_temperature_K * c.compression_ratio ** (c.gamma - 1.0)
        self.assertAlmostEqual(summary["T_at_TDC_K"], expected, delta=1.0)

    def test_methane_cantera_smoke(self):
        c = RigConfig(step_deg=2.0, wall_mode="finite", fuel_profile="methane")
        rows, summary = simulate(c)
        self.assertTrue(rows)
        self.assertTrue(math.isfinite(summary["peak_pressure_bar"]))
        self.assertEqual(summary["fuel_profile"], "methane")

    def test_ndodecane_cantera_smoke(self):
        c = RigConfig(step_deg=5.0, wall_mode="adiabatic", fuel_profile="ndodecane")
        _, summary = simulate(c)
        self.assertEqual(summary["fuel_profile"], "ndodecane")
        self.assertGreaterEqual(summary["max_fuel_consumed_fraction"], 0.0)

    def test_orifice_is_one_way_and_detects_choking(self):
        reverse, reverse_choked = compressible_orifice_mdot(
            1e5, 350.0, 2e5, 1e-8, 0.7, 1.35, 287.05)
        forward, forward_choked = compressible_orifice_mdot(
            5e5, 700.0, 1e5, 1e-8, 0.7, 1.35, 287.05)
        self.assertEqual(reverse, 0.0)
        self.assertFalse(reverse_choked)
        self.assertGreater(forward, 0.0)
        self.assertTrue(forward_choked)

    def test_annular_leakage_cube_law_and_eccentricity(self):
        args = (2e6, 900.0, 1e5, 0.0085)
        flow_3 = compressible_annular_mdot(*args, 3e-6, 0.008, 4e-5, 287.0)
        flow_5 = compressible_annular_mdot(*args, 5e-6, 0.008, 4e-5, 287.0)
        eccentric = compressible_annular_mdot(
            *args, 5e-6, 0.008, 4e-5, 287.0, eccentricity_ratio=1.0)
        self.assertAlmostEqual(flow_5 / flow_3, (5.0 / 3.0) ** 3, places=10)
        self.assertAlmostEqual(eccentric / flow_5, annular_eccentricity_factor(1.0), places=10)

    def test_dme_profile_blend_and_combustion_diagnostics(self):
        profile = BUILTIN_FUELS["dme_zhao_sk39"]
        self.assertIn("engine-unvalidated", profile.validation_status)
        self.assertIn("CH4", profile.note)
        self.assertIn("not CH3OH", profile.note)
        config = RigConfig(
            fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
            fuel_primary_mole_fraction=0.20, intake_temperature_K=300.0,
            intake_pressure_bar=1.5, equivalence_ratio=1.1,
            wall_mode="fixed", wall_temperature_K=550.0,
            effective_h_W_m2K=300.0, blowby_mode="orifice",
            blowby_effective_area_mm2=0.004,
            blowby_discharge_coefficient=1.0, step_deg=1.0,
        )
        rows, summary = simulate(config)
        self.assertGreater(summary["max_fuel_consumed_fraction"], 0.80)
        self.assertGreater(summary["peak_pressure_bar"], 80.0)
        self.assertIsNotNone(summary["CA10_deg_atdc"])
        self.assertIsNotNone(summary["CA50_deg_atdc"])
        self.assertIsNotNone(summary["CA90_deg_atdc"])
        self.assertGreater(summary["max_pressure_rise_bar_per_deg"], 0.0)
        self.assertIn("X_CO", rows[0])
        self.assertIn("end_X_CO", summary)
        self.assertIn("max_X_CH2O", summary)
        self.assertIn("max_fuelConsumed_CH3OCH3_fraction", summary)
        self.assertIn("max_fuelConsumed_CH4_fraction", summary)
        self.assertTrue(summary["warnings"])

    def test_zhao_parent_profile_and_deprecated_alias_are_explicit(self):
        parent = BUILTIN_FUELS["dme_zhao_full"]
        self.assertIn("pressure-rate-selection-open", parent.validation_status)
        self.assertEqual(parent.citation_doi, "10.1002/kin.20285")
        self.assertTrue(Path(parent.mechanism).is_file())
        old = BUILTIN_FUELS["dme_luo_sk39"]
        new = BUILTIN_FUELS["dme_zhao_sk39"]
        self.assertEqual(old.mechanism, new.mechanism)
        self.assertIn("deprecated-alias", old.validation_status)

    def test_bundled_llnl_dme_profile_loads(self):
        import cantera as ct

        profile = BUILTIN_FUELS["dme_llnl_2004"]
        mechanism = Path(profile.mechanism)
        self.assertTrue(mechanism.is_file())
        gas = ct.Solution(str(mechanism), profile.phase)
        self.assertEqual(gas.n_species, 79)
        self.assertEqual(gas.n_reactions, 660)
        self.assertIn("ch3och3", gas.species_names)

    def test_mechanical_screen_reports_loads_not_a_pass_fail_limit(self):
        result = mechanical_metrics(
            peak_pressure_bar=80.0, peak_temperature_K=1191.0,
            max_pressure_rise_bar_per_deg=6.23, peak_pressure_deg_atdc=0.0,
        )
        self.assertAlmostEqual(result["peak_net_gas_force_N"], 448.286, places=3)
        self.assertGreater(result["thick_wall_inner_hoop_stress_MPa"], 17.0)
        self.assertGreater(result["pressure_rise_bar_per_ms"], 40.0)
        self.assertIn("Add inertia", result["mechanical_note"])

    def test_boost_screen_counts_compressor_electrical_power(self):
        result = boost_metrics(
            initial_trapped_mass_mg_per_cylinder=1.2,
            intake_pressure_bar=2.3, intake_temperature_K=300.0, rpm=1200.0,
        )
        self.assertGreater(result["estimated_actual_compressor_outlet_K"], 300.0)
        self.assertGreater(result["estimated_compressor_electrical_power_W"], 0.0)
        self.assertGreater(result["estimated_aftercooler_heat_rejection_W"], 0.0)

    def test_two_zone_collapses_to_single_zone_when_adiabatic(self):
        # This is a fine-step equivalence regression, not a coarse production
        # diagnostic.  The preflight showed that the 2-degree fixture was
        # under-resolved while 0.125 degrees with Cantera's explicit CVODE
        # tolerances collapses to the single-zone result.
        config = RigConfig(
            fuel_profile="methane", intake_temperature_K=300.0,
            intake_pressure_bar=1.2, equivalence_ratio=0.4,
            wall_mode="adiabatic", blowby_mode="off", step_deg=0.125,
            bore_mm=8.5, stroke_mm=7.0, compression_ratio=7.0, rpm=1200.0,
        )
        _, single = simulate(config)
        _, two = simulate_two_zone(
            config,
            TwoZoneOptions(integrator_rtol=1.0e-9, integrator_atol=1.0e-15),
        )
        self.assertAlmostEqual(
            two["peak_pressure_bar"], single["peak_pressure_bar"], delta=0.005
        )
        self.assertAlmostEqual(
            two["peak_temperature_K"], single["peak_temperature_K"], delta=0.05
        )
        self.assertLess(two["max_interzone_pressure_difference_bar"], 1e-6)

    def test_two_zone_reacting_case_closes_mass_and_volume(self):
        config = RigConfig(
            fuel_profile="dme_luo_sk39", fuel_blend_partner="CH4",
            fuel_primary_mole_fraction=0.25, equivalence_ratio=0.40,
            intake_pressure_bar=2.3, intake_temperature_K=300.0,
            wall_mode="fixed", wall_temperature_K=560.0,
            effective_h_W_m2K=300.0, blowby_mode="annular",
            annular_radial_clearance_um=3.0,
            annular_skirt_length_mm=8.0, step_deg=0.5,
            bore_mm=8.5, stroke_mm=7.0, compression_ratio=7.0, rpm=1200.0,
        )
        _, summary = simulate_two_zone(config, TwoZoneOptions())
        self.assertLess(abs(summary["mass_balance_residual_mg"]), 1e-3)
        self.assertLess(abs(summary["CH3OCH3_mass_balance_residual_mg"]), 1e-3)
        self.assertLess(abs(summary["CH4_mass_balance_residual_mg"]), 1e-3)
        self.assertLess(summary["max_volume_closure_error_mm3"], 0.5)
        self.assertLess(summary["max_interzone_pressure_difference_bar"], 0.1)
        self.assertGreater(
            abs(summary["peak_core_temperature_K"] - summary["peak_boundary_temperature_K"]),
            20.0,
        )

    def test_two_zone_diffusion_strain_mixing_and_orifice_leakage(self):
        config = RigConfig(
            fuel_profile="dme_zhao_sk39", fuel_blend_partner="CH4",
            fuel_primary_mole_fraction=0.25, equivalence_ratio=0.40,
            intake_pressure_bar=1.5, intake_temperature_K=300.0,
            wall_mode="fixed", wall_temperature_K=560.0,
            effective_h_W_m2K=300.0, blowby_mode="orifice",
            blowby_effective_area_mm2=0.002, step_deg=1.0,
            bore_mm=8.5, stroke_mm=7.0, compression_ratio=7.0, rpm=1200.0,
        )
        options = TwoZoneOptions(
            mixing_model="diffusion-strain", mixing_length_mm=1.0,
            molecular_diffusivity_m2_s=3e-6, piston_strain_coefficient=1.0,
        )
        _, summary = simulate_two_zone(config, options)
        self.assertEqual(summary["mixing_model"], "diffusion-strain")
        self.assertLess(
            summary["mixing_time_min_observed_ms"],
            summary["mixing_time_max_observed_ms"],
        )
        self.assertGreater(summary["blowby_mass_out_mg"], 0.0)
        self.assertLess(abs(summary["mass_balance_residual_mg"]), 1e-3)

    def test_repeated_wall_cycles_preserve_fractional_temperature(self):
        base = RigConfig(
            ignition_mode="off", wall_mode="finite", wall_temperature_K=550,
            effective_h_W_m2K=200.0, wall_mass_g=2.0, wall_cp_J_kgK=850.0,
            wall_ambient_conductance_W_K=0.02, thermal_cycles=3,
            thermal_min_cycles=3, thermal_convergence_tolerance_K=1e-9,
            step_deg=2.0,
        )
        patched = apply_config_patch(base, {"wall_temperature_K": 550.375})
        self.assertAlmostEqual(patched.wall_temperature_K, 550.375)
        _, summary = simulate(base)
        history = summary["thermal_cycle_history"]
        self.assertEqual(len(history), 3)
        self.assertAlmostEqual(history[1]["wall_start_K"], history[0]["wall_next_cycle_K"])
        self.assertNotEqual(history[1]["wall_start_K"], round(history[1]["wall_start_K"]))

    def test_cantera_blowby_reduces_tdc_mass_and_closes_balance(self):
        sealed = RigConfig(step_deg=2.0, wall_mode="adiabatic", blowby_mode="off")
        leaking = RigConfig(step_deg=2.0, wall_mode="adiabatic", blowby_mode="orifice")
        _, sealed_summary = simulate(sealed)
        _, leaking_summary = simulate(leaking)
        self.assertAlmostEqual(sealed_summary["mass_retained_TDC_fraction"], 1.0, places=8)
        self.assertLess(leaking_summary["mass_retained_TDC_fraction"], 0.9)
        self.assertLess(leaking_summary["P_at_TDC_bar"], sealed_summary["P_at_TDC_bar"])
        self.assertLess(abs(leaking_summary["mass_balance_residual_mg"]), 1e-4)
        self.assertTrue(math.isfinite(leaking_summary["imep_bar"]))

    def test_standard_library_blowby_screen_mass_balance(self):
        result = run_blowby_screen(step_deg=0.25, effective_h_W_m2K=0.0)
        self.assertLess(result["tdc_mass_retained_fraction"], 1.0)
        self.assertLess(abs(result["mass_balance_residual_mg"]), 1e-9)

    def test_phase_map_expands_to_3200_cases(self):
        self.assertEqual(len(load_sweep("phase_map.json")), 3200)


if __name__ == "__main__":
    unittest.main()
