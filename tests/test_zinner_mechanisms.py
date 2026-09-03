from __future__ import annotations

import unittest

from scripts.validate_zinner_mechanisms import MECHANISMS, _state, load_rows


class ZinnerMechanismValidationTests(unittest.TestCase):
    def test_source_row_count_and_state_basis(self):
        rows = load_rows()
        self.assertEqual(len(rows), 167)
        self.assertGreater(_state(rows[0], "adjusted")[0], 0)
        self.assertGreater(_state(rows[0], "original")[1], 0)

    def test_declared_mechanisms_are_repo_relative(self):
        self.assertEqual(set(MECHANISMS), {"zhao_sk39", "zhao_full", "llnl79", "burke56_54"})
        self.assertTrue(all(path.startswith("mechanisms/") for path in MECHANISMS.values()))


if __name__ == "__main__":
    unittest.main()
