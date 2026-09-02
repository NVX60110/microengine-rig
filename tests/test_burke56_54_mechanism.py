import unittest

import cantera as ct


class BurkeMech5654SmokeTests(unittest.TestCase):
    def test_required_species_and_transport_load(self):
        gas = ct.Solution("mechanisms/burke_mech_56_54.yaml")
        self.assertEqual((gas.n_species, gas.n_reactions), (113, 710))
        required = {"ch4", "ch3och3", "o2", "n2", "co2", "oh", "ho2", "h2o2"}
        self.assertTrue(required.issubset(gas.species_names))
        self.assertEqual(gas.transport_model, "mixture-averaged")
        gas.TPX = 1000.0, 20.0 * ct.one_atm, {
            "ch4": 0.08,
            "ch3och3": 0.02,
            "o2": 0.21,
            "n2": 0.79,
        }
        self.assertGreater(gas.density, 0.0)
        self.assertGreater(gas.viscosity, 0.0)


if __name__ == "__main__":
    unittest.main()
