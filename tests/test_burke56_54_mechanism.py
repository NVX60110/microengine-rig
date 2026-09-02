import hashlib
import subprocess
import unittest
from pathlib import Path

import cantera as ct

from burke2015_gate import _map_composition


ROOT = Path(__file__).resolve().parents[1]
RAW_FILES = {
    "data/burke2015/mech_56_54/56.54_c3_chem.dat.txt":
        "C18CEFE98BDBEF7568DAA50B72C4A3871653FFABCA2E371834A151C61FD8BD89",
    "data/burke2015/mech_56_54/56.54_therm.dat.txt":
        "E4E4866D21CB80C1EE636C3829BA2B48DD7F4F9E899676E43FDC1030144FA3DD",
    "data/burke2015/mech_56_54/56.54_tran.dat.txt":
        "E9412904407B917CC17EA2B71FA87AA038AAC1DEA42F6323C21483CE09DE2D1B",
}


class BurkeMech5654SmokeTests(unittest.TestCase):
    def test_required_species_and_transport_load(self):
        gas = ct.Solution("mechanisms/burke_mech_56_54.yaml")
        self.assertEqual((gas.n_species, gas.n_reactions), (113, 710))
        required = {
            "CH4": "ch4",
            "CH3OCH3": "ch3och3",
            "O2": "o2",
            "N2": "n2",
            "CO2": "co2",
            "OH": "oh",
            "HO2": "ho2",
            "H2O2": "h2o2",
        }
        self.assertTrue(all(name in gas.species_names for name in required.values()))
        self.assertEqual(gas.transport_model, "mixture-averaged")
        gas.TPX = 1000.0, 20.0 * ct.one_atm, {
            "ch4": 0.08,
            "ch3och3": 0.02,
            "o2": 0.21,
            "n2": 0.79,
        }
        self.assertGreater(gas.density, 0.0)
        self.assertGreater(gas.viscosity, 0.0)

    def test_blended_schema_and_dme_alias_map_to_lowercase_phase(self):
        gas = ct.Solution("mechanisms/burke_mech_56_54.yaml")
        aliases = {
            "DME": "CH3OCH3",
            "CH3OCH3": "ch3och3",
            "CH4": "ch4",
            "O2": "o2",
            "N2": "n2",
        }
        mapped = _map_composition(
            {"CH4": 0.08, "DME": 0.02, "O2": 0.21, "N2": 0.79},
            gas,
            aliases,
        )
        self.assertEqual(mapped["ch3och3"], 0.02)
        self.assertEqual(mapped["ch4"], 0.08)
        self.assertEqual(set(mapped), {"ch4", "ch3och3", "o2", "n2"})

    def test_raw_hashes_match_lf_normalized_committed_bytes(self):
        for relative, expected in RAW_FILES.items():
            path = ROOT / relative
            working = path.read_bytes().replace(b"\r\n", b"\n")
            committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"])
            self.assertEqual(working, committed, relative)
            self.assertEqual(hashlib.sha256(committed).hexdigest().upper(), expected)


if __name__ == "__main__":
    unittest.main()
