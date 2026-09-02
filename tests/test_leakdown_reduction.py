import csv
import tempfile
import unittest
from pathlib import Path

from physics.annulus import annulus_mdot
from scripts.reduce_leakdown_experiment import fit_h3, load_profiles, reduce_row, required_schema_fields, validate_input_header


class LeakdownReductionTests(unittest.TestCase):
    def setUp(self):
        self.profiles = load_profiles()

    @staticmethod
    def row(*, record_id="r1", mode="static_direct", clearance_um=4.0, mass_flow=None):
        bore = 12.5
        piston = bore - 2.0 * clearance_um / 1000.0
        row = {
            "record_id": record_id,
            "run_id": "synthetic-run",
            "reference_cylinder_id": "synthetic-12p5",
            "timestamp_utc": "2026-09-02T00:00:00Z",
            "mode": mode,
            "repeat_number": "1",
            "stabilization_criterion": "synthetic fixture state held 30 s",
            "bore_diameter_cold_mm": str(bore),
            "piston_diameter_cold_mm": f"{piston:.12f}",
            "stroke_mm": "12.0",
            "cold_radial_clearance_um": str(clearance_um),
            "measurement_axial_position_mm": "2.0",
            "thrust_orientation": "neutral",
            "bore_roundness_um": "0.2",
            "bore_taper_um_per_mm": "0.0",
            "piston_material": "steel_4140",
            "liner_material": "steel_4140",
            "lubricant": "synthetic-test-oil",
            "lubricant_condition": "synthetic-wet-constant",
            "piston_temperature_K": "293.15",
            "liner_temperature_K": "293.15",
            "chamber_gas_temperature_K": "293.15",
            "upstream_pressure_bar_abs": "4.0",
            "downstream_pressure_bar_abs": "1.0",
            "ambient_pressure_bar_abs": "1.0",
            "mass_flow_kg_s": "" if mass_flow is None else f"{mass_flow:.16g}",
            "volume_flow_L_min": "",
            "flow_meter_reference_pressure_bar_abs": "",
            "flow_meter_reference_temperature_K": "",
            "gas": "air",
            "gas_constant_J_kgK": "287.0",
            "gamma": "1.35",
            "viscosity_Pa_s": "1.816e-5",
            "axial_flow_length_mm": "8.0",
            "eccentricity": "0.0",
            "piston_temperature_uncertainty_K": "2.0",
            "liner_temperature_uncertainty_K": "2.0",
            "bore_diameter_uncertainty_mm": "0.0005",
            "piston_diameter_uncertainty_mm": "0.0005",
            "upstream_pressure_uncertainty_bar": "0.01",
            "downstream_pressure_uncertainty_bar": "0.01",
            "mass_flow_uncertainty_kg_s": "1e-10" if mass_flow is not None else "",
            "volume_flow_uncertainty_L_min": "",
            "viscosity_uncertainty_fraction": "0.02",
            "source_url": "synthetic://test-only",
            "notes": "Synthetic test row; never accepted as leakage evidence.",
        }
        return row

    def test_local_hot_clearance_and_annulus_ratio(self):
        expected = annulus_mdot(12.5, 4.0, 8.0, 4.0, 1.0, T=293.15, mu=1.816e-5, eccentricity=0.0)
        reduced = reduce_row(self.row(mass_flow=expected), self.profiles, index=0, mc_samples=100, seed=7)
        self.assertEqual(reduced["status"], "valid")
        self.assertAlmostEqual(reduced["hot_radial_clearance_um"], 4.0, places=6)
        self.assertAlmostEqual(reduced["measured_to_annulus_flow_ratio"], 1.0, places=6)
        self.assertGreater(reduced["uncertainty_successful_samples"], 0)
        self.assertIsNotNone(reduced["uncertainty_measured_cda_p50_mm2"])
        self.assertTrue(reduced["uncertainty"]["sensitivity_ranking"])

    def test_dynamic_flow_is_not_inverted_to_cda(self):
        reduced = reduce_row(self.row(mode="dynamic_blowby", mass_flow=1e-8), self.profiles, index=0, mc_samples=0, seed=7)
        self.assertEqual(reduced["status"], "valid")
        self.assertEqual(reduced["model_status"], "dynamic_not_inverted")
        self.assertIsNone(reduced["measured_effective_cda_mm2"])
        self.assertIsNone(reduced["measured_to_annulus_flow_ratio"])

    def test_nonpositive_pressure_delta_is_explicit(self):
        row = self.row(mass_flow=1e-8)
        row["upstream_pressure_bar_abs"] = "1.0"
        row["downstream_pressure_bar_abs"] = "1.0"
        reduced = reduce_row(row, self.profiles, index=0, mc_samples=0, seed=7)
        self.assertEqual(reduced["model_status"], "nonpositive_pressure_delta")
        self.assertIsNone(reduced["annulus_model_mass_flow_kg_s"])

    def test_nitrogen_uses_its_specific_gas_constant(self):
        row = self.row(mass_flow=None)
        row["gas"] = "nitrogen"
        row["gas_constant_J_kgK"] = "296.8"
        row["mass_flow_kg_s"] = ""
        row["volume_flow_L_min"] = "0.0"
        row["flow_meter_reference_pressure_bar_abs"] = "1.0"
        row["flow_meter_reference_temperature_K"] = "293.15"
        reduced = reduce_row(row, self.profiles, index=0, mc_samples=0, seed=7)
        expected = annulus_mdot(12.5, 4.0, 8.0, 4.0, 1.0, T=293.15, mu=1.816e-5, gas_constant=296.8)
        self.assertAlmostEqual(reduced["annulus_model_mass_flow_kg_s"], expected, places=14)

    def test_h3_fit_recovers_known_exponent(self):
        rows = []
        for index, clearance in enumerate((2.0, 3.0, 4.0, 5.0)):
            mdot = annulus_mdot(12.5, clearance, 8.0, 4.0, 1.0, T=293.15, mu=1.816e-5, eccentricity=0.0)
            rows.append(reduce_row(self.row(record_id=f"r{index}", clearance_um=clearance, mass_flow=mdot), self.profiles, index=index, mc_samples=0, seed=7))
        fits = fit_h3(rows)
        self.assertEqual(len(fits), 1)
        self.assertAlmostEqual(fits[0]["clearance_exponent"], 3.0, places=10)
        self.assertLess(fits[0]["ci95_low"], 3.0)
        self.assertGreater(fits[0]["ci95_high"], 3.0)

    def test_h3_does_not_mix_pressure_states(self):
        rows = []
        for index, pressure in enumerate((3.0, 4.0, 5.0)):
            row = self.row(record_id=f"p{index}", clearance_um=2.0 + index, mass_flow=1e-8)
            row["upstream_pressure_bar_abs"] = str(pressure)
            rows.append(reduce_row(row, self.profiles, index=index, mc_samples=0, seed=7))
        self.assertEqual(fit_h3(rows), [])

    def test_synthetic_rows_stay_out_of_canonical_records(self):
        # The CLI is intentionally not pointed at records.csv; this test also
        # proves synthetic inputs can be written only to a temporary file.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.csv"
            fields = list(self.row().keys())
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(self.row(mass_flow=1e-8))
            self.assertTrue(path.exists())
        self.assertTrue((Path("data/leakage") / "records.csv").exists())

    def test_schema_rejects_missing_required_channel(self):
        with self.assertRaises(ValueError):
            validate_input_header(sorted(required_schema_fields() - {"ambient_pressure_bar_abs"}))


if __name__ == "__main__":
    unittest.main()
